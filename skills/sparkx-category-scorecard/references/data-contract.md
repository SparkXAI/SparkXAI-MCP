# Category comparison: MCP data contract

## Store discovery before category selection

For a store-level request without a confirmed scope, use `get_ads_perf` for one authorized
profile, the requested or default report dates, `factEntity: "asin"`, and
`select: ["asin.asin_"]`. Request `Spend`, `Sales`, and `ACOS`, order by Spend descending,
and start with one page of up to 20 rows. Keep rows with positive Spend; use the returned ASIN
identifier rather than the title as the key. This gives leading advertised products, not a
catalog census. If concentration is useful, query the ungrouped ASIN-grain store Spend over
the same scope and dates; divide the sample's spend by that denominator only if both are
complete for their respective scopes. Never use the sample subtotal as the store denominator.

Enrich those ASINs with `get_entity_metadata(entity="asin")`, filtering
`{"asin": {"in": [...]}}` to the selected list. Use brand, parent/child category metadata,
and BSR or title clues to suggest plainly labeled product groups, not verified assignments.
Show the paid-ASIN evidence first, then ask which candidate to analyze if follow-up is needed.
If there are no usable paid rows, distinguish a confirmed zero from an empty, refused, or
partial read. Do not fill the gap by scanning the whole catalog.

For an explicit catalog inventory request, keep it separate from performance. Use small
metadata pages, select only the needed fields, and follow `meta.hasNextPage` when present.
If it is absent, a full page is not proof of completion: probe the next page with otherwise
unchanged parameters. If pages repeat, the probe fails, or the read is truncated or stopped
early, deduplicate by profile and child ASIN and report how many unique child ASINs were read;
do not claim a full catalog. An empty or short final page can end an otherwise consistent, nontruncated read
without paging metadata. Keep row count, distinct child ASIN count, and title count separate.

## Category scope and performance

Use one authorized profile. For selected ASINs, read metadata with
`get_entity_metadata(entity="asin")`. Request only necessary fields, such as
`asin`, `parentAsin`, `asinTitle`, `asinBrand`, `asinCategoryInfo`,
`parentAsinCategoryInfo` and relevant BSR labels. Category info is a JSON array string
and can be empty or contain merchandising nodes. BSR names are not a crosswalk to
benchmark browse IDs. Titles may suggest a mapping to confirm, not establish one.

If category metadata is empty or looks like a merchandising node, check the parent metadata
when available. BSR labels/IDs, titles, the node returned by a default peer query, and
`sdCategory` lookups can suggest a candidate; none alone proves which ASINs belong to it.
Prefer verifying from a trusted product-to-browse assignment. If only the customer confirms
which products to analyze, report the confirmed ASIN scope without claiming a verified
browse assignment. A customer-supplied catalog assignment can be evidence when it explicitly
identifies the products and node; do not require the customer to locate an ID just to get
a useful first result. If mapping is still uncertain, do not infer or invent the category ID.

With a verified or customer-confirmed child-ASIN set, use `get_ads_perf` with
`factEntity: "asin"`, `filters: {"asin.asin_": {"in": [...]}}` and metrics
`["Spend", "Sales", "ACOS"]`. Omit `select` for a single scoped total; use
`select: ["asin.asin_"]` only for a bounded product breakdown. Keep one currency and
state that these are the ASIN-grain ad metrics, not every campaign's entire spend.
Do not add a parent and its children in the same total. Unknown assignments are not
zero spend. Do not quote a whole-store unknown spend percentage unless that denominator
and the unassigned spend were directly established for the same scope and window.

If a confirmed ASIN filter is too large, split it into nonoverlapping batches of distinct
child ASINs. Use identical profile, dates, metrics and currency. Query one subtotal per
batch; combine only additive counts and amounts from complete, successful batches.
Recompute ACOS as total Spend / total Sales and display it as a percentage; compute ROAS as
total Sales / total Spend. Do not compute a ratio with a missing or zero denominator, and do
not scale a tool-returned ACOS percentage again. If all intended batches cannot be verified
or the number of batches is too large for a reliable no-script response, report only the
verified subset or ask to narrow. No fixed ASIN batch-size limit is assumed here.

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

When there is no verified assignment, omitting `categoryIds` can provide a default-node
row as **brand peer background**, not as evidence that the confirmed ASINs belong to the
node. Label it with brand, returned node, ad product, goal and period. Compare only the
brand's own benchmark value with the percentiles **in that same row**. Do not insert this
background into the category comparison or quadrant. If the assignment is later verified,
query using explicit `categoryIds` for the category comparison.

For each reported brand x node x ad product x goal, count the complete Sunday-Saturday weeks
wholly inside the benchmark window and list those with usable returned rows and those
missing. Report the specific usable week selected; never average weekly peer percentiles.
An expanded boundary week is outside the requested scope and can be shown only as dated
background, not counted as coverage. `pulledAt` is the pull time, not proof of why
weeks are missing or when they will arrive. If the request has no dates, label the default
benchmark window separately from the default ad-performance window.

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

Read own purchases per click against the market's on the same rows, recomputing both from
summed counts; never average the returned rates.

**De-duplicate the market side by search term and week.** `marketAsinQuery` repeats a term's
market counts once per ASIN that matched it, so summing the column double-counts. Count each
term-week once, then sum across terms. Own-brand counts are the store's own and do sum across
ASINs. If two rows carry different market counts for the same term and week, the market side is
inconsistent: report that and do not place the quadrant.

**Measure coverage by spend, not by ASIN count.** Coverage is the share of the confirmed
scope's ad spend, in the same window, that belongs to ASINs with usable SQP rows. Half the
products can be a small share of the money, and a market coordinate built on that does not
represent the scope. Below 50% by spend, say so and do not place the quadrant. State the figure
either way. A flagged low-sample row is not evidence in either direction.

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
