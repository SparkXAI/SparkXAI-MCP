#!/usr/bin/env python3
"""
sqp_plan.py - plan mode: one category, one goal, one budget answer -> a confirm-first plan.

Never writes. It reads SQP rows (through sqp_rows.py) plus the read tools' JSON, applies the
plan rules in references/plan-mode.md IN CODE, and emits rows whose ids and fields are ready for
the owning write skill's route. Only rows the user confirms are executed, by that skill.

Inputs (each a JSON file: a whole tool response, its `data`, or a bare row list)
  --sqp FILE ...        get_market_search_perf rows (marketAsinQuery for the category's ASINs,
                        optionally marketSearchQuery for the same searches) or SQP exports.
                        Omit (or --store-type vendor) for the ads-only plan.
  --category NAME       the BSR category (asinBsrCategoryName / parentAsinBsrCategoryName)
  --asin-meta           get_entity_metadata entity=asin rows: asin, parentAsin, asinBsrCategoryName,
                        parentAsinBsrCategoryName, asinPrice, sku, asinTitle
  --target-perf         get_ads_perf factEntity=target rows (keywords AND targets) for the
                        category's campaigns: target.targetId_ (Amazon), target.targetText_,
                        target.targetMatchType_, target.targetBid_, campaign / ad group ids,
                        Clicks, Spend, Sales, Conversions
  --keyword-meta        get_entity_metadata entity=keyword rows (keywordId, amazonKeywordId, adGroupId,
                        campaignId, campaignType, matchType, keywordBid, keywordState, profileId)
  --target-meta         get_entity_metadata entity=target rows (targetId, amazonTargetId, targetMatchType,
                        targetBid, targetState, campaignId, adGroupId, campaignType, profileId)
  --campaign-meta       get_entity_metadata entity=campaign rows with budgetUsage (pass
                        budgetUsageDateStart / End): campaignId, amazonCampaignId, campaignName,
                        campaignState, campaignType, aiGroupId, dailyBudget, budgetUsage.outOfBudgetMinutes
  --campaign-perf       get_ads_perf factEntity=campaign rows (Amazon campaign id, Clicks, Spend, Sales, Conversions)
  --ai-groups           get_entity_metadata entity=aiGroup rows (aiGroupId, aiStatus, targetAcos, campaignType)
  --search-terms        get_ads_perf factEntity=searchTerm rows (query_, matchType_, campaignId_, adGroupId_,
                        targetId_, Clicks, Spend, Sales, Conversions)
  --placement-perf      get_ads_perf factEntity=placement rows (campaignId_, placement_, Clicks, Spend, Sales, Conversions)
  --placement-meta      get_entity_metadata entity=placement rows (campaignId, amazonCampaignId, placement,
                        multiplier, writeField, campaignType)
  --changes             get_operation_log rows for the last 14 days (one call per entity type)
  --asin-perf           optional get_ads_perf factEntity=asin child rows (asin, Spend, Sales) for the pack lead

Answers from Step 1: --goal grow|efficiency|both, --budget same|+10%|-20%|+2000|-1500,
--acos-goal 25 (percent), --brand-terms, --competitor-terms, --leave-alone, --test-budget.
Calendar: --event "Black Friday:2026-11-27:2026-11-30" (repeatable), --today YYYY-MM-DD.

Outputs: <out>/plan.json and plan_en.md / plan_zh.md. Stdlib only.
"""
import argparse, datetime as dt, json, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqp_rows  # noqa: E402  (the only module that names SQP columns)

# ------------------------------------------------------------------ plan rules (references/plan-mode.md)
EVIDENCE_CLICKS = 20          # ad clicks on the keyword / target / campaign in the window
SQP_CLICKS = 20               # store clicks on the search before SQP judges it
RAISE_MIN_CVR_INDEX = 1.0     # store converts >= 1.0x market on the search
SHARE_CAP = 0.10              # purchase share below 10% = room
SQP_DRIVEN = ("bid_raise", "placement_top", "keyword_create", "test_campaign")
LISTING_PATH_CVR_INDEX = 0.80 # below 0.80x market: no raise, listing / page path
RAISE_STEP = 10               # +10% per step
CUT_LINE, CUT_STEP = 1.2, 15  # ACOS > goal x 1.2 -> -15%
DEEP_LINE, DEEP_STEP = 1.6, 20  # ACOS > goal x 1.6 -> -20% (max step down)
BID_FLOOR = 0.10
BUDGET_RAISE_STEP, BUDGET_CUT_LINE, BUDGET_CUT_STEP = 20, 1.5, 20
TOS_STEP, TOS_MAX = 10, 900
TOS_CVR_LIFT, TOS_SPEND_SHARE = 1.1, 0.5
HOLD_DAYS = 14                # one step per object per 2 SQP weeks
PROMO_LEAD_DAYS = 7           # from 7 days before a retail event to its end: plan only
TYPO_STORE_X, TYPO_OWN_X = 5, 3
WON_SHARE, WON_CVR = 0.20, 1.0
TEST_CLICKS_PER_DAY = 20
AUTO_TARGET_TYPES = {"queryhighrelmatches", "querybroadrelmatches", "asinsubstituterelated", "asinaccessoryrelated"}
KEYWORD_MATCH = {"exact", "phrase", "broad"}
KEYWORD_SOURCES = {"broad", "phrase", "close-match", "loose-match"}   # never harvest from product targets


# ------------------------------------------------------------------ small helpers
def load_json(path):
    if not path:
        return []
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    if isinstance(obj, dict):
        d = obj.get("data") if isinstance(obj.get("data"), dict) else obj
        return d.get("rows") or d.get("list") or []
    return obj


def nk(k):
    """Normalise a field name: 'target.targetId_' / 'targetId_' / 'targetId' -> 'targetid'."""
    return str(k).split(".")[-1].rstrip("_").lower()


def row(r):
    """Row with normalised keys (nested budgetUsage flattened)."""
    out = {}
    for k, v in r.items():
        if isinstance(v, dict) and nk(k) == "budgetusage":
            for k2, v2 in v.items():
                out[nk(k2)] = v2
        out.setdefault(nk(k), v)
    return out


def f(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def acos_of(spend, sales):
    if sales:
        return spend / sales * 100
    return math.inf if spend else None


def terms(spec):
    if not spec:
        return []
    if spec.startswith("@"):
        with open(spec[1:], encoding="utf-8") as fh:
            return [l.split("#")[0].strip().lower() for l in fh if l.split("#")[0].strip()]
    return [t.strip().lower() for t in spec.split(",") if t.strip()]


def has_term(text, ts):
    t = " " + sqp_rows.norm_query(text) + " "
    return any((" " + x + " ") in t or x.replace(" ", "") in t.replace(" ", "") for x in ts if x)


def parse_budget(spec, spend):
    s = (spec or "same").strip().lower()
    if s in ("same", "keep", "0"):
        return 0.0
    if s.endswith("%"):
        return spend * float(s[:-1]) / 100
    return float(s)


def parse_events(specs):
    out = []
    for e in specs or []:
        name, start, end = e.rsplit(":", 2)
        out.append((name, dt.date.fromisoformat(start), dt.date.fromisoformat(end)))
    return out


def r2(x):
    return None if x is None else round(x, 2)


# ------------------------------------------------------------------ SQP side
def category_asins(asin_meta, category):
    """ASINs whose BSR category (child or parent field) equals the category, case-insensitive."""
    cat = (category or "").strip().lower()
    out = set()
    for m in asin_meta:
        names = {str(m.get("asinbsrcategoryname") or "").strip().lower(),
                 str(m.get("parentasinbsrcategoryname") or "").strip().lower()}
        if cat and cat in names:
            out |= {x for x in (m.get("asin"), m.get("parentasin")) if x}
    return out


def search_view(sqp_paths, cat_asins, brand_ts, comp_ts, head_volume):
    """Per category search: window counts (market once per search and week), rates, the product
    carrying it. Returns (searches, notes, has_asin_rows)."""
    rows, infos = sqp_rows.load(sqp_paths)
    notes = sqp_rows.coverage_notes(infos)
    truncated = any(i.get("truncated") for i in infos)
    asin_rows = [r for r in rows if r["asin"] and r["source_kind"] in sqp_rows.ASIN_KINDS]
    split = True
    if asin_rows and cat_asins:
        # The category's own metrics come ONLY from its own ASIN rows. Store-level query rows and
        # other categories' ASIN rows on a shared search would mix another category's conversion in.
        rows = [r for r in asin_rows if r["asin"] in cat_asins]
        notes.append(f"Category scope: {len({sqp_rows.norm_query(r['query']) for r in rows})} searches where the "
                     f"category's ASINs appear ({len({r['asin'] for r in rows})} ASINs with SQP rows); store and "
                     "share figures use only those ASINs' rows.")
    elif not cat_asins:
        # plan mode is always one category: an unmatched category must never fall back to the whole store
        split = False
        rows = []
        notes.append("The category matched no ASIN's BSR category (asinBsrCategoryName / parentAsinBsrCategoryName): "
                     "no category scope, so no SQP-driven raise, new keyword, test or listing task is proposed. "
                     "Check the category name against the ASIN metadata.")
    else:
        split = False
        notes.append("No own-ASIN rows (marketSearchQuery only): store figures cannot be split to this category, "
                     "so no SQP-driven raise, new keyword, test or listing task is proposed. Pull marketAsinQuery "
                     "for the category's ASINs.")
    q = sqp_rows.query_rows(rows)
    by_asin = {}
    for r in sqp_rows.collapse_weeks([r for r in rows if r["asin"] and r["source_kind"] in sqp_rows.ASIN_KINDS]):
        by_asin.setdefault(sqp_rows.norm_query(r["query"]), []).append(r)
    out = {}
    ratios = []
    for r in q:
        k = sqp_rows.norm_query(r["query"])
        rt = sqp_rows.rates(r)
        if rt["impr_share"] and rt["click_share"] and (r["impr_brand"] or 0) >= 500:
            ratios.append(rt["click_share"] / rt["impr_share"])
        prods = sorted(by_asin.get(k, []), key=lambda x: -(x["purch_brand"] or 0))
        top = prods[0] if prods else None
        top_rt = sqp_rows.rates(top) if top else {}
        pi = None
        if top and top["med_click_price_brand"] and (top["med_click_price_mkt"] or r["med_click_price_mkt"]):
            pi = top["med_click_price_brand"] / (top["med_click_price_mkt"] or r["med_click_price_mkt"])
        out[k] = {"search": r["query"], "volume": r["search_volume"], "weeks": len(r.get("weeks") or []),
                  "clicks_brand": r["clicks_brand"], "purch_brand": r["purch_brand"], "purch_mkt": r["purch_mkt"],
                  "impr_share": rt["impr_share"], "click_share": rt["click_share"], "purch_share": rt["purch_share"],
                  "cvr_brand": rt["cvr_brand"], "cvr_index": rt["cvr_index"],
                  "sample_ok": (r["clicks_brand"] or 0) >= SQP_CLICKS and not rt["low_cvr_mkt"],
                  "own_brand": has_term(r["query"], brand_ts), "other_brand": has_term(r["query"], comp_ts),
                  "head": (r["search_volume"] or 0) >= head_volume,
                  "top_asin": top["asin"] if top else None,
                  "top_asin_cvr_index": top_rt.get("cvr_index"), "top_asin_clicks": top["clicks_brand"] if top else None,
                  "top_asin_purchases": top["purch_brand"] if top else None,
                  "price_index": r2(pi), "market_click_price": r["med_click_price_mkt"] or (top or {}).get("med_click_price_mkt"),
                  "products": [{"asin": p["asin"], "clicks": p["clicks_brand"], "purchases": p["purch_brand"],
                                "cvr_index": r2(sqp_rows.rates(p)["cvr_index"])} for p in prods[:5]]}
    med = sorted(ratios)[len(ratios) // 2] if ratios else None
    for s in out.values():
        s["category_split"] = split
        s["pattern"] = funnel_pattern(s, med)
        s["product_role"] = product_role(s)
    return out, notes, truncated, med


def funnel_pattern(s, usual):
    """Shown -> clicked -> bought. 'Clicked more than shown' is judged against the store's usual
    click-share / impression-share ratio (market impressions count every position on the page)."""
    i, c, p = s["impr_share"], s["click_share"], s["purch_share"]
    if not (i and c) or p is None:
        return "no_data"
    base = usual or 1.0
    clicked_more = c / i >= 1.15 * base
    clicked_less = c / i <= base / 1.15
    bought_more = c and p >= 1.15 * c
    bought_less = c and p <= c / 1.15
    if clicked_more and not bought_less:
        return "hidden_winner"
    if clicked_more and bought_less:
        return "click_magnet"
    if bought_more:
        return "strong_closer"
    if bought_less:
        return "loses_buyers"
    if clicked_less:
        return "overlooked"
    return "steady"


PATTERN_TEXT = {
    "hidden_winner": ("Clicked more than shown, keeps the buyers", "Ad manager: show it more (bid / budget within the goal)"),
    "click_magnet": ("Clicked more than shown, bought less", "Category manager: page, price or pack before more bids"),
    "strong_closer": ("Bought more than clicked", "Category manager: main image, title, price shown"),
    "loses_buyers": ("Bought less than clicked", "Category manager: page, price or pack; hold bids"),
    "overlooked": ("Clicked less than shown", "Category manager: main image, price shown, reviews"),
    "steady": ("In line at every step", "Keep"),
    "no_data": ("No store rows on this search", "-"),
}


def product_role(s):
    ci, pi, clicks = s["top_asin_cvr_index"], s["price_index"], s["top_asin_clicks"] or 0
    if not s["top_asin"]:
        return None
    if clicks < 30:
        return "Few clicks - watch"
    if (s["top_asin_purchases"] or 0) == 0:
        return "Clicks but no sales - stop showing this product here"
    if ci is not None and ci >= 0.9:
        if pi and pi >= 1.15:
            return "Wins at a higher price - keep this pack here"
        if pi and pi <= 0.85:
            return "Wins on price - push within the ACOS goal"
        return "Leads this search - keep bids and exact coverage"
    if pi and pi >= 1.3 and ci is not None and ci < 0.8:
        return "Priced above what these shoppers pay - show a closer-priced pack"
    if pi and pi >= 1.15:
        return "Gets the most clicks, converts below the market - share the search with a closer-priced pack"
    return "Gets the most clicks, converts below the market - fix the page before bidding more"


def pack_lead(s, asin_meta, asin_acos, goal):
    """A closer-priced pack from the same family: list price at least $3 closer to what shoppers
    click, and never a pack whose ACOS is above the goal x 1.1."""
    top, mcp = s["top_asin"], s["market_click_price"]
    if not top or not mcp or not s["price_index"] or s["price_index"] < 1.3:
        return None
    meta = {m.get("asin"): m for m in asin_meta if m.get("asin")}
    parent = (meta.get(top) or {}).get("parentasin") or top
    lead_price = mcp * s["price_index"]
    best = None
    for a, m in meta.items():
        if a == top or (m.get("parentasin") or a) != parent or f(m.get("asinprice")) in (None, 0):
            continue
        ac = asin_acos.get(a)
        if ac is not None and ac > goal * 1.1:
            continue
        gap = abs(f(m["asinprice"]) - mcp)
        if gap + 3 <= abs(lead_price - mcp) and (best is None or gap < best[1]):
            best = (a, gap, f(m["asinprice"]))
    return {"show": best[0], "list_price": best[2], "instead_of": top} if best else None


# ------------------------------------------------------------------ the planner
def build(a):
    goal = a.goal
    allow_raise, allow_cut = goal in ("grow", "both"), goal in ("efficiency", "both")
    G = a.acos_goal
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    events = parse_events(a.event)
    promo = next((e for e in events if e[1] - dt.timedelta(days=PROMO_LEAD_DAYS) <= today <= e[2]), None)
    brand_ts, comp_ts = terms(a.brand_terms), terms(a.competitor_terms)
    leave = {x.strip().lower() for x in (a.leave_alone or "").split(",") if x.strip()}
    notes = []

    asin_meta = [row(r) for r in load_json(a.asin_meta)]
    cat_asins = category_asins(asin_meta, a.category)
    ads_only = a.store_type == "vendor" or not a.sqp
    searches, usual, sqp_truncated = {}, None, False
    if ads_only:
        notes.append("Ads-only plan: no market search data (Vendor profile or no SQP rows). Raises, new keywords, "
                     "top of search and tests need market data and are not proposed.")
    else:
        searches, sn, sqp_truncated, usual = search_view(a.sqp, cat_asins, brand_ts, comp_ts, a.head_volume)
        notes += sn
        if sqp_truncated:
            notes.append("SQP data was truncated (meta.truncated): rows driven by SQP (bid raises, top of search, new "
                         "keywords, tests) are listed but not executable until a narrower re-pull succeeds.")

    kmeta = {str(row(r).get("amazonkeywordid")): row(r) for r in load_json(a.keyword_meta)}
    tmeta = {str(row(r).get("amazontargetid")): row(r) for r in load_json(a.target_meta)}
    camps = [row(r) for r in load_json(a.campaign_meta)]
    camp_by_int = {str(c.get("campaignid")): c for c in camps}
    camp_by_amz = {str(c.get("amazoncampaignid")): c for c in camps}
    ai = {str(row(r).get("aigroupid")): row(r) for r in load_json(a.ai_groups)}
    cutoff = today - dt.timedelta(days=HOLD_DAYS)
    changed = {"target": set(), "campaign": set(), "placement": set()}
    for c in (row(r) for r in load_json(a.changes)):
        d = str(c.get("createddate") or "")[:10]
        if d and d < cutoff.isoformat():
            continue
        ent = str(c.get("entity") or "").lower()
        if ent == "target":
            changed["target"].add(str(c.get("amazonentityid")))
        elif ent in ("campaign", "placement"):
            changed[ent].add(str(c.get("amazoncampaignid") or c.get("amazonentityid")))
    asin_acos = {}
    for r in (row(x) for x in load_json(a.asin_perf)):
        if r.get("asin") and f(r.get("sales")):
            asin_acos[r["asin"]] = f(r.get("spend")) / f(r["sales"]) * 100

    perf = [row(r) for r in load_json(a.target_perf)]
    tot_spend = sum(f(r.get("spend")) or 0 for r in perf)
    tot_clicks = sum(f(r.get("clicks")) or 0 for r in perf)
    tot_sales = sum(f(r.get("sales")) or 0 for r in perf)
    tot_orders = sum(f(r.get("conversions")) or 0 for r in perf)
    store_cpc = tot_spend / tot_clicks if tot_clicks else None
    order_value = tot_sales / tot_orders if tot_orders else None

    st_rows = [row(r) for r in load_json(a.search_terms)]
    best_group = {}            # search -> amazon ad group with most ad orders (protected on won searches)
    for r in st_rows:
        k = sqp_rows.norm_query(r.get("query"))
        if k not in best_group or (f(r.get("conversions")) or 0) > best_group[k][1]:
            best_group[k] = (str(r.get("adgroupid")), f(r.get("conversions")) or 0)

    rows, anomalies, held, groups, owner, not_checked = [], [], [], {}, [], []
    check_on = (today + dt.timedelta(days=HOLD_DAYS + 3)).isoformat()

    def camp_hold(c, kind):
        """Return a hold reason for writes on this campaign, or None."""
        if not c:
            return "unresolved: campaign not in get_entity_metadata rows"
        if str(c.get("campaignstate") or "").lower() != "enabled":
            return "campaign paused or archived - skipped"
        gid = str(c.get("aigroupid") or "0")
        if gid not in ("0", "", "None"):
            st = (ai.get(gid) or {}).get("aistatus")
            if st is None or int(st) == 1:
                g = groups.setdefault(gid, {"aiGroupId": gid, "campaigns": [], "aiStatus": st,
                                            "targetAcos": (ai.get(gid) or {}).get("targetacos"),
                                            "campaignType": c.get("campaigntype")})
                if c.get("campaignname") not in g["campaigns"]:
                    g["campaigns"].append(c.get("campaignname"))
                return ("AI managed group with AI on - no keyword, placement or budget write" if st is not None
                        else "AI managed group, AI status unknown - read entity=aiGroup first; no write")
        if leave & {str(c.get("campaignname") or "").lower(), str(c.get("campaignid")), str(c.get("amazoncampaignid"))}:
            return "on the leave-alone list"
        return None

    pid_default = str(a.profile_id or "")

    def pid(*objs):
        for o in objs:
            if o and o.get("profileid"):
                return str(o["profileid"])
        return pid_default

    # ---- keywords and targets: decided on their OWN metrics
    raise_by_campaign = {}
    for p in perf:
        amz = str(p.get("targetid"))
        km, tm = kmeta.get(amz), tmeta.get(amz)
        meta = km or tm
        text = (km or {}).get("keywordtext") or p.get("targettext") or (tm or {}).get("targettext") or ""
        match = str((km or {}).get("matchtype") or p.get("targetmatchtype") or (tm or {}).get("targetmatchtype") or "")
        clicks, spend, sales = f(p.get("clicks")) or 0, f(p.get("spend")) or 0, f(p.get("sales")) or 0
        acos = acos_of(spend, sales)
        cpc = spend / clicks if clicks else None
        c = camp_by_int.get(str((meta or {}).get("campaignid"))) or camp_by_amz.get(str(p.get("campaignid")))
        base = {"object": {"text": text, "matchType": match, "campaign": (c or {}).get("campaignname"),
                           "amazonId": amz},
                "evidence": {"clicks": clicks, "spend": r2(spend), "sales": r2(sales),
                             "acos": None if acos in (None, math.inf) else round(acos, 1), "cpc": r2(cpc),
                             "acos_goal": G}}
        if not meta:
            held.append({**base, "reason": "unresolved: no internal id in keyword / target metadata"})
            continue
        why = camp_hold(c, "bid")
        if why:
            held.append({**base, "reason": why}); continue
        if amz in changed["target"]:
            held.append({**base, "reason": f"changed in the last {HOLD_DAYS} days - one step per 2 SQP weeks"}); continue
        state = str((km or {}).get("keywordstate") or (tm or {}).get("targetstate") or "enabled").lower()
        if state != "enabled":
            held.append({**base, "reason": f"{state} - skipped"}); continue
        is_kw = km is not None or match.lower() in KEYWORD_MATCH
        bid = f((km or {}).get("keywordbid")) if km else f((tm or {}).get("targetbid"))
        if bid is None:
            bid = f(p.get("targetbid"))
        ctype = (meta or {}).get("campaigntype") or (c or {}).get("campaigntype")
        if bid is None:
            held.append({**base, "reason": "current bid unknown - re-read metadata"}); continue

        def bid_row(step, kind, why_text):
            new = max(BID_FLOOR, round(bid * (1 + step / 100), 2))
            item = {"id": int((km or {}).get("keywordid") or (tm or {}).get("targetid")), "profileId": pid(meta, c),
                    "campaignType": ctype, "bid": {"type": "setTo", "previousBid": bid, "amount": new}}
            req = {"profileIds": [int(pid(meta, c))] if pid(meta, c) else [], "data": [item]}
            if is_kw:
                item["matchType"] = (km or {}).get("matchtype") or match
                ent = "keyword"
            else:
                req["targetType"] = "auto" if match.lower() in AUTO_TARGET_TYPES else "product"
                ent = "target"
            return {**base, "kind": kind, "from": bid, "to": new, "pct": step, "why": why_text,
                    "route": {"skill": "sparkx-edit-ads", "tool": "batch_update_ads", "entity": ent,
                              "action": "updateBid", "platform_preview": True},
                    "call": {"entity": ent, "action": "updateBid", "request": req},
                    "campaignId": (c or {}).get("campaignid"), "check_on": check_on}

        # suspected typo: listed apart, default proposal is the normal -20% step
        if store_cpc and cpc and bid >= TYPO_STORE_X * store_cpc and bid >= TYPO_OWN_X * cpc:
            r = bid_row(-DEEP_STEP, "anomaly_bid", f"bid ${bid:.2f} is {bid / store_cpc:.1f}x the category CPC and "
                                                   f"{bid / cpc:.1f}x its own CPC - likely a typo")
            r["alternative"] = {"to": round(max(BID_FLOOR, cpc), 2), "note": "set straight to its actual CPC - only as a "
                                "separate, explicitly confirmed choice (more than one step)"}
            anomalies.append(r)
            continue
        k = sqp_rows.norm_query(text)
        s = searches.get(k) if is_kw else None
        own = has_term(text, brand_ts)
        won_best = bool(s and (s["purch_share"] or 0) >= WON_SHARE and (s["cvr_index"] or 0) >= WON_CVR
                        and best_group.get(k, ("",))[0] in (str(p.get("adgroupid")), ""))
        if allow_cut and clicks >= EVIDENCE_CLICKS and acos is not None and acos > G * CUT_LINE:
            if own:
                held.append({**base, "reason": "own-brand search - never cut"}); continue
            if won_best:
                held.append({**base, "reason": "best ad group on a search the store already wins - never cut"}); continue
            step = DEEP_STEP if acos > G * DEEP_LINE else CUT_STEP
            label = "no sales" if acos == math.inf else f"ACOS {acos:.1f}%"
            rows.append(bid_row(-step, "bid_cut", f"{label} vs goal {G}% on {int(clicks)} clicks (its own metrics)"))
            continue
        if allow_raise and is_kw:
            if ads_only:
                held.append({**base, "reason": "raise needs market data (ads-only plan)"}); continue
            if own:
                held.append({**base, "reason": "own-brand search - protect, no push"}); continue
            if not s:
                continue      # no SQP search with this text: keep
            if not s["category_split"]:
                held.append({**base, "reason": "SQP rows cannot be split to this category - no SQP-driven raise"}); continue
            if not s["sample_ok"]:
                held.append({**base, "reason": f"search has under {SQP_CLICKS} store clicks in SQP - insufficient sample"}); continue
            ci = s["cvr_index"]
            if ci is not None and ci < LISTING_PATH_CVR_INDEX:
                held.append({**base, "reason": f"converts {ci:.2f}x market (< {LISTING_PATH_CVR_INDEX}x) - listing / page path, no raise"}); continue
            if ci is None or ci < RAISE_MIN_CVR_INDEX:
                held.append({**base, "reason": f"converts {ci:.2f}x market - below 1.0x, no raise" if ci else "no conversion data"}); continue
            if (s["purch_share"] or 0) >= SHARE_CAP:
                continue      # already wins 10%+: keep
            if clicks < EVIDENCE_CLICKS or acos is None or acos == math.inf or acos > G:
                held.append({**base, "reason": f"ad evidence short of a raise (needs {EVIDENCE_CLICKS}+ clicks at ACOS <= {G}%)"}); continue
            r = bid_row(RAISE_STEP, "bid_raise", f"converts {ci:.2f}x market, {s['purch_share'] * 100:.1f}% purchase share, "
                                                 f"ACOS {acos:.1f}% <= goal {G}% on {int(clicks)} clicks")
            r["acos_sort"] = acos
            r["est"] = {"spend_change": r2(spend * RAISE_STEP / 100)}
            r["search"] = s["search"]
            rows.append(r)
            raise_by_campaign.setdefault(str((c or {}).get("campaignid")), []).append((r, spend))

    # ---- top of search instead of a keyword raise where the raised keyword carries the campaign
    pperf = [row(r) for r in load_json(a.placement_perf)]
    pmeta = [row(r) for r in load_json(a.placement_meta)]
    cperf = {str(row(r).get("campaignid")): row(r) for r in load_json(a.campaign_perf)}
    if allow_raise and not ads_only:
        for cid, lst in raise_by_campaign.items():
            c = camp_by_int.get(cid)
            if not c or str(c.get("campaigntype")) not in ("sponsoredProducts", "sponsoredBrands"):
                continue
            amz = str(c.get("amazoncampaignid"))
            cp = cperf.get(amz) or {}
            c_spend, c_clicks, c_orders = f(cp.get("spend")) or 0, f(cp.get("clicks")) or 0, f(cp.get("conversions")) or 0
            tos = next((x for x in pperf if str(x.get("campaignid")) == amz and "top" in str(x.get("placement")).lower()), None)
            pm = next((x for x in pmeta if str(x.get("campaignid")) == cid and str(x.get("placement")) == "topOfSearch"), None)
            r, kw_spend = max(lst, key=lambda t: t[1])
            if not (tos and pm and c_spend and c_clicks and kw_spend / c_spend >= TOS_SPEND_SHARE):
                continue
            t_clicks, t_spend, t_sales, t_orders = (f(tos.get(x)) or 0 for x in ("clicks", "spend", "sales", "conversions"))
            t_acos = acos_of(t_spend, t_sales)
            if t_clicks < EVIDENCE_CLICKS or t_acos is None or t_acos > G or not c_orders:
                continue
            if (t_orders / t_clicks) < TOS_CVR_LIFT * (c_orders / c_clicks):
                continue
            if amz in changed["placement"]:
                held.append({"object": {"campaign": c.get("campaignname"), "placement": "top of search"},
                             "reason": f"placement changed in the last {HOLD_DAYS} days"}); continue
            cur = f(pm.get("multiplier"))
            if cur is None:
                held.append({"object": {"campaign": c.get("campaignname"), "placement": "top of search"},
                             "reason": "current top-of-search adjustment unavailable (null) - not written"}); continue
            sb = c.get("campaigntype") == "sponsoredBrands"
            new = min(TOS_MAX, cur + TOS_STEP)
            field = pm.get("writefield") or ("topOfSearchAdjustment" if sb else "topAdjustment")
            item = {"id": int(cid), "profileId": pid(c), "campaignType": c.get("campaigntype"),
                    field: int(round(new)) if sb else new}
            rows.remove(r)
            rows.append({"kind": "placement_top", "object": {"campaign": c.get("campaignname"), "placement": "top of search"},
                         "from": cur, "to": new, "pct": None, "acos_sort": t_acos,
                         "why": f"top of search converts {(t_orders / t_clicks) / (c_orders / c_clicks):.2f}x the campaign at "
                                f"ACOS {t_acos:.1f}%; keyword \"{r['object']['text']}\" carries {kw_spend / c_spend * 100:.0f}% of "
                                "the campaign's spend (replaces its bid raise this round)",
                         "warnings": (["SB: this write also turns the campaign's bidOptimization off (custom bidding)"] if sb else [])
                         + ["if AI placement bid optimization is on for this campaign it overrides manual values"],
                         "evidence": {"clicks": t_clicks, "spend": r2(t_spend), "acos": round(t_acos, 1), "acos_goal": G},
                         "route": {"skill": "sparkx-edit-ads", "tool": "batch_update_ads", "entity": "campaign",
                                   "action": "updatePlacementBid", "platform_preview": True},
                         "call": {"entity": "campaign", "action": "updatePlacementBid",
                                  "request": {"profileIds": [int(pid(c))] if pid(c) else [], "data": [item]}},
                         "est": {"spend_change": r2(t_spend * TOS_STEP / 100)}, "check_on": check_on})

    # ---- searches: new exact keywords, single-keyword tests, owner tasks
    exact_live = {sqp_rows.norm_query(m.get("keywordtext")) for m in kmeta.values()
                  if str(m.get("matchtype")) == "exact" and str(m.get("keywordstate") or "enabled") == "enabled"}
    by_tid = {}
    for m in kmeta.values():
        by_tid[str(m.get("amazonkeywordid"))] = m
    tests = []
    for k, s in sorted(searches.items(), key=lambda t: -(t[1]["purch_mkt"] or 0)):
        if not s["category_split"]:
            continue
        ci = s["cvr_index"]
        if s["sample_ok"] and ci is not None and ci < LISTING_PATH_CVR_INDEX:
            path = ("page and price" if (s["purch_share"] or 0) >= 0.02 else "brand reach or a product made for this search")
            task = {"search": s["search"], "converts_vs_market": r2(ci), "purchase_share": r2(s["purch_share"]),
                    "store_clicks": s["clicks_brand"], "path": path, "product": s["top_asin"],
                    "price_vs_market": s["price_index"], "owner": "Category manager",
                    "note": "no bid raise until conversion vs market recovers"}
            pk = pack_lead(s, asin_meta, asin_acos, G)
            if pk:
                task["pack_lead"] = pk
            owner.append(task)
            continue
        if ads_only or not allow_raise or not s["sample_ok"] or ci is None or ci < RAISE_MIN_CVR_INDEX \
                or (s["purch_share"] or 0) >= SHARE_CAP or s["own_brand"]:
            continue
        if s["other_brand"]:
            held.append({"object": {"search": s["search"]}, "reason": "another brand's name - not added automatically; "
                                                                        "a competitor test needs its own yes"}); continue
        if k in exact_live:
            continue                       # the keyword raise path owns it
        src = [r for r in st_rows if sqp_rows.norm_query(r.get("query")) == k]
        ad_clicks = sum(f(r.get("clicks")) or 0 for r in src)
        kw_src = [r for r in src if str(r.get("matchtype")).lower() in KEYWORD_SOURCES]
        manual = [r for r in kw_src if str(r.get("targetid")) in by_tid]
        if manual:
            o = sum(f(r.get("conversions")) or 0 for r in manual)
            sp = sum(f(r.get("spend")) or 0 for r in manual)
            sa = sum(f(r.get("sales")) or 0 for r in manual)
            cl = sum(f(r.get("clicks")) or 0 for r in manual)
            src_acos = acos_of(sp, sa)
            if o >= 3 and src_acos is not None and src_acos <= G and cl:
                best = max(manual, key=lambda r: f(r.get("conversions")) or 0)
                m = by_tid[str(best.get("targetid"))]
                c = camp_by_int.get(str(m.get("campaignid")))
                why = camp_hold(c, "keyword")
                if why:
                    held.append({"object": {"search": s["search"], "campaign": (c or {}).get("campaignname")},
                                 "reason": f"new exact keyword not added: {why}"}); continue
                bid = round(min(sp / cl, sa / cl * G / 100), 2)
                rows.append({"kind": "keyword_create", "search": s["search"],
                             "object": {"text": s["search"], "matchType": "exact", "campaign": (c or {}).get("campaignname"),
                                        "adGroupId": int(m["adgroupid"])},
                             "from": None, "to": bid, "pct": None, "acos_sort": src_acos,
                             "why": f"converts {ci:.2f}x market, {(s['purch_share'] or 0) * 100:.1f}% share; {int(o)} ad orders at "
                                    f"ACOS {src_acos:.1f}% through {best.get('matchtype')} - no enabled exact keyword yet",
                             "evidence": {"clicks": cl, "spend": r2(sp), "acos": round(src_acos, 1), "acos_goal": G},
                             "route": {"skill": "sparkx-edit-ads", "tool": "batch_update_ads", "entity": "keyword",
                                       "action": "create", "platform_preview": False},
                             "call": {"entity": "keyword", "action": "create", "request": {
                                 "profileIds": [int(pid(m, c))] if pid(m, c) else [],
                                 "data": [{"adGroupId": int(m["adgroupid"]), "profileId": pid(m, c),
                                           "campaignType": m.get("campaigntype"),
                                           "keywords": [{"keywordText": s["search"].strip(), "matchType": "exact",
                                                         "bid": bid, "state": "enabled"}]}]}},
                             "est": {"spend_change": 0.0, "note": "spend moves from the source match type; it is not added"},
                             "check_on": check_on})
                continue
        if ad_clicks < EVIDENCE_CLICKS and (s["head"] or (s["purch_share"] or 0) < 0.02):
            tests.append((s, ad_clicks))

    meta_by_asin = {m.get("asin"): m for m in asin_meta if m.get("asin")}
    for s, ad_clicks in tests[: a.max_tests]:
        cvr = s["cvr_brand"] or 0
        start = (order_value or 0) * cvr * G / 100
        if store_cpc:
            start = min(start, store_cpc)
        start = round(max(start, 0.02), 2)
        budget = a.test_budget or max(1.0, math.ceil(start * TEST_CLICKS_PER_DAY))
        prod = meta_by_asin.get(s["top_asin"]) or {}
        missing = [x for x, v in (("asin", s["top_asin"]), ("sku (Seller)", prod.get("sku"))) if not v]
        if a.store_type == "vendor":
            missing = [x for x in missing if not x.startswith("sku")]
        pa = {"asin": s["top_asin"]}
        if prod.get("sku") and a.store_type != "vendor":
            pa["sku"] = prod["sku"]
        name = f"SQP test - {s['search']}"[:128]
        rows.append({"kind": "test_campaign", "search": s["search"],
                     "object": {"text": s["search"], "matchType": "exact", "campaign": name, "asin": s["top_asin"]},
                     "from": None, "to": start, "pct": None, "acos_sort": math.inf,
                     "why": f"converts {s['cvr_index']:.2f}x market, {(s['purch_share'] or 0) * 100:.1f}% share, "
                            f"{int(ad_clicks)} ad clicks so far" + (" - head term, the most expensive clicks" if s["head"] else ""),
                     "needs": missing,
                     "evidence": {"clicks": ad_clicks, "acos_goal": G},
                     "route": {"skill": "sparkx-create-campaign", "tool": "create_sp_sb_campaign", "platform_preview": False},
                     "call": {"tool": "create_sp_sb_campaign", "arguments": {
                         "profileId": int(pid_default) if pid_default else None,
                         "campaigns": [{"campaignType": "sponsoredProducts", "name": name, "budget": budget,
                                        "startDate": today.strftime("%Y%m%d"), "targetingType": "manual",
                                        "biddingStrategy": "legacyForSales", "state": "paused",
                                        "adGroups": [{"name": f"exact - {s['search']}"[:255], "defaultBid": start,
                                                      "state": "enabled", "productAds": [pa],
                                                      "keywords": [{"keywordText": s["search"].strip(), "matchType": "exact",
                                                                    "bid": start}]}]}]}},
                     "est": {"spend_change": 0.0, "if_started": round(budget * a.window_days, 2),
                             "note": "created paused: no spend until the user starts it"},
                     "check_on": check_on})

    # ---- campaign budgets
    usage_floor = a.capped_minutes_per_day * a.usage_days
    seen = set()
    for c in camps:
        cid, amz = str(c.get("campaignid")), str(c.get("amazoncampaignid"))
        if cid in seen:
            continue
        seen.add(cid)
        cp = cperf.get(amz)
        if not cp:
            continue
        spend, sales, clicks = f(cp.get("spend")) or 0, f(cp.get("sales")) or 0, f(cp.get("clicks")) or 0
        acos = acos_of(spend, sales)
        daily = f(c.get("dailybudget"))
        base = {"object": {"campaign": c.get("campaignname")},
                "evidence": {"clicks": clicks, "spend": r2(spend), "acos": None if acos in (None, math.inf) else round(acos, 1),
                             "acos_goal": G, "outOfBudgetMinutes": c.get("outofbudgetminutes")}}
        why = camp_hold(c, "budget")
        want_raise = allow_raise and acos is not None and acos <= G and clicks >= EVIDENCE_CLICKS
        want_cut = allow_cut and acos is not None and acos > G * BUDGET_CUT_LINE and clicks >= EVIDENCE_CLICKS
        if not (want_raise or want_cut):
            continue
        if why:
            held.append({**base, "reason": why}); continue
        if amz in changed["campaign"]:
            held.append({**base, "reason": f"campaign changed in the last {HOLD_DAYS} days"}); continue
        if daily is None:
            held.append({**base, "reason": "daily budget unknown"}); continue
        oob = f(c.get("outofbudgetminutes"))
        if want_raise:
            if oob is None:
                not_checked.append({**base, "reason": "budget usage not checked (outOfBudgetMinutes is null)"}); continue
            if oob < usage_floor:
                continue
            step, kind = BUDGET_RAISE_STEP, "budget_raise"
            why_t = f"ACOS {acos:.1f}% <= goal {G}% and out of budget ~{oob / 60:.0f} h in {a.usage_days} days (approximate)"
        else:
            step, kind = -BUDGET_CUT_STEP, "budget_cut"
            why_t = ("no sales" if acos == math.inf else f"campaign ACOS {acos:.1f}%") + f" > goal x {BUDGET_CUT_LINE} ({G * BUDGET_CUT_LINE:.1f}%)"
        new = round(daily * (1 + step / 100), 2)
        item = {"campaignId": int(cid), "profileId": pid(c), "campaignType": c.get("campaigntype"),
                "budget": {"type": "setTo", "amount": new}}
        r = {**base, "kind": kind, "from": daily, "to": new, "pct": step, "why": why_t,
             "acos_sort": acos if acos != math.inf else 1e9,
             "route": {"skill": "sparkx-edit-ads", "tool": "batch_update_ads", "entity": "campaign",
                       "action": "updateBudget", "platform_preview": True},
             "call": {"entity": "campaign", "action": "updateBudget",
                      "request": {"profileIds": [int(pid(c))] if pid(c) else [], "data": [item]}},
             "check_on": check_on}
        if kind == "budget_raise":
            r["est"] = {"spend_change": r2(daily * step / 100 * a.window_days)}
        else:
            r["est"] = {"saving": r2(spend * BUDGET_CUT_STEP / 100 * 0.8)}
        rows.append(r)

    # cut savings (estimates, labelled)
    for r in rows:
        if r["kind"] == "bid_cut":
            r["est"] = {"saving": r2((r["evidence"]["spend"] or 0) * abs(r["pct"]) / 100 * 0.6)}

    # ---- fit to the budget answer: cuts first (when allowed), then raises best ACOS first
    cat_spend = sum(f(x.get("spend")) or 0 for x in cperf.values()) or tot_spend
    room = parse_budget(a.budget, cat_spend)
    savings = sum((r.get("est") or {}).get("saving") or 0 for r in rows if r["kind"] in ("bid_cut", "budget_cut"))
    available = room + savings
    raises = sorted([r for r in rows if r["kind"] in ("bid_raise", "budget_raise", "placement_top")],
                    key=lambda r: r.get("acos_sort", 0))
    funded, waiting, used = [], [], 0.0
    for r in raises:
        cost = (r.get("est") or {}).get("spend_change") or 0
        if used + cost <= available + 1e-6:
            funded.append(r); used += cost
        else:
            waiting.append(r)
    rows = [r for r in rows if r not in waiting]
    fit = {"budget_answer": a.budget, "window_days": a.window_days, "category_spend": r2(cat_spend),
           "room": r2(room), "savings_from_cuts": r2(savings), "available": r2(available),
           "raises_cost": r2(used), "net_spend_change": r2(used - savings), "unused_room": r2(max(available - used, 0)),
           "waiting_for_budget": [{"kind": r["kind"], "object": r["object"], "cost": (r.get("est") or {}).get("spend_change")}
                                  for r in waiting]}
    if goal == "grow" and room <= 0:
        fit["note"] = ("Grow makes no cuts, so with the same or a smaller budget nothing pays for raises: pick Both or an "
                       "increase to fund them. New exact keywords (spend moves, not added) and paused tests are still listed.")
    elif room < 0 and savings < -room:
        fit["note"] = f"the cuts save ${savings:,.0f}; the budget answer needs ${-room:,.0f}: deeper cuts are needed - say how far short and offer them"
    elif waiting:
        fit["note"] = (f"{len(waiting)} raise(s) wait for budget: the budget answer plus savings leaves ${available - used:,.0f}, "
                       "less than the next raise costs. Not forced.")
    elif available - used > 1:
        fit["note"] = f"${available - used:,.0f} of the room is not used: nothing else qualifies under the goal. Not forced."

    # ---- order and number the write rows
    order = {"efficiency": ["bid_cut", "budget_cut"], "grow": ["budget_raise", "bid_raise", "placement_top", "keyword_create", "test_campaign"],
             "both": ["bid_cut", "budget_cut", "budget_raise", "bid_raise", "placement_top", "keyword_create", "test_campaign"]}[goal]
    rows = [r for r in rows if r["kind"] in order]
    rows.sort(key=lambda r: (order.index(r["kind"]), r.get("acos_sort", 0) if r["kind"] not in ("bid_cut", "budget_cut")
                             else -((r.get("est") or {}).get("saving") or 0)))
    for i, r in enumerate(rows, 1):
        r["n"] = i
        r.pop("acos_sort", None)
        if sqp_truncated and r["kind"] in SQP_DRIVEN:
            r["needs"] = (r.get("needs") or []) + ["re-pull SQP in smaller batches (the response was truncated)"]
        r["executable"] = promo is None and not r.get("needs")
    for i, r in enumerate(anomalies, 1):
        r["n"] = f"A{i}"
        r["executable"] = promo is None
    if promo:
        notes.append(f"{promo[0]} runs {promo[1]} to {promo[2]}: from {PROMO_LEAD_DAYS} days before it to its end this plan is "
                     "plan only - nothing is written. Promotion changes belong to sparkx-promo-prep / sparkx-promo-monitor.")
    group_rows = []
    for g in groups.values():
        ct = str(g.get("campaignType") or "")
        tool = "edit_sd_ai_managed_group" if ct == "sponsoredDisplay" else "save_sp_sb_ai_managed_group (edit mode)"
        group_rows.append({**g, "suggest": f"review the group's target ACOS ({g.get('targetAcos')}) against the goal {G}%",
                           "route": {"skill": "sparkx-edit-ai-group", "tool": tool},
                           "warning": "changing the group's total budget rescales every enabled campaign in the group"})
    return {"meta": {"category": a.category, "goal": goal, "budget": a.budget, "acos_goal": G, "today": today.isoformat(),
                     "plan_only": bool(promo), "ads_only": ads_only, "store_cpc": r2(store_cpc), "order_value": r2(order_value),
                     "usual_click_vs_impression_share": r2(usual), "notes": notes},
            "rows": rows, "anomalies": anomalies, "held": held, "group_suggestions": group_rows,
            "owner_tasks": owner, "not_checked": not_checked, "budget_fit": fit,
            "searches": sorted(searches.values(), key=lambda s: -(s["purch_mkt"] or 0))}


# ------------------------------------------------------------------ rendering
L = {
 "en": {"title": "Plan - {cat} - goal {goal} - ACOS goal {g}%", "rows": "Changes to confirm",
        "head": "| # | Change | Where | Now -> new | Why | Applied by |",
        "kinds": {"bid_raise": "Raise bid +{p}%", "bid_cut": "Lower bid {p}%", "keyword_create": "Add exact keyword",
                  "placement_top": "Top of search +10 pts", "budget_raise": "Raise daily budget +{p}%",
                  "budget_cut": "Lower daily budget {p}%", "test_campaign": "New test campaign (paused)", "anomaly_bid": "Suspected typo bid: lower {p}%"},
        "preview": "platform preview, then your yes", "nopreview": "no platform preview - applies on submit: restate the row and get a yes first",
        "anomalies": "Anomalies (confirm separately)", "held": "Not written", "groups": "AI managed groups (suggestion only)",
        "owner": "Listing, price and pack (owner tasks - never written)", "fit": "Budget fit",
        "plan_only": "PLAN ONLY - a retail event window is open; nothing will be written.",
        "how": "Reply with the row numbers to run (e.g. \"confirm 1, 3\"), \"run all\" (numbered rows only, not anomalies), "
               "or \"no changes\". Nothing is written before that reply; each row then goes through its write skill "
               "with pre-read, platform preview where the route has one, and read-back."},
 "zh": {"title": "计划 - {cat} - 目标 {goal} - ACOS 目标 {g}%", "rows": "待确认的改动",
        "head": "| # | 改动 | 位置 | 当前 -> 新值 | 依据 | 执行方式 |",
        "kinds": {"bid_raise": "提高出价 +{p}%", "bid_cut": "降低出价 {p}%", "keyword_create": "新增精准关键词",
                  "placement_top": "搜索结果顶部 +10 个百分点", "budget_raise": "日预算 +{p}%",
                  "budget_cut": "日预算 {p}%", "test_campaign": "新建测试活动（暂停状态）", "anomaly_bid": "疑似误填出价：降低 {p}%"},
        "preview": "平台预览后再确认", "nopreview": "无平台预览，提交即生效：先复述该行并取得确认",
        "anomalies": "异常（需单独确认）", "held": "不写入", "groups": "AI 托管组（仅建议）",
        "owner": "Listing、价格与规格（负责人任务，不会写入）", "fit": "预算匹配",
        "plan_only": "仅计划 - 处于大促窗口，不会写入任何改动。",
        "how": "回复要执行的行号（如「确认 1, 3」）、「全部执行」（仅编号行，不含异常）或「暂不调整」。"
               "回复前不会写入；每行由对应的写入 skill 执行：先读取、有预览的路由先预览、执行后回读。"},
}


def cell(x):
    return str("" if x is None else x).replace("|", "/")


def render(plan, lang="en"):
    T = L[lang]
    m = plan["meta"]
    out = [f"## {T['title'].format(cat=m['category'], goal=m['goal'], g=m['acos_goal'])}", ""]
    if m["plan_only"]:
        out += [f"**{T['plan_only']}**", ""]
    for n in m["notes"]:
        out.append(f"- {n}")
    if plan["owner_tasks"] and m["goal"] == "efficiency":
        out += ["", f"### {T['owner']}"] + [f"- \"{t['search']}\": {t['path']} (converts {t['converts_vs_market']}x, "
                                              f"product {t['product']}, price vs market {t['price_vs_market']})" for t in plan["owner_tasks"]]
    out += ["", f"### {T['rows']}", "", T["head"], "|---|---|---|---|---|---|"]

    def line(r):
        k = T["kinds"][r["kind"]].format(p=abs(r["pct"]) if r.get("pct") is not None else "")
        o = r["object"]
        what = f"{k} · \"{o.get('text') or o.get('placement') or ''}\" {o.get('matchType') or ''}".strip()
        ft = f"{'-' if r['from'] is None else r['from']} -> {r['to']}"
        how = T["preview"] if r["route"].get("platform_preview") else T["nopreview"]
        flagx = "" if r.get("executable") else " (not executable)"
        return f"| {r['n']} | {cell(what)} | {cell(o.get('campaign'))} | {ft} | {cell(r['why'])} | {r['route']['skill']}: {how}{flagx} |"

    out += [line(r) for r in plan["rows"]]
    if plan["anomalies"]:
        out += ["", f"### {T['anomalies']}", "", T["head"], "|---|---|---|---|---|---|"] + [line(r) for r in plan["anomalies"]]
    if plan["owner_tasks"] and m["goal"] != "efficiency":
        out += ["", f"### {T['owner']}"] + [f"- \"{t['search']}\": {t['path']} (converts {t['converts_vs_market']}x, "
                                              f"product {t['product']}, price vs market {t['price_vs_market']})" for t in plan["owner_tasks"]]
    if plan["group_suggestions"]:
        out += ["", f"### {T['groups']}"] + [f"- group {g['aiGroupId']} ({', '.join(str(x) for x in g['campaigns'])}): {g['suggest']}; "
                                               f"{g['route']['tool']}. {g['warning']}." for g in plan["group_suggestions"]]
    if plan["held"] or plan["not_checked"]:
        out += ["", f"### {T['held']}"] + [f"- {cell(h['object'].get('text') or h['object'].get('search') or h['object'].get('campaign'))}"
                                             f" ({cell(h['object'].get('campaign'))}): {h['reason']}" for h in plan["held"] + plan["not_checked"]]
    fit = plan["budget_fit"]
    out += ["", f"### {T['fit']}", f"- budget answer {fit['budget_answer']}: room ${fit['room']}, savings ${fit['savings_from_cuts']}, "
                                   f"raises ${fit['raises_cost']}, net ${fit['net_spend_change']}, unused ${fit['unused_room']}"]
    if fit.get("note"):
        out.append(f"- {fit['note']}")
    out += ["", T["how"]]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="SQP Insight plan mode: confirm-first plan for one category.")
    ap.add_argument("--sqp", nargs="*", default=[])
    ap.add_argument("--category", required=True)
    ap.add_argument("--goal", required=True, choices=["grow", "efficiency", "both"])
    ap.add_argument("--budget", default="same", help="same | +10%% | -20%% | +2000 | -1500")
    ap.add_argument("--acos-goal", type=float, required=True, help="ACOS goal in percent, e.g. 25")
    ap.add_argument("--asin-meta"); ap.add_argument("--target-perf"); ap.add_argument("--keyword-meta")
    ap.add_argument("--target-meta"); ap.add_argument("--campaign-meta"); ap.add_argument("--campaign-perf")
    ap.add_argument("--ai-groups"); ap.add_argument("--search-terms"); ap.add_argument("--placement-perf")
    ap.add_argument("--placement-meta"); ap.add_argument("--changes"); ap.add_argument("--asin-perf")
    ap.add_argument("--brand-terms", default=""); ap.add_argument("--competitor-terms", default="")
    ap.add_argument("--leave-alone", default="", help="campaign names or ids, comma list")
    ap.add_argument("--event", action="append", default=[], help='"Name:YYYY-MM-DD:YYYY-MM-DD"')
    ap.add_argument("--today")
    ap.add_argument("--store-type", default="seller", choices=["seller", "vendor"])
    ap.add_argument("--profile-id", default="")
    ap.add_argument("--usage-days", type=int, default=14, help="length of the budget-usage window passed to get_entity_metadata")
    ap.add_argument("--capped-minutes-per-day", type=float, default=60)
    ap.add_argument("--window-days", type=int, default=28)
    ap.add_argument("--head-volume", type=float, default=100000)
    ap.add_argument("--max-tests", type=int, default=3)
    ap.add_argument("--test-budget", type=float)
    ap.add_argument("--out", default="sqp_plan_out")
    a = ap.parse_args(argv)
    plan = build(a)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False, default=lambda o: None)
    for lang in L:
        with open(os.path.join(a.out, f"plan_{lang}.md"), "w", encoding="utf-8") as fh:
            fh.write(render(plan, lang))
    print(json.dumps({"out": a.out, "rows": len(plan["rows"]), "anomalies": len(plan["anomalies"]),
                      "held": len(plan["held"]), "owner_tasks": len(plan["owner_tasks"]),
                      "plan_only": plan["meta"]["plan_only"]}, indent=1))
    return plan


if __name__ == "__main__":
    main()
