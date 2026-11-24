#!/usr/bin/env python3
"""Market read per category from get_market_search_perf (factEntity=marketAsinQuery, weekly rows).

  python3 market_by_category.py --market sqp_batch1.json --market sqp_batch2.json \
      --spend parent_spend.json --category-map parent_category.json --asin-parent asin_parent.json \
      --brand-terms "<your brand names>" --out out/

Input rows (tool field names, references/data-contract.md): asin, searchQuery, startDate, endDate,
myBrandClickCount, myBrandPurchaseCount, totalClickCount, totalPurchaseCount, *LowSample flags. The file may be the
whole tool response ({"data": {"rows", "missingWeekEnds", ...}, "meta": {"truncated"}}), its "data" object, or a list.

Fallback: --export <file> takes the SparkX SQP "ASIN detail" export (xlsx: one sheet per ASIN, sheet name = ASIN,
rows = searches; needs openpyxl) or a CSV/JSON with an ASIN column. Columns: "Search Query", "Clicks-Brand",
"Purchases-Brand", "Clicks-Market", "Purchases-Market". An export has no week labels: it is treated as one period.

Rules (references/rules.md section 1):
  - Own counts are summed over the category's ASIN rows. Market counts are taken ONCE per search x week (they repeat on
    every ASIN row) - never summed across ASINs.
  - Rates are recomputed from summed counts; row-level rates and *LowSample flags are never used to judge.
  - A row with null own counts is skipped, never read as 0. Missing weeks are reported, never filled.
  - Relevant search = own clicks >= 0.5% of market clicks, or any own purchase, over the window.
  - Generic = relevant searches without a brand term (--brand-terms own, --competitor-terms others). Conversion uses
    generic searches; it falls back to all relevant searches when generic has < 50 own clicks; under 50 own clicks
    on all relevant searches it is not computed (low sample).
  - Coverage = share of the category's ad spend on parent ASINs that have market rows.
  - One read per category (all brands in it together); category_scorecard.py splits orders at stake by ad spend.
Output: market_by_category.json {"categories": {category id: {...}}, "window", "missing_weeks", "truncated", "notes"}
"""
import argparse, csv, json, os, re
from collections import defaultdict


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unwrap(obj):
    """tool response -> (rows, data, meta)"""
    meta = {}
    if isinstance(obj, dict) and "data" in obj and isinstance(obj["data"], (dict, list)):
        meta = obj.get("meta") or {}
        obj = obj["data"]
    if isinstance(obj, list):
        return obj, {}, meta
    return obj.get("rows") or [], obj, meta


def num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(s or "").lower())).strip()


def has_term(q, terms):
    q = " " + q + " "
    return any((" " + t + " ") in q for t in terms if t)


def cat_key(v):
    if isinstance(v, dict):
        return str(v.get("id") or v.get("name"))
    return str(v) if v is not None else None


EXPORT_COLS = {"query": ["Search Query", "searchQuery"], "oc": ["Clicks-Brand", "myBrandClickCount"],
               "op": ["Purchases-Brand", "myBrandPurchaseCount"], "mc": ["Clicks-Market", "totalClickCount"],
               "mp": ["Purchases-Market", "totalPurchaseCount"], "asin": ["ASIN", "asin", "Child ASIN"]}


def pick(r, key):
    for n in EXPORT_COLS[key]:
        if r.get(n) not in (None, ""):
            return r[n]
    return None


def export_rows(path):
    rows = []
    if path.lower().endswith(".xlsx"):
        import openpyxl  # only the export fallback needs it
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            hdr = [str(h).strip() if h is not None else "" for h in next(it, [])]
            for vals in it:
                r = dict(zip(hdr, vals))
                r.setdefault("ASIN", ws.title.strip().upper())
                rows.append(r)
    elif path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        rows, _, _ = unwrap(load(path))
    out = []
    for r in rows:
        out.append({"asin": str(pick(r, "asin") or "").strip().upper(), "searchQuery": pick(r, "query"),
                    "startDate": "export", "endDate": "export",
                    "myBrandClickCount": num(pick(r, "oc")), "myBrandPurchaseCount": num(pick(r, "op")),
                    "totalClickCount": num(pick(r, "mc")), "totalPurchaseCount": num(pick(r, "mp"))})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", action="append", default=[], help="get_market_search_perf response (marketAsinQuery, weekly); repeat per call")
    ap.add_argument("--export", action="append", default=[], help="fallback: SparkX SQP ASIN detail export (.xlsx / .csv / .json)")
    ap.add_argument("--spend", required=True, help="[{parent_asin, Spend, Sales}] 14 days (get_ads_perf)")
    ap.add_argument("--category-map", required=True, help="{parent_asin: category id | {id, name, ...}}")
    ap.add_argument("--asin-parent", help="{child asin: parent asin}; without it an ASIN is its own parent")
    ap.add_argument("--brand-terms", default="", help="own brand names, comma separated (asinBrand plus spacing variants)")
    ap.add_argument("--competitor-terms", default="", help="other brands' names, comma separated (optional)")
    ap.add_argument("--min-share", type=float, default=0.005); ap.add_argument("--min-own-clicks", type=float, default=50)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if not a.market and not a.export:
        ap.error("give --market (tool JSON) or --export (fallback)")

    rows, missing, truncated, notes, windows, low_flags = [], set(), False, [], [], 0
    for p in a.market:
        rs, data, meta = unwrap(load(p))
        rows += rs
        missing |= set(data.get("missingWeekEnds") or [])
        if meta.get("truncated") or data.get("truncated"):
            truncated = True
        if data.get("queryWindow"):
            windows.append(data["queryWindow"])
    for p in a.export:
        rows += export_rows(p)
        notes.append(f"export {os.path.basename(p)}: no week labels, read as one period")
    amap = load(a.asin_parent) if a.asin_parent else {}
    cmap = load(a.category_map)
    spend_rows = load(a.spend)
    bt = [norm(x) for x in a.brand_terms.split(",") if x.strip()]
    ct = [norm(x) for x in a.competitor_terms.split(",") if x.strip()]

    def key_of(parent):
        return cat_key(cmap.get(parent))

    # own counts per (category, query, week); market counts once per (query, week)
    own = defaultdict(lambda: [0.0, 0.0])
    market = {}
    covered_parents = set()
    skipped_null = 0
    weeks = set()
    for r in rows:
        asin = str(r.get("asin") or "").strip().upper()
        q = norm(r.get("searchQuery"))
        if not asin or not q:
            continue
        if any(k.endswith("LowSample") and r.get(k) for k in r):
            low_flags += 1
        oc, op = num(r.get("myBrandClickCount")), num(r.get("myBrandPurchaseCount"))
        mc, mp = num(r.get("totalClickCount")), num(r.get("totalPurchaseCount"))
        wk = str(r.get("endDate") or r.get("startDate") or "")
        if oc is None or op is None or mc is None or mp is None:
            skipped_null += 1
            continue
        parent = amap.get(asin, asin)
        c = key_of(parent)
        if not c:
            continue
        covered_parents.add(parent)
        weeks.add(wk)
        o = own[(c, q, wk)]; o[0] += oc; o[1] += op
        m = market.get((q, wk))
        market[(q, wk)] = (max(m[0], mc), max(m[1], mp)) if m else (mc, mp)

    # coverage of ad spend per category key
    spend_by, cov_by = defaultdict(float), defaultdict(float)
    for s in spend_rows:
        p = s.get("parent_asin") or s.get("asin.parent_asin_") or s.get("parentAsin")
        c = key_of(p)
        if not c:
            continue
        sp = num(s.get("Spend")) or 0
        spend_by[c] += sp
        if p in covered_parents:
            cov_by[c] += sp

    per = defaultdict(lambda: defaultdict(lambda: {"oc": 0.0, "op": 0.0, "mc": 0.0, "mp": 0.0}))
    for (c, q, wk), (oc, op) in own.items():
        mc, mp = market[(q, wk)]
        d = per[c][q]; d["oc"] += oc; d["op"] += op; d["mc"] += mc; d["mp"] += mp

    out = {}
    for c in set(list(per) + list(spend_by)):
        qs = per.get(c, {})
        rel = {q: d for q, d in qs.items() if d["op"] > 0 or (d["mc"] and d["oc"] >= a.min_share * d["mc"])}
        gen = {q: d for q, d in rel.items() if not has_term(q, bt) and not has_term(q, ct)}

        def ratio(ds):
            oc = sum(d["oc"] for d in ds.values()); op = sum(d["op"] for d in ds.values())
            mc = sum(d["mc"] for d in ds.values()); mp = sum(d["mp"] for d in ds.values())
            conv = round((op / oc) / (mp / mc), 2) if oc >= a.min_own_clicks and mc and mp else None
            return conv, oc, op, mc, mp

        cg = ratio(gen); ca = ratio(rel)
        basis = "generic searches" if cg[0] is not None else ("all relevant searches" if ca[0] is not None else None)
        used = cg if cg[0] is not None else ca
        out[c] = {
            "conv_vs_market_generic": cg[0], "conv_vs_market": ca[0], "conversion_basis": basis,
            "low_sample": basis is None and bool(rel),
            "relevant_searches": len(rel), "generic_searches": len(gen),
            "own_clicks_used": round(used[1]), "own_purchases_used": round(used[2]),
            "market_clicks_used": round(used[3]), "market_purchases_used": round(used[4]),
            "purchase_share": round(used[2] / used[4], 4) if used[4] else None,
            "click_share": round(used[1] / used[3], 4) if used[3] else None,
            "sqp_coverage_of_ad_spend": round(cov_by[c] / spend_by[c], 3) if spend_by.get(c) else None,
            "weeks": len({wk for (cc, q, wk) in own if cc == c}),
        }
    if skipped_null:
        notes.append(f"{skipped_null} rows without own or market counts skipped (not read as 0)")
    if low_flags:
        notes.append(f"{low_flags} rows carry *LowSample flags; only summed counts are used, never row rates")
    if truncated:
        notes.append("a response was truncated (meta.truncated): counts are lower bounds - re-pull in smaller ASIN batches before using")
    if missing:
        notes.append("missing weeks (not filled, not 0): " + ", ".join(sorted(missing)))
    res = {"categories": out, "window": windows[0] if windows else None, "weeks_seen": sorted(weeks),
           "missing_weeks": sorted(missing), "truncated": truncated, "notes": notes}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "market_by_category.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    r = main()
    for k, v in r["categories"].items():
        print(k, v["conv_vs_market_generic"], v["conv_vs_market"], v["sqp_coverage_of_ad_spend"])
