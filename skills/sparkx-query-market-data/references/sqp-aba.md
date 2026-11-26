# `get_market_search_perf` - SQP and ABA

One store, one search term per row, one week per row. Own-store counts are summed over that
store's ASINs. Market totals are de-duplicated, but **where** depends on the row: within the
store for main-table rows, across all stores that collected the term for supplemented and
`marketOnly` rows - see "Three kinds of row" in the main skill before describing a number as
market-wide.

⚠️ **Only Seller profiles in US, CA, UK, DE, FR, IT, ES and JP have data.** A Vendor profile or
any other marketplace returns nothing - say it is out of coverage, never that the store has no
demand.

## Choosing the grain

| `factEntity` | Row | Use for |
|---|---|---|
| `marketSearchQuery` | store x search term | demand, share, "should we bid on this" |
| `marketAsinQuery` | own ASIN x search term | which of our products wins or loses a term |

`marketOnly: true` reads only the cross-store market table: market columns plus ABA, **no
own-store columns, no shares, no gaps**. It is how you price a candidate term the store never
ran - the honest phrasing is "this store has no data on this term", not "this term performs
badly for us".

**It only evaluates terms you name.** It requires `factEntity: marketSearchQuery` and explicit
`searchQueries` in `exact` mode (at most 1000), and **rejects** `asins`,
`searchQueryMatchType: contains`, `metricGroups` `score` or `delta`, and any filter on own-brand
metrics, shares or gaps. A term or week missing from the market table is simply absent - the
table drops terms whose values conflict across stores - and is never filled in from the store's
own SQP data.

So there is no "show me terms I should be running" query. Candidates have to come from
somewhere else: the user, the store's own search-term report, `suggestedKeyword`, or a
`contains` root search over terms the store already has.

`aggregate: false` (default) returns one row per week. `aggregate: true` sums the weeks and
recomputes rates from the summed counts - **aggregated rows carry no ABA columns**. Weekly rows
alone are not enough either: ABA needs weekly rows AND `factEntity: marketSearchQuery`. See the
grain table under "ABA columns" below.

⚠️ **On an aggregated row, check `weekCount` against `marketWeekCount` before quoting a share.**
`weekCount` is how many weeks this store had own-ASIN SQP data; `marketWeekCount` is how many
weeks the market columns cover, and the market side can include weeks where the store had no
data at all. When the two differ, the share is **not** own-column over market-column for the
same period, and reading it as one understates the share. The response says so in its notes
when it happens - relay that rather than presenting the ratio as a clean share.

## Selecting terms

| Parameter | Rule |
|---|---|
| `searchQueries` + `searchQueryMatchType: exact` (default) | Case-insensitive exact match on whole terms, at most 1000. Omit for all terms (then the row cap decides) |
| `searchQueryMatchType: contains` | Case-insensitive substring, so the root `shoe` matches `shoes` and `running shoe` |
| `maxTermsPerRoot` | Only with `contains`: terms per root, ranked by search volume high to low. Default 100, max 300 |
| `asins` | At most 500 own ASINs; omit for all |
| `orderBy` | Sort rules. Exact duplicates are de-duplicated before the rule count is checked, so repeating the same rule is no longer rejected |

Use `contains` when the user says "terms with X in them" or names a root; use `exact` when
they hand you a list. Three limits on `contains`:

- **At most 3 roots per call**, and roots below a minimum length are skipped (Japanese roots
  have no minimum).
- **It searches this store's own SQP data only** - terms the store has no row for are *not*
  filled in from the market table. It finds variants of what you already run, not new demand.
- The response carries `termMatches` (how many terms matched, how many were queried). **State
  both in the answer** - "the root matched 940 terms, the top 100 by volume were queried" is
  the honest form.

**There is no negative matching** - "terms *without* X" cannot be queried, so filter
client-side and say you did.

Row volume is terms x weeks (x ASINs for `marketAsinQuery`). Estimate before calling: a
90-day window is 13 weeks, so 500 terms is already 6,500 rows. Narrow the terms or the window
rather than relying on truncation.

## Rates, and the three click-through rates

`metricGroups` loads optional blocks only when asked: `shipping` (same / one / two-day
shipping counts), `medianPrice` (median click / cart / purchase price) and `score` (SQP score).

Three different click-through rates exist and **none of them compare**:

| Rate | Numerator / denominator |
|---|---|
| Market | all products on that term, organic plus ads |
| Own ASIN (SQP) | our products only, organic plus ads |
| Ad (from `get_ads_perf`) | our ads only |

A gap between them is not automatically a problem. Say which one you are quoting.

**Never use Amazon's own `total_click_rate` / `total_cart_add_rate` / `total_purchase_rate`.**
Their denominator is search volume, not impressions or clicks - roughly 20x off from the
click-divided-by-impression definition, and `total_click_rate` can legitimately exceed 100%
because it counts clicks per search, not a share. The tool exposes the correct derived rates;
use those.

## Sample thresholds

A rate computed on too little traffic gets a `*LowSample` flag rather than being hidden:

| Flag driven by | Default | Affects |
|---|---|---|
| `minClicks` | 5 | add-to-cart rate, conversion rate |
| `minImpressions` | 10 | click-through rate |

Both are parameters, so the defaults can be raised for a noisy catalogue. **A flagged rate
must not be used to rank terms, pick terms, or call performance good or bad.** Sort flagged
rows to the end and say their value is unreliable.

An empty `medianPrice` means the price is unavailable - it is not a zero price and not
evidence that nothing sold. Judge sales from the counts.

`score` does not aggregate across weeks; read it per week only.

## ABA columns

### Which pulls carry them

ABA is attached to **weekly `marketSearchQuery` rows only**. Ask for the wrong grain and the
columns are simply absent - which reads like "this market has no ABA data" and is not.

| `factEntity` | `aggregate` | ABA columns |
|---|---|---|
| `marketSearchQuery` | `false` | **Yes** |
| `marketSearchQuery` | `true` | No - aggregated rows carry none |
| `marketAsinQuery` | either | **No - never** |

`marketAsinQuery` is the ASIN x term grain, and it carries no ABA at all. A run that needs both
the per-ASIN view and ABA makes **two calls**: `marketAsinQuery` for the products and
`marketSearchQuery` (weekly) for the demand side, over the same weeks.

The response carries `abaStatus` at the data level (`INCLUDED` when ABA was attached). Read it
before reporting coverage instead of inferring coverage from the rows.

### The fields

| Field | What it is |
|---|---|
| `abaRank` | ABA search frequency rank for that term and week. A **rank**, not a volume |
| `abaTop1Asin` / `abaTop2Asin` / `abaTop3Asin` | The three most-clicked ASINs on that term |
| `abaTop1ClickShare` / `abaTop2ClickShare` / `abaTop3ClickShare` | Each one's share of the term's clicks, already 0-100 |
| `abaTop1ConversionShare` / `abaTop2ConversionShare` / `abaTop3ConversionShare` | Each one's share of the term's conversions, already 0-100 |
| `abaTop3TotalClickShare` | The three together - how concentrated the term is |
| `abaTop3TotalConversionShare` | The three together, on conversions |
| `asinCount` | How many ASINs the term had that week (context for the shares above) |

They answer "how much did the market want this search, which way is it moving, and is it owned
by a few listings".

⚠️ **They are not automatically competitors.** The top three are whatever took the most clicks
on that **search term**, which can include this store's own products, sibling variants of the
same parent, or items from another category that happen to rank for it. Check each ASIN's
identity - against the store's own ASIN list, and against
`get_entity_metadata(entity='competitorProduct')` where that is available - before calling one a
competitor. Reporting an own-brand ASIN as a competitor is the mistake this prevents.

- Shares are **already 0-100**. Do not multiply by 100.
- ABA search frequency rank is a **rank**, not a volume. It cannot be converted into a number
  of searches, and a rank of 1,000 in one marketplace is not comparable with 1,000 in another.
- The rank comes from the term-level table, and **falls back to the top-3 table when the
  term-level table has no row or a null rank** for that term and week. The term-level value
  wins when both exist. So a rank can be present on a row whose other ABA columns are thin -
  do not read its presence as proof the term-level data was complete.
- ABA is an attached column set, not a filter: do not sort or filter the query by ABA values.
- `ABA.dt` aligns with the SQP week **end** date. Aligning on the start date is off by a week.

## Coverage limits to state in the answer

- At most **100 search terms per ASIN per week** are collected. Any "all terms" list is the
  top 100 per ASIN.
- Only ASINs with recent ad spend are covered.
- **The tenant has to be onboarded for this data, and that is a fourth condition on top of the
  three above.** A Seller profile, in a covered marketplace, with ad spend, can still return zero
  rows because the tenant it belongs to has no SQP / ABA ingestion. Observed in November 2026:
  tenant 20442 returned data, while five Seller profiles under tenant 29291 across US, DE and UK
  all returned zero rows while meeting every documented condition.

  **An empty result does not by itself prove which cause applies.** The weeks, the terms or the
  ASINs asked for can also legitimately return nothing. So when a store meets Seller + covered
  marketplace + recent ad spend and still comes back empty on every profile tried, stop
  re-querying and report it as **"no data returned; tenant onboarding status to be confirmed"** -
  never as "no demand", and not as "not onboarded" either. Say what would settle it: a profile
  under the same tenant that is known to return rows, a different week or term set on the same
  profile, or the platform team's own ingestion status.
- The own-ASIN roll-up to store level is a sum over the store's ASINs; it is **not** the
  platform's brand-level figure, and an ASIN counts if it appeared in any week of the window.
- SQP purchases are attributed within 24 hours, ad orders within 7 or 14 days. Do not subtract
  one from the other.

## A single campaign

The tools take terms, not campaigns. To answer "why did this campaign change":

1. Get that campaign's search terms from `get_ads_perf`.
2. Pass the main ones here.

**SD campaigns and product-targeting campaigns have no search terms**, so this path does not
exist for them - say that rather than returning an empty result as if it were a finding.
