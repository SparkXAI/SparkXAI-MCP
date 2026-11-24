#!/usr/bin/env python3
"""
Executable tests for sparkx-sqp-insight (stdlib unittest; sqp_calc needs pandas).

Run from anywhere, e.g.:  python -I <skill>/scripts/test_sqp_insight.py -v
All data is synthetic (store "test-store", brands "Brand A" / "Brand B", made-up ids). Covers:
  * tool-shaped get_market_search_perf JSON (marketAsinQuery + marketSearchQuery, real field
    names) -> sqp_rows -> sqp_calc -> sqp_plan end to end
  * the plan rules: grow never lowers, efficiency never raises, conversion < 0.80x -> no raise,
    AI group -> no write + group suggestion, changed in 14 days -> held, typo bid -> -20% default,
    budget raise reads outOfBudgetMinutes, null usage -> not checked, promo window -> plan only.
"""
import json, math, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sqp_rows  # noqa: E402
import sqp_plan  # noqa: E402

PID = 1000000001
WEEKS = [("2026-10-18", "2026-10-24"), ("2026-10-25", "2026-10-31"), ("2026-11-01", "2026-11-07"), ("2026-11-08", "2026-11-14")]
CAT = "Vitamin Example"
A1, A2, AX = "B0EXAMPLE1", "B0EXAMPLE2", "B0OTHER001"

# search -> (market clicks/wk, market purchases/wk, brand clicks/wk, brand purchases/wk)
SEARCH = {
    "alpha drops": (1000, 100, 40, 6),          # 1.5x market, 6% share -> raise
    "beta gummies": (1000, 100, 50, 3.5),       # 0.70x market -> listing path, no raise
    "gamma caps": (1000, 100, 40, 5),           # 1.25x
    "delta powder": (1000, 100, 40, 5),
    "brand a drops": (200, 60, 100, 40),  # own brand
    "epsilon oil": (1000, 100, 40, 6),
    "zeta tabs": (1000, 100, 40, 6),
    "typo term": (1000, 100, 40, 6),
    "new chance": (5000, 400, 10, 1),           # 2.5x market, 0.25% share, few ad clicks -> test
}


def tool_rows():
    rows = []
    for q, (mc, mp, bc, bp) in SEARCH.items():
        for s, e in WEEKS:
            common = {"searchQuery": q, "startDate": s, "endDate": e, "searchVolume": mc * 20,
                      "totalQueryImpressionCount": mc * 50, "totalClickCount": mc, "totalCartAddCount": mc * 0.3,
                      "totalPurchaseCount": mp, "totalCtr": 2.0, "totalCvr": 10.0, "totalMedianClickPrice": 20.0}
            rows.append({**common, "asin": A1, "myBrandImpressionCount": bc * 25, "myBrandClickCount": bc,
                         "myBrandCartAddCount": bc * 0.3, "myBrandPurchaseCount": bp, "myBrandCvr": 15.0,
                         "myBrandCvrLowSample": False, "myBrandMedianClickPrice": 30.0 if q == "beta gummies" else 21.0})
    return rows


def write(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return p


def fixture(d):
    asin_rows = tool_rows()
    # a marketSearchQuery pull: one store row and one market-only (supplemented) term with null own columns
    q_rows = [{"searchQuery": "alpha drops", "startDate": s, "endDate": e, "searchVolume": 20000,
               "totalQueryImpressionCount": 50000, "totalClickCount": 1000, "totalPurchaseCount": 100,
               "myBrandImpressionCount": 1000, "myBrandClickCount": 40, "myBrandPurchaseCount": 6,
               "myBrandCvrLowSample": False} for s, e in WEEKS]
    q_rows.append({"searchQuery": "omega market only", "startDate": WEEKS[0][0], "endDate": WEEKS[0][1],
                   "searchVolume": 900, "totalQueryImpressionCount": 3000, "totalClickCount": 90, "totalPurchaseCount": 9,
                   "myBrandImpressionCount": None, "myBrandClickCount": None, "myBrandPurchaseCount": None})
    p = {}
    p["sqp_asin"] = write(d, "sqp_asin.json", {"data": {"rows": asin_rows, "missingWeekEnds": ["2026-10-17"],
                                                       "queryWindow": {"alignedStart": "2026-10-18", "alignedEnd": "2026-11-14"}},
                                              "meta": {"truncated": False, "limit": 100000, "hint": "synthetic"}})
    p["sqp_query"] = write(d, "sqp_query.json", {"data": {"rows": q_rows, "missingWeekEnds": []}, "meta": {"truncated": False}})
    p["sqp_query_trunc"] = write(d, "sqp_query_trunc.json", {"data": {"rows": q_rows, "missingWeekEnds": []},
                                                            "meta": {"truncated": True, "limit": 100000}})
    # another category's ASIN converting very well on a search the category shares ("beta gummies"),
    # plus a store-level row for that search mixing both: neither may lift the category over the raise line
    shared = []
    for s, e in WEEKS:
        common = {"searchQuery": "beta gummies", "startDate": s, "endDate": e, "searchVolume": 20000,
                  "totalQueryImpressionCount": 50000, "totalClickCount": 1000, "totalCartAddCount": 300,
                  "totalPurchaseCount": 100}
        shared.append({**common, "asin": AX, "myBrandImpressionCount": 2000, "myBrandClickCount": 80,
                       "myBrandCartAddCount": 30, "myBrandPurchaseCount": 30, "myBrandCvrLowSample": False})
    p["sqp_shared_asin"] = write(d, "sqp_shared_asin.json", {"data": {"rows": shared}, "meta": {"truncated": False}})
    p["sqp_shared_query"] = write(d, "sqp_shared_query.json", {"data": {"rows": [
        {"searchQuery": "beta gummies", "startDate": s, "endDate": e, "searchVolume": 20000,
         "totalQueryImpressionCount": 50000, "totalClickCount": 1000, "totalPurchaseCount": 100,
         "myBrandImpressionCount": 3250, "myBrandClickCount": 130, "myBrandPurchaseCount": 33.5,
         "myBrandCvrLowSample": False} for s, e in WEEKS]}, "meta": {"truncated": False}})
    p["asin_meta"] = write(d, "asin.json", [
        {"asin": A1, "parentAsin": "B0PARENT01", "asinBsrCategoryName": CAT, "asinPrice": 30.0, "sku": "EX-SKU-1"},
        {"asin": A2, "parentAsin": "B0PARENT01", "asinBsrCategoryName": CAT, "asinPrice": 19.0, "sku": "EX-SKU-2"},
        {"asin": AX, "parentAsin": "B0PARENT09", "asinBsrCategoryName": "Other Category", "asinPrice": 9.0}])
    # keywords: (amazonId, internalId, text, campaign internal id, bid, clicks, spend, sales)
    kws = [("9001", 501, "alpha drops", 11, 1.00, 60, 60, 400),        # ACOS 15 -> raise
           ("9002", 502, "beta gummies", 11, 1.00, 60, 60, 600),       # ACOS 10 but 0.70x -> no raise
           ("9003", 503, "gamma caps", 13, 1.00, 50, 100, 200),        # ACOS 50 -> -20%
           ("9004", 504, "delta powder", 13, 1.00, 50, 100, 300),      # ACOS 33 -> -15%
           ("9005", 505, "brand a drops", 13, 1.00, 50, 120, 200),  # own brand, ACOS 60 -> never cut
           ("9006", 506, "epsilon oil", 12, 1.00, 60, 60, 400),        # AI group campaign
           ("9007", 507, "zeta tabs", 11, 1.00, 60, 60, 400),          # changed 5 days ago
           ("9008", 508, "typo term", 11, 10.00, 30, 30, 200)]         # bid 10 vs CPC 1
    p["target_perf"] = write(d, "target_perf.json", {"data": {"rows": [
        {"target.targetId_": amz, "target.targetText_": t, "target.targetMatchType_": "exact",
         "campaign.campaignId_": str(7000 + cid), "adGroup.adGroupId_": str(8000 + cid),
         "Clicks": cl, "Spend": sp, "Sales": sa, "Conversions": sa / 25} for amz, _, t, cid, _, cl, sp, sa in kws]}})
    p["keyword_meta"] = write(d, "kw.json", [
        {"keywordId": iid, "amazonKeywordId": amz, "adGroupId": 600 + cid, "campaignId": cid, "campaignType": "sponsoredProducts",
         "matchType": "exact", "keywordText": t, "keywordBid": bid, "keywordState": "enabled", "profileId": str(PID)}
        for amz, iid, t, cid, bid, *_ in kws])
    p["campaign_meta"] = write(d, "camp.json", [
        {"campaignId": 11, "amazonCampaignId": "7011", "campaignName": "EX SP main", "campaignState": "enabled",
         "campaignType": "sponsoredProducts", "aiGroupId": 0, "dailyBudget": 50.0, "profileId": str(PID),
         "budgetUsage": {"outOfBudgetMinutes": 1500, "outOfBudgetPercentage": 3.1}},
        {"campaignId": 12, "amazonCampaignId": "7012", "campaignName": "EX SP managed", "campaignState": "enabled",
         "campaignType": "sponsoredProducts", "aiGroupId": 77, "dailyBudget": 40.0, "profileId": str(PID),
         "budgetUsage": {"outOfBudgetMinutes": 2000}},
        {"campaignId": 13, "amazonCampaignId": "7013", "campaignName": "EX SP costly", "campaignState": "enabled",
         "campaignType": "sponsoredProducts", "aiGroupId": 0, "dailyBudget": 30.0, "profileId": str(PID),
         "budgetUsage": {"outOfBudgetMinutes": 0}},
        {"campaignId": 14, "amazonCampaignId": "7014", "campaignName": "EX SP unknown usage", "campaignState": "enabled",
         "campaignType": "sponsoredProducts", "aiGroupId": 0, "dailyBudget": 20.0, "profileId": str(PID),
         "budgetUsage": {"outOfBudgetMinutes": None}}])
    p["campaign_perf"] = write(d, "camp_perf.json", [
        {"campaign.campaignId_": "7011", "Clicks": 210, "Spend": 210, "Sales": 1600, "Conversions": 64},
        {"campaign.campaignId_": "7012", "Clicks": 60, "Spend": 60, "Sales": 400, "Conversions": 16},
        {"campaign.campaignId_": "7013", "Clicks": 150, "Spend": 320, "Sales": 700, "Conversions": 28},
        {"campaign.campaignId_": "7014", "Clicks": 40, "Spend": 20, "Sales": 200, "Conversions": 8}])
    p["ai_groups"] = write(d, "ai.json", [{"aiGroupId": 77, "aiStatus": 1, "targetAcos": 30, "campaignType": "sponsoredProducts"}])
    p["changes"] = write(d, "oplog.json", {"data": {"rows": [
        {"entity": "target", "amazonEntityId": 9007, "createdDate": "2026-11-05 10:00:00", "changeField": "bid"},
        {"entity": "target", "amazonEntityId": 9001, "createdDate": "2026-09-01 10:00:00", "changeField": "bid"}]}})
    p["search_terms"] = write(d, "st.json", [
        {"query_": "new chance", "matchType_": "CLOSE-MATCH", "campaignId_": "7011", "adGroupId_": "8011",
         "targetId_": "1", "Clicks": 5, "Spend": 5, "Sales": 50, "Conversions": 2}])
    return p


def args(p, out, goal, budget="+60%", today="2026-11-10", extra=()):
    a = ["--sqp", p["sqp_asin"], p["sqp_query"], "--category", CAT, "--goal", goal, "--budget", budget,
         "--acos-goal", "25", "--asin-meta", p["asin_meta"], "--target-perf", p["target_perf"],
         "--keyword-meta", p["keyword_meta"], "--campaign-meta", p["campaign_meta"],
         "--campaign-perf", p["campaign_perf"], "--ai-groups", p["ai_groups"], "--changes", p["changes"],
         "--search-terms", p["search_terms"], "--brand-terms", "brand a", "--competitor-terms", "brand b", "--today", today,
         "--profile-id", str(PID), "--out", out]
    return a + list(extra)


def kinds(plan, kind):
    return [r for r in plan["rows"] if r["kind"] == kind]


def find_held(plan, text):
    return [h for h in plan["held"] if text in json.dumps(h["object"])]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="sqp test ")     # a space in the path on purpose
        cls.p = fixture(cls.d)

    def plan(self, goal, **kw):
        out = os.path.join(self.d, f"out_{goal}_{kw.get('budget', 'x')}_{kw.get('today', 'x')}".replace("%", "p").replace("+", ""))
        return sqp_plan.main(args(self.p, out, goal, **kw))


class TestRows(Base):
    def test_tool_rows_normalised(self):
        rows, infos = sqp_rows.load([self.p["sqp_asin"], self.p["sqp_query_trunc"]])
        self.assertEqual({r["source_kind"] for r in rows}, {"tool_asin", "tool_query"})
        r = next(x for x in rows if x["source_kind"] == "tool_asin")
        self.assertEqual((r["query"], r["asin"], r["week_end"]), ("alpha drops", A1, "2026-10-24"))
        self.assertEqual(r["clicks_brand"], 40.0)
        self.assertIs(r["ls_cvr_brand"], False)
        mo = next(x for x in rows if x["query"] == "omega market only")
        self.assertIsNone(mo["purch_brand"])                 # empty, not zero
        notes = " ".join(sqp_rows.coverage_notes(infos))
        self.assertIn("2026-10-17", notes)
        self.assertIn("truncated", notes)

    def test_query_rows_prefer_store_grain_and_sum_weeks(self):
        rows, _ = sqp_rows.load([self.p["sqp_query"]])
        q = {x["query"]: x for x in sqp_rows.query_rows(rows)}
        self.assertEqual(q["alpha drops"]["purch_mkt"], 400.0)       # 4 weeks added, not maxed
        rt = sqp_rows.rates(q["alpha drops"])
        self.assertAlmostEqual(rt["purch_share"], 24 / 400)
        self.assertIsNone(sqp_rows.rates(q["omega market only"])["purch_share"])

    def test_rollup_from_asin_rows_counts_market_once(self):
        rows, _ = sqp_rows.load([self.p["sqp_asin"]])
        extra = [dict(r, asin=A2, clicks_brand=10.0, purch_brand=1.0) for r in rows if r["query"] == "alpha drops"]
        q = {x["query"]: x for x in sqp_rows.query_rows(rows + extra)}
        self.assertEqual(q["alpha drops"]["purch_mkt"], 400.0)       # two ASINs, market still once per week
        self.assertEqual(q["alpha drops"]["purch_brand"], 28.0)

    def test_windows_path_with_date_suffix(self):
        self.assertEqual(sqp_rows.split_spec(r"C:\data\week1.xlsx@2026-10-24"), (r"C:\data\week1.xlsx", "2026-10-24"))
        self.assertEqual(sqp_rows.split_spec(r"D:\a@b\x.json"), (r"D:\a@b\x.json", None))


class TestCalcEndToEnd(Base):
    def test_sqp_calc_runs_on_tool_json(self):
        try:
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("pandas not installed")
        out = os.path.join(self.d, "calc out")
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "sqp_calc.py"), "--current", self.p["sqp_asin"],
                            self.p["sqp_query"], "--out", out, "--split-at", "2026-10-31"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(out, "sqp_summary.json"), encoding="utf-8") as fh:
            s = json.load(fh)
        self.assertIn("store_position", s)
        self.assertEqual(s["inputs"]["weeks_current"], ["2026-11-07", "2026-11-14"])
        self.assertTrue(any("2026-10-17" in n for n in s["notes"]))


class TestPlanRules(Base):
    def test_end_to_end_both(self):
        plan = self.plan("both")
        self.assertTrue(plan["rows"])
        for r in plan["rows"]:
            self.assertIn("call", r)
            self.assertTrue(r["route"]["skill"].startswith("sparkx-"))
        raise_row = kinds(plan, "bid_raise")[0]
        item = raise_row["call"]["request"]["data"][0]
        self.assertEqual(item["id"], 501)                    # internal keywordId, not the Amazon id
        self.assertEqual(item["profileId"], str(PID))
        self.assertEqual(item["matchType"], "exact")
        self.assertEqual(item["bid"], {"type": "setTo", "previousBid": 1.0, "amount": 1.1})

    def plan_sqp(self, name, sqp, goal="both"):
        out = os.path.join(self.d, f"out_{name}")
        a = args(self.p, out, goal)
        i = a.index("--sqp")
        j = next(k for k in range(i + 1, len(a)) if a[k].startswith("--"))
        return sqp_plan.main(a[:i + 1] + list(sqp) + a[j:])

    def test_category_metrics_use_only_its_own_asin_rows(self):
        plan = self.plan_sqp("shared", [self.p["sqp_asin"], self.p["sqp_query"], self.p["sqp_shared_asin"],
                                        self.p["sqp_shared_query"]])
        s = next(x for x in plan["searches"] if x["search"] == "beta gummies")
        self.assertAlmostEqual(s["cvr_index"], 0.70, places=2)      # category ASIN only, not 1.29x store / 3.75x other
        self.assertFalse([r for r in kinds(plan, "bid_raise") if r["object"]["text"] == "beta gummies"])
        self.assertTrue([r for r in kinds(plan, "bid_raise") if r["object"]["text"] == "alpha drops"])

    def test_no_asin_rows_holds_sqp_driven_moves(self):
        plan = self.plan_sqp("noasin", [self.p["sqp_query"]])
        self.assertFalse([r for r in plan["rows"] if r["kind"] in sqp_plan.SQP_DRIVEN])
        self.assertTrue([h for h in plan["held"] if "cannot be split" in h["reason"]])
        self.assertTrue(kinds(plan, "bid_cut"))                     # ad-metric cuts still planned

    def test_unmatched_category_never_plans_the_whole_store(self):
        out = os.path.join(self.d, "out_unknown_cat")
        a = args(self.p, out, "both")
        a[a.index("--category") + 1] = "Unknown Category"
        plan = sqp_plan.main(a)
        self.assertFalse([r for r in plan["rows"] if r["kind"] in sqp_plan.SQP_DRIVEN])
        self.assertFalse(plan["searches"])
        self.assertTrue(any("matched no ASIN" in n for n in plan["meta"]["notes"]))

    def test_truncated_sqp_rows_not_executable(self):
        plan = self.plan_sqp("trunc", [self.p["sqp_asin"], self.p["sqp_query_trunc"]])
        driven = [r for r in plan["rows"] if r["kind"] in sqp_plan.SQP_DRIVEN]
        self.assertTrue(driven)
        for r in driven:
            self.assertFalse(r["executable"])
            self.assertTrue(any("re-pull" in n for n in r["needs"]))
        self.assertTrue([r for r in kinds(plan, "bid_cut") if r["executable"]])
        self.assertTrue(any("truncated" in n for n in plan["meta"]["notes"]))

    def test_grow_never_lowers(self):
        plan = self.plan("grow")
        self.assertFalse(kinds(plan, "bid_cut") + kinds(plan, "budget_cut"))
        for r in plan["rows"]:
            if r.get("pct") is not None:
                self.assertGreater(r["pct"], 0)

    def test_efficiency_never_raises(self):
        plan = self.plan("efficiency")
        self.assertFalse([r for r in plan["rows"] if r["kind"] in ("bid_raise", "budget_raise", "placement_top",
                                                                   "keyword_create", "test_campaign")])
        cuts = {r["object"]["text"]: r["pct"] for r in kinds(plan, "bid_cut")}
        self.assertEqual(cuts.get("gamma caps"), -20)
        self.assertEqual(cuts.get("delta powder"), -15)
        self.assertNotIn("brand a drops", cuts)        # own brand never cut
        self.assertTrue(find_held(plan, "brand a drops"))

    def test_low_conversion_no_raise_listing_path(self):
        plan = self.plan("grow")
        self.assertNotIn("beta gummies", [r["object"].get("text") for r in kinds(plan, "bid_raise")])
        self.assertTrue(any("0.70x" in h["reason"] for h in find_held(plan, "beta gummies")))
        self.assertIn("beta gummies", [t["search"] for t in plan["owner_tasks"]])

    def test_ai_group_no_write_group_suggestion(self):
        plan = self.plan("both")
        self.assertFalse([r for r in plan["rows"] + plan["anomalies"] if r["object"].get("campaign") == "EX SP managed"])
        self.assertTrue(any("AI managed group" in h["reason"] for h in find_held(plan, "epsilon oil")))
        g = plan["group_suggestions"][0]
        self.assertEqual(str(g["aiGroupId"]), "77")
        self.assertIn("rescales every enabled campaign", g["warning"])

    def test_changed_in_14_days_held(self):
        plan = self.plan("both")
        self.assertTrue(any("last 14 days" in h["reason"] for h in find_held(plan, "zeta tabs")))
        self.assertIn("alpha drops", [r["object"]["text"] for r in kinds(plan, "bid_raise")])  # old change ignored

    def test_typo_bid_default_minus_20(self):
        for goal in ("grow", "efficiency"):
            plan = self.plan(goal)
            a = [r for r in plan["anomalies"] if r["object"]["text"] == "typo term"]
            self.assertEqual(len(a), 1)
            self.assertEqual(a[0]["pct"], -20)
            self.assertEqual(a[0]["to"], 8.0)
            self.assertEqual(a[0]["alternative"]["to"], 1.0)
            self.assertNotIn("typo term", [r["object"].get("text") for r in plan["rows"]])

    def test_budget_raise_uses_minutes_and_null_not_checked(self):
        plan = self.plan("grow")
        b = kinds(plan, "budget_raise")
        self.assertEqual([r["object"]["campaign"] for r in b], ["EX SP main"])
        self.assertEqual((b[0]["from"], b[0]["to"]), (50.0, 60.0))
        self.assertEqual(b[0]["call"]["request"]["data"][0]["budget"], {"type": "setTo", "amount": 60.0})
        self.assertIn("EX SP unknown usage", [n["object"]["campaign"] for n in plan["not_checked"]])

    def test_budget_cut_efficiency(self):
        plan = self.plan("efficiency")
        self.assertEqual([(r["object"]["campaign"], r["to"]) for r in kinds(plan, "budget_cut")], [("EX SP costly", 24.0)])

    def test_test_campaign_shape(self):
        plan = self.plan("grow")
        t = kinds(plan, "test_campaign")
        self.assertEqual([r["search"] for r in t], ["new chance"])
        c = t[0]["call"]["arguments"]["campaigns"][0]
        self.assertEqual(c["state"], "paused")
        self.assertIn("budget", c)
        self.assertNotIn("dailyBudget", c)
        self.assertEqual(c["adGroups"][0]["productAds"][0], {"asin": A1, "sku": "EX-SKU-1"})

    def test_promo_window_plan_only(self):
        plan = self.plan("both", today="2026-11-23", extra=("--event", "Black Friday:2026-11-27:2026-11-30"))
        self.assertTrue(plan["meta"]["plan_only"])
        self.assertTrue(plan["rows"])
        self.assertFalse([r for r in plan["rows"] + plan["anomalies"] if r["executable"]])

    def test_grow_same_budget_funds_no_raises(self):
        plan = self.plan("grow", budget="same")
        self.assertFalse(kinds(plan, "bid_raise") + kinds(plan, "budget_raise"))
        self.assertIn("nothing pays for raises", plan["budget_fit"]["note"])

    def test_vendor_ads_only(self):
        out = os.path.join(self.d, "vendor")
        a = args(self.p, out, "both") + ["--store-type", "vendor"]
        plan = sqp_plan.main(a)
        self.assertTrue(plan["meta"]["ads_only"])
        self.assertFalse(kinds(plan, "bid_raise") + kinds(plan, "keyword_create") + kinds(plan, "test_campaign"))
        self.assertTrue(kinds(plan, "bid_cut"))

    def test_markdown_written_utf8(self):
        out = os.path.join(self.d, "md out")
        sqp_plan.main(args(self.p, out, "both"))
        with open(os.path.join(out, "plan_zh.md"), encoding="utf-8") as fh:
            self.assertIn("待确认", fh.read())


class TestReportAndCategory(Base):
    def test_report_renders_with_store_placeholder_and_plan(self):
        try:
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("pandas not installed")
        calc = os.path.join(self.d, "calc for report")
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "sqp_calc.py"), "--current", self.p["sqp_asin"],
                        "--out", calc], check=True, capture_output=True)
        plan_out = os.path.join(self.d, "plan for report")
        sqp_plan.main(args(self.p, plan_out, "both"))
        with open(os.path.join(os.path.dirname(HERE), "references", "example-narrative-health.json"), encoding="utf-8") as fh:
            nar = fh.read().replace("{store}", "test-store")
        narrative = write(self.d, "narrative.json", json.loads(nar))
        html_out = os.path.join(self.d, "report.html")
        for brand in ("sparkx", "none"):
            r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "sqp_report.py"), "--summary",
                                os.path.join(calc, "sqp_summary.json"), "--narrative", narrative, "--brand", brand,
                                "--plan", os.path.join(plan_out, "plan.json"), "--out", html_out],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(html_out, encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("test-store", page)
            self.assertNotIn("{store}", page)
            self.assertEqual("SparkX ·" in page, brand == "sparkx")

    def test_pick_category_default(self):
        import pick_category
        cur = {"P1": {"parent_asin": "P1", "Spend": 900, "TotalSalesAmount": 5000},
               "P2": {"parent_asin": "P2", "Spend": 100, "TotalSalesAmount": 3000}}
        prev = {"P1": {"TotalSalesAmount": 5000}, "P2": {"TotalSalesAmount": 1000}}
        out = pick_category.pick(cur, prev, {"P1": CAT, "P2": "Other Category"})
        self.assertEqual(out["default_category"], CAT)
        self.assertEqual(out["reference_categories"], ["Other Category"])


if __name__ == "__main__":
    unittest.main()
