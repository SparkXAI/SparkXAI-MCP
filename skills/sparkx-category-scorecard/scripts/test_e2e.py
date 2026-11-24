#!/usr/bin/env python3
"""End to end on tool-shaped JSON: market_by_category -> category_scorecard -> budget_room -> render_scorecard.
Synthetic store "test-store". Run: python3 scripts/test_e2e.py"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import market_by_category, category_scorecard, budget_room, render_scorecard
from tool_fixtures import Dir, envelope, peer_row, sqp_row, ads_campaign, meta_campaign

SPC, SBC = "sponsoredProducts", "sponsoredBrands"
D = Dir()
W = ["2026-10-24", "2026-10-31", "2026-11-07", "2026-11-14"]
# market: Magnesium (cat 501) converts at market; Zinc (cat 502) behind; Probiotics (503) no rows
sqp = []
for w in W[:3]:                      # week of Nov 14 missing
    sqp += [sqp_row("B0MAGCHLD1", "magnesium glycinate", w, 60, 6, 2000, 200), sqp_row("B0MAGCHLD2", "magnesium glycinate", w, 40, 4, 2000, 200),
            sqp_row("B0ZINCCHL1", "zinc supplement", w, 100, 3, 3000, 180)]
market_json = envelope(sqp, missingWeekEnds=[W[3]], queryWindow={"alignedStart": "2026-10-18", "alignedEnd": W[3]})
spend = [{"asin.parent_asin_": "PMAG", "Spend": 20000, "Sales": 100000}, {"asin.parent_asin_": "PZNC", "Spend": 8000, "Sales": 20000},
         {"asin.parent_asin_": "PPRO", "Spend": 6000, "Sales": 15000}]
cmap = {"PMAG": {"id": "501", "name": "Magnesium"}, "PZNC": {"id": "502", "name": "Zinc"}, "PPRO": {"id": "503", "name": "Probiotics"}}
amap = {"B0MAGCHLD1": "PMAG", "B0MAGCHLD2": "PMAG", "B0ZINCCHL1": "PZNC"}
pmeta = {p: {"brand": "Brand A"} for p in cmap}
path = lambda c: ["5", c]
peer = [
    peer_row("Brand A", "501", SPC, "CONVERSION", parent="5", path=path("501"), name="Magnesium",
             roas=5.0, roas_p=(2.5, 3.5, 4.5), acos=20.0, acos_p=(22.2, 28.6, 40.0)),
    peer_row("Brand A", "501", SBC, "CONSIDERATION", parent="5", path=path("501"), name="Magnesium",
             cpc=0.9, cpc_p=(0.8, 1.2, 1.6), ctr=0.6, ctr_p=(0.3, 0.4, 0.5)),
    peer_row("Brand A", "502", SPC, "UNKNOWN_GOAL", parent="5", path=path("502"), name="Zinc", roas=1.0, roas_p=(2.0, 3.0, 4.0)),
    peer_row("Brand A", "503", SPC, "CONVERSION", parent="5", path=path("503"), name="Probiotics", roas=2.5),  # NO_PEER_BENCHMARK
]
o1 = market_by_category.main(["--market", D.w("sqp.json", market_json), "--spend", D.w("spend.json", spend),
                              "--category-map", D.w("cmap.json", cmap), "--asin-parent", D.w("amap.json", amap),
                              "--brand-terms", "brand a", "--out", D.d])
sc = category_scorecard.main(["--peer", D.w("peer.json", envelope(peer, factEntity="browseCategory")), "--market", D.p("market_by_category.json"),
                              "--spend", D.p("spend.json"), "--category-map", D.p("cmap.json"), "--parent-meta", D.w("pm.json", pmeta),
                              "--ad-type-share", "SP:0.85,SB:0.15", "--acos-goal", "30", "--min-spend", "2000",
                              "--event", "Black Friday to Cyber Monday|2026-11-27|2026-11-30", "--today", "2026-11-28", "--out", D.d])
H = 60 * 14
camps = [ads_campaign("7001", "Test Magnesium SP exact", SPC, 4200, 21000), ads_campaign("7002", "Test Zinc SP auto", SPC, 3000, 6000),
         ads_campaign("7003", "Test Probiotics SP", SPC, 2000, 5000), ads_campaign("7004", "Test Magnesium AI", SPC, 2000, 10000),
         ads_campaign("7005", "Test Magnesium SP broad", SPC, 1400, 7000)]
meta = [meta_campaign(71, "7001", "Test Magnesium SP exact", SPC, 300, 6 * H, 18 * H),
        meta_campaign(72, "7002", "Test Zinc SP auto", SPC, 400, 0, 24 * H),
        meta_campaign(73, "7003", "Test Probiotics SP", SPC, 200, usage=False),                 # null budget usage
        meta_campaign(74, "7004", "Test Magnesium AI", SPC, 150, 8 * H, 16 * H, ai_group=900),  # AI group with AI on
        meta_campaign(75, "7005", "Test Magnesium SP broad", SPC, 100, 4 * H, 20 * H)]
op = envelope([{"entity": "campaign", "operationType": "DailyBudget Increased", "amazonCampaignId": 7005, "changedBy": "Manual"}])
br = budget_room.main(["--campaigns", D.w("camp.json", envelope(camps)), "--entities", D.w("meta.json", envelope(meta)),
                       "--ai-groups", D.w("ai.json", envelope([{"aiGroupId": 900, "aiStatus": 1, "aiGroupName": "Test AI group"}])),
                       "--recent-changes", D.w("op.json", op), "--acos-goal", "30", "--budget", "+10%",
                       "--event", "Black Friday to Cyber Monday|2026-11-27|2026-11-30", "--today", "2026-11-28",
                       "--total-sales-14d", "150000", "--out", D.d])
summary = {"headline": "Plan only until Dec 1: 1 capped campaign under 30% ACOS is ready for +$420 a week after Cyber Monday.",
           "do_first": [{"owner": "Ad manager", "action": "After Nov 30, raise Test Magnesium SP exact 300 -> 405", "why": "ACOS 20%, capped 6 h a day"}],
           "opportunity": "Magnesium converts at 1.00x the market with ROAS 5.0 vs peers' 3.5.",
           "challenge": "Zinc converts at 0.30x the market; its peer row has an unknown goal and was not used.",
           "actions": [], "not_checked": "budget usage for 1 campaign ($2.0K)"}
errs = render_scorecard.main(["--in", D.p("category_scorecard.json"), "--budget-room", D.p("budget_room.json"),
                              "--summary", D.w("summary.json", summary), "--store", "test-store", "--period", "synthetic", "--out", D.d])
cards = {c["category_id"]: c for c in sc["categories"]}
rows = list(csv.DictReader(open(D.p("change_list.csv"), encoding="utf-8")))
report = open(D.p("report.md"), encoding="utf-8").read()
html = open(D.p("report.html"), encoding="utf-8").read()
results = [
    ("E1 market read from tool JSON: Magnesium 1.00x, market clicks deduped (6,000 over 3 weeks)",
     o1["categories"]["501"]["conv_vs_market_generic"] == 1.0 and o1["categories"]["501"]["market_clicks_used"] == 6000),
    ("E2 Magnesium: SP leads, top quarter, Scale -> plan only during the event (sparkx-promo-monitor)",
     cards["501"]["play"] == "Scale" and "sparkx-promo-monitor" in cards["501"]["timing"]),
    ("E3 SB CONSIDERATION row kept on cost per click in the goals list", any(g["ad"] == "SB" and g["metric"] == "cpc" for g in cards["501"]["peer_goals"])),
    ("E4 Zinc: unknown goal not used, behind the market on ACOS basis -> Fix first",
     cards["502"]["play_ad_type"] is None and "unknown goal" in cards["502"]["play_note"] and cards["502"]["play"] == "Fix first"),
    ("E5 Probiotics: NO_PEER_BENCHMARK and no market rows -> said, Fix the data first",
     "NO_PEER_BENCHMARK" in cards["503"]["peer_note"] and cards["503"]["converts_vs_market"] is None
     and any("Probiotics" in f["category"] for f in sc["data_fixes"])),
    ("E6 null budget usage -> not checked, not in the CSV", br["plan"]["not_checked_campaigns"] == 1 and not any(r["amazonCampaignId"] == "7003" for r in rows)),
    ("E7 AI group campaign kept out of the CSV, listed with the group", not any(r["amazonCampaignId"] == "7004" for r in rows)
     and br["ai_managed"][0]["aiGroupName"] == "Test AI group"),
    ("E8 recent change and in-event both held: no row ready during Black Friday",
     rows and all(r["ready"] == "no" for r in rows) and "last 7 days" in [r for r in rows if r["amazonCampaignId"] == "7005"][0]["hold"]),
    ("E9 report renders: plan-only banner, peer goal range, no removed sections, summary checks pass",
     not errs and "plan only" in report and "Fair peer goals" in report and "Price and pack" not in report
     and "Branded, non-branded" not in report and "<table>" in html),
]
for n, ok in results:
    print(("PASS " if ok else "FAIL ") + n)
bad = sum(1 for _, ok in results if not ok)
print(f"{len(results) - bad}/{len(results)} passed")
sys.exit(1 if bad else 0)
