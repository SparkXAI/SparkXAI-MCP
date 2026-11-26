# SQP MCP queries and evidence rules

## Recent spend and term discovery

For broad scope, use `get_ads_perf` on one profile and the last 14 complete store-local days.
Use `factEntity: "asin"`, `metrics: ["Spend"]` and the requested ASIN filter when scoped.
A successful complete result confirming zero ASIN ad spend means no recent eligible ASINs
were found in that scope; skip SQP and offer ads-only context if available. An empty, refused,
truncated or ambiguous response is not proof of zero spend or missing tenant onboarding.
Positive spend is not proof that SQP rows exist.

For a sampled search-term list, the documented `get_ads_perf` request is:

```json
{
  "profileIds": [123],
  "factEntity": "searchTerm",
  "dateStart": "2026-11-01",
  "dateEnd": "2026-11-14",
  "select": ["query_"],
  "metrics": ["Spend", "Clicks", "Conversions", "Sales"],
  "orderBy": [{"field": "Spend", "direction": "DESC"}],
  "page": 1,
  "pageSize": 10,
  "userContext": "Find top paid search terms for a scoped SQP diagnosis"
}
```

Replace sample dates and identifier. Omitting `select` returns totals, not term rows.
The base search-term contract documents `query_`, not `searchTerm.query_`. Use the
actual returned key; do not assume the `p.query_` spelling works across deployments.
Omit `queryType` for mixed coverage. If you need to distinguish product-page traffic,
read `matchType_` as well; it then adds another grouping dimension, so those rows are not
a consolidated spend ranking by term.

Use the diagnosis window actually being analyzed for term discovery, not the separate
14-day eligibility check. When the first page has fewer than 10 distinct shopper queries after excluding
product-page ASIN values, follow `meta.hasNextPage`, advancing only `page`. Stop once there
are 10 eligible queries, the tool reports no next page, or three pages have been read,
whichever comes first. If fewer remain, show the partial sample and the number analyzed;
do not infer a lack of search demand. If no usable text queries remain, show any
verifiable ad context first, then ask for a few search terms or ASINs.

## Market pull

Use `get_market_search_perf` with one authorized profile in `profileIds`, exact
`searchQueries` where known, `factEntity: "marketSearchQuery"`, and the complete
Sunday-Saturday dates. Use `factEntity: "marketAsinQuery"` and explicit `asins` for
own-product detail. Keep requests small; narrow a truncated response rather than ranking it.

- The ads and market calls allow at most 90 days per request. For a longer request,
  start with the most recent up to 12 complete weeks inside the requested range; for
  a comparison, use equal-size supported windows if both sides have enough complete
  weeks. State both the requested and analyzed dates and label the result partial.
  If matching windows are unavailable, report available evidence without a change claim. Never stitch individual
  subperiod Top 10 lists into a full-period ranking.
- On aggregate rows, check `queryWindow`, `weekCount`, `marketWeekCount`, and the notes
  before claiming that numerator and denominator cover the same weeks. Equal counts alone
  are insufficient if other evidence shows different weeks.
- For comparisons check `missingWeekEnds` and the actual week ends on weekly reads. A week
  missing or filtered out is not zero. Dates that are not Sunday and Saturday can expand.
  Select complete contained weeks before aggregating; if an aggregate includes an
  unwanted boundary week, re-query the exact complete-week dates rather than using it.
  Do not compare totals for unequal or nonmatching coverage. Prefer matched complete weeks;
  if a small weekly comparison still cannot be aligned, show available weekly values as
  context and qualify any direction instead of inventing a normalized total or rate.
- For ABA use weekly `marketSearchQuery` with `aggregate: false`. No ABA is expected on
  aggregated or ASIN rows. Check `abaStatus` and which term/weeks contain columns; distinguish
  not requested, no rows returned, and partial evidence. A smaller `abaRank` is better
  relative rank, not proof that absolute demand rose. Use returned search volume to establish
  that. Shares are already percentages.
- Amazon collects at most 100 search terms per ASIN per week. Any list is the top 100 per ASIN
  for those weeks, so a term absent for an ASIN is not proof nobody searched it, and a set of
  terms is never a complete market. Say "the terms returned", not "all terms".
- Rates are ratios, so they do not average. Read a rate from the row whose counts produced it:
  the aggregate row for a period total, the weekly row for that week. Never take the mean of
  weekly rates, and never carry a rate across a differently covered period. When only counts
  line up, state the counts.
- Own and market click-through rates do not share a denominator: the market rate is over all
  impressions on the term, the brand rate only over impressions the store's advertised ASINs
  received. One is not a bar for the other. Judge click-through against the store's own usual
  level across its terms, and say that is the comparison being made. Conversion rates do share
  a denominator shape (purchases over clicks) and can be compared with the market directly.
- Report permission errors as access gaps. An empty eligible pull does not confirm whether
  the tenant is onboarded. Never turn null counts or low-sample rates into zero or a verdict.

For detailed parameter rules, use the sparkx-query-market-data and sparkx-query-ads-performance
Skills by name when they are installed. The scoped workflows above do not require fetching
extra files from the web.
