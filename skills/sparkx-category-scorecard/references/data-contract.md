# Category comparison: MCP data contract

## Category scope and performance

Use one authorized profile. For selected ASINs, read metadata with
`get_entity_metadata(entity="asin")`. Request only necessary fields, such as
`asin`, `parentAsin`, `asinTitle`, `asinBrand`, `asinCategoryInfo`,
`parentAsinCategoryInfo` and relevant BSR labels. Category info is a JSON array string
and can be empty or contain merchandising nodes. BSR names are not a crosswalk to
benchmark browse IDs. Titles may suggest a mapping to confirm, not establish one.

With a verified or customer-confirmed child-ASIN set, use `get_ads_perf` with
`factEntity: "asin"`, `filters: {"asin.asin_": {"in": [...]}}` and metrics
`["Spend", "Sales", "ACOS"]`. Omit `select` for a single scoped total; use
`select: ["asin.asin_"]` only for a bounded product breakdown. Keep one currency and
state that these are the ASIN-grain ad metrics, not every campaign's entire spend.
Do not add a parent and its children in the same total. Unknown assignments are not
zero spend. Do not quote a whole-store unknown spend percentage unless that denominator
and the unassigned spend were directly established for the same scope and window.

Ads and peer calls allow at most 90 days per request. For a longer request, first report
the most recent supported subperiod within the requested dates, up to 90 days, with its
actual dates and a partial-coverage label. Find peer weeks inside that analyzed subperiod.
Do not describe its totals, rates or leading ASINs as covering the full requested range.

## Peer matching

Use `get_peer_benchmark` with one numeric `profileId`, explicit verified
`categoryIds` (strings), and `timeUnit: "WEEK"`. When the user specifies a period,
look for complete Sunday-Saturday benchmark weeks inside that period. With no
specified period, use the last four complete weeks. If there is no comparable
week, say so; if useful, show an available week separately as dated background,
never as a match for the requested period. Filter to the relevant ad product and
goal when known.
Compare each matched brand x node x ad product x goal row separately. Follow
`meta.hasNextPage`, advancing only `page`; report the latest complete week with a usable
row. A verified ancestor is broader context, not a leaf score. Check the actual returned
`browseCategoryId` even if the name is empty. A default-node query may discover a
candidate node but does not prove it matches. `sdCategory` may help look up a known
node; never synthesize an ID or assume it maps from a BSR name. Never average peer
percentiles or treat a brand-level row as a campaign benchmark.

Read each percentile in its own direction. For ROAS, CTR and conversion, a higher
percentile is better. **ACOS percentiles are already derived from reversed ROAS
percentiles, so P25 is the good end and P75 the expensive one** - do not re-invert them,
and do not describe a brand sitting at ACOS P25 as behind its peers. CPC and CPM read like
ACOS: lower is cheaper, which is not automatically better. Name the metric, the direction
and the level every time a percentile is quoted.

## Market side of the quadrant

Only for a quadrant placement, and only with a confirmed ASIN scope. Use
`get_market_search_perf` with one authorized profile, `factEntity: "marketAsinQuery"`,
explicit `asins` for the confirmed set, and complete Sunday-Saturday weeks inside the analyzed
period. SQP covers Seller profiles in US, CA, UK, DE, FR, IT, ES and JP, and only ASINs with
recent ad spend, so partial coverage is normal.

Read own purchases per click against the market's on the same rows. Recompute both from summed
counts; never average the returned rates, and never add market counts across ASINs - the same
term repeats across them. State the share of the confirmed scope the returned rows actually
cover. Below roughly half, the market coordinate is not representative of the scope: say so and
do not place the quadrant on it. A flagged low-sample row is not evidence either way.

Market purchases are attributed within 24 hours and ad orders over 7 or 14 days, so the two
sides are compared as directions, not as a subtraction.

## Optional campaign check

Use a few named candidates only, not an account-wide metadata pull. For example:

```json
{
  "profileIds": [123],
  "entity": "campaign",
  "filters": {"amazonCampaignId": {"in": ["298539385213868"]}},
  "select": ["amazonCampaignId", "campaignName", "campaignState", "dailyBudget", "budgetType", "budgetUsage"],
  "budgetUsageDateStart": "2026-11-01",
  "budgetUsageDateEnd": "2026-11-14",
  "page": 1,
  "pageSize": 20,
  "userContext": "Check budget usage for a selected campaign"
}
```

Replace the identifiers and dates. **Both budget usage dates and the `budgetUsage`
field in an explicit `select` are required for this read.**

**Budget usage has its own window and it is not the report's.** The dates must start no
earlier than 30 days ago, end no later than tomorrow, and span at most 30 days. A request
about a historical month, or any range beyond 30 days, cannot be answered here: passing the
report dates through is refused by the service. Check recent budget usage as dated
background instead, say which days it covers, and never present it as budget evidence for
the older window being reported.

Follow pages until complete for the selected candidates. Use `budgetUsage.outOfBudgetMinutes` as an approximate
duration; null means not checked, not zero. If discovering currently active candidates,
filter `campaignState` to `enabled`; do not drop a named paused campaign from a
requested status check. Use `get_operation_log` only if change history is relevant.
An ASIN inventory field may be null; report it as unverified, distinct from low stock.
No inventory or usage outcome in this workflow authorizes a budget change.
