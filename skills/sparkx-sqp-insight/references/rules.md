# Rules - read before quoting any SQP number

Tool behaviour (parameters, row kinds, flags) is defined in `sparkx-query-market-data`
(`references/sqp-aba.md`, `references/peer-benchmark.md`); this file holds the answer rules this
skill adds. `scripts/sqp_rows.py` and `scripts/sqp_calc.py` enforce the numeric ones. Plan-mode
rules are PL1-PL14 in `plan-mode.md`.

## 1. What "brand" means

- SQP "Brand" columns = **the store's advertised ASINs summed** (ASINs with ad spend > 0 in the
  last 14 days). Call it "your advertised ASINs", not "your brand": it is not Amazon's official
  Brand view, and an ASIN sold through several offers can be counted more than once.
- A query the store has no advertised ASIN on comes back market-only: brand columns are
  **empty, not 0**. Say "no advertised ASIN appeared here", never "you got 0".
- Amazon returns at most **100 queries per ASIN per week**. Any "all my search terms" list is
  the top 100 per ASIN per week; say so.

## 2. Metric discipline (computed, not judged)

| # | Rule | Why |
|---|---|---|
| M1 | Every rate (CTR, ATC rate, CVR, impression / click / ATC / purchase share) is recomputed from counts | Amazon's `total_click_rate`, `total_cart_add_rate`, `total_purchase_rate` divide by **search volume**; against brand rates that is a ~20x error. Never expose or compare them |
| M2 | Across weeks or ASINs: add counts first, then divide. Never average weekly rates or shares | Small weeks pull averages; a past failure read 0.17% for a true 1.12% |
| M3 | Market columns repeat on every ASIN row of a query: never add Market across ASINs. Store totals come from query-level (deduplicated) rows | Same query x N ASINs = N times the market |
| M4 | Different marketplaces never add up. Same marketplace, several stores: advertised-ASIN counts add, market counts do not | Market is one number per query per week per marketplace |
| M5 | Median prices: `0` or empty currency = no data. State coverage before using price | Price coverage is often partial; an empty median price is unavailable, not zero |
| M6 | SQP Score: single week only, and never used to rank queries | The score does not aggregate across weeks and does not track volume |
| M7 | Count deltas (Brand - Market counts) are always negative and not comparable across queries: not used | |
| M8 | Missing weeks are missing, not 0. Name them | The tool lists them in `missingWeekEnds` |

## 3. The three CTRs are different things

- **Market CTR**: all listings on the query, organic + ads.
- **Advertised-ASIN CTR (SQP)**: only your listings, organic + ads.
- **Ad CTR (ads report)**: only your ads.

They are not directly comparable: brand CTR usually runs above market CTR on most searches,
because market impressions count every listing on the page.

**Click share vs impression share is the same comparison.** Click share / impression share =
(brand clicks / market clicks) / (brand impressions / market impressions) = brand CTR / market
CTR. So the help-center signal "Click Share > Impression Share = bid up" and the preset
conditions that use "Brand CTR >= Market CTR" fire for most queries of any brand that ranks well
(market impressions include every listing on the page, down to positions few shoppers reach).
Use them relative to the store's own usual ratio: "click share runs well above impression share
compared with your usual" (CTR index >= 1.2 x the store median). So:

- Do **not** say "your CTR is X% of the market". Never lead with a wrong comparison and add a
  caveat afterwards (this failed in English testing: "1/11 of the market", ~20x wrong).
- For click-stage leaks, compare a query's CTR index (brand CTR / market CTR) with **the
  store's own median index** and say "below your usual CTR on this query".
- CVR (purchases / clicks) vs market CVR is the comparison SQP supports (it is what the
  "High Loss Converter" preset uses).

## 3b. Preset filters (as the product defines them)

`sqp_calc.py` reproduces the five presets exactly, so an answer matches what the user sees in
SQP Analysis. Minimum 5 brand clicks where noted.

| Preset | Condition in the product | Read it as |
|---|---|---|
| High Loss Converter | Brand CVR < Market CVR, clicks >= 5 | Converts below market after the click |
| High Click, Low Cart | Brand CTR >= Market CTR and Brand ATC rate < Market ATC rate, clicks >= 5 | Detail page loses shoppers before the cart (CTR half fires broadly, see section 3) |
| High Cart, Low Purchase | Brand ATC rate >= Market ATC rate and Brand CVR < Market CVR | After-cart loss: price, delivery, trust - or a long decision (24h window) |
| Under-Exposed Top Performer | Brand CVR >= Market CVR and Impression Delta < 0 | Converts at or above market; the delta condition is almost always true |
| Excess Impression Sink | Impression share > 2% and Brand CVR < Market CVR | Big visibility, below-market conversion. Note: the help-center article describes this preset as a CTR problem ("impressions far exceed clicks"); the product condition is CVR-based. Describe it by the product condition |

Presets need the ATC columns for the two cart presets; when an export lacks them, report "not
available in this export", never 0.

## 3c. Product, price and brand on a search

- **Which product carries a search**: `top_asin` in the summary = the store's ASIN with most
  clicks on that search (detail rows only). `asins_on_query` > 1 means clicks are split.
- **Price vs market**: `price_gap` = that ASIN's median click price / the market median click
  price - 1 (falls back to the market median purchase price). Median price 0 = no data. Per
  listing, not per serving: a large premium on a big pack is a prompt to show value per
  serving, not proof of overpricing.
- **Head term**: search volume >= `--head-volume` (default 100,000). The most expensive
  clicks in the category; grow with capped exact-match tests, never described as cheap.
- **Another brand's name** (`--competitor-terms`): not a protect term even when the store
  wins 20%+ of its purchases. Listed under `use_cases.conquest`.
- **Dollar ceiling**: orders within reach x (store Sponsored Products sales / ad orders, same
  weeks). Always "a ceiling, not a forecast".

## 3d. Brand, competitor and generic searches (prices)

- **Brand counts are everything**: SQP brand impressions, clicks and purchases include organic
  and paid. Never write "your keywords", "your own searches" (in any language) for SQP rows;
  write "purchase share across N searches" or just "search purchases".
- **Three search types** (`brand_segments` in the summary): own brand = query contains a
  `--brand-terms` name (add common misspellings and run-together spellings); other brands =
  a `--competitor-terms` name (a list the user confirms, seeded from `brand_candidates_to_confirm`; remove any
  brand the store owns, review `brand_candidates_to_confirm`); generic = the rest.
- **Click price vs buy price**: market median click price (click-weighted) vs market median
  purchase price (purchase-weighted); `price_step` = purchase-weighted mean of
  (median purchase price / median click price - 1). Rows with a price of 0 or a click price
  5x away from the purchase price are data errors and are left out.
- How to read it: generic searches usually show a **negative** step (shoppers click premium,
  buy cheaper - price-driven, high CPC); other brands' names a **positive** step (shoppers pay
  up for the brand they typed - loyalty ads cannot buy). Own-brand rows show the store's share
  there (normally very high). Together they are the case for brand awareness.
- **Ad side** (same weeks, `get_ads_perf` `searchTerm`, no select): own brand = `OR` of
  `{"query_": {"like": "%<name>%"}}`; other brands = the same for the competitor list; ASIN
  targets = `{"query_": {"like": "b0%"}}`; generic = all search terms minus those three.
  Report CPC, ROAS and ad sales per order per type.
- **Own-brand size**: a 10,000-row export often misses the main brand-name searches. When ad
  clicks on own-brand terms exceed 3x the own-brand searches in the export, say the export
  undercounts branded demand; quote rates and prices, not the volume.

## 4. Sample flags and verdict gate

- Platform flags (same for market and advertised ASINs, on totals after aggregation):
  clicks < 5 -> ATC rate and CVR "insufficient sample"; impressions < 10 -> CTR "insufficient
  sample". Values are still returned, flagged, and **sorted last** in any ranking by a rate.
- Verdict gate (this skill): a cut / fix / scale verdict on one query needs >= 20 advertised-ASIN
  clicks in the window. Below it, list the query as "insufficient sample" - never drop it.
- Any rate mentioned from a flagged row is called low-confidence and is not used to pick or
  judge a query.

## 5. Time

- SQP weeks are **Sunday-Saturday**. ABA `dt` = SQP `end_date`. Never use `toMonday`.
- No daily SQP. A question about one day ("why was Sep 7 bad?") gets the week that contains it,
  as background, and says so.
- Ads data used next to SQP is rebuilt from daily rows into the same Sun-Sat weeks first.
  "Last 7 days" of ads vs "last SQP week" is a different window - even direction-only checks
  go wrong.
- Single week vs single week is mostly noise on mid- and long-tail queries: prefer 4-week
  windows or a volume floor for Q1, Q2, Q4, Q6.
- Relay any data break the tool's notes report. Events (Prime Day, Prime Big Deal Days,
  BFCM) can only be excluded by whole week.

## 6. SQP vs everything else

- **SQP is not joined to ads data.** Each source is fetched separately and read together in the
  conclusion. SQP queries have no category, so they cannot be joined to category Benchmark rows.
- **SQP purchases != ad orders.** SQP counts purchases within 24 hours of the click; ads use
  7/14 days and include halo (other ASINs). Never subtract to get "organic".
- **SQP vs Seller Central / other tools.** SQP is a separate Seller Central report with
  unpublished attribution. Differences come from: ASINs without ad spend in the last 14 days are
  excluded here; ad orders include non-advertised ASINs. Explain the two reports as
  independent; do not pick one as "right". Our numbers have matched Amazon's SQP back end on
  spot checks.
- No brand revenue in SQP (orders only): money comes only from `get_ads_perf`.

## 7. Peer benchmark (`get_peer_benchmark`)

Full rules: `sparkx-query-market-data` `references/peer-benchmark.md`. What this skill relies on:

- Rows are **brand-level** peer groups ("this brand's peers in this browse category"), never an
  ASIN-level or campaign-level benchmark. Rows never combine: no averaging across brands,
  goals, percentiles or parent / child categories.
- The tool already derives the ACOS percentiles from the reversed ROAS percentiles (P25 is the
  good, low-ACOS end). Do not invert or swap anything yourself.
- The profile parameter is `profileId`; filters are `brandIds`, `categoryIds`, `adProducts`,
  `goals`, `timeUnit`. There is no `factEntity` parameter on this tool.
- Empty peer values: read the row's `<metric>_status` (`NO_PEER_BENCHMARK`, `INCOMPLETE`,
  `AVAILABLE`) and say "no peer benchmark for this brand in this category" - never 0 and never a
  guess about how many peers exist.
- Prefer the P25-P75 range over P50; when the spread is wide, give only the range.
- `purchaseRate` and `addToCartRate` divide by impressions - never call them CVR.
- A single campaign: by default no benchmark (see peer-benchmark.md); answer "is it the whole
  market?" with SQP demand on its main searches instead.

## 8. Red lines - refuse and redirect

| Ask | Answer |
|---|---|
| SQP minus ads = organic? | Cannot subtract (definitions and windows differ). Offer direction-only checks: organic share without ads -> keyword expansion; ad spend up but impression share flat -> efficiency issue; click share above impression share -> strong main image, worth more exposure |
| Why doesn't SQP match Seller Central / H10? | Explain both definitions and the 14-day rule; do not pick a winner |
| Estimate search volume from rank (ABA, BSR) | No: order of magnitude and ordering only |
| Category performance of a query | No category on SQP queries; use the market behaviour class |
| CVR verdict on a handful of clicks | "Not enough sample to diagnose" |
| A bid or budget value in Diagnose mode | Direction only; for numbers, run Plan mode for the category (`plan-mode.md`) |
| Who is taking my share? | SQP has no competitor identity; the ABA top-3 columns on weekly rows (check each ASIN is not the store's own before calling it a competitor) |
| Profit, ROAS or ACOS from SQP | SQP has no money; use ads data |

## 9. Structural gaps - say the relevant one once per answer

| SQP has no... | Fill from |
|---|---|
| campaigns, ad groups, targets, match types | `get_ads_perf` searchTerm / target / productAd |
| spend, CPC, bids, brand revenue | `get_ads_perf` |
| serving status (a "not running" query looks like "not competitive") | `get_entity_metadata` campaign / productAd |
| placement split | `get_ads_perf` placement rows for the store's own ads only; no market placement share via MCP |
| competitor identity | ABA top-3 via `get_market_search_perf` (not automatically competitors) |
| own price, stock, Buy Box, delivery speed, reviews | `get_entity_metadata` asin, `get_ads_perf` asin (no reviews, no delivery tier) |
