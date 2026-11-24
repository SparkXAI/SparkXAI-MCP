#!/usr/bin/env python3
"""Golden tests for category_scorecard.py on get_peer_benchmark-shaped JSON - run: python3 scripts/test_scorecard.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from category_scorecard import main, pos
from tool_fixtures import Dir, envelope, peer_row

SP, SB = "sponsoredProducts", "sponsoredBrands"
P = ["1", "10"]  # root -> Herbal Supplements
ROWS = [
    peer_row("A", "10", SP, "CONVERSION", parent="1", path=P, name="Herbal Supplements",
             roas=3.3, roas_p=(1.6, 1.7, 2.0), acos=30.3, acos_p=(40.0, 58.0, 61.0)),  # ACOS columns as the tool gives them
    peer_row("A", "101", SP, "CONVERSION", parent="10", path=P + ["101"], name="Oregano", roas=3.0),   # own value, no peers
    peer_row("A", "102", SP, "CONVERSION", parent="10", path=P + ["102"], name="Leaf", roas=1.0, roas_p=(1.6, 2.0, 2.5)),
    peer_row("A", "103", SB, "CONSIDERATION", parent="2", path=["2", "103"], name="Cons", cpc=1.0, cpc_p=(1.5, 2.0, 3.0),
             roas=1.0, roas_p=(2.0, 3.0, 4.0)),
    peer_row("A", "104", SP, "CONVERSION", parent="10", path=P + ["104"], name="Both", roas=1.0, roas_p=(2.0, 3.0, 4.0)),
    peer_row("A", "104", SB, "CONSIDERATION", parent="10", path=P + ["104"], name="Both", cpc=1.0, cpc_p=(1.5, 2.0, 3.0)),
    peer_row("A", "105", SP, "ALL", parent=None, path=None, name="Odd", roas=9.0, roas_p=(1.0, 2.0, 3.0)),      # unknown goal
    peer_row("A", "106", SP, "CONVERSION", parent=None, path=None, name="Empty", roas=2.5),                    # NO_PEER_BENCHMARK
    peer_row("A", "108", SP, "CONVERSION", parent="10", path=P + ["108"], name="Periods", period="2026-09-01", roas=3.0, roas_p=(4.0, 5.0, 6.0)),
    peer_row("A", "108", SP, "CONVERSION", parent="10", path=P + ["108"], name="Periods", period="2026-10-01", roas=3.0, roas_p=(1.0, 2.0, 2.5)),
    peer_row("A", "109", SP, "CONVERSION", parent="10", path=P + ["109"], name="Fine", roas=2.1, roas_p=(1.6, 2.0, 2.4)),
]
results = []


def check(name, cond):
    results.append((name, bool(cond)))


def run(cats, spend, cmap, meta=None, extra=(), market=True, rows=None, truncated=False):
    D = Dir()
    args = ["--peer", D.w("peer.json", envelope(rows or ROWS, factEntity="browseCategory")),
            "--spend", D.w("s.json", spend), "--category-map", D.w("c.json", cmap),
            "--parent-meta", D.w("m.json", meta or {}), "--brand", "A", "--min-spend", "100",
            "--ad-type-share", "SP:0.9,SB:0.08,SD:0.02", "--out", D.d, *extra]
    if market:
        args += ["--market", D.w("mk.json", {"categories": cats, "notes": [], "truncated": truncated})]
    return main(args)


def card(out, cid):
    return next(c for c in out["categories"] if c["category_key"] == cid)


full = {"conv_vs_market_generic": 1.0, "sqp_coverage_of_ad_spend": 1.0}
one = lambda cat, sales=5000: ([{"parent_asin": "P1", "Spend": 1000, "Sales": sales}], {"P1": cat})

o = run({"101": full}, *one("101")); c = card(o, "101"); pr = c["peer_rows"]["SP"]
check("S1 node walks up via categoryMetadata to Herbal Supplements; level named", pr["level"] == "10"
      and pr["level_name"] == "Herbal Supplements" and pr["own"] == 3.3 and pr["level_note"])
check("S2 fair range = P25-P75 with the tool's own ACOS columns (no re-inversion)", pr["goal_set"]["roas_range"] == [1.6, 2.0]
      and pr["goal_set"]["acos_range"] == [40.0, 61.0] and pr["position"] == "top quarter" and c["play"] == "Scale")
o = run({"102": {"conv_vs_market_generic": 0.6, "sqp_coverage_of_ad_spend": 0.9}}, *one("102"))
check("S3 behind + bottom quarter = Fix first", card(o, "102")["play"] == "Fix first")
o = run({"102": full}, *one("102")); c = card(o, "102")
check("S4 converting + worse than median = Fix ad cost, hand-off to sparkx-sqp-insight plan mode",
      c["play"] == "Fix ad cost" and c["next"] == "sparkx-sqp-insight plan mode: Improve efficiency")
check("S5 CPC above peers' P75 reads bottom quarter (cost flipped)", pos(1.6, 1.0, 1.2, 1.5, False) == "bottom quarter")
o = run({"103": full}, *one("103")); c = card(o, "103")
check("S6 SB CONSIDERATION row judged on cost per click; weak ROAS flagged", c["play_ad_type"] == "SB"
      and c["peer_rows"]["SB"]["metric"] == "cpc" and c["play"] == "Scale" and "bottom 25%" in c["play_note"])
o = run({"104": full}, *one("104")); c = card(o, "104")
check("S7 SP row leads the play when present", c["play_ad_type"] == "SP" and c["play"] == "Fix ad cost" and "SB" in c["peer_rows"])
o = run({"105": full}, *one("105")); c = card(o, "105")
check("S8 unknown goal: row unusable (not read as conversion), said, ACOS basis", c["play_ad_type"] is None
      and "unknown goal 'ALL'" in (c["play_note"] or "") and "account" in c["ad_cost_basis"] and o["unusable_peer_rows"])
o = run({"106": full}, *one("106")); c = card(o, "106")
check("S9 empty peer row: says NO_PEER_BENCHMARK status, never a peer count", "NO_PEER_BENCHMARK" in c["peer_note"]
      and "fewer" not in c["peer_note"] and "account" in c["ad_cost_basis"])
o = run({"109": full}, *one("109"), {"P1": {"brand": "ZZ"}})
check("S10 brand with no peer rows: said in the row", "no peer benchmark rows for brand ZZ" in card(o, "109")["peer_note"])
o = run({"109": {"conv_vs_market_generic": 0.4, "sqp_coverage_of_ad_spend": 0.2}}, *one("109")); c = card(o, "109")
check("S11 market coverage 20%: conversion shown, not used", c["play"] == "Scale" and "not used" in c["converts_note"])
o = run({"109": full}, *one("109"), extra=("--acos-goal", "15"))
check("S12 category ACOS 20% above a 15% goal: Keep", card(o, "109")["play"] == "Keep")
D = Dir()
o = run({"109": full}, *one("109"), extra=("--stock", D.w("st.json", {"P1": 12})))
check("S13 Scale with 12 days of stock = Hold (stock)", card(o, "109")["play"] == "Hold (stock)" and card(o, "109")["next"] == "-")
o = run({"102": full, "109": full}, [{"parent_asin": "P1", "Spend": 1000, "Sales": 4000}, {"parent_asin": "P2", "Spend": 1000, "Sales": 5000}],
        {"P1": "102", "P2": "109"}, extra=("--event", "Black Friday|2026-11-27|2026-11-30", "--today", "2026-11-23"))
check("S14 four days before an event: plan only - Scale via sparkx-promo-prep, Fix ad cost from the day after",
      card(o, "109")["timing"] == "plan only; before Nov 27 via sparkx-promo-prep" and card(o, "102")["timing"] == "from Dec 1")
o = run({"109": full}, *one("109"), extra=("--event", "Black Friday|2026-11-27|2026-11-30", "--today", "2026-11-28"))
check("S15 event in progress is held too (not read as 'now')", o["event"]["in_progress"] and o["event"]["plan_only"]
      and "sparkx-promo-monitor" in card(o, "109")["timing"])
cat = {"107": {"conv_vs_market_generic": 0.5, "sqp_coverage_of_ad_spend": 1, "own_purchases_used": 150, "weeks": 4}}
o = run(cat, [{"parent_asin": "P1", "Spend": 750, "Sales": 3000}, {"parent_asin": "P2", "Spend": 250, "Sales": 2000}],
        {"P1": "107", "P2": "107"}, {"P2": {"brand": "B"}})
check("S16 orders at stake split by ad spend across brands in one category (150 -> 112 / 38)",
      card(o, "107 · A")["orders_if_market_conversion"] == 112 and card(o, "107 · B")["orders_if_market_conversion"] == 38)
o = run({}, *one("109"), market=False, extra=("--account", "vendor")); c = card(o, "109")
check("S17 Vendor / no SQP: runs on peers and ACOS, no SQP hand-off", c["converts_vs_market"] is None and c["play"] == "Scale"
      and "sqp-insight" not in c["next"] and "Vendor" in c["play_note"])
o = run({"108": full}, *one("108")); pr = card(o, "108")["peer_rows"]["SP"]
check("S18 latest period per row key is used, periods never mixed", pr["p50"] == 2.0 and pr["period"] == "2026-10-01")
check("S19 wide P25-P75 spread flagged: range, not median", pr["goal_set"]["wide_spread"] is True)
behind = {"109": {"conv_vs_market_generic": 0.4, "sqp_coverage_of_ad_spend": 1.0}}
check("S20 control: complete market data, converts 0.4x -> Fix listing", card(run(behind, *one("109")), "109")["play"] == "Fix listing")
o = run(behind, *one("109"), truncated=True); c = card(o, "109")
check("S21 truncated market data: market axis not used for the play, said in the row", c["play"] == "Scale"
      and "truncated" in (c["converts_note"] or "") and c.get("orders_if_market_conversion") is None)
check("S22 truncated market data: conversion, band and share not shown, not counted in the summary",
      c["converts_vs_market"] is None and c["converts_band"] is None and c["purchase_share"] is None
      and c["market_data_truncated"] is True and o["converts_summary"].get("behind", 0) == 0)
WK = [peer_row("A", "110", SP, "CONVERSION", parent="10", path=P + ["110"], name="Weekly", period=d, time_unit="WEEK",
               roas=3.0, roas_p=rp) for d, rp in (("2026-10-25", (4.0, 5.0, 6.0)), ("2026-11-01", (1.0, 2.0, 2.5)))]
o = run({"110": full}, *one("110"), rows=ROWS + WK); pr = card(o, "110")["peer_rows"]["SP"]
check("S23 weekly peer rows (the default): latest week used and named, weeks never mixed", pr["p50"] == 2.0
      and pr["period"] == "2026-11-01" and any("WEEK" in x for x in o["peer_periods"]))
o = run({"109": full}, *one("109"), rows=[{"_status": "x"}], extra=("--peer-unavailable", "MCP_tool_benchmark")); c = card(o, "109")
check("S24 peer call refused: access gap named, never 'no peers'; ad cost from account ACOS",
      "not accessible (MCP_tool_benchmark)" in c["peer_note"] and "account" in c["ad_cost_basis"])
o = run({}, *one("109"), market=False, extra=("--market-unavailable", "sqp:read")); c = card(o, "109")
check("S25 market call refused: access gap named in the row, play on peers and ACOS", c["converts_vs_market"] is None
      and "not accessible (sqp:read)" in (c["converts_note"] or "") and "not accessible" in (c["play_note"] or ""))

for n, ok in results:
    print(("PASS " if ok else "FAIL ") + n)
bad = sum(1 for _, ok in results if not ok)
print(f"{len(results) - bad}/{len(results)} passed")
sys.exit(1 if bad else 0)
