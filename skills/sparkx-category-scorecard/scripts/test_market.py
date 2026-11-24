#!/usr/bin/env python3
"""Golden tests for market_by_category.py on get_market_search_perf-shaped JSON - run: python3 scripts/test_market.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import market_by_category
from tool_fixtures import Dir, envelope, sqp_row

results = []


def check(name, cond):
    results.append((name, bool(cond)))


D = Dir()
W1, W2, W3 = "2026-10-24", "2026-10-31", "2026-11-07"
rows = [
    # two own child ASINs of parent P1 on the same search and week: market totals repeat on both rows
    sqp_row("B0CHILD001", "magnesium glycinate", W1, 30, 3, 1000, 100),
    sqp_row("B0CHILD002", "magnesium glycinate", W1, 20, 2, 1000, 100),
    sqp_row("B0CHILD001", "magnesium glycinate", W2, 50, 5, 1000, 100),
    sqp_row("B0CHILD001", "brand a magnesium", W2, 40, 20, 200, 60),   # own-brand search: not generic
    sqp_row("B0CHILD001", "magnesium powder", W2, None, None, 500, 50),       # null own counts: skipped, never 0
    sqp_row("B0CHILD003", "zinc tablets", W1, 10, 1, 400, 40),                 # Zinc: few own clicks -> low sample
]
resp = envelope(rows, missingWeekEnds=[W3], queryWindow={"alignedStart": "2026-10-18", "alignedEnd": W3})
spend = [{"parent_asin": "P1", "Spend": 9000, "Sales": 30000}, {"parent_asin": "P2", "Spend": 1000, "Sales": 3000},
         {"parent_asin": "P3", "Spend": 2000, "Sales": 5000}]
cmap = {"P1": {"id": "100", "name": "Magnesium"}, "P2": {"id": "100", "name": "Magnesium"}, "P3": "200"}
amap = {"B0CHILD001": "P1", "B0CHILD002": "P1", "B0CHILD003": "P3"}
o = market_by_category.main(["--market", D.w("sqp.json", resp), "--spend", D.w("s.json", spend), "--category-map", D.w("c.json", cmap),
                             "--asin-parent", D.w("a.json", amap), "--brand-terms", "Brand A", "--out", D.d])
m = o["categories"]["100"]
check("M1 market totals once per search x week, never summed across ASINs (2,000 market clicks, not 3,000)",
      m["market_clicks_used"] == 2000 and m["market_purchases_used"] == 200)
check("M2 rate from summed counts: (10 / 100) / (200 / 2000) = 1.00", m["conv_vs_market_generic"] == 1.0 and m["own_clicks_used"] == 100)
check("M3 own-brand search left out of the generic read", m["generic_searches"] == 1 and m["relevant_searches"] == 2)
check("M4 missing week named, not filled", o["missing_weeks"] == [W3] and any(W3 in n for n in o["notes"]))
check("M5 row with null own counts skipped and said", any("skipped" in n for n in o["notes"]))
check("M6 coverage = spend on parents with market rows (9,000 / 10,000)", m["sqp_coverage_of_ad_spend"] == 0.9)
check("M7 under 50 own clicks: conversion not computed, low sample", o["categories"]["200"]["conv_vs_market"] is None
      and o["categories"]["200"]["low_sample"])

# generic too thin -> falls back to all relevant searches
rows2 = [sqp_row("B0CHILD001", "brand a magnesium", W1, 80, 16, 400, 40), sqp_row("B0CHILD001", "magnesium", W1, 10, 1, 500, 50)]
o2 = market_by_category.main(["--market", D.w("sqp2.json", envelope(rows2)), "--spend", D.w("s.json", spend),
                              "--category-map", D.w("c.json", cmap), "--asin-parent", D.w("a.json", amap),
                              "--brand-terms", "brand a", "--out", D.p("o2")])
m2 = o2["categories"]["100"]
check("M8 generic < 50 own clicks: falls back to all relevant searches", m2["conv_vs_market_generic"] is None
      and m2["conversion_basis"] == "all relevant searches" and m2["conv_vs_market"] == round((17 / 90) / (90 / 900), 2))

o3 = market_by_category.main(["--market", D.w("sqp3.json", envelope(rows, truncated=True)), "--spend", D.w("s.json", spend),
                              "--category-map", D.w("c.json", cmap), "--asin-parent", D.w("a.json", amap), "--out", D.p("o3")])
check("M9 meta.truncated carried through with a re-pull note", o3["truncated"] and any("truncated" in n for n in o3["notes"]))

csvp = D.p("export.csv")
with open(csvp, "w", encoding="utf-8") as f:
    f.write("ASIN,Search Query,Clicks-Brand,Purchases-Brand,Clicks-Market,Purchases-Market\n"
            "B0CHILD001,magnesium glycinate,60,6,1000,100\nB0CHILD002,magnesium glycinate,40,4,1000,100\n")
o4 = market_by_category.main(["--export", csvp, "--spend", D.w("s.json", spend), "--category-map", D.w("c.json", cmap),
                              "--asin-parent", D.w("a.json", amap), "--out", D.p("o4")])
check("M10 export fallback: same dedupe, one period, said", o4["categories"]["100"]["market_clicks_used"] == 1000
      and o4["categories"]["100"]["conv_vs_market_generic"] == 1.0 and any("no week labels" in n for n in o4["notes"]))

for n, ok in results:
    print(("PASS " if ok else "FAIL ") + n)
bad = sum(1 for _, ok in results if not ok)
print(f"{len(results) - bad}/{len(results)} passed")
sys.exit(1 if bad else 0)
