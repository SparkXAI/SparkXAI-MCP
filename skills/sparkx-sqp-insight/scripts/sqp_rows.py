#!/usr/bin/env python3
"""
sqp_rows.py - the ONE place where SQP input columns are named.

Every other script in this skill (sqp_calc.py, sqp_plan.py, title_audit.py) loads SQP rows
through this module and works on the canonical row schema below. No other script carries a
column alias table: when the tool or an export adds a column, map it here once.

Inputs it reads
  * get_market_search_perf JSON (the whole tool response, its `data`, or a bare row list).
    factEntity is inferred per row: a row with an `asin` is marketAsinQuery (own ASIN x search),
    a row without one is marketSearchQuery (store x search). Weekly rows (default) and
    aggregated rows (`aggregate: true`) are both accepted.
  * The four SparkX SQP Analysis exports (.xlsx): Search Term main page, Search Term detail
    (one sheet per search), ASIN main page, ASIN detail (one sheet per ASIN). Needs openpyxl.
    Exports carry no dates: append `@YYYY-MM-DD` (the Saturday the file's period ends) to the
    path to label it, e.g. `week1.xlsx@2026-10-24`. Windows paths (C:\\...) are fine.

Canonical row (missing value = None, never 0; counts are floats):
  query, asin (None on marketSearchQuery rows and query-level exports), week_start, week_end,
  search_volume, impr_mkt, impr_brand, clicks_mkt, clicks_brand, atc_mkt, atc_brand,
  purch_mkt, purch_brand, med_{click,atc,purch}_price_{mkt,brand},
  ship_{sameday,1d,2d}_{clicks,purch}, ls_{ctr,atcr,cvr}_{brand,mkt} (tool *LowSample flags),
  week_count, market_week_count (aggregated tool rows), cvr_brand_rate / cvr_mkt_rate
  (export fractions, used only to derive a missing click count), source_kind, period, file.

source_kind: tool_query | tool_asin | query_main | query_detail | asin_main | asin_detail.

Rates are never read from the tool (they are percentages there, 3.2 = 3.2%): every rate is
recomputed from counts by rates() below. Stdlib only, except openpyxl for .xlsx exports.
"""
import json, math, os, re

import codecs
from collections import OrderedDict, defaultdict

# ------------------------------------------------------------------ the column maps
# get_market_search_perf output columns (verified against SqpSqlBuilder / the tool description).
TOOL_COLS = {
    "searchQuery": "query", "asin": "asin", "startDate": "week_start", "endDate": "week_end",
    "searchVolume": "search_volume",
    "totalQueryImpressionCount": "impr_mkt", "myBrandImpressionCount": "impr_brand",
    "totalClickCount": "clicks_mkt", "myBrandClickCount": "clicks_brand",
    "totalCartAddCount": "atc_mkt", "myBrandCartAddCount": "atc_brand",
    "totalPurchaseCount": "purch_mkt", "myBrandPurchaseCount": "purch_brand",
    "totalMedianClickPrice": "med_click_price_mkt", "myBrandMedianClickPrice": "med_click_price_brand",
    "totalMedianCartAddPrice": "med_atc_price_mkt", "myBrandMedianCartAddPrice": "med_atc_price_brand",
    "totalMedianPurchasePrice": "med_purch_price_mkt", "myBrandMedianPurchasePrice": "med_purch_price_brand",
    "totalSameDayShippingClickCount": "ship_sameday_clicks", "totalOneDayShippingClickCount": "ship_1d_clicks",
    "totalTwoDayShippingClickCount": "ship_2d_clicks",
    "totalSameDayShippingPurchaseCount": "ship_sameday_purch", "totalOneDayShippingPurchaseCount": "ship_1d_purch",
    "totalTwoDayShippingPurchaseCount": "ship_2d_purch",
    "myBrandCtrLowSample": "ls_ctr_brand", "myBrandCartAddRateLowSample": "ls_atcr_brand",
    "myBrandCvrLowSample": "ls_cvr_brand", "totalCtrLowSample": "ls_ctr_mkt",
    "totalCartAddRateLowSample": "ls_atcr_mkt", "totalCvrLowSample": "ls_cvr_mkt",
    "weekCount": "week_count", "marketWeekCount": "market_week_count",
    # ABA (Brand Analytics), attached to WEEKLY marketSearchQuery rows only.
    # marketAsinQuery rows and aggregate=true rows carry none of these.
    "asinCount": "asin_count", "abaRank": "aba_rank",
    "abaTop1Asin": "aba_top1_asin", "abaTop1ClickShare": "aba_top1_click_share",
    "abaTop1ConversionShare": "aba_top1_conv_share",
    "abaTop2Asin": "aba_top2_asin", "abaTop2ClickShare": "aba_top2_click_share",
    "abaTop2ConversionShare": "aba_top2_conv_share",
    "abaTop3Asin": "aba_top3_asin", "abaTop3ClickShare": "aba_top3_click_share",
    "abaTop3ConversionShare": "aba_top3_conv_share",
    "abaTop3TotalClickShare": "aba_top3_click_share_total",
    "abaTop3TotalConversionShare": "aba_top3_conv_share_total",
}
# Shares above are ALREADY 0-100 - never multiply by 100 again.
# abaRank is a rank, not a volume: it cannot be turned into a number of searches and ranks from
# different marketplaces are not comparable.
# SparkX SQP Analysis export headers.
EXPORT_COLS = {
    "Search Query": "query", "Parent ASIN": "asin", "Search Volume": "search_volume",
    "Impressions-Market": "impr_mkt", "Impressions-Brand": "impr_brand",
    "Clicks-Market": "clicks_mkt", "Clicks-Brand": "clicks_brand",
    "ATC-Market": "atc_mkt", "Add To Cart-Market": "atc_mkt", "ATC-Brand": "atc_brand", "Add To Cart-Brand": "atc_brand",
    "Purchases-Market": "purch_mkt", "Purchases-Brand": "purch_brand",
    "CVR-Brand": "cvr_brand_rate", "CVR-Market": "cvr_mkt_rate",
    "Median Click Price-Market": "med_click_price_mkt", "Clicks-Median Click Price (Market)": "med_click_price_mkt",
    "Median Click Price-Brand": "med_click_price_brand",
    "Median ATC Price-Market": "med_atc_price_mkt", "Median ATC Price-Brand": "med_atc_price_brand",
    "Median Purchase Price-Market": "med_purch_price_mkt", "Purchases-Median Purchase Price (Market)": "med_purch_price_mkt",
    "Median Purchase Price-Brand": "med_purch_price_brand",
    "Purchase By Shipping Duration-Same Day Shipping Purchases (Market)": "ship_sameday_purch",
    "Purchase By Shipping Duration-1 Day Shipping Purchases (Market)": "ship_1d_purch",
    "Purchase By Shipping Duration-2 Day Shipping Purchases (Market)": "ship_2d_purch",
    "Click By Shipping Duration-Same Day Shipping Clicks (Market)": "ship_sameday_clicks",
    "Click By Shipping Duration-1 Day Shipping Clicks (Market)": "ship_1d_clicks",
    "Click By Shipping Duration-2 Day Shipping Clicks (Market)": "ship_2d_clicks",
}
CANON = ["query", "asin", "week_start", "week_end", "search_volume",
         "impr_mkt", "impr_brand", "clicks_mkt", "clicks_brand", "atc_mkt", "atc_brand", "purch_mkt", "purch_brand",
         "med_click_price_mkt", "med_click_price_brand", "med_atc_price_mkt", "med_atc_price_brand",
         "med_purch_price_mkt", "med_purch_price_brand",
         "ship_sameday_clicks", "ship_1d_clicks", "ship_2d_clicks", "ship_sameday_purch", "ship_1d_purch", "ship_2d_purch",
         "ls_ctr_brand", "ls_atcr_brand", "ls_cvr_brand", "ls_ctr_mkt", "ls_atcr_mkt", "ls_cvr_mkt",
         "week_count", "market_week_count", "cvr_brand_rate", "cvr_mkt_rate",
         "asin_count", "aba_rank",
         "aba_top1_asin", "aba_top1_click_share", "aba_top1_conv_share",
         "aba_top2_asin", "aba_top2_click_share", "aba_top2_conv_share",
         "aba_top3_asin", "aba_top3_click_share", "aba_top3_conv_share",
         "aba_top3_click_share_total", "aba_top3_conv_share_total"]
ABA_COLS = [c for c in CANON if c.startswith("aba_")]
TEXT = {"query", "asin", "week_start", "week_end",
        "aba_top1_asin", "aba_top2_asin", "aba_top3_asin"}
FLAGS = {c for c in CANON if c.startswith("ls_")}
BRAND_COUNTS = ["impr_brand", "clicks_brand", "atc_brand", "purch_brand"]
MARKET_COUNTS = ["search_volume", "impr_mkt", "clicks_mkt", "atc_mkt", "purch_mkt",
                 "ship_sameday_clicks", "ship_1d_clicks", "ship_2d_clicks",
                 "ship_sameday_purch", "ship_1d_purch", "ship_2d_purch"]
QUERY_KINDS = ("tool_query", "query_main")          # one row per search (market counted once)
ASIN_KINDS = ("tool_asin", "query_detail", "asin_detail")   # own ASIN x search rows
EXPORT_ROW_CAP = 10000                               # Search Term main page export cap
DATE_SUFFIX = re.compile(r"^(.*)@(\d{4}-\d{2}-\d{2})$")


def num(v, rate=False):
    """Number or None. Empty, '-', NaN -> None. '17%' -> 0.17 when rate=True."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "--", "N/A", "n/a", "null", "None"):
        return None
    pct = s.endswith("%")
    try:
        x = float(s.rstrip("%"))
    except ValueError:
        return None
    return x / 100 if (pct and rate) else x


def flag(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes")


def norm_query(q):
    """Join key for search text: lowercase, '+' removed, spaces collapsed."""
    return " ".join(str(q or "").lower().replace("+", " ").split())


def _blank():
    return {c: None for c in CANON}


def _map_row(src, colmap, kind, period, file):
    r = _blank()
    for k, v in src.items():
        c = colmap.get(k) or (k if k in r else None)       # canonical keys pass through
        if not c:
            continue
        if c in TEXT:
            r[c] = None if v in (None, "") else str(v).strip()
        elif c in FLAGS:
            r[c] = flag(v)
        else:
            r[c] = num(v, rate=c.endswith("_rate"))
    for c in ("med_click_price_mkt", "med_click_price_brand", "med_atc_price_mkt", "med_atc_price_brand",
              "med_purch_price_mkt", "med_purch_price_brand"):
        if r[c] is not None and r[c] <= 0:          # median price 0 = no data
            r[c] = None
    if r["week_end"]:
        r["week_end"] = r["week_end"][:10]
    if r["week_start"]:
        r["week_start"] = r["week_start"][:10]
    r["source_kind"], r["period"], r["file"] = kind, period, file
    return r


# ------------------------------------------------------------------ tool JSON
def _tool_payload(obj):
    """Return (rows, data, meta) from a tool response, its data object, or a bare list."""
    if isinstance(obj, list):
        return obj, {}, {}
    if not isinstance(obj, dict):
        return [], {}, {}
    data = obj.get("data") if isinstance(obj.get("data"), dict) else obj
    meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
    return data.get("rows") or [], data, meta


def load_tool_json(path, period="current", week_end=None):
    # utf-8-sig: _is_json() already tolerates a BOM, so the reader has to as well -
    # Windows exports and some saved tool results carry one and json.load chokes on it.
    with open(path, encoding="utf-8-sig") as fh:
        obj = json.load(fh)
    raw, data, meta = _tool_payload(obj)
    rows = []
    for src in raw:
        kind = "tool_asin" if src.get("asin") else "tool_query"
        r = _map_row(src, TOOL_COLS, kind, period, os.path.basename(path))
        if week_end and not r["week_end"]:
            r["week_end"] = week_end
        rows.append(r)
    info = {"file": os.path.basename(path), "kind": "tool", "rows": len(rows),
            "kinds": sorted({r["source_kind"] for r in rows}),
            "query_window": data.get("queryWindow"), "missing_week_ends": data.get("missingWeekEnds") or [],
            "truncated": bool(meta.get("truncated")), "row_limit": meta.get("limit"),
            "hint": meta.get("hint"), "term_matches": data.get("termMatches"),
            "aba_status": data.get("abaStatus"),
            "aggregated": any(r["week_count"] is not None for r in rows),
            "columns_found": sorted({TOOL_COLS[k] for s in raw[:50] for k in s if k in TOOL_COLS})}
    return rows, info


# ------------------------------------------------------------------ xlsx exports
def _sheet_rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def load_export(path, period="current", week_end=None):
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("Reading .xlsx exports needs openpyxl: pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    names = wb.sheetnames
    first = _sheet_rows(wb[names[0]])
    row0 = [str(x) if x is not None else "" for x in (first[0] if first else [])]
    out, kinds = [], []
    base = os.path.basename(path)

    def emit(header, body, kind, extra):
        hdr = [str(h).strip() if h is not None else "" for h in header]
        for vals in body:
            if not any(v not in (None, "") for v in vals):
                continue
            src = dict(zip(hdr, vals))
            if kind == "query_main":
                src.pop("ASIN", None)                   # here "ASIN" is a count of ASINs
            if kind == "asin_main":
                src.pop("Search Query", None)           # here "Search Query" is a count of searches
            if kind == "query_detail" and "ASIN" in src and not src.get("Parent ASIN"):
                src["Parent ASIN"] = src["ASIN"]
            src.update(extra)
            r = _map_row(src, EXPORT_COLS, kind, period, base)
            if week_end:
                r["week_end"] = week_end
            out.append(r)

    if len(names) > 1 and "Parent ASIN" not in row0 and "Search Query" not in row0:
        for sh in names:                                 # Search Term detail: row0 = query, row1 = header
            rows = _sheet_rows(wb[sh])
            if len(rows) < 2:
                continue
            emit(rows[1], rows[2:], "query_detail", {"Search Query": rows[0][0]})
        kinds.append("query_detail")
    elif len(names) > 1 and row0 and row0[0] == "Search Query":
        for sh in names:                                 # ASIN detail: one sheet per ASIN
            rows = _sheet_rows(wb[sh])
            if rows:
                emit(rows[0], rows[1:], "asin_detail", {"Parent ASIN": sh})
        kinds.append("asin_detail")
    elif "Parent ASIN" in row0 and "Search Query" in row0:
        emit(first[0], first[1:], "asin_main", {})
        kinds.append("asin_main")
    elif "Search Query" in row0:
        emit(first[0], first[1:], "query_main", {})
        kinds.append("query_main")
    else:
        kinds.append("unknown")
    n_main = sum(1 for r in out if r["source_kind"] == "query_main")
    info = {"file": base, "kind": kinds[0], "rows": len(out), "kinds": kinds, "missing_week_ends": [],
            "truncated": False, "export_cap_hit": n_main >= EXPORT_ROW_CAP, "week_end_label": week_end,
            "columns_found": sorted({EXPORT_COLS[h] for h in row0 if h in EXPORT_COLS})}
    return out, info


# ------------------------------------------------------------------ entry points
def split_spec(spec):
    """'file.xlsx@2026-10-24' -> (file, '2026-10-24'); a Windows path without @date is untouched."""
    m = DATE_SUFFIX.match(spec)
    return (m.group(1), m.group(2)) if m else (spec, None)


def _is_json(path):
    """A JSON tool response starts with '{' or '[' whatever the file is called; .xlsx starts with 'PK'."""
    if path.lower().endswith((".xlsx", ".xls")):
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(4096).lstrip()
    except OSError:
        return path.lower().endswith(".json")
    if head[:2] == b"PK":
        return False
    if head[:3] == codecs.BOM_UTF8:
        head = head[3:].lstrip()
    return head[:1] in (b"{", b"[")


def load(paths, period="current"):
    """Load any mix of tool JSON and exports. Returns (rows, infos)."""
    rows, infos = [], []
    for spec in paths or []:
        path, wk = split_spec(spec)
        # S4: tool responses that exceed the context limit are saved as .txt, so routing on the
        # extension sent them to the .xlsx reader. Sniff the first non-space byte instead.
        if _is_json(path):
            r, i = load_tool_json(path, period, wk)
        else:
            r, i = load_export(path, period, wk)
        rows += r
        infos.append(i)
    fill_counts(rows, infos)
    return rows, infos


def fill_counts(rows, infos=None):
    """Exports without click columns: derive clicks = purchases / CVR (export fraction), marked approximate."""
    derived = set()
    for r in rows:
        for side in ("brand", "mkt"):
            c, p, rate = "clicks_" + side, "purch_" + side, r.get("cvr_%s_rate" % side)
            if r.get(c) is None and r.get(p) is not None and rate:
                r[c] = r[p] / rate
                r["clicks_derived"] = True
                derived.add(r["file"])
    for i in infos or []:
        if i["file"] in derived:
            i["clicks_derived"] = True
    return rows


def _sum(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def collapse_weeks(rows):
    """Window rows: one per (period, source_kind, query, asin). Counts are added across weeks
    (never rates). Market counts on own-ASIN rows are that ASIN's weeks of the search's market.
    Low-sample flags survive only on rows that were not combined (a single week or a tool
    aggregate); combined rows get None and rates() recomputes the flag on the summed counts."""
    groups = OrderedDict()
    for r in rows:
        groups.setdefault((r["period"], r["source_kind"], norm_query(r["query"]), r["asin"]), []).append(r)
    out = []
    for (period, kind, _, asin), g in groups.items():
        if len(g) == 1:
            w = dict(g[0])
            w["weeks"] = [g[0]["week_end"]] if g[0]["week_end"] else []
            out.append(w)
            continue
        w = _blank()
        w.update({"query": g[0]["query"], "asin": asin, "source_kind": kind, "period": period, "file": g[0]["file"]})
        for c in BRAND_COUNTS + MARKET_COUNTS:
            w[c] = _sum(x[c] for x in g)
        weeks = sorted({x["week_end"] for x in g if x["week_end"]})
        w["weeks"], w["week_start"], w["week_end"] = weeks, (min(x["week_start"] for x in g if x["week_start"]) if any(x["week_start"] for x in g) else None), (weeks[-1] if weeks else None)
        for c, wt in (("med_click_price_mkt", "clicks_mkt"), ("med_click_price_brand", "clicks_brand"),
                      ("med_atc_price_mkt", "atc_mkt"), ("med_atc_price_brand", "atc_brand"),
                      ("med_purch_price_mkt", "purch_mkt"), ("med_purch_price_brand", "purch_brand")):
            # a median cannot be added: keep the value from the week with the most weight
            best = max((x for x in g if x[c] is not None), key=lambda x: x[wt] or 0, default=None)
            w[c] = best[c] if best else None
        w["clicks_derived"] = any(x.get("clicks_derived") for x in g)
        out.append(w)
    return out


def query_rows(rows):
    """One row per (period, search) at query grain. For each search, query-grain rows
    (tool_query, then query_main) are used when that search has them; otherwise its own-ASIN rows
    are rolled up: market counts taken ONCE per search and week (they repeat on every ASIN row),
    brand counts added over ASINs and weeks."""
    out = []
    for period in sorted({r["period"] for r in rows}):
        pr = [r for r in rows if r["period"] == period]
        covered = set()
        for kind in QUERY_KINDS:
            src = [r for r in pr if r["source_kind"] == kind and norm_query(r["query"]) not in covered]
            out += collapse_weeks(src)
            covered |= {norm_query(r["query"]) for r in src}
        src = [r for r in pr if r["source_kind"] in ASIN_KINDS and norm_query(r["query"]) not in covered]
        per_week = OrderedDict()
        for r in src:
            per_week.setdefault((norm_query(r["query"]), r["week_end"]), []).append(r)
        weekly = []
        for (_, wk), g in per_week.items():
            w = _blank()
            w.update({"query": g[0]["query"], "asin": None, "week_end": wk, "period": period,
                      "source_kind": "query_from_asin", "file": g[0]["file"]})
            for c in BRAND_COUNTS:
                w[c] = _sum(x[c] for x in g)
            for c in MARKET_COUNTS + ["med_click_price_mkt", "med_atc_price_mkt", "med_purch_price_mkt"]:
                vals = [x[c] for x in g if x[c] is not None]
                w[c] = max(vals) if vals else None
            weekly.append(w)
        out += collapse_weeks(weekly)
    return out


def weeks_seen(rows):
    return sorted({r["week_end"] for r in rows if r.get("week_end")})


def rates(r, min_clicks=5, min_impr=10):
    """Rates and shares from counts (fractions: 0.032 = 3.2%), plus low-sample flags.
    The tool's *LowSample flag is used when the row carries one; otherwise the same rule
    (clicks < min_clicks, impressions < min_impr) is applied to the row's own counts."""
    def div(a, b):
        return (a / b) if (a is not None and b) else None

    def low(tool_flag, count, floor):
        if tool_flag is not None:
            return bool(tool_flag)
        return count is None or count < floor

    o = {"ctr_brand": div(r.get("clicks_brand"), r.get("impr_brand")),
         "ctr_mkt": div(r.get("clicks_mkt"), r.get("impr_mkt")),
         "atcr_brand": div(r.get("atc_brand"), r.get("clicks_brand")),
         "atcr_mkt": div(r.get("atc_mkt"), r.get("clicks_mkt")),
         "cvr_brand": div(r.get("purch_brand"), r.get("clicks_brand")),
         "cvr_mkt": div(r.get("purch_mkt"), r.get("clicks_mkt")),
         "impr_share": div(r.get("impr_brand"), r.get("impr_mkt")),
         "click_share": div(r.get("clicks_brand"), r.get("clicks_mkt")),
         "purch_share": div(r.get("purch_brand"), r.get("purch_mkt"))}
    o["cvr_index"] = div(o["cvr_brand"], o["cvr_mkt"])
    o["ctr_index"] = div(o["ctr_brand"], o["ctr_mkt"])
    o["low_cvr_brand"] = low(r.get("ls_cvr_brand"), r.get("clicks_brand"), min_clicks)
    o["low_ctr_brand"] = low(r.get("ls_ctr_brand"), r.get("impr_brand"), min_impr)
    o["low_cvr_mkt"] = low(r.get("ls_cvr_mkt"), r.get("clicks_mkt"), min_clicks)
    return o


def coverage_notes(infos):
    """Plain-language notes every answer must carry (missing weeks, truncation, caps)."""
    notes = []
    for i in infos:
        if i.get("missing_week_ends"):
            notes.append(f"{i['file']}: no data for the weeks ending {', '.join(i['missing_week_ends'])} "
                         "(missing, not zero).")
        if i.get("truncated"):
            notes.append(f"{i['file']}: the tool hit its row limit ({i.get('row_limit') or 100000}) and truncated "
                         "the result; narrow the searches, ASINs or weeks and pull again.")
        if i.get("export_cap_hit"):
            notes.append(f"{i['file']}: {EXPORT_ROW_CAP} rows - the Search Term main page export cap. Totals across "
                         "searches are a lower bound.")
        if i.get("clicks_derived"):
            notes.append(f"{i['file']}: click columns were missing; clicks derived as purchases / CVR (approximate).")
        if i.get("kind") == "unknown":
            notes.append(f"{i['file']}: layout not recognised; ignored.")
        if i.get("kind") != "tool" and not i.get("week_end_label"):
            notes.append(f"{i['file']}: exports carry no dates - confirm which weeks it covers.")
        if i.get("term_matches"):
            notes.append(f"{i['file']}: termMatches {json.dumps(i['term_matches'], ensure_ascii=False)} "
                         "(state matched vs queried terms).")
        if i.get("hint"):
            notes.append(f"{i['file']}: tool notes to pass on: {i['hint']}")
    return notes


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Normalise SQP inputs and print a short profile (debug aid).")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    rs, inf = load(a.files)
    print(json.dumps({"rows": len(rs), "kinds": sorted({r["source_kind"] for r in rs}),
                      "weeks": weeks_seen(rs), "notes": coverage_notes(inf)}, indent=1, ensure_ascii=False))
