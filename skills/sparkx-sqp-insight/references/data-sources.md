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
Omit `queryType` for mixed coverage. Treat a value matching `^B[A-Z0-9]{9}$`
(case-insensitive) as an ASIN candidate, not proof of a product-page placement. Set
ambiguous identifiers aside from default text discovery. If the distinction matters,
read `matchType_` for the candidate: `SUBSTITUTES` and `COMPLEMENTS` are documented
product-side matches. An ASIN can also be typed as a search query; do not label it
product-page traffic on format alone. Adding `matchType_` changes grouping; use those
rows as evidence of match type, not as the original spend ranking. Do not silently drop
an identifier the user explicitly asked to analyze.

Use the planned current diagnosis window for discovery, not the separate 14-day eligibility
check. By default 8 distinct eligible shopper queries are enough; keep at most 10. If there
are fewer than 8, follow `meta.hasNextPage`, advancing only `page`. Stop at a sufficient
sample, no next page, or three pages, whichever comes first. If the user explicitly wants
10, try for 10 within the same cap. Report the actual sample size and dates, including any
difference from the usable SQP window. If no usable text queries remain, show verifiable ad
context first, then ask for a few search terms or ASINs. A small sample does not mean low demand.

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
- Date endpoints are inclusive. The tool moves the start back to the previous or same Sunday
  and the end forward to the next or same Saturday. Already-aligned endpoints do not move.
  Example: 2026-09-27 through 2026-10-17 is exactly three weeks; ending on Sunday 10-18
  instead includes the week ending 10-24. Inspect `queryWindow` before using the result.
  If an aggregate includes an unwanted boundary week, re-query exact week boundaries
  rather than treating it as the requested period.
- For ABA use weekly `marketSearchQuery` with `aggregate: false`. No ABA is expected on
  aggregated or ASIN rows. Check `abaStatus` and which term/weeks contain columns; distinguish
  not requested, no rows returned, and partial evidence. A smaller `abaRank` is better
  relative rank, not proof that absolute demand rose. Use returned search volume to establish
  that. Shares are already percentages.
- The 100-term cap is about own-ASIN collection, not about the market. Amazon collects at most
  100 search terms per ASIN per week, so the own-brand side - `marketAsinQuery` rows and the own
  columns on `marketSearchQuery` - is the top 100 for each ASIN and week. A term missing there
  was not collected for that ASIN; it does not mean the term has no demand, and it does not
  bound a market read of terms you named or an ABA pull. Say "the terms returned for these
  ASINs", not "all terms", and never turn a gap in own coverage into a finding about the market.
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

## Current coverage, then baseline

1. Use the first current-period response both for evidence and coverage. Use aggregate rows
   for period metrics when the week sets can be established; use weekly rows when week
   identity matters or ABA is already needed. Check `queryWindow`, `missingWeekEnds`, per-row
   `weekCount` and `marketWeekCount` where present, and any response notes. A calendar-complete
   week can still be missing in the data. A window-level missing-week list is not proof that
   every term or ASIN has data in all remaining weeks; filtered-out rows are not zeros.
2. For a change question without a specified baseline, use an equal number of consecutive
   complete weeks immediately before the first week in the verified current comparison block.
   Example: a request for 2026-10-25 to 2026-11-21 has four complete weeks; if only the final
   week is missing and the preceding three are verified for the comparison, use 10-25 to
   11-14 as current and 10-04 to 10-24 as baseline. Do not change user-specified baselines.
3. If there are gaps in the middle, counts only, or different coverage by term, do not infer
   week identity from the counts. Use a bounded weekly read for the affected scope if needed
   to verify comparable weeks. If the coverage cannot be matched, show dated observations
   without a period-change claim; do not keep pulling new baselines to fit noisy rows.

## Partial own and market coverage

When market supplementation extends the aggregate market columns beyond the own-data weeks,
the tool keeps its returned own-share metrics on the original own-data weeks. For example,
with `weekCount=2` and `marketWeekCount=3`, retain the term and label the returned share as
partial (two own-data weeks, market columns cover three). Do not recalculate that share
from the displayed market totals. If the share is absent, leave it absent. Own and market
CTR/CVR may be reported as separate values with their own coverage and sample flags. Do not
use mismatched weeks for own-versus-market comparisons or cross-period share changes; verify
the actual week sets first. Equal week counts alone do not prove the sets match.
