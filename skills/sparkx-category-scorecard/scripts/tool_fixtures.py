"""Synthetic data in the real tool shapes (field names from the tool code), shared by the tests. No real store data."""
import json, os, tempfile


def envelope(rows, **data):
    """ToolResponse shape: {"success", "data": {...rows...}, "meta": {...}}"""
    meta = {"truncated": data.pop("truncated", False)}
    return {"success": True, "data": dict(rows=rows, rowCount=len(rows), **data), "meta": meta}


def _status(p):
    if all(v is None for v in p):
        return "NO_PEER_BENCHMARK"
    return "AVAILABLE" if all(v is not None for v in p) else "INCOMPLETE"


def peer_row(brand, cat, ad, goal, parent=None, path=None, name=None, period="2026-10-01", default=True, time_unit="MONTH",
             roas=None, roas_p=(None, None, None), acos_p=(None, None, None), acos=None,
             cpc=None, cpc_p=(None, None, None), ctr=None, ctr_p=(None, None, None), cpm=None, cpm_p=(None, None, None)):
    """One get_peer_benchmark row (BenchmarkQueryService output aliases)."""
    r = {"advertiserAccountId": "A1", "profileId": "1001", "benchmarkBrandId": "id-" + brand.lower().replace(" ", "-"),
         "benchmarkBrandName": brand, "marketplaceValue": "US", "countryCode": "US", "browseCategoryId": cat,
         "browseCategoryPath": name or cat, "browseCategoryLevel": len(path or [cat]) - 1, "adProduct": ad, "goal": goal,
         "timeUnit": time_unit, "periodStart": period, "budgetCurrency": "USD", "isDefaultNode": default, "pulledAt": "2026-11-05"}
    for m, own, p in (("roas", roas, roas_p), ("acos", acos, acos_p), ("cpc", cpc, cpc_p), ("ctr", ctr, ctr_p), ("cpm", cpm, cpm_p)):
        r[m] = own
        r[m + "_p25"], r[m + "_p50"], r[m + "_p75"] = p
        r[m + "_spread"] = (p[2] - p[0]) if p[0] is not None and p[2] is not None else None
        r[m + "_status"] = _status(p)
    r["categoryMetadata"] = {"countryCode": "US", "categoryId": cat, "categoryName": name or cat, "categoryNameEn": name or cat,
                             "parentCategoryId": parent, "pathIds": path, "hierarchyStatus": "COMPLETE" if path else "NOT_FOUND"}
    return r


def sqp_row(asin, query, week_end, own_clicks, own_purch, mkt_clicks, mkt_purch):
    """One get_market_search_perf row, factEntity=marketAsinQuery, weekly (SqpSqlBuilder aliases)."""
    from datetime import date, timedelta
    start = (date.fromisoformat(week_end) - timedelta(days=6)).isoformat()
    r = {"asin": asin, "searchQuery": query, "startDate": start, "endDate": week_end,
         "myBrandClickCount": own_clicks, "myBrandPurchaseCount": own_purch,
         "totalClickCount": mkt_clicks, "totalPurchaseCount": mkt_purch, "searchVolume": mkt_clicks * 5}
    r["myBrandCvrLowSample"] = own_clicks is not None and own_clicks < 5
    r["totalCvrLowSample"] = mkt_clicks is not None and mkt_clicks < 5
    return r


def ads_campaign(aid, name, ctype, spend, sales):
    """get_ads_perf factEntity=campaign row (Amazon campaign id)."""
    return {"campaign.campaignId_": aid, "campaign.campaignName_": name, "campaign.campaignType_": ctype, "Spend": spend, "Sales": sales}


def meta_campaign(cid, aid, name, ctype, budget, oob_min=None, in_min=None, usage=True, ai_group=None, budget_type=None, profile="1001"):
    """get_entity_metadata entity=campaign row with budgetUsage (window fields)."""
    r = {"campaignId": cid, "profileId": profile, "amazonCampaignId": aid, "campaignName": name, "campaignType": ctype,
         "campaignState": "enabled", "dailyBudget": budget, "budgetType": budget_type or "daily", "aiGroupId": ai_group}
    if usage:
        r["budgetUsage"] = {"outOfBudgetMinutes": oob_min, "inBudgetMinutes": in_min,
                            "outOfBudgetPercentage": None if oob_min is None else 99.0,  # deliberately misleading: never used
                            "inBudgetPercentage": None, "timezone": "America/Los_Angeles"}
    else:
        r["budgetUsage"] = None
    return r


class Dir:
    def __init__(self):
        self.d = tempfile.mkdtemp()

    def w(self, name, obj):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return p

    def p(self, *parts):
        return os.path.join(self.d, *parts)
