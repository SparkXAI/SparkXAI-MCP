# Data sources and joins

The tool rules (parameters, row kinds, ABA columns, `marketOnly`, `contains` roots, caps) live
in [`../sparkx-query-market-data/references/sqp-aba.md`](../../sparkx-query-market-data/references/sqp-aba.md)
and [`peer-benchmark.md`](../../sparkx-query-market-data/references/peer-benchmark.md). Read
them there; this file adds only what this skill does on top.

Order of preference: `get_market_search_perf` -> exports the user supplied (or when the tool is
unavailable) -> ask for exports. The ads, metadata and change-log tools always supply what SQP
lacks.

## 1. `get_market_search_perf` - what this skill pulls

| Need | factEntity | Scope (always pass one - never a full dump) |
|---|---|---|
| Market-level view: demand, share, conversion vs market per search (S1, S3, S4, S5, P3, Q1-Q9) | `marketSearchQuery` | `searchQueries` = the searches found in the account first (top N by ad spend, impressions or change; a category's searches) |
| Which own product carries a search, per-product splits, category scope in Plan mode (S2, S7, P2, P5, Plan) | `marketAsinQuery` | `asins` = the products in scope (a category's ASINs in Plan mode) |
| A candidate term the store never ran | `marketSearchQuery` + `marketOnly: true` | explicit `searchQueries` (see sqp-aba.md) |

- **Weekly rows** (`aggregate: false`, the default). The dates are aligned to whole
  Sunday-Saturday weeks; quote the aligned window from `queryWindow`. For a change question pull
  8 weeks once and split with `sqp_calc.py --split-at <last Saturday of the prior window>`.
- **Missing weeks:** `missingWeekEnds` names them. Missing is not zero; say which.
- **Truncation:** up to 100,000 rows per call; `meta.truncated: true` means the result was cut -
  narrow and pull again. Estimate rows first: searches x weeks (x ASINs).
- **Low sample:** read the `*LowSample` flags (`myBrandCvrLowSample`, `myBrandCtrLowSample`,
  `totalCvrLowSample`, ...). `sqp_rows.py` keeps them on single-week and aggregated rows; when
  it adds weeks together it applies the same rule (clicks < 5, impressions < 10) to the summed
  counts.
- **Percent scale:** tool rates and shares are percentages (3.2 = 3.2%). The scripts never read
  them; they recompute from counts.
- **Market-only rows:** a supplemented row carries `total*` columns and null `myBrand*`
  columns - "no advertised ASIN appeared", never 0.
- Pass the response notes (`meta.hint`, `termMatches`) on to the user; `sqp_rows.py` puts them
  in the script notes.

Save each response as JSON (the whole response is fine) and pass the files to the scripts:
`sqp_calc.py --current a.json b.json`, `sqp_plan.py --sqp a.json`. Column names are mapped in
`scripts/sqp_rows.py` only.

## 1b. ABA (Brand Analytics) - the second pull

SQP says how the store did on a search. ABA says **how much the market wanted that search and
who owns it**. Both arrive on the same row, but only in one query shape.

| Pull | factEntity | aggregate | Carries ABA |
|---|---|---|---|
| The one this skill already makes | `marketAsinQuery` | false | **No** |
| The ABA pull | `marketSearchQuery` | false | **Yes** |
| Any pull | either | true | **No** |

So ABA needs its own call, for the terms the first pull already surfaced (fix-first rows,
quadrant rows, the protect list), at most 1000 in `exact` mode:

```
get_market_search_perf(profileIds=[<one>], factEntity="marketSearchQuery", aggregate=false,
                       dateStart=<same Sunday>, dateEnd=<same Saturday>,
                       searchQueries=[...], searchQueryMatchType="exact")
```

Pass that file to `sqp_calc.py --current` alongside the first one. The ABA columns are picked up
automatically and land in `sqp_summary.json` under `aba`.

### Columns

`abaRank`; `abaTop1Asin` / `abaTop2Asin` / `abaTop3Asin` each with `ClickShare` and
`ConversionShare`; `abaTop3TotalClickShare`; `abaTop3TotalConversionShare`; `asinCount` (how many
ASINs the term had); and a response-level `abaStatus`.

### Rules, all enforced in `aba_section`

1. **`abaRank` is a rank, not a volume.** It cannot be turned into a number of searches, it is
   never summed or averaged into one, and a rank of 1,000 in one marketplace is not comparable
   with 1,000 in another. Report it as a band and as a direction only.
2. **A rank getting smaller means the search got more popular.** Say "demand rising"; never
   "rank up" or "rank down" on their own - readers split on what those mean.
3. **Shares arrive already 0-100.** Never multiply by 100 again.
4. **The ABA top 3 are not automatically competitors.** They are whatever took the most clicks
   on that term, which can be the store's own products or sibling variants of the same parent.
   `aba_section` checks each top-3 ASIN against the store's own ASINs and reports `is_own_asin`;
   with no own-ASIN list it reports `null`, which means unknown and must never be rendered as
   "not ours". Reporting an own listing as a competitor is the mistake this prevents.
5. **The rank can be present on a row whose other ABA columns are thin** - it falls back to the
   top-3 table when the term-level table has no row for that term and week. Its presence is not
   proof the term-level data was complete.
6. ABA aligns with the SQP week **end** date; aligning on the start date is off by a week.
7. State coverage: `aba.rows_with_aba` of `aba.rows_total`. When the pull carried no ABA at all,
   `aba.status` is `NOT_RETURNED` and the answer says the query shape was wrong - never "the
   market has no data".

### What it answers that SQP alone cannot

- Which demand tier the store actually competes in: group terms by rank band and read market
  conversion, own clicks, own orders and own purchase share side by side. A store can look
  acceptable overall and still hold 0.07% of the purchases in the top demand band.
- Whether a search is rising or fading, so a weak result on a fading term is not treated as a
  listing problem.
- How concentrated a term is: `abaTop3TotalClickShare` is how much of it three listings own.

## 2. Exports (fallback)

Use only when the user supplies files or the tool is unavailable. From SparkX SQP Analysis ->
Export, all metric columns on. `sqp_rows.py` detects four layouts:

| Export | Grain | Notes |
|---|---|---|
| Search Term main page | search | Caps at 10,000 rows: totals are a lower bound |
| Search Term detail | own ASIN x search (one sheet per search) | `Parent ASIN` mixes parent and child ASINs |
| ASIN main page | parent ASIN | Market columns are sums over that ASIN's searches: never add across ASINs |
| ASIN detail | own ASIN x search (one sheet per ASIN) | Columns follow the user's picker; clicks may be derived as purchases / CVR (approximate) |

- **Exports carry no dates.** Ask which weeks each file covers; label a file with
  `file.xlsx@YYYY-MM-DD` (the Saturday its period ends). One file = one period.
- Export rates are fractions (0.17 = 17%); used only to derive a missing click count.

### Asking for exports

> To answer this from SQP I need, from SQP Analysis for <store>, with all metric columns on:
> the Search Term tab -> Export -> main page for <current weeks>, and the same for <prior weeks>
> if the question is about a change. For "which product", also the ASIN detail export. Tell me
> the weeks each file covers - the files carry no dates.

## 3. MCP signals and joins

| Signal | Call | Gotchas |
|---|---|---|
| Total sales, orders, sessions, Buy Box, TACOS, ad spend / sales per product | `get_ads_perf` `factEntity: "asin"`, `select: ["asin.parent_asin_"]` | For weeks, select `date` and bucket Sunday-Saturday yourself |
| Store daily trend (event spikes) | `get_ads_perf` `factEntity: "asin"`, `select: ["date"]` | A one- or two-day jump marks an event week |
| Ad search terms for the same searches | `get_ads_perf` `factEntity: "searchTerm"` | Fields have no entity prefix. Join to SQP by normalised text (lowercase, `+` removed, spaces collapsed) |
| Keyword and target results (Plan mode) | `get_ads_perf` `factEntity: "target"` | `target.targetId_` is the Amazon keyword / target id |
| Internal ids, bids, states | `get_entity_metadata` `entity: "keyword"` / `"target"` / `"campaign"` | Writes need internal ids; ads rows carry Amazon ids |
| Category, price, SKU, brand | `get_entity_metadata` `entity: "asin"` | `asinBsrCategoryName` / `parentAsinBsrCategoryName` = BSR category; one row per SKU, dedupe by `asin` |
| Budget usage (Plan mode) | `get_entity_metadata` `entity: "campaign"` with `budgetUsageDateStart` / `End` | Use `outOfBudgetMinutes`; never threshold on `outOfBudgetPercentage`; null = not checked (budget-usage.md) |
| Which campaigns advertise a product | `get_entity_metadata` `entity: "productAd"` -> `adGroupId` -> `entity: "adGroup"` | Internal vs Amazon ids differ |
| What changed | `get_operation_log`, one entity per call (`campaign`, `target`, `placement`), `resourceIds` = Amazon campaign ids | One entity keeps real pagination (op-log SKILL.md). `Amazon Console` = changed on Amazon's side |
| AI group state | `get_entity_metadata` `entity: "aiGroup"` | `aiStatus` 1 = AI running |
| Peer level for a brand | `get_peer_benchmark` | See `rules.md` section 7 |

**Join keys.** SQP ASIN -> metadata asin -> parent ASIN -> `get_ads_perf` rows. Search text ->
ads `query_` by normalised text. SQP is never joined to peer rows by category.
