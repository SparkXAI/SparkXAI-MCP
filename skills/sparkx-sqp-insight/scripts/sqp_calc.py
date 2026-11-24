#!/usr/bin/env python3
"""
sqp_calc.py - deterministic SQP calculations for the sparkx-sqp-insight skill (diagnose mode).

Same input -> same numbers. The skill never recomputes these by hand in the answer.

Input: anything sqp_rows.py loads - get_market_search_perf JSON (marketSearchQuery and/or
marketAsinQuery, weekly or aggregated) or the four SparkX SQP exports. Column names live in
sqp_rows.py only.

Usage:
  python sqp_calc.py --current FILE [FILE ...] [--prior FILE [FILE ...]] [--split-at YYYY-MM-DD]
                     [--out DIR] [--flag-clicks 5] [--flag-impr 10] [--min-clicks 20] [--min-impr 500] [--top 15]

  --split-at                : one tool pull covering both windows: weeks ending on or before this
                              date become the prior period
  --flag-clicks/--flag-impr : sample flags used only when the row carries no tool *LowSample flag
  --min-clicks              : verdict gate for cut / fix / scale on one query
  --min-impr                : gate for click-stage leak estimates
  --brand-terms             : the store's own brand names (branded searches rank last)
  --competitor-terms        : other brands' names, comma list or @file (protect -> conquest; brand segments)
  --head-volume 100000      : search volume from which a search is a head term

Writes DIR/sqp_rows.csv (window rows + derived fields), DIR/sqp_summary.json and
DIR/sqp_actions.csv (every search with 20+ clicks: group, shares, conversion vs market,
orders within reach, the product carrying it and its price vs market).
Read the summary; quote numbers from it, never from a re-calculation in prose.
Requires pandas (pip install pandas; openpyxl as well for .xlsx exports).
"""
import argparse, json, os, re, sys, math
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqp_rows  # noqa: E402  (the only module that names SQP columns)

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas openpyxl")

QUERY_GRAIN = ("tool_query", "query_main", "query_from_asin")


def load(paths, label, split_at=None):
    """Load through sqp_rows and return window rows as a DataFrame: query-grain rows (market
    counted once per search and week), own-ASIN rows and ASIN main-page rows, each collapsed
    over its weeks. With split_at, weeks ending on or before it are labelled 'prior'."""
    rows, infos = sqp_rows.load(paths, label)
    if split_at:
        for r in rows:
            if r.get("week_end") and r["week_end"] <= split_at:
                r["period"] = "prior"
    weeks = {p: sqp_rows.weeks_seen([r for r in rows if r["period"] == p]) for p in ("current", "prior")}
    parts = sqp_rows.query_rows(rows)
    parts += sqp_rows.collapse_weeks([r for r in rows if r["source_kind"] in sqp_rows.ASIN_KINDS + ("asin_main",)])
    for r in parts:
        r["weeks"] = len(r.get("weeks") or [])
    df = pd.DataFrame(parts, columns=list(dict.fromkeys(sqp_rows.CANON + ["source_kind", "period", "file", "weeks"]
                                                          + [k for r in parts[:1] for k in r])))
    for c in sqp_rows.CANON:
        if c not in sqp_rows.TEXT and c not in sqp_rows.FLAGS:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, infos, weeks


def derive(df, notes):
    """Recompute every ratio from counts (tool rates are percentages and are never read)."""
    def ratio(a, b):
        if a not in df.columns or b not in df.columns:
            return None
        return df.apply(lambda r: (r[a] / r[b]) if (r[b] and r[b] > 0 and not pd.isna(r[a])) else None, axis=1)

    for name, a, b in [("ctr_brand", "clicks_brand", "impr_brand"), ("ctr_mkt", "clicks_mkt", "impr_mkt"),
                       ("cvr_brand", "purch_brand", "clicks_brand"), ("cvr_mkt", "purch_mkt", "clicks_mkt"),
                       ("atcr_brand", "atc_brand", "clicks_brand"), ("atcr_mkt", "atc_mkt", "clicks_mkt"),
                       ("impr_share", "impr_brand", "impr_mkt"), ("click_share", "clicks_brand", "clicks_mkt"),
                       ("purch_share", "purch_brand", "purch_mkt")]:
        r = ratio(a, b)
        if r is not None:
            df[name] = r
    return df


def funnel_loss(df, min_clicks, min_impr):
    """Q2. Orders lost vs market rate. Two additive stages; ATC is diagnostic only."""
    def click_loss(r):
        if None in (r.get("impr_brand"), r.get("ctr_mkt"), r.get("ctr_brand"), r.get("cvr_brand")):
            return None
        if r["impr_brand"] < min_impr:
            return None
        gap = r["ctr_mkt"] - r["ctr_brand"]
        return max(gap, 0) * r["impr_brand"] * r["cvr_brand"]

    def conv_loss(r):
        if None in (r.get("clicks_brand"), r.get("cvr_mkt"), r.get("cvr_brand")):
            return None
        if r["clicks_brand"] < min_clicks:
            return None
        return max(r["cvr_mkt"] - r["cvr_brand"], 0) * r["clicks_brand"]

    rec = df.to_dict("records")
    df["lost_orders_click"] = [click_loss(r) for r in rec]
    # Brand CTR vs market CTR is often structurally above 1 (market impressions count every
    # listing on the page, brand impressions only the brand's own), so the market benchmark can
    # show zero click-stage loss everywhere. Second benchmark: the store's own median CTR index
    # on gated rows of the same grain. Report it as "below your usual CTR", never "below market".
    if "ctr_brand" in df.columns and "ctr_mkt" in df.columns:
        df["ctr_index"] = df.apply(lambda r: r["ctr_brand"] / r["ctr_mkt"]
                                   if r.get("ctr_mkt") and not pd.isna(r.get("ctr_brand")) else None, axis=1)
        df["lost_orders_click_rel"] = None
        for _, g in df.groupby("source_kind", sort=False):
            ok = g[(g["impr_brand"].fillna(0) >= min_impr) & g["ctr_index"].notna()]
            if ok.empty:
                continue
            med = ok["ctr_index"].median()
            for i, r in ok.iterrows():
                if pd.isna(r.get("cvr_brand")):
                    continue
                df.at[i, "lost_orders_click_rel"] = max(med * r["ctr_mkt"] - r["ctr_brand"], 0) * r["impr_brand"] * r["cvr_brand"]
            df.loc[g.index, "store_median_ctr_index"] = med
    df["lost_orders_conv"] = [conv_loss(r) for r in rec]
    df["sample_ok_cvr"] = df.get("clicks_brand", pd.Series([None] * len(df))).map(
        lambda v: v is not None and not pd.isna(v) and v >= min_clicks)
    return df


def behaviour_class(df):
    """Market-side behaviour of each query (uses market rates only; relative to the scope's median)."""
    if "ctr_mkt" not in df.columns or "cvr_mkt" not in df.columns:
        df["behaviour"] = None
        return df
    ctr_med = df["ctr_mkt"].median(skipna=True)
    cvr_med = df["cvr_mkt"].median(skipna=True)
    atc_med = df["atcr_mkt"].median(skipna=True) if "atcr_mkt" in df.columns else None

    def cls(r):
        if pd.isna(r.get("ctr_mkt")) or pd.isna(r.get("cvr_mkt")):
            return None
        hi_ctr = r["ctr_mkt"] >= ctr_med
        hi_cvr = r["cvr_mkt"] >= cvr_med
        hi_atc = None if atc_med is None or pd.isna(r.get("atcr_mkt")) else r["atcr_mkt"] >= atc_med
        if not hi_ctr:
            return "low_ctr_shelf"          # nobody on this shelf earns the click: opportunity signal
        if hi_cvr:
            return "high_intent"            # title, exact, defend
        if hi_atc is True:
            return "long_consideration"     # change tactic not bid (24h window undercounts)
        return "browse"                     # broad/awareness, keep out of title
    df["behaviour"] = [cls(r) for r in df.to_dict("records")]
    return df


def flags(df, flag_clicks, flag_impr):
    """Sample flags: the tool's own *LowSample flag when the row carries one (single week or a tool
    aggregate); otherwise the same rule on the row's summed counts. Rates stay, flagged rows sort last."""
    def pick(tool_col, count_col, floor):
        out = []
        for t, v in zip(df.get(tool_col, pd.Series([None] * len(df))), df.get(count_col, pd.Series([None] * len(df)))):
            if t is not None and not (isinstance(t, float) and pd.isna(t)):
                out.append(bool(t))
            else:
                out.append(v is None or pd.isna(v) or v < floor)
        return out
    df["flag_low_sample_cvr"] = pick("ls_cvr_brand", "clicks_brand", flag_clicks)
    df["flag_low_sample_ctr"] = pick("ls_ctr_brand", "impr_brand", flag_impr)
    return df


def share_eff(df, min_clicks):
    """Q4 / Q6 matrix. X = purchase share vs scope median, Y = brand CVR / market CVR."""
    if "purch_share" not in df.columns or "cvr_brand" not in df.columns:
        df["quadrant"] = None
        return df
    # Median over rows that pass the sample gate only - otherwise the many zero-share
    # long-tail rows pull the median to 0 and every row looks "high share".
    ok = df["sample_ok_cvr"].fillna(False).astype(bool) & df["purch_share"].notna()
    med = df.loc[ok, "purch_share"].median()

    def q(r):
        if not r.get("sample_ok_cvr"):
            return "insufficient_sample"
        if pd.isna(r.get("purch_share")) or pd.isna(r.get("cvr_mkt")) or not r.get("cvr_mkt"):
            return None
        eff = r["cvr_brand"] / r["cvr_mkt"]
        hi_s = r["purch_share"] >= med
        # A +-10% band around market CVR counts as "at market": a query converting at 0.94x
        # market is not a cut candidate.
        if eff >= 1.0:
            return "defend" if hi_s else "scale"
        if eff >= 0.9:
            return "defend" if hi_s else "hold_at_market"
        return "fix_listing_risk" if hi_s else "fix_or_cut"
    df["quadrant"] = [q(r) for r in df.to_dict("records")]
    df["cvr_index"] = df.apply(lambda r: r["cvr_brand"] / r["cvr_mkt"]
                               if r.get("cvr_mkt") and not pd.isna(r.get("cvr_brand")) else None, axis=1)
    return df


def query_level(df):
    """Collapse to one row per query (Market fields are per query; never sum Market across ASINs)."""
    if "query" not in df.columns or df["query"].isna().all():
        return None
    brand = [c for c in ("impr_brand", "clicks_brand", "atc_brand", "purch_brand") if c in df.columns]
    mkt = [c for c in ("search_volume", "impr_mkt", "clicks_mkt", "atc_mkt", "purch_mkt",
                       "ship_sameday_purch", "ship_1d_purch", "ship_2d_purch") if c in df.columns]
    g = df.groupby(["period", "query"], dropna=True)
    q = g[brand].sum(min_count=1).join(g[mkt].max())   # market: same value on every ASIN row
    return q.reset_index()


def decompose(cur_q, pri_q):
    """Q1. Was it me or the market? Uses purchases (brand vs market) per query."""
    if pri_q is None or cur_q is None:
        return None
    m = cur_q.merge(pri_q, on="query", suffixes=("_t1", "_t0"))
    out = []
    for r in m.to_dict("records"):
        b0, b1, k0, k1 = r.get("purch_brand_t0"), r.get("purch_brand_t1"), r.get("purch_mkt_t0"), r.get("purch_mkt_t1")
        if not b0 or not k0 or b1 is None or k1 is None:
            continue
        gm, gk = b1 / b0 - 1, k1 / k0 - 1
        if gm >= 0 and gk > gm:
            v = "growing_slower_than_market"   # add exposure, not a listing fix
        elif gm < 0 and gk >= 0:
            v = "real_loss"                     # most urgent: who took it?
        elif gm < 0 and gk < gm:
            v = "category_shrinking_you_outran"  # do not panic, do not add spend
        elif gm < 0 and gk < 0:
            v = "both_down_you_fell_faster"
        elif gm >= 0 and gk < 0:
            v = "taking_share_against_market"   # press
        else:
            v = "growing_faster_than_market"
        out.append({"query": r["query"], "brand_purch_t0": b0, "brand_purch_t1": b1,
                    "mkt_purch_t0": k0, "mkt_purch_t1": k1, "g_brand": gm, "g_market": gk,
                    "share_t0": b0 / k0, "share_t1": (b1 / k1) if k1 else None, "verdict": v})
    return pd.DataFrame(out)


def demand_index(cur_q, pri_q, basket=None):
    """Q9. Market demand for a fixed basket of queries (present in BOTH periods)."""
    if pri_q is None or cur_q is None:
        return None
    m = cur_q.merge(pri_q, on="query", suffixes=("_t1", "_t0"))
    if basket:
        m = m[m["query"].isin(basket)]
    if m.empty or "search_volume_t0" not in m.columns:
        return None
    sv0, sv1 = m["search_volume_t0"].sum(), m["search_volume_t1"].sum()
    p0, p1 = m["purch_mkt_t0"].sum(), m["purch_mkt_t1"].sum()
    b0, b1 = m["purch_brand_t0"].sum(), m["purch_brand_t1"].sum()
    return {"basket_queries": int(len(m)),
            "search_volume_change": sv1 / sv0 - 1 if sv0 else None,
            "market_purchases_change": p1 / p0 - 1 if p0 else None,
            "brand_purchases_change": b1 / b0 - 1 if b0 else None,
            "brand_share_t0": b0 / p0 if p0 else None, "brand_share_t1": b1 / p1 if p1 else None}


def position(q):
    """Store position on the query set: shares and CVR index from summed counts (market counted
    once per query). A lower bound when the query export hit its row cap."""
    if q is None or q.empty:
        return None
    s = lambda c: q[c].sum(skipna=True) if c in q.columns else None
    out = {"queries": int(len(q)), "queries_with_brand_purchases": int((q.get("purch_brand", 0) > 0).sum())}
    for name, b, m in [("impression_share", "impr_brand", "impr_mkt"), ("click_share", "clicks_brand", "clicks_mkt"),
                       ("purchase_share", "purch_brand", "purch_mkt")]:
        bb, mm = s(b), s(m)
        out[name] = (bb / mm) if bb is not None and mm else None
    pb, cb, pm, cm = s("purch_brand"), s("clicks_brand"), s("purch_mkt"), s("clicks_mkt")
    if pb and cb and pm and cm:
        out["cvr_brand"], out["cvr_market"] = pb / cb, pm / cm
        out["cvr_index"] = (pb / cb) / (pm / cm)
    out["brand_purchases"], out["market_purchases"] = pb, pm
    out["market_search_volume"] = s("search_volume")
    return out


def concentration(q, top_n=10):
    """Q5. Brand purchase concentration vs market concentration on the same queries."""
    if q is None or "purch_brand" not in q.columns:
        return None
    q = q[q["purch_brand"].fillna(0) > 0].sort_values("purch_brand", ascending=False)
    if q.empty or "purch_mkt" not in q.columns:
        return None
    tot_b, tot_m = q["purch_brand"].sum(), q["purch_mkt"].sum()
    top = q.head(top_n)
    nb, nm = top["purch_brand"].sum() / tot_b, top["purch_mkt"].sum() / tot_m
    nxt = q.iloc[top_n:top_n + 20]
    return {"top_n": top_n, "brand_share_of_own_purchases": nb, "market_share_of_purchases_same_queries": nm,
            "concentration_ratio": nb / nm if nm else None,
            "next_20_market_purchase_share": nxt["purch_mkt"].sum() / tot_m if len(nxt) else None,
            "next_20_avg_brand_purchase_share": (nxt["purch_brand"].sum() / nxt["purch_mkt"].sum())
            if len(nxt) and nxt["purch_mkt"].sum() else None,
            "queries_with_brand_purchases": int(len(q)),
            "next_20_top_room": _rec(nxt.assign(purch_share=nxt["purch_brand"] / nxt["purch_mkt"])
                                     .sort_values("purch_mkt", ascending=False),
                                     ["query", "purch_mkt", "purch_brand", "purch_share"], 5)}


def shipping_gate(df):
    """Q8. Share of market purchases that ship same-day / 1-day, per query."""
    cols = ["ship_sameday_purch", "ship_1d_purch", "ship_2d_purch", "purch_mkt"]
    if not all(c in df.columns for c in cols):
        return df
    df["fast_ship_share_mkt"] = df.apply(
        lambda r: (r["ship_sameday_purch"] + r["ship_1d_purch"]) / r["purch_mkt"]
        if r.get("purch_mkt") and r.get("ship_1d_purch") is not None and r.get("ship_sameday_purch") is not None
        else None, axis=1)
    return df


def _rec(d, cols, n):
    keep = [c for c in cols if c in d.columns]
    return json.loads(d[keep].head(n).to_json(orient="records"))


def presets(df, min_clicks=5):
    """The five SparkX SQP preset filters, exactly as defined in the product
    ("SQP default filters - condition definitions"). Rates from counts. Reproduced as the
    product shows them; read rules.md section 3 before turning a CTR-based preset into advice."""
    def g(r, k):
        v = r.get(k)
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else v
    out = {k: [] for k in ("high_loss_converter", "high_click_low_cart", "high_cart_low_purchase",
                           "under_exposed_top_performer", "excess_impression_sink")}
    for r in df.to_dict("records"):
        cb, cm, ctb, ctm = g(r, "cvr_brand"), g(r, "cvr_mkt"), g(r, "ctr_brand"), g(r, "ctr_mkt")
        ab, am, clk, ish = g(r, "atcr_brand"), g(r, "atcr_mkt"), g(r, "clicks_brand") or 0, g(r, "impr_share")
        hlc = cb is not None and cm is not None and cb < cm and clk >= min_clicks
        hclc = None not in (ctb, ctm, ab, am) and ctb >= ctm and ab < am and clk >= min_clicks
        hclp = None not in (ab, am, cb, cm) and ab >= am and cb < cm and clk >= min_clicks
        # Impression Delta < 0 holds for almost every row (brand < market count), so in
        # practice this is "converts at or above market".
        uetp = cb is not None and cm is not None and cb >= cm and clk >= min_clicks
        eis = ish is not None and ish > 0.02 and cb is not None and cm is not None and cb < cm
        for k, v in zip(out, (hlc, hclc, hclp, uetp, eis)):
            out[k].append(bool(v))
    for k, v in out.items():
        df[f"preset_{k}"] = v
    return df


def use_cases(qv, min_volume, top, brand_terms=(), vocab_extra=(), competitor_terms=()):
    """Help-center use cases on query-grain rows (one row per query). Deterministic lists."""
    if qv is None or qv.empty or "search_volume" not in qv.columns:
        return {}
    q = qv[qv["search_volume"].fillna(0) >= min_volume].copy()
    # Junk queries (single letters, numbers) are never opportunities
    q = q[q["query"].fillna("").str.strip().map(lambda t: len(t) >= 3 and not t.replace(" ", "").isdigit())]
    if q.empty:
        return {"note": f"no query reaches the volume floor ({min_volume})"}
    # Relevance: a query counts as "in your category" when it shares a meaningful word with
    # searches where the store already wins purchases (plus any vocabulary passed in).
    stop = {"for", "and", "with", "the", "best", "organic", "natural", "pure", "women", "men", "kids",
            "capsules", "capsule", "powder", "softgels", "softgel", "gummies", "supplement", "supplements",
            "pills", "tablets", "liquid", "drops", "oil", "extract", "mg", "mcg", "high", "potency", "pack"}
    tok = lambda t: {w for w in str(t).lower().replace("-", " ").split() if len(w) >= 3 and w not in stop}
    vocab = set(vocab_extra or ())
    for t, pb in zip(qv["query"], qv.get("purch_brand", pd.Series([0] * len(qv)))):
        if pb and not pd.isna(pb) and pb >= 3:
            vocab |= tok(t)
    q["relevant"] = q["query"].map(lambda t: bool(tok(t) & vocab))
    bt = [b.lower() for b in brand_terms if b]
    q["branded"] = q["query"].fillna("").str.lower().map(lambda t: any(b in t for b in bt)) if bt else False
    ct = [c.lower() for c in competitor_terms if c]
    q["competitor_brand"] = q["query"].fillna("").str.lower().map(lambda t: any(c in t for c in ct)) if ct else False
    cols = ["query", "search_volume", "impr_share", "click_share", "purch_share", "ctr_index", "cvr_index",
            "purch_brand", "purch_mkt", "cvr_mkt", "branded", "competitor_brand"]
    res = {"volume_floor": min_volume, "queries_over_floor": int(len(q))}
    med_ctr = q.loc[q["impr_brand"].fillna(0) >= 500, "ctr_index"].median() if "ctr_index" in q.columns else None
    res["store_median_ctr_index"] = med_ctr
    # 1. Bid-up: click share clearly above impression share RELATIVE to the store's usual ratio
    #    (click share / impression share == CTR index, which runs above 1 for most brands).
    if med_ctr:
        b = q[(q["ctr_index"] >= 1.2 * med_ctr) & (q["impr_brand"].fillna(0) >= 500) & q["relevant"]
              & (q["purch_brand"].fillna(0) >= 5)]
        b = b.sort_values(["branded", "search_volume"], ascending=[True, False])
        res["bid_up"] = {"rule": "CTR index >= 1.2 x store median, 500+ impressions, 5+ purchases, relevant, volume floor; non-branded first",
                         "count": int(len(b)), "rows": _rec(b, cols, top)}
    # 2. Protect: purchase share >= 20% (HC: 20%+ = high incrementality)
    p = q[q["purch_share"].fillna(0) >= 0.20].sort_values("purch_brand", ascending=False)
    # Another brand's name is not ours to protect: list it apart as conquest (won organically or by ads)
    cq = p[p["competitor_brand"].astype(bool)]
    p = p[~p["competitor_brand"].astype(bool)]
    res["protect"] = {"rule": "purchase share >= 20%, volume floor, not another brand's name", "count": int(len(p)), "rows": _rec(p, cols, top)}
    res["conquest"] = {"rule": "another brand's name where the store wins 20%+ of purchases; not a protect term",
                       "count": int(len(cq)), "rows": _rec(cq, cols, top)}
    # 3. Coverage gaps: big searches where the store is barely visible
    vmed = q["search_volume"].median()
    g = q[(q["impr_share"].fillna(0) < 0.01) & (q["search_volume"] >= vmed) & q["relevant"]]
    cvr_med = q["cvr_mkt"].median()
    g = g.assign(intent=g["cvr_mkt"] >= cvr_med).sort_values(["intent", "search_volume"], ascending=[False, False])
    res["coverage_gaps"] = {
        "rule": "impression share < 1%, volume above the median, relevant to the store; high market CVR first",
        "count": int(len(g)),
        "organic_carrying": int((g["purch_brand"].fillna(0) > 0).sum()),
        "true_gap": int((g["purch_brand"].fillna(0) == 0).sum()),
        "rows": _rec(g, cols, top),
        "note": "Exports only list searches where the store already appeared; searches with no presence at all need market-only rows from the SQP tool."}
    # 4. Keyword tiers (launch / content): volume x market CVR
    q = q[q["relevant"]].copy()
    res["relevant_queries"] = int(len(q))
    q["tier"] = [("title_must" if v >= vmed and c >= cvr_med else "broad_only" if v >= vmed else
                  "backend_exact" if c >= cvr_med else "low_priority")
                 for v, c in zip(q["search_volume"], q["cvr_mkt"].fillna(0))]
    res["keyword_tiers"] = {"rule": "volume vs median x market CVR vs median, over the floor",
                            "counts": q["tier"].value_counts().to_dict(),
                            "title_must_top": _rec(q[q["tier"] == "title_must"].sort_values("search_volume", ascending=False), cols, top)}
    # 5. Peak-season priority: volume x purchase share
    smed = q["purch_share"].median()
    q["peak"] = [("defend_scale" if v >= vmed and s >= smed else "test_before_event" if v >= vmed else
                  "niche_hold" if s >= smed else "deprioritize")
                 for v, s in zip(q["search_volume"], q["purch_share"].fillna(0))]
    res["peak_priority"] = {"rule": "volume vs median x purchase share vs median", "counts": q["peak"].value_counts().to_dict(),
                            "test_before_event_top": _rec(q[q["peak"] == "test_before_event"].sort_values("search_volume", ascending=False), cols, top)}
    return res


def _ok_price(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or v <= 0) else v  # median price 0 = no data


def query_owner(drill, qv):
    """Which of the store's products carries each search, and its price vs the market median.
    Needs ASIN x query rows (detail exports or tool rows). Price is per listing (pack size not
    normalised): a gap is a prompt to check value per serving, not proof of overpricing."""
    out = {}
    mk = {}
    if qv is not None and not qv.empty:
        for c in ("med_purch_price_mkt", "med_click_price_mkt"):
            if c in qv.columns:
                for q, v in zip(qv["query"], qv[c]):
                    if _ok_price(v) and q not in mk:
                        mk[q] = _ok_price(v)
    if drill is not None and not drill.empty and "clicks_brand" in drill.columns:
        d = drill.dropna(subset=["query"])
        for q, g in d.groupby("query"):
            g = g.sort_values("clicks_brand", ascending=False)
            tot = g["clicks_brand"].fillna(0).sum()
            r = g.iloc[0]
            if not tot:
                continue
            pb = _ok_price(r.get("med_click_price_brand"))
            pm = _ok_price(r.get("med_click_price_mkt")) or mk.get(q)
            out[q] = {"top_asin": r.get("asin"), "top_asin_click_share": float(r["clicks_brand"] / tot),
                      "asins_on_query": int((g["clicks_brand"].fillna(0) > 0).sum()),
                      "price_top_asin": pb, "price_mkt_median": pm,
                      "price_gap": (pb / pm - 1) if (pb and pm) else None}
    for q, pm in mk.items():
        out.setdefault(q, {"price_mkt_median": pm})
    return out


def product_queries(drill, min_clicks=20, top=5):
    """Top searches per product (detail rows): explains a product-level conversion index."""
    if drill is None or drill.empty:
        return {}
    d = drill[drill["clicks_brand"].fillna(0) >= min_clicks].copy()
    d["cvr_index"] = (d["purch_brand"] / d["clicks_brand"]) / d["cvr_mkt"]
    res = {}
    for a, g in d.groupby("asin"):
        g = g.sort_values("clicks_brand", ascending=False).head(top)
        res[a] = _rec(g, ["query", "clicks_brand", "purch_brand", "cvr_index", "med_click_price_brand", "med_click_price_mkt"], top)
    return res


def _terms(spec):
    """Comma-separated terms, or @file with one term per line (# comments allowed)."""
    if not spec:
        return []
    if spec.startswith("@"):
        return [l.split("#")[0].strip().lower() for l in open(spec[1:], encoding="utf-8") if l.split("#")[0].strip()]
    return [t.strip().lower() for t in spec.split(",") if t.strip()]


def brand_segments(qv, own_terms, comp_terms, top=10):
    """Own-brand vs competitor-brand vs generic searches, read through market prices.
    Median click price = typical price of what shoppers click; median purchase price = typical
    price of what they buy. On generic searches shoppers usually click pricier items and buy
    cheaper ones (price shopping); on brand searches they pay up for the brand they asked for.
    Prices are per query medians: averaged with clicks / purchases as weights, never summed."""
    import numpy as np
    if qv is None or qv.empty or "med_purch_price_mkt" not in qv.columns:
        return {"note": "needs the Search Term main page (median click and purchase prices)"}
    q = qv.copy()
    for c in ("search_volume", "clicks_mkt", "purch_mkt", "clicks_brand", "purch_brand"):
        q[c] = pd.to_numeric(q.get(c), errors="coerce").astype(float)
    t = q["query"].fillna("").str.lower()
    hit = lambda terms: t.map(lambda x: next((b for b in terms if b in x), None))
    q["own_term"] = hit(own_terms) if own_terms else None
    q["comp_term"] = hit(comp_terms) if comp_terms else None
    q["segment"] = np.where(q["own_term"].notna(), "own_brand", np.where(q["comp_term"].notna(), "competitor_brand", "generic"))
    cp = pd.to_numeric(q.get("med_click_price_mkt"), errors="coerce")
    pp = pd.to_numeric(q.get("med_purch_price_mkt"), errors="coerce")
    # median price 0 = no data; a click price 5x away from the purchase price is a data error
    ok = (cp > 0) & (pp > 0) & (cp <= 5 * pp) & (cp >= pp / 5)
    q["click_price_ok"] = cp.where(ok)
    q["purch_price_ok"] = pp.where(ok)
    q["price_step"] = (pp / cp - 1).where(ok)
    out = {"rule": "own_brand = query contains one of --brand-terms; competitor_brand = one of --competitor-terms; "
                   "generic = the rest. Prices: click-weighted median click price, purchase-weighted median purchase price; "
                   "price_step = purchase-weighted mean of (median purchase price / median click price - 1).",
           "segments": {}}
    for seg, g in q.groupby("segment"):
        gp = g[g["price_step"].notna()]
        wc, wp = gp["clicks_mkt"].fillna(0), gp["purch_mkt"].fillna(0)
        cm, pm = g["clicks_mkt"].sum(), g["purch_mkt"].sum()
        cb, pb = g["clicks_brand"].sum(), g["purch_brand"].sum()
        out["segments"][seg] = {
            "queries": int(len(g)), "search_volume": float(g["search_volume"].sum()),
            "clicks_mkt": float(cm), "purch_mkt": float(pm), "cvr_mkt": float(pm / cm) if cm else None,
            "click_price": float((gp["click_price_ok"] * wc).sum() / wc.sum()) if wc.sum() else None,
            "purchase_price": float((gp["purch_price_ok"] * wp).sum() / wp.sum()) if wp.sum() else None,
            "price_step": float((gp["price_step"] * wp).sum() / wp.sum()) if wp.sum() else None,
            "purch_brand": float(pb), "purch_share": float(pb / pm) if pm else None,
            "cvr_index": float((pb / cb) / (pm / cm)) if cb and cm and pm else None,
            "share_of_brand_purchases": None}
    tot = sum(v["purch_brand"] for v in out["segments"].values())
    for v in out["segments"].values():
        v["share_of_brand_purchases"] = v["purch_brand"] / tot if tot else None
    cols = ["query", "search_volume", "purch_share", "cvr_index", "click_price_ok", "purch_price_ok", "price_step", "purch_brand"]
    with np.errstate(divide="ignore", invalid="ignore"):
        q["cvr_index"] = (q["purch_brand"] / q["clicks_brand"].replace(0, np.nan)) / (q["purch_mkt"] / q["clicks_mkt"].replace(0, np.nan))
    for seg in ("own_brand", "competitor_brand"):
        g = q[q["segment"] == seg].sort_values("search_volume", ascending=False)
        out[seg + "_top"] = _rec(g, cols + (["comp_term"] if seg == "competitor_brand" else ["own_term"]), top)
    if comp_terms:
        cb = q[q["segment"] == "competitor_brand"].groupby("comp_term").agg(
            queries=("query", "size"), search_volume=("search_volume", "sum"), purch_mkt=("purch_mkt", "sum"),
            purch_brand=("purch_brand", "sum")).sort_values("search_volume", ascending=False)
        cb["purch_share"] = cb["purch_brand"] / cb["purch_mkt"]
        out["competitor_brands"] = [dict(brand=k, **{c: float(v) for c, v in r.items()}) for k, r in cb.head(top).iterrows()]
    # Possible brand names to confirm: two-word openings shared by 8+ searches that are not
    # product words the store already sells on. A list for the analyst, never used unconfirmed.
    vocab = set()
    for x, pb in zip(q["query"], q["purch_brand"].fillna(0)):
        if pb >= 3:
            vocab |= set(str(x).lower().split())
    from collections import Counter
    c = Counter(" ".join(str(x).lower().split()[:2]) for x in q["query"] if len(str(x).split()) >= 3)
    known = set(own_terms) | set(comp_terms)
    out["brand_candidates_to_confirm"] = [k for k, n in c.most_common(400) if n >= 8 and not (set(k.split()) & vocab)
                                          and not any(b in k or k in b for b in known)][:20]
    out["note"] = ("Own-brand rows in a 10,000-row export are often incomplete: size branded demand from the "
                   "ad report or a branded SQP pull; read the rates and prices here.")
    return out


def enrich(rows, owner):
    for r in rows or []:
        o = owner.get(r.get("query"))
        if o:
            for k, v in o.items():
                r.setdefault(k, v)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", nargs="+", required=True)
    ap.add_argument("--prior", nargs="*", default=[])
    ap.add_argument("--split-at", help="weeks ending on or before this date (YYYY-MM-DD) are the prior period")
    ap.add_argument("--out", default="sqp_out")
    ap.add_argument("--flag-clicks", type=float, default=5)
    ap.add_argument("--flag-impr", type=float, default=10)
    ap.add_argument("--min-clicks", type=float, default=20)
    ap.add_argument("--min-impr", type=float, default=500)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-volume", type=float, default=1000, help="search volume floor for use-case lists")
    ap.add_argument("--vocab", help="optional file of category words (e.g. product titles) to widen relevance")
    ap.add_argument("--brand-terms", default="", help="the store's own brand names incl. common misspellings, comma list or @file")
    ap.add_argument("--competitor-terms", default="", help="other brands' names, comma list or @file (one per line): kept out of protect; competitor segment")
    ap.add_argument("--head-volume", type=float, default=100000, help="search volume from which a search counts as a head term (expensive to test)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    notes = []

    cur, meta_c, weeks_c = load(a.current, "current", a.split_at)
    if a.prior:
        pri, meta_p, weeks_p = load(a.prior, "prior")
        pri["period"] = "prior"
    elif a.split_at:
        pri, meta_p, weeks_p = cur[cur["period"] == "prior"].copy(), [], weeks_c
        cur = cur[cur["period"] == "current"].copy()
    else:
        pri, meta_p, weeks_p = pd.DataFrame(), [], {}
    if cur.empty:
        sys.exit("No readable SQP rows in --current.")
    notes += sqp_rows.coverage_notes(meta_c + meta_p)
    if not cur["source_kind"].isin(QUERY_GRAIN).any():
        notes.append("No search-level rows: only ASIN main-page rows were given, so search views are empty.")
    if "tool_query" not in set(cur["source_kind"]) and "tool_asin" in set(cur["source_kind"]):
        notes.append("Search totals were rolled up from own-ASIN rows (market counted once per search and week).")

    cur = derive(cur, notes)
    cur = funnel_loss(cur, a.min_clicks, a.min_impr)
    cur = flags(cur, a.flag_clicks, a.flag_impr)
    cur = presets(cur, a.flag_clicks)
    cur = behaviour_class(cur)
    # quadrant medians are per grain (ASIN rows vs query rows are not comparable)
    cur = pd.concat([share_eff(g.copy(), a.min_clicks) for _, g in cur.groupby("source_kind", sort=False)])
    cur = shipping_gate(cur)
    cur.to_csv(os.path.join(a.out, "sqp_rows.csv"), index=False, encoding="utf-8")

    # Query views use ONE grain: one row per search, market counted once (sqp_rows.query_rows).
    qsrc = cur[cur["source_kind"].isin(QUERY_GRAIN)]
    summ_grain = ("search (" + ", ".join(sorted(set(qsrc["source_kind"]))) + ")") if not qsrc.empty else "none"
    drill = cur[cur["source_kind"].isin(sqp_rows.ASIN_KINDS)]
    cur_q = query_level(qsrc) if not qsrc.empty else None
    pri_q = None
    if not pri.empty:
        pri = derive(pri, notes)
        psrc = pri[pri["source_kind"].isin(QUERY_GRAIN)]
        pri_q = query_level(psrc) if not psrc.empty else None

    summ = {"inputs": {"current": meta_c, "prior": meta_p, "weeks_current": weeks_c.get("current"),
                       "weeks_prior": (weeks_p or {}).get("prior")},
            "params": {"flag_clicks_lt": a.flag_clicks, "flag_impr_lt": a.flag_impr,
                       "verdict_gate_clicks": a.min_clicks, "click_leak_gate_impr": a.min_impr},
            "query_grain": summ_grain,
            "notes": notes}

    # Coverage
    cov = {}
    for c in [c for c in cur.columns if c.startswith("med_") and c.endswith("_mkt")]:
        cov[c + "_coverage"] = float(cur[c].notna().mean())
    cov["rows"] = int(len(cur))
    cov["rows_with_cvr_sample"] = int(cur["sample_ok_cvr"].sum()) if "sample_ok_cvr" in cur else None
    cov["rows_flagged_low_sample_cvr"] = int(cur["flag_low_sample_cvr"].sum()) if "flag_low_sample_cvr" in cur else None
    summ["coverage"] = cov

    # ASIN main page view
    am = cur[cur["source_kind"] == "asin_main"]
    if not am.empty:
        am = am.copy()
        am["lost_total"] = am[["lost_orders_click_rel", "lost_orders_conv"]].sum(axis=1, min_count=1)
        summ["asin_view"] = {
            "asins": int(len(am)),
            "note": "Market columns per ASIN are sums over that ASIN's queries; never add them across ASINs.",
            "top_by_lost_orders": _rec(am.sort_values("lost_total", ascending=False),
                                       ["asin", "query_count", "purch_brand", "purch_share", "ctr_brand", "ctr_mkt",
                                        "cvr_brand", "cvr_mkt", "lost_orders_click_rel", "lost_orders_conv", "quadrant"], a.top),
            "quadrants": am["quadrant"].value_counts(dropna=False).to_dict()}

    # Query view (Q2, Q4, Q6, behaviour)
    qv = qsrc.copy()
    if not qv.empty:
        lc, lv = qv["lost_orders_click"].sum(skipna=True), qv["lost_orders_conv"].sum(skipna=True)
        qv["lost_total"] = qv[["lost_orders_click_rel", "lost_orders_conv"]].sum(axis=1, min_count=1)
        top = qv.sort_values("lost_total", ascending=False)
        tot = qv["lost_total"].sum(skipna=True)
        k = top.head(10)["lost_total"].sum(skipna=True)
        lr = pd.to_numeric(qv.get("lost_orders_click_rel"), errors="coerce").sum(skipna=True) \
            if "lost_orders_click_rel" in qv.columns else None
        summ["fix_first"] = {
            "lost_orders_conversion_stage": lv,
            "lost_orders_click_stage": lr,
            "click_stage_basis": "below the store's own median CTR index (market CTR is not a like-for-like bar)",
            "click_stage_vs_market_ctr_diagnostic_only": lc,
            "store_median_ctr_index": float(qv["store_median_ctr_index"].dropna().iloc[0])
            if "store_median_ctr_index" in qv.columns and qv["store_median_ctr_index"].notna().any() else None,
            "ctr_note": "If click-stage loss vs market is ~0 while the CTR index sits well above 1, the market "
                        "CTR is not a usable bar for this store; use the own-median view and say so.",
            "top10_share_of_loss": (k / tot) if tot else None,
            "rows": _rec(top, ["query", "asin", "search_volume", "impr_brand", "clicks_brand", "purch_brand",
                               "ctr_brand", "ctr_mkt", "cvr_brand", "cvr_mkt", "atcr_brand", "atcr_mkt",
                               "lost_orders_click", "lost_orders_click_rel", "lost_orders_conv", "behaviour", "fast_ship_share_mkt"], a.top),
            "caveat": "Orders, not money: SQP has no brand-side sales amount."}
        summ["quadrants"] = qv["quadrant"].value_counts(dropna=False).to_dict()
        summ["scale_candidates"] = _rec(qv[qv["quadrant"] == "scale"].sort_values("purch_mkt", ascending=False),
                                        ["query", "asin", "search_volume", "purch_mkt", "purch_brand", "purch_share",
                                         "cvr_index"], a.top)
        summ["fix_or_cut"] = _rec(qv[qv["quadrant"] == "fix_or_cut"].sort_values("clicks_brand", ascending=False),
                                  ["query", "asin", "search_volume", "clicks_brand", "purch_brand", "cvr_brand", "cvr_mkt",
                                   "cvr_index", "purch_share", "lost_orders_conv", "lost_orders_click_rel", "behaviour"], a.top)
        summ["fix_listing"] = _rec(qv[qv["quadrant"] == "fix_listing_risk"].sort_values("lost_orders_conv", ascending=False),
                                   ["query", "search_volume", "clicks_brand", "purch_brand", "purch_share", "cvr_index",
                                    "lost_orders_conv", "lost_orders_click_rel"], a.top)
        pb = qv.groupby("quadrant", dropna=False)["purch_brand"].sum()
        tpb = pb.sum()
        summ["quadrant_purchase_share"] = {str(k): float(v / tpb) for k, v in pb.items()} if tpb else {}
        # Operator file: every judged search with its numbers, for the CSV download
        cols = [c for c in ["query", "quadrant", "search_volume", "impr_share", "click_share", "purch_share",
                            "clicks_brand", "purch_brand", "cvr_brand", "cvr_mkt", "cvr_index", "ctr_index",
                            "lost_orders_conv", "lost_orders_click_rel", "behaviour"] if c in qv.columns]
        judged = qv[qv["quadrant"] != "insufficient_sample"][cols].copy()
        judged["lost_total"] = judged[["lost_orders_conv", "lost_orders_click_rel"]].sum(axis=1, min_count=1)
        summ["_judged"] = judged.sort_values("lost_total", ascending=False)
        summ["behaviour_mix"] = qv["behaviour"].value_counts(dropna=False).to_dict()
        if "fast_ship_share_mkt" in qv.columns:
            gated = qv[(qv["fast_ship_share_mkt"] >= 0.6) & (qv["cvr_brand"] < qv["cvr_mkt"]) & qv["sample_ok_cvr"]]
            summ["shipping_gate"] = _rec(gated.sort_values("clicks_brand", ascending=False),
                                         ["query", "asin", "cvr_brand", "cvr_mkt", "fast_ship_share_mkt"], a.top)

    # Drill-down: which ASIN carries the leak on the top leaking queries
    if not drill.empty and "fix_first" in summ:
        top_q = [r["query"] for r in summ["fix_first"]["rows"][:10]]
        dd = drill[drill["query"].isin(top_q)].copy()
        dd["lost_total"] = dd[["lost_orders_click_rel", "lost_orders_conv"]].sum(axis=1, min_count=1)
        summ["drill_top_queries_by_asin"] = _rec(dd.sort_values("lost_total", ascending=False),
                                                  ["query", "asin", "clicks_brand", "purch_brand", "cvr_brand",
                                                   "cvr_mkt", "lost_total", "fast_ship_share_mkt"], 20)
    owner = query_owner(drill, qv if not qv.empty else None)
    summ["product_queries"] = product_queries(drill)
    summ["concentration"] = concentration(cur_q)
    summ["store_position"] = position(cur_q)
    # Preset filter counts per grain (as the product shows them)
    pc = {}
    need = {"high_loss_converter": ["cvr_brand", "cvr_mkt"], "high_click_low_cart": ["ctr_brand", "ctr_mkt", "atcr_brand", "atcr_mkt"],
            "high_cart_low_purchase": ["atcr_brand", "atcr_mkt", "cvr_brand", "cvr_mkt"],
            "under_exposed_top_performer": ["cvr_brand", "cvr_mkt"], "excess_impression_sink": ["impr_share", "cvr_brand", "cvr_mkt"]}
    for kind, g in cur.groupby("source_kind"):
        pc[kind] = {}
        for k, cols in need.items():
            ok = all(c in g.columns and g[c].notna().any() for c in cols)
            pc[kind][k] = int(g[f"preset_{k}"].sum()) if ok else "n/a (columns not in this export)"
    summ["preset_counts"] = pc
    uq = qv.copy() if not qv.empty else None
    vx = set()
    if a.vocab:
        for line in open(a.vocab, encoding="utf-8"):
            vx |= {w for w in line.lower().split() if len(w) >= 3}
    summ["use_cases"] = use_cases(uq, a.min_volume, a.top, _terms(a.brand_terms), vx, _terms(a.competitor_terms))
    if cur_q is not None and "purch_brand" in cur_q.columns:
        top = cur_q.sort_values("purch_brand", ascending=False).head(a.top).copy()
        top["purch_share"] = top["purch_brand"] / top["purch_mkt"]
        if "clicks_brand" in top.columns and "clicks_mkt" in top.columns:
            top["cvr_index"] = (top["purch_brand"] / top["clicks_brand"]) / (top["purch_mkt"] / top["clicks_mkt"])
        summ["top_queries_by_purchases"] = _rec(top, ["query", "search_volume", "purch_mkt", "purch_brand",
                                                       "purch_share", "cvr_index"], a.top)
    summ["brand_segments"] = brand_segments(qv if not qv.empty else None, _terms(a.brand_terms), _terms(a.competitor_terms))
    for path in (("fix_first", "rows"), ("scale_candidates",), ("fix_or_cut",), ("fix_listing",),
                 ("use_cases", "protect", "rows"), ("use_cases", "conquest", "rows"), ("use_cases", "coverage_gaps", "rows"), ("use_cases", "bid_up", "rows"),
                 ("top_queries_by_purchases",)):
        node = summ
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, list):
            enrich(node, owner)
            for r in node:
                if r.get("search_volume") is not None:
                    r["head_term"] = bool(float(r["search_volume"]) >= a.head_volume)
    summ["owner_note"] = ("top_asin = the store's product with most clicks on that search (detail rows); price_gap = its "
                          "median click price vs the market's, per listing (pack size not normalised).")
    summ["params"]["head_volume"] = a.head_volume
    if "_judged" in summ:
        j = summ.pop("_judged")
        for k in ("top_asin", "price_top_asin", "price_mkt_median", "price_gap"):
            j[k] = j["query"].map(lambda q, k=k: (owner.get(q) or {}).get(k))
        for c in j.columns:
            if c not in ("query", "quadrant", "behaviour", "top_asin"):
                j[c] = pd.to_numeric(j[c], errors="coerce")
            if j[c].dtype.kind == "f":
                j[c] = j[c].round(4 if c.endswith(("_share", "cvr_brand", "cvr_mkt", "price_gap")) else 2)
        j.to_csv(os.path.join(a.out, "sqp_actions.csv"), index=False, encoding="utf-8")
        summ["actions_file"] = {"file": "sqp_actions.csv", "rows": int(len(j)),
                                "note": "every search with 20+ clicks, ranked by orders within reach"}
    if pri_q is not None:
        d = decompose(cur_q, pri_q)
        if d is not None and not d.empty:
            d.to_csv(os.path.join(a.out, "sqp_share_decomposition.csv"), index=False, encoding="utf-8")
            summ["share_decomposition"] = {
                "verdict_counts": d["verdict"].value_counts().to_dict(),
                "real_loss_top": _rec(d[d["verdict"] == "real_loss"].sort_values("brand_purch_t0", ascending=False),
                                      list(d.columns), a.top)}
        summ["demand_index"] = demand_index(cur_q, pri_q)
    else:
        summ["share_decomposition"] = "needs a prior period (second export or tool weeks)"
        summ["demand_index"] = "needs a prior period"

    with open(os.path.join(a.out, "sqp_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else str(o))
    print(json.dumps({"out": a.out, "notes": notes, "coverage": cov}, indent=1))


if __name__ == "__main__":
    main()
