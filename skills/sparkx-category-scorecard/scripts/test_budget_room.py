#!/usr/bin/env python3
"""Golden tests for budget_room.py on get_ads_perf / get_entity_metadata / get_operation_log-shaped JSON.
Run: python3 scripts/test_budget_room.py"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import budget_room
from tool_fixtures import Dir, envelope, ads_campaign, meta_campaign

SPC, SBC = "sponsoredProducts", "sponsoredBrands"
H = 60 * 14  # minutes of "1 hour a day" over a 14-day window
camps = [
    ads_campaign("9001", "Test SP CAPPED4", SPC, 1400, 7000),     # ACOS 20%, 4 h/day capped -> +20%
    ads_campaign("9002", "Test SP CAPPED13", SPC, 1400, 7000),    # 13 h/day -> +50%
    ads_campaign("9003", "Test SP NOUSAGE", SPC, 1400, 7000),     # budgetUsage null -> not checked
    ads_campaign("9004", "Test SP PCTONLY", SPC, 1400, 7000),     # percentage 99 but 1 h/day -> not capped
    ads_campaign("9005", "Test SP HIGHCAPPED", SPC, 3000, 7500),  # ACOS 40% capped -> flag
    ads_campaign("9006", "Test SP HIGHFREE", SPC, 2800, 7000),    # ACOS 40% not capped -> lower
    ads_campaign("9007", "Test SP AION", SPC, 1400, 7000),        # AI group on -> ai_managed
    ads_campaign("9008", "Test SP AIOFF", SPC, 1400, 7000),       # AI group off -> normal raise
    ads_campaign("9009", "Test SP AIUNKNOWN", SPC, 1400, 7000),   # group not in --ai-groups -> ai_managed
    ads_campaign("9010", "Test SP RECENT", SPC, 1400, 7000),      # changed in last 7 days -> held
    ads_campaign("9011", "Test SP B0STOCK001", SPC, 1400, 7000),  # 12 days of stock -> held
    ads_campaign("9012", "Test SB LIFETIME", SBC, 1400, 7000),    # lifetime budget -> held
    ads_campaign("9013", "Test SB BANNER", SBC, 4000, 10000),     # SB 40% (<= 2x goal) -> kept
    ads_campaign("9014", "Test SP NOMETA", SPC, 1400, 7000),      # no metadata row -> not checked
    ads_campaign("9015", "Test SP TINY", SPC, 70, 700),           # $5 budget, capped -> floor $10
]
meta = [
    meta_campaign(1, "9001", "Test SP CAPPED4", SPC, 100, 4 * H, 20 * H),
    meta_campaign(2, "9002", "Test SP CAPPED13", SPC, 100, 13 * H, 11 * H),
    meta_campaign(3, "9003", "Test SP NOUSAGE", SPC, 100, usage=False),
    meta_campaign(4, "9004", "Test SP PCTONLY", SPC, 100, 1 * H, 2 * H),
    meta_campaign(5, "9005", "Test SP HIGHCAPPED", SPC, 300, 8 * H, 16 * H),
    meta_campaign(6, "9006", "Test SP HIGHFREE", SPC, 250, 0, 24 * H),
    meta_campaign(7, "9007", "Test SP AION", SPC, 100, 8 * H, 16 * H, ai_group=77),
    meta_campaign(8, "9008", "Test SP AIOFF", SPC, 100, 4 * H, 20 * H, ai_group=78),
    meta_campaign(9, "9009", "Test SP AIUNKNOWN", SPC, 100, 4 * H, 20 * H, ai_group=79),
    meta_campaign(10, "9010", "Test SP RECENT", SPC, 100, 4 * H, 20 * H),
    meta_campaign(11, "9011", "Test SP B0STOCK001", SPC, 100, 4 * H, 20 * H),
    meta_campaign(12, "9012", "Test SB LIFETIME", SBC, 100, 4 * H, 20 * H, budget_type="lifetime"),
    meta_campaign(13, "9013", "Test SB BANNER", SBC, 400, 0, 24 * H),
    meta_campaign(15, "9015", "Test SP TINY", SPC, 5, 10 * H, 14 * H),
]
ai = [{"aiGroupId": 77, "aiGroupName": "Test group", "aiStatus": 1}, {"aiGroupId": 78, "aiStatus": 2}]
oplog = envelope([{"entity": "campaign", "operationType": "DailyBudget Increased", "amazonCampaignId": 9010,
                   "campaignName": "Test SP RECENT", "createdDate": "2026-11-20 09:00:00", "changedBy": "Manual"}],
                 page=1, pageSize=1000, hasNextPage=False)
D = Dir()
# every campaign maps to a product with stock, so only the cases below are held for stock
casins = {str(9000 + i): [f"B0TEST{i:05d}"] for i in range(1, 16)}
casins["9011"] = ["B0STOCK001"]
stock = {f"B0TEST{i:05d}": 60 for i in range(1, 16)}
stock["B0STOCK001"] = 12
base = ["--campaigns", D.w("c.json", envelope(camps)), "--entities", D.w("e.json", envelope(meta)),
        "--ai-groups", D.w("ai.json", envelope(ai)), "--recent-changes", D.w("op.json", oplog),
        "--stock", D.w("st.json", stock), "--acos-goal", "25",
        "--campaign-asins", D.w("cas.json", casins)]
o = budget_room.main(base + ["--budget", "+50%", "--today", "2026-11-10", "--out", D.d])
R = {r["campaign"].split()[-1]: r for r in o["raises"]}; L = {r["campaign"].split()[-1]: r for r in o["lowers"]}
F = {r["campaign"].split()[-1] for r in o["flags"]}; AI = {r["campaign"].split()[-1] for r in o["ai_managed"]}
NC = {r["campaign"].split()[-1] for r in o["not_checked"]}
rows = list(csv.DictReader(open(D.p("change_list.csv"), encoding="utf-8")))
names = {r["campaignName"].split()[-1]: r for r in rows}
results = []


def check(name, cond):
    results.append((name, bool(cond)))


check("B1 capped 4 h/day under goal - 3: raise +20% ($100 -> $120)", R["CAPPED4"]["new_daily_budget"] == 120 and not R["CAPPED4"]["hold"])
check("B2 capped 13 h/day: +50%, the step cap ($100 -> $150)", R["CAPPED13"]["new_daily_budget"] == 150)
check("B3 budgetUsage null: not checked, no move, not in the CSV", "NOUSAGE" in NC and "NOUSAGE" not in names)
check("B4 outOfBudgetPercentage never used: 99% but 1 h/day is not capped", "PCTONLY" not in R and "PCTONLY" not in F)
check("B5 over goal + 5 and capped: flag, budget unchanged, keyword bids via sparkx-sqp-insight", "HIGHCAPPED" in F
      and names["HIGHCAPPED"]["ready"] == "no" and names["HIGHCAPPED"]["dailyBudget_new"] == "" and "sparkx-sqp-insight" in names["HIGHCAPPED"]["reason"])
check("B6 over goal + 5, not capped: lower to 80% of average daily spend ($250 -> $160)",
      L["HIGHFREE"]["new_daily_budget"] == 160 and L["HIGHFREE"]["saving_per_week"] == 280 and names["HIGHFREE"]["ready"] == "yes")
check("B7 AI on: listed under ai_managed, not in the CSV; AI off: normal raise", "AION" in AI and "AION" not in names and "AIOFF" in R)
check("B8 AI group status unknown: kept out of the change list", "AIUNKNOWN" in AI)
check("B9 changed in the last 7 days (op-log rows): held", any("last 7 days" in h for h in R["RECENT"]["hold"]) and names["RECENT"]["ready"] == "no")
check("B10 < 30 days of stock: held", any("stock" in h for h in R["B0STOCK001"]["hold"]))
check("B11 lifetime budget: held (updateBudget is daily only)", any("lifetime" in h for h in R["LIFETIME"]["hold"]))
check("B12 SB inside the banner allowance: kept, not lowered", "BANNER" not in L and any("BANNER" in r["campaign"] for r in o["sb_kept"]))
check("B13 no metadata match: not checked (no internal id to write)", "NOMETA" in NC)
check("B14 floor: a $5 campaign goes to at least $10", R["TINY"]["new_daily_budget"] >= 10 and o["plan"]["under_floor"] == 1)
r = names["CAPPED4"]
check("B15 CSV carries what campaign.updateBudget needs", r["profileId"] == "1001" and r["campaignId"] == "1" and r["amazonCampaignId"] == "9001"
      and r["campaignType"] == SPC and r["budget.type"] == "setTo" and r["budget.amount"] == "120")

ev = budget_room.main(base + ["--budget", "+50%", "--event", "BF|2026-11-27|2026-11-30", "--today", "2026-11-28", "--out", D.p("ev")])
check("B16 event in progress (days < 0) is held: every row ready = no, nothing lowered now",
      all(any("window" in h for h in x["hold"]) for x in ev["raises"] + ev["lowers"]) and ev["plan"]["event"]["in_progress"]
      and ev["lowers"][0]["when"] == "from Dec 1")
ev2 = budget_room.main(base + ["--budget", "+50%", "--event", "BF|2026-11-27|2026-11-30", "--today", "2026-11-23", "--out", D.p("ev2")])
check("B17 four days before the event: plan only (sparkx-promo-prep)", all(any("promo-prep" in h for h in x["hold"]) for x in ev2["raises"]))
daily = [{"campaign.campaignId_": "9001", "date": f"2026-10-{d:02d}", "Spend": v} for d, v in zip(range(1, 8), [100, 100, 140, 400, 100, 100, 100])]
pk = budget_room.main(base + ["--budget", "+50%", "--daily", D.w("d.json", daily), "--out", D.p("pk")])
check("B18 de-spiked peak (2nd highest 140 x 1.1 = 154), capped at +50% ($150)",
      [x for x in pk["raises"] if x["amazonCampaignId"] == "9001"][0]["new_daily_budget"] == 150)
same = budget_room.main(base + ["--budget", "same", "--out", D.p("same")])
check("B19 same budget: raises funded only by ready lowers; the rest does not fit; not placed >= 0",
      same["plan"]["fits_extra_per_week"] <= same["plan"]["savings_per_week"] and same["plan"]["not_placed_per_week"] >= 0
      and any("does not fit" in h for x in same["raises"] for h in x["hold"]))
tg = budget_room.main(base + ["--budget", "+50%", "--total-sales-14d", "200000", "--tacos-goal", "13.5", "--out", D.p("tg")])
t = tg["plan"]["tacos"]
check("B20 TACOS goal caps the weekly extra; now and after shown", "capped_extra_per_week" in t and t["now"] == 12.63 and t["after"] <= 13.5)
# a campaign whose products cannot be resolved: no ASIN in the name, none in --campaign-asins
nos = budget_room.main(base + ["--budget", "+50%", "--campaign-asins",
                               D.w("cas2.json", {k: v for k, v in casins.items() if k != "9001"}), "--out", D.p("nos")])
n1 = [x for x in nos["raises"] if x["amazonCampaignId"] == "9001"][0]
check("B21 stock not confirmed for a raise (no ASIN mapping, none in the name): held",
      n1["stock_days"] is None and any("stock not confirmed" in h for h in n1["hold"]))
# already past the TACOS goal: the cap is 0, cuts fund the raises back up, and the plan still misses the goal.
# The combination is judged, not the allowance: the shortfall is stated on every ready raise.
over = budget_room.main(base + ["--budget", "+50%", "--total-sales-14d", "60000", "--tacos-goal", "30", "--out", D.p("over")])
ot = over["plan"]["tacos"]
ready_over = [x for x in over["raises"] if not x["hold"]]
check("B22 past the TACOS goal and the raises help: shortfall stated on the plan and on every ready raise",
      ot["now"] > 30 and ot["after"] > 30 and ot["goal_missed"] and ot["shortfall_pts"] == round(ot["after"] - 30, 2)
      and ot["after"] < ot["after_cuts_only"] and ready_over
      and all("30% goal" in x["tacos_note"] for x in ready_over))
# the same check the other way: a raise that would make TACOS worse is held, cuts stay
worse = budget_room.main(base + ["--budget", "+50%", "--total-sales-14d", "505400", "--tacos-goal", "4", "--out", D.p("worse")])
wt = worse["plan"]["tacos"]
check("B23 past the goal and the raise does not improve TACOS: held, cuts still ready",
      wt["goal_missed"] and wt["after"] >= wt["after_cuts_only"] and worse["plan"]["fits_extra_per_week"] == 0
      and worse["plan"]["raise_ready"] == 0
      and any(any("does not improve it" in h for h in x["hold"]) for x in worse["raises"])
      and any(x["move"] == "lower" and not x["hold"] for x in worse["lowers"]))
# a campaign advertising two products, only one with a stock figure (60 days): held, the unknown one named
part = budget_room.main(base + ["--budget", "+50%", "--campaign-asins",
                                D.w("cas3.json", {**casins, "9001": ["B0TEST00001", "B0UNKNOWN1"]}), "--out", D.p("part")])
p1 = [x for x in part["raises"] if x["amazonCampaignId"] == "9001"][0]
check("B25 stock known for only some of a campaign's products: raise held, unknown ASIN named",
      p1["stock_days"] is None and p1["stock_unknown_asins"] == ["B0UNKNOWN1"]
      and any("B0UNKNOWN1" in h for h in p1["hold"]))
check("B24 raises held for TACOS: 'after' and the shortfall are recomputed from the ready cuts only",
      wt["after"] == wt["after_cuts_only"] and wt["shortfall_pts"] == round(max(wt["after_cuts_only"] - 4, 0), 2))

for n, ok in results:
    print(("PASS " if ok else "FAIL ") + n)
bad = sum(1 for _, ok in results if not ok)
print(f"{len(results) - bad}/{len(results)} passed")
sys.exit(1 if bad else 0)
