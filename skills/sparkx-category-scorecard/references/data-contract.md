# Data contract

Exact call syntax lives in the owning query skills; this page says which call, which window, and which fields the
scripts read. `get_ads_perf` takes `entity.field_` in `select` and returns plain names (`asin.parent_asin_` in,
`parent_asin` out); the scripts accept both forms. `get_entity_metadata` uses plain camelCase.

## Calls

| # | Data | Call | Window | Fields the scripts read | When missing |
|---|---|---|---|---|---|
| 1 | Profile, Seller / Vendor, country | `get_user_authorized_context` | now | `profileId`, country | stop: name the profile that is not authorized |
| 2 | Spend, sales by parent ASIN | `get_ads_perf` `factEntity: asin`, `select: ["asin.parent_asin_"]`, metrics `Spend`, `Sales` | last 14 complete days | `parent_asin`, `Spend`, `Sales` | - |
| 3 | Spend, sales by campaign | `get_ads_perf` `factEntity: campaign`, `select: ["campaign.campaignId_", "campaign.campaignName_", "campaign.campaignType_"]` | same 14 days | campaign id (Amazon), name, type, `Spend`, `Sales`; ad type share is computed from these | - |
| 4 | Daily spend per campaign (optional, sizing) | `get_ads_perf` `factEntity: campaign`, `select` campaign id + `date` | last 30 days | campaign id, `date`, `Spend` | raise sized from hours capped only |
| 5 | Store sales (optional, TACOS) | `get_ads_perf` `factEntity: asin`, metric `TotalSalesAmount` | same 14 days | total | TACOS not shown, said so |
| 6 | Parent, brand, category, stock | `get_entity_metadata` `entity: asin` (or `parentAsin`) | now | `parentAsin`, `asinBrand` / `parentAsinBrand`, `asinCategoryInfo` (JSON array string - parse it), `parentAsinDayAvailability30` | stock: "not checked", never 0 |
| 7 | Campaign ids, budgets, budget usage | `get_entity_metadata` `entity: campaign`, `filters: {"campaignState": {"in": ["enabled"]}}`, `budgetUsageDateStart` / `budgetUsageDateEnd` = the 14 days; if `select` is passed it must include `budgetUsage` | 14 days (max 30) | `campaignId` (internal), `profileId`, `amazonCampaignId`, `campaignName`, `campaignType`, `dailyBudget`, `budgetType`, `aiGroupId`, `budgetUsage.outOfBudgetMinutes` | `budgetUsage: null` = not checked |
| 8 | AI managed groups | `get_entity_metadata` `entity: aiGroup`, `filters: {"aiGroupId": {"in": [...]}}` | now | `aiGroupId`, `aiGroupName`, `aiStatus` (1 = AI running) | group status unknown -> campaign kept out of the change list |
| 9 | Budget changes, last 7 days | `get_operation_log` with one `profileId`, `entities: ["campaign"]`, `resourceIds: [{"idEntity": "campaign", "ids": [<amazonCampaignId>...]}]`, `operationType: {"operator": "IN", "values": ["DailyBudget Increased", "DailyBudget Decreased"]}`, `dateStart` = today - 7, `dateEnd` = today, `pageSize: 1000`, loop `page` while `hasNextPage` | 7 days | `amazonCampaignId` | if the response shows `limit` / `truncated` instead of `hasNextPage`, it did not page: split the window and say the list may be partial |
| 10 | Peer benchmark | `get_peer_benchmark` `profileId`, `timeUnit: "WEEK"`, `dateStart` / `dateEnd` = the last 4 complete Sun-Sat weeks, `metrics: ["roas", "acos", "cpc", "ctr", "cpm"]`, `categoryIds` = the leaf ids from call 6; then a second call with the ancestor ids from `categoryMetadata.pathIds` | latest complete week with a row (`MONTH` only on request and when monthly rows exist) | see below | no row / `_status` `NO_PEER_BENCHMARK` -> said; ad cost from account ACOS |
| 11 | Market search data | `get_market_search_perf` `factEntity: marketAsinQuery`, `asins` = child ASINs of the scored parents (<= 500 a call), `aggregate: false` | last 4 complete Sun-Sat weeks | see below | Vendor / uncovered marketplace: "no market data" (coverage gap, not a finding) |

## Peer rows (`category_scorecard.py --peer`)

Send one authorized numeric `profileId` and pass `categoryIds` as strings. For each set of leaf or
ancestor IDs, start at `page: 1` and use the same filters and `pageSize` (default 1,000, maximum
10,000) on subsequent pages. Collect `data.rows` until `meta.hasNextPage` is false. Pass all
pages to the script before marking a category as missing.

`benchmarkBrandId`, `benchmarkBrandName`, `browseCategoryId`, `adProduct` (`sponsoredProducts` / `sponsoredBrands` /
`sponsoredDisplay`), `goal` (`CONVERSION` / `CONSIDERATION` / `AWARENESS`), `periodStart`, `timeUnit`, `budgetCurrency`,
`isDefaultNode`, and per metric `<m>`, `<m>_p25`, `<m>_p50`, `<m>_p75`, `<m>_spread`, `<m>_status` (`AVAILABLE` /
`NO_PEER_BENCHMARK` / `INCOMPLETE`); `categoryMetadata.parentCategoryId`, `pathIds`, `categoryNameEn`. Brands are matched
on `benchmarkBrandName` (case-insensitive) or `benchmarkBrandId` against the product's brand. Rows are brand peer groups:
never a campaign benchmark, never summed or averaged across rows. The tool has no daily grain.

## Market rows (`market_by_category.py --market`, one file per call)

`asin`, `searchQuery`, `startDate`, `endDate`, `myBrandClickCount`, `myBrandPurchaseCount`, `totalClickCount`,
`totalPurchaseCount`, `*LowSample` (counted, not used); response `missingWeekEnds`, `queryWindow`, `meta.truncated`.
Fallback without the tool: the SparkX SQP "ASIN detail" export (`--export`, one sheet per ASIN; columns `Search Query`,
`Clicks-Brand`, `Purchases-Brand`, `Clicks-Market`, `Purchases-Market`); it has no week labels and is read as one period.

## Files the agent writes for the scripts

| File | Shape | From |
|---|---|---|
| `parent_spend.json` | the call 2 rows as returned | call 2 |
| `parent_category.json` | `{parent: {"id": "<browse category id>", "name": "...", "path_ids": [root..leaf]}}` (`path_ids` optional) | call 6 `asinCategoryInfo`, **after the check below** |

### `asinCategoryInfo` is not always a browse category

The field carries whatever node Amazon attached to the ASIN, and on some accounts that is a
promotional or merchandising node rather than a browse category. Observed values: `Standard`,
`Kategorien`, `Iphone` (a Seller store on Amazon DE), `Bosch Holiday Deals`, `$20 off $100`
(a Vendor store on Amazon US). Scoring on those produces categories that match nothing in the peer
benchmark.

Check before building `parent_category.json`: a usable value is a browse node with a numeric id,
and its name should look like a category path, not a campaign or deal name. If most scored parents
fail that check:

1. Use the browse node that `get_peer_benchmark` itself resolved for the brand (`browseCategoryId`
   on the returned rows) and map every scored parent to it.
2. Say so in the report as a stated deviation - the categories are then one node, not the real
   tree, so "top N categories" and the per-category split are coarser than they look.
3. Never silently score on the polluted values, and never drop the affected parents: dropping them
   would quietly shrink the ad spend the scorecard claims to cover.
| `parent_meta.json` | `{parent: {"brand": "<asinBrand>"}}` | call 6 |
| `asin_parent.json` | `{child asin: parent asin}` | call 6 |
| `stock_days.json` | `{parent or asin: days}` | call 6 |
| `campaign_asins.json` (required for raises) | `{internal campaignId: [asins]}` (Amazon ids also accepted) | `get_entity_metadata` `entity: productAd`, filtered to the scored campaigns, paged to the end: `campaignId` (internal) + `asin`. Without a mapping (and no ASIN in the campaign name) a raise is held as "stock not confirmed"; SB / SD campaigns usually have no product-ad rows and stay held unless the user confirms stock |

## Never use

Amazon `total_click_rate` / `total_cart_add_rate` / `total_purchase_rate` (denominator = search volume);
`outOfBudgetPercentage` for thresholds or ranking; console ACOS or one campaign against a peer row; SQP purchases minus ad
orders as organic sales (different attribution).
