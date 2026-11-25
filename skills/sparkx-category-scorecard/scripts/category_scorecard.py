#!/usr/bin/env python3
"""Category scorecard - every category on two axes, one play each, fair peer goals, timing.

  python3 category_scorecard.py --peer peer_leaf.json --peer peer_parents.json --market out/market_by_category.json \
      --spend parent_spend.json --category-map parent_category.json --parent-meta parent_meta.json \
      --stock stock_days.json --ad-type-share camp14.json --acos-goal 25 \
      --event "Black Friday to Cyber Monday|2026-11-27|2026-11-30" --today 2026-11-23 --out out/

Axis 1  Shoppers buy vs market (market_by_category.json): conversion on generic searches (fallback: all relevant).
        Bands: ahead >= 0.95x, close 0.80-0.95x, behind < 0.80x. Play line = 0.80x.
        Coverage < 40% of the category's ad spend -> shown, not used; 40-60% -> used, noted.
Axis 2  Ads vs peers' median (get_peer_benchmark rows, read directly - field names as the tool returns them):
          adProduct sponsoredProducts / sponsoredBrands / sponsoredDisplay -> SP / SB / SD
          goal CONVERSION -> ROAS (higher is better); CONSIDERATION -> CPC (lower is better);
          AWARENESS -> CPM (lower is better). Any other goal value -> row unusable (never defaulted to conversion).
          <metric>, <metric>_p25/_p50/_p75, <metric>_status (AVAILABLE / NO_PEER_BENCHMARK / INCOMPLETE).
          ACOS columns are the tool's own (already derived); they are never re-inverted here.
        Node = the finest level on the category's path (leaf -> root, from categoryMetadata.pathIds / parentCategoryId)
        where the brand's own key metric and the peers' P50 both exist; the level is always named.
        Latest period per brand x category x ad product x goal; periods, goals, levels and brands are never combined.
        Lead row = the first ad type by your spend share that has a usable row; within it SP -> CONVERSION,
        SB -> CONSIDERATION first, SD -> CONVERSION first.
        No usable peer row -> category ACOS vs account ACOS (<= 1.10x = fine), said in the row.
Play    >= 0.80x and at/better than median -> Scale; >= 0.80x and worse -> Fix ad cost;
        < 0.80x and at/better -> Fix listing; < 0.80x and worse -> Fix first.
        Scale with < 30 days of stock on either top product -> Hold (stock); Scale above the ACOS goal -> Keep.
Timing  --event NAME|START|END and --today: from 7 days before the start until the end (in-event included) this skill
        plans only - no budget lowering, no writes; promotions go to sparkx-promo-prep / sparkx-promo-monitor.
Sizing  Orders at stake = own purchases on the searches used x (1 / conversion - 1), over the market weeks. Upper bound.
"""
import argparse, json, os
from collections import defaultdict, Counter
from datetime import date, timedelta

AD = {"sponsoredProducts": "SP", "sponsoredBrands": "SB", "sponsoredDisplay": "SD"}
GOALS = {"CONVERSION": "conversion", "CONSIDERATION": "consideration", "AWARENESS": "awareness"}
METRIC = {"conversion": ("roas", True), "consideration": ("cpc", False), "awareness": ("cpm", False)}
GOAL_ORDER = {"SP": ["conversion"], "SB": ["consideration", "conversion", "awareness"],
              "SD": ["conversion", "consideration", "awareness"]}
POS_ORDER = ["top quarter", "above median", "below median", "bottom quarter"]
NEXT_GOAL = {"Scale": "Grow", "Fix ad cost": "Improve efficiency", "Fix listing": "Both (listing first)",
             "Fix first": "Improve efficiency", "Keep": "Improve efficiency"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rows_of(obj):
    if isinstance(obj, dict) and isinstance(obj.get("data"), (dict, list)):
        obj = obj["data"]
    if isinstance(obj, list):
        return obj
    return obj.get("rows") or []


def fnum(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def pos(v, p25, p50, p75, higher_is_better=True):
    if v is None or p50 is None:
        return None
    if not higher_is_better:  # flip so "top quarter" always means best
        v, p25, p50, p75 = -v, (-p75 if p75 is not None else None), -p50, (-p25 if p25 is not None else None)
    if p75 is not None and v >= p75:
        return "top quarter"
    if v >= p50:
        return "above median"
    if p25 is not None and v < p25:
        return "bottom quarter"
    return "below median"


def cat_id(v):
    if isinstance(v, dict):
        return str(v.get("id") or v.get("name"))
    return str(v) if v is not None else None


def parse_event(spec, today):
    if not spec:
        return None
    n, s, e = spec.split("|")
    s, e = date.fromisoformat(s), date.fromisoformat(e)
    days = (s - today).days
    return {"name": n, "start": s.isoformat(), "end": e.isoformat(), "days_to_start": days,
            "in_progress": days <= 0 <= (e - today).days,
            "plan_only": days <= 7 and today <= e,     # 7 days before the start through the last day
            "reset_from": (e + timedelta(days=1)).isoformat()}


def ad_share(spec):
    if spec and os.path.exists(spec):
        tot = defaultdict(float)
        for r in rows_of(load(spec)):
            t = AD.get(r.get("campaign.campaignType_") or r.get("campaignType"))
            if t:
                tot[t] += fnum(r.get("Spend")) or 0
        s = sum(tot.values()) or 1
        return {k: round(v / s, 3) for k, v in tot.items()}
    return {k: float(v) for k, v in (x.split(":", 1) for x in spec.split(","))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--peer", action="append", default=[], help="get_peer_benchmark response (repeat per call)")
    ap.add_argument("--peer-unavailable", help="the peer call was refused: the missing permission, e.g. MCP_tool_benchmark")
    ap.add_argument("--market-unavailable", help="the market search call was refused: the missing permission, e.g. sqp:read")
    ap.add_argument("--market", help="market_by_category.json; without it (Vendor, no SQP) the play rests on peers and ACOS")
    ap.add_argument("--account", default="seller", choices=["seller", "vendor"])
    ap.add_argument("--spend", required=True, help="[{parent_asin, Spend, Sales}] 14 days")
    ap.add_argument("--category-map", required=True, help="{parent_asin: category id | {id, name, path_ids}}")
    ap.add_argument("--parent-meta", help="{parent_asin: {brand}} - brand from asinBrand / parentAsinBrand")
    ap.add_argument("--brand", help="default brand when a parent has none")
    ap.add_argument("--labels", help="{category id: display name}")
    ap.add_argument("--stock", help="{parent_asin: days of stock (parentAsinDayAvailability30)}")
    ap.add_argument("--ad-type-share", default="SP:0.9,SB:0.08,SD:0.02",
                    help="SP:0.90,SB:0.08,SD:0.02 or a path to get_ads_perf campaign rows (share computed from Spend)")
    ap.add_argument("--event", help="NAME|YYYY-MM-DD|YYYY-MM-DD"); ap.add_argument("--today")
    ap.add_argument("--min-spend", type=float, default=5000, help="14-day ad spend under this: listed, not scored")
    ap.add_argument("--conv-line", type=float, default=0.80); ap.add_argument("--ahead-line", type=float, default=0.95)
    ap.add_argument("--min-coverage", type=float, default=0.6); ap.add_argument("--drop-coverage", type=float, default=0.4)
    ap.add_argument("--acos-slack", type=float, default=1.10); ap.add_argument("--min-stock-days", type=float, default=30)
    ap.add_argument("--acos-goal", type=float, help="the confirmed ACOS goal (percent): Scale needs the category's ACOS at or under it")
    ap.add_argument("--sqp-weeks", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else date.today()

    # ---------- peer rows, as the tool returns them ----------
    idx, parent_of, path_of, names, unusable, periods = {}, {}, {}, {}, [], set()
    bench_brands = set()
    for p in a.peer:
        for r in rows_of(load(p)):
            meta = r.get("categoryMetadata") or {}
            cid = str(r.get("browseCategoryId"))
            if meta.get("parentCategoryId"):
                parent_of.setdefault(cid, str(meta["parentCategoryId"]))
            if meta.get("pathIds"):
                path_of.setdefault(cid, [str(x) for x in meta["pathIds"]])
            names.setdefault(cid, meta.get("categoryNameEn") or meta.get("categoryName") or r.get("browseCategoryPath"))
            brand = str(r.get("benchmarkBrandName") or "").strip().lower()
            bench_brands |= {brand, str(r.get("benchmarkBrandId") or "").strip().lower()}
            ad = AD.get(r.get("adProduct"))
            goal = GOALS.get(str(r.get("goal") or "").strip().upper())
            if not ad or not goal:
                unusable.append({"brand": r.get("benchmarkBrandName"), "category": cid, "adProduct": r.get("adProduct"),
                                 "goal": r.get("goal"), "reason": ("unknown goal" if ad else "unknown adProduct")
                                 + f" '{r.get('goal') if ad else r.get('adProduct')}': row not used"})
                continue
            per = str(r.get("periodStart") or "")
            periods.add(f"{r.get('timeUnit') or ''} {per}".strip())
            for b in {brand, str(r.get("benchmarkBrandId") or "").strip().lower()} - {""}:
                k = (b, cid, ad, goal)
                if k not in idx or per > idx[k][0]:
                    idx[k] = (per, r)

    def chain(leaf, path_hint):
        if path_hint:
            return [str(x) for x in reversed(path_hint)]
        if leaf in path_of:
            return list(reversed(path_of[leaf]))
        out, c = [], leaf
        while c and c not in out and len(out) < 10:
            out.append(c); c = parent_of.get(c)
        return out

    def node(brand, leaf, ad, goal, path_hint):
        m, _ = METRIC[goal]
        seen = []
        for steps, c in enumerate(chain(leaf, path_hint)):
            hit = idx.get((brand, c, ad, goal))
            if not hit:
                continue
            per, r = hit
            seen.append(r.get(f"{m}_status") or "missing")
            if fnum(r.get(m)) is not None and fnum(r.get(f"{m}_p50")) is not None:
                return {"row": r, "level": c, "steps": steps, "period": per}, seen
        return None, seen

    def peer_read(n, goal):
        r = n["row"]; m, hib = METRIC[goal]
        g = lambda k: fnum(r.get(k))
        own, p25, p50, p75 = g(m), g(f"{m}_p25"), g(f"{m}_p50"), g(f"{m}_p75")
        pr = {"goal": goal, "level": n["level"], "level_name": names.get(n["level"]) or n["level"],
              "level_note": None if not n["steps"] else f"no peer range at the product's own category: compared {n['steps']} level(s) up",
              "is_default_node": r.get("isDefaultNode"), "period": n["period"], "currency": r.get("budgetCurrency"),
              "metric": m, "own": own, "p25": p25, "p50": p50, "p75": p75, "status": r.get(f"{m}_status"),
              "position": pos(own, p25, p50, p75, hib), "vs_median": round(own / p50, 2) if own and p50 else None,
              "roas": g("roas"), "roas_p25": g("roas_p25"), "roas_p50": g("roas_p50"), "roas_p75": g("roas_p75"),
              "ctr": g("ctr"), "ctr_p25": g("ctr_p25"), "ctr_p75": g("ctr_p75")}
        pr["roas_position"] = pos(pr["roas"], pr["roas_p25"], pr["roas_p50"], pr["roas_p75"])
        wide = bool(p25 and p75 and p75 >= 2 * p25)
        if goal == "conversion":
            pr["goal_set"] = {"roas_range": [p25, p75], "roas_median": p50,
                              "acos_range": [g("acos_p25"), g("acos_p75")], "acos_median": g("acos_p50"),
                              "own_acos": g("acos"), "wide_spread": wide}
        else:
            pr["goal_set"] = {f"{m}_range": [p25, p75], f"{m}_median": p50, "wide_spread": wide,
                              "ctr_range": [g("ctr_p25"), g("ctr_p75")] if goal == "consideration" else None,
                              "roas_reference": pr["roas_p50"]}
        return pr

    # ---------- own spend by category x brand ----------
    cmap = load(a.category_map)
    pmeta = load(a.parent_meta) if a.parent_meta else {}
    labels = load(a.labels) if a.labels else {}
    stock = load(a.stock) if a.stock else {}
    share = ad_share(a.ad_type_share)
    ad_order = [t for t, _ in sorted(share.items(), key=lambda kv: -kv[1])]
    market = load(a.market) if a.market else None
    opp = (market or {}).get("categories", {})
    brand0 = a.brand or ""
    groups = defaultdict(lambda: {"spend": 0.0, "sales": 0.0, "parents": [], "path": None, "name": None})
    unmapped = 0.0
    spend_rows = rows_of(load(a.spend))
    for r in spend_rows:
        p = r.get("parent_asin") or r.get("asin.parent_asin_") or r.get("parentAsin")
        sp, sa = fnum(r.get("Spend")) or 0, fnum(r.get("Sales")) or 0
        cv = cmap.get(p)
        c = cat_id(cv)
        if not c:
            unmapped += sp; continue
        br = str((pmeta.get(p) or {}).get("brand") or brand0).strip()
        g = groups[(c, br)]
        g["spend"] += sp; g["sales"] += sa; g["parents"].append((sp, p))
        if isinstance(cv, dict):
            g["path"] = g["path"] or cv.get("path_ids"); g["name"] = g["name"] or cv.get("name")
    tot = sum(g["spend"] for g in groups.values()) or 1
    acct_acos = round(tot / (sum(g["sales"] for g in groups.values()) or 1) * 100, 1)
    per_cat = Counter(k[0] for k, g in groups.items() if g["spend"] >= a.min_spend)
    ev = parse_event(a.event, today)
    fmt = lambda iso: (lambda d: d.strftime("%b ") + str(d.day))(date.fromisoformat(iso))

    cards, small = [], []
    for (cat, br), g in sorted(groups.items(), key=lambda kv: -kv[1]["spend"]):
        if g["spend"] < a.min_spend:
            small.append({"category": cat, "ad_spend_14d": round(g["spend"])}); continue
        key = cat if per_cat[cat] == 1 else f"{cat} · {br or 'no brand'}"
        name = labels.get(key) or labels.get(cat) or g["name"] or names.get(cat) or cat
        if per_cat[cat] > 1:
            name = f"{name} · {br or 'no brand'}"
        top = [p for _, p in sorted(g["parents"], reverse=True)[:2]]
        card = {"category": name, "category_key": key, "category_id": cat, "brand": br,
                "ad_spend_14d": round(g["spend"]), "share_of_ad_spend": round(g["spend"] / tot, 3),
                "acos_14d": round(g["spend"] / g["sales"] * 100, 1) if g["sales"] else None, "top_products": top}
        card["acos_vs_account"] = round(card["acos_14d"] / acct_acos, 2) if card["acos_14d"] else None
        sd = [stock[p] for p in top if stock.get(p) is not None]
        card["stock_days_min_top2"] = min(sd) if sd else None
        notes = []

        # axis 1
        o = opp.get(cat) or {}
        conv = o.get("conv_vs_market_generic") if o.get("conv_vs_market_generic") is not None else o.get("conv_vs_market")
        cov = o.get("sqp_coverage_of_ad_spend")
        share = o.get("purchase_share")
        truncated = bool(market and market.get("truncated") and conv is not None)
        if truncated:
            # counts from a truncated pull are lower bounds: not shown, not charted, not counted, not used for the play
            conv = share = None
        card.update({"converts_vs_market": conv, "conversion_basis": o.get("conversion_basis"),
                     "purchase_share": share, "relevant_searches": o.get("relevant_searches"),
                     "market_data_coverage": cov, "market_data_truncated": truncated})
        if a.market_unavailable:
            card["converts_note"] = f"market data not accessible ({a.market_unavailable}) - an access gap, not a finding"
        card["converts_band"] = None if conv is None else ("ahead" if conv >= a.ahead_line else ("close" if conv >= a.conv_line else "behind"))
        usable_conv = conv
        if truncated:
            card["converts_note"] = ("market data was truncated (meta.truncated): conversion vs market is not shown or "
                                     "used until a narrower re-pull succeeds")
        if usable_conv is not None and cov is not None and cov < a.drop_coverage:
            card["converts_note"] = (f"market data covers only {round(cov * 100)}% of this category's ad spend (main products "
                                     "missing from the market search data): shown, not used for the play")
            usable_conv = None
        elif usable_conv is not None and o.get("low_sample"):
            card["converts_note"] = "too few own clicks on the category's searches to compare with the market"
        if per_cat[cat] > 1 and conv is not None and "converts_note" not in card:
            card["converts_note"] = "market read is for the whole category (all brands together)"
        if usable_conv and usable_conv < 1 and o.get("own_purchases_used"):
            cat_spend = sum(gg["spend"] for kk, gg in groups.items() if kk[0] == cat) or g["spend"]
            card["orders_if_market_conversion"] = round(o["own_purchases_used"] * (1 / usable_conv - 1) * g["spend"] / cat_spend)
            card["orders_period"] = f"{o.get('weeks') or a.sqp_weeks} weeks"

        # axis 2
        card["peer_rows"], card["peer_goals"] = {}, []
        bkey = br.strip().lower()
        if bkey and bkey in bench_brands:
            statuses = []
            for ad in ("SP", "SB", "SD"):
                for goal in GOAL_ORDER[ad]:
                    n, seen = node(bkey, cat, ad, goal, g["path"])
                    statuses += seen
                    if not n:
                        continue
                    pr = peer_read(n, goal)
                    card["peer_goals"].append(dict(pr, ad=ad))
                    card["peer_rows"].setdefault(ad, pr)
            if not card["peer_rows"]:
                st = "NO_PEER_BENCHMARK" if "NO_PEER_BENCHMARK" in statuses else (statuses[0] if statuses else "no row returned")
                card["peer_note"] = f"no peer benchmark for this brand in this category (status {st})"
        elif a.peer_unavailable:
            card["peer_note"] = f"peer data not accessible ({a.peer_unavailable}) - an access gap, not a finding about peers"
        else:
            card["peer_note"] = f"no peer benchmark rows for brand {br or '(unknown)'}"
        bad = [u for u in unusable if u["category"] in chain(cat, g["path"]) and str(u["brand"] or "").strip().lower() == bkey]
        if bad:
            card["unusable_peer_rows"] = bad
            notes.append("; ".join(sorted({u["reason"] for u in bad})))
            if not card["peer_rows"]:
                card["peer_note"] = "peer rows returned but not usable (" + "; ".join(sorted({u["reason"] for u in bad})) + ")"
        lead = next((ad for ad in ad_order if ad in card["peer_rows"]), None)
        card["play_ad_type"] = lead
        posn = card["peer_rows"][lead]["position"] if lead else None
        if posn:
            pr = card["peer_rows"][lead]
            eff_ok, basis = posn in POS_ORDER[:2], f"peers ({lead}, {pr['goal']} goal, {pr['metric'].upper()}, {pr['level_name']})"
        elif card["acos_vs_account"] is not None:
            eff_ok, basis = card["acos_vs_account"] <= a.acos_slack, "your account ACOS (no usable peer row)"
        else:
            eff_ok, basis = None, None
        card["ad_cost_basis"] = basis; card["ad_cost_ok"] = eff_ok

        # play. note_codes mirrors notes so a report can phrase each one in the user's language.
        note_codes = []
        if usable_conv is None and eff_ok is None:
            play = "No read"; notes.append("no market data and no peer row")
            note_codes.append({"code": "no_data_no_peer"})
        elif usable_conv is None:
            play = "Scale" if eff_ok else "Fix ad cost"
            if a.market_unavailable:
                notes.append(f"market data not accessible ({a.market_unavailable}): judged on peers and ACOS")
                note_codes.append({"code": "market_unavailable", "reason": a.market_unavailable})
            elif a.account == "vendor" or not market:
                notes.append("Vendor or no SQP: judged on peers and ACOS")
                note_codes.append({"code": "vendor_no_sqp"})
            else:
                notes.append("based on ads only (market data missing or not usable)")
                note_codes.append({"code": "ads_only"})
        elif eff_ok is None:
            play = "Scale" if usable_conv >= a.conv_line else "Fix listing"
            notes.append("based on market data only (no peer row)")
            note_codes.append({"code": "market_only"})
        else:
            play = ("Scale" if eff_ok else "Fix ad cost") if usable_conv >= a.conv_line else ("Fix listing" if eff_ok else "Fix first")
        if cov is not None and a.drop_coverage <= cov < a.min_coverage and usable_conv is not None:
            notes.append(f"market data covers {round(cov * 100)}% of spend")
            note_codes.append({"code": "coverage", "pct": round(cov * 100)})
        if play == "Scale":
            if lead and lead != "SP" and (usable_conv is None or (card["acos_vs_account"] or 0) > 1.2):
                card["scale_scope"] = {"SB": "Sponsored Brands", "SD": "Sponsored Display"}[lead] + " only"
                notes.append(f"evidence is {lead} only")
                note_codes.append({"code": "evidence_adtype", "ad": lead})
            if a.acos_goal and card["acos_14d"] and card["acos_14d"] > a.acos_goal:
                play = "Keep"; card.pop("scale_scope", None)
                notes.append(f"category ACOS {card['acos_14d']}% is above your {a.acos_goal:g}% goal: no raise until it is back under")
                note_codes.append({"code": "acos_above_goal", "acos": card["acos_14d"], "goal": a.acos_goal})
            if card["converts_band"] == "close" and usable_conv is not None:
                notes.append("check the page as you scale (close to market, not ahead)")
                note_codes.append({"code": "close_to_market"})
            if card["stock_days_min_top2"] is not None and card["stock_days_min_top2"] < a.min_stock_days:
                play = "Hold (stock)"; notes.append(f"main product: {card['stock_days_min_top2']:g} days of stock")
                note_codes.append({"code": "low_stock", "days": card["stock_days_min_top2"]})
        if lead and card["peer_rows"][lead]["goal"] != "conversion" and card["peer_rows"][lead]["roas_position"] == "bottom quarter":
            pr = card["peer_rows"][lead]
            notes.append(f"{lead} ROAS {pr['roas']:.2f} is in peers' bottom 25% (median {pr['roas_p50']:.2f}): check before adding budget")
            note_codes.append({"code": "roas_bottom", "ad": lead, "roas": round(pr["roas"], 2),
                               "median": round(pr["roas_p50"], 2)})
        card["play"] = play; card["play_note"] = "; ".join(notes) or None
        card["play_note_codes"] = note_codes
        ng = NEXT_GOAL.get(play)
        if not ng:
            card["next"] = "-"; card["next_code"] = {"code": "none"}
        elif a.account == "vendor" or not market:
            if play != "Scale":
                card["next"] = "sparkx-search-term-diagnosis (search terms; no SQP)"
                card["next_code"] = {"code": "std_no_sqp"}
            else:
                card["next"] = "budget raises in change_list.csv"
                card["next_code"] = {"code": "raises_in_csv"}
        else:
            card["next"] = f"sparkx-sqp-insight plan mode: {ng}"
            card["next_code"] = {"code": "sqp_plan", "goal": ng}
        card["next_goal"] = ng
        if ev and ev["plan_only"]:
            when_before = "sparkx-promo-monitor (event in progress)" if ev["in_progress"] else f"before {fmt(ev['start'])} via sparkx-promo-prep"
            card["timing"] = {"Scale": f"plan only; {when_before}", "Fix listing": "now (page work)",
                              "Fix ad cost": f"from {fmt(ev['reset_from'])}", "Fix first": f"page now; ad cost from {fmt(ev['reset_from'])}",
                              "Hold (stock)": "refill now", "Keep": f"from {fmt(ev['reset_from'])}"}.get(play, "-")
            _d, _s = fmt(ev["reset_from"]), fmt(ev["start"])
            card["timing_code"] = {
                "Scale": {"code": "plan_only_in_progress"} if ev["in_progress"] else {"code": "plan_only_before", "start": _s},
                "Fix listing": {"code": "now_page"}, "Fix ad cost": {"code": "from_date", "date": _d},
                "Fix first": {"code": "page_now_ads_from", "date": _d},
                "Hold (stock)": {"code": "refill_now"}, "Keep": {"code": "from_date", "date": _d},
            }.get(play, {"code": "none"})
        cards.append(card)

    with_peer = [c for c in cards if c["play_ad_type"]]
    pos_count = Counter(c["peer_rows"][c["play_ad_type"]]["position"] for c in with_peer)
    data_fixes = [{"category": c["category"], "ad_spend_14d": c["ad_spend_14d"],
                   "fix": "add the main products to the market search data (SQP)" if c.get("market_data_coverage") is not None
                   else "no market search rows: add the category's products to the market search data (SQP)"}
                  for c in cards if market and (c.get("market_data_coverage") or 0) < a.drop_coverage and c["ad_spend_14d"] >= 3 * a.min_spend]
    out = {"account_acos_14d": acct_acos, "ad_type_share": share, "event": ev, "account": a.account,
           "market_used": bool(market), "market_notes": (market or {}).get("notes", []),
           "peer_periods": sorted(periods), "unusable_peer_rows": unusable,
           "peer_summary": {"categories_with_peer_row": len(with_peer), **{k: pos_count.get(k, 0) for k in POS_ORDER}},
           "sp_peer_rows": any("SP" in c["peer_rows"] for c in cards),
           "converts_summary": {b: sum(1 for c in cards if c.get("converts_band") == b and (c.get("market_data_coverage") or 0) >= a.drop_coverage)
                                for b in ("ahead", "close", "behind")},
           "data_fixes": data_fixes, "categories": cards,
           "by_play": {p: [c["category"] for c in cards if c["play"] == p]
                       for p in ("Scale", "Keep", "Hold (stock)", "Fix ad cost", "Fix listing", "Fix first", "No read")},
           "not_scored_small": small[:30], "not_scored_small_count": len(small),
           "scored_share_of_ad_spend": round(sum(c["ad_spend_14d"] for c in cards) / ((sum(g["spend"] for g in groups.values()) + unmapped) or 1), 3),
           "unmapped_ad_spend": round(unmapped),
           "notes": ["Peer rows are brand peer groups (brand x category x ad product x goal totals), read row by row; "
                     "levels, goals, brands and periods are never added or averaged",
                     "Your own value in a peer row is the brand's total for all campaigns in that row: never compare it with one "
                     "campaign or with the console ACOS",
                     "Market purchases use 24-hour attribution, ads 7 days (SP) / 14 days (SB, SD): compare directions, not decimals"]}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "category_scorecard.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["by_play"], indent=1))
