# `get_peer_benchmark` - brand peer benchmarks

One authorized profile per call. Each row is one **brand x browse category x ad product x
campaign goal x period**, carrying the brand's own value and the peer group's P25 / P50 / P75.

## What a row is, and is not

**It is a peer group built around that brand**, not an average of the category. Two brands in
the same category get different percentiles. A store with several brands therefore has several
sets of percentiles, and averaging them into "the category benchmark" is wrong - there is no
such row.

**There is no campaign-level benchmark.** A row's own value is the brand's total across every
campaign in that row.

**Rows never combine.** Do not sum or average across rows, brands, goals, percentiles, or
category levels. A parent category already contains its children, so a parent row and a child
row of the same brand must not be added or averaged either.

## Access

`get_peer_benchmark` needs the `benchmark:read` scope and the menu permission `MCP_tool_benchmark`
(see the table in SKILL.md). A refusal - for the permission `passport_permission_denied` - is an
access gap: name the missing one, never report it as "no peers" or `NO_PEER_BENCHMARK`, and do not
retry.

## Parameters

| Parameter | Rule |
|---|---|
| `profileId` | Prefer one authorized positive 64-bit JSON integer, e.g. `123`. Arrays such as `[123]` and `[123,123]` are accepted after deduplication. Empty arrays, distinct IDs, strings and objects are rejected. |
| `userContext` | Original user request and reason for the query, 1–100 characters |
| `dateStart` / `dateEnd` | At most 90 days; expanded to covering periods |
| `timeUnit` | `WEEK` (default, Sunday-Saturday) or `MONTH` |
| `metrics` | Default `ctr,cpc,cpm,roas,acos`. Also ROAS variants, purchase and add-to-cart rates, cost-per-purchase variants, detail-page-view rate and more |
| `brandIds` | Omit for all brands in the profile |
| `categoryIds` | Omit to let each peer group pick its categories from its latest period with default nodes in the window, then return those categories across the whole window |
| `adProducts` | `sponsoredProducts` / `sponsoredBrands` / `sponsoredDisplay`; omit to get each separately |
| `goals` | `AWARENESS` / `CONSIDERATION` / `CONVERSION`; omit to get each separately. **There is no merged or ALL goal** |
| `page` | Page number starting at 1 (default) |
| `pageSize` | Rows per page, 1–10,000 (default 1,000) |

For example, replace `123` with an ID returned by `get_user_authorized_context`:

```json
{"profileId":123,"dateStart":"2026-11-15","dateEnd":"2026-11-21","metrics":["roas","acos"],"page":1,"pageSize":1000,"userContext":"Compare weekly brand ROAS and ACOS with peers"}
```

Read `data.rows` on each page. While `meta.hasNextPage` is true, repeat the request with only
`page` increased by one. Stop when it is false, even if the page is full. `data.rowCount` and
`data.returnedCategoryCount` describe the current page. For a count of distinct categories
across pages, deduplicate the returned `browseCategoryId` values.

## Reading the values

- **Null is not zero.** All three percentiles empty means no peer basis for that row. Say "no
  peer benchmark for this brand in this category", not "0" and not "peers are too few".
- **ACOS percentiles are already derived** from reversed ROAS percentiles - P25 is the good
  (low-ACOS) end. They are approximate because the inversion is applied to percentile points.
  Do not invert them again.
- **Currency is the row's own.** No conversion is applied, so rows in different currencies do
  not aggregate.
- **CPM here is spend divided by all impressions**, not viewable impressions. Compare it only
  with a CPM computed the same way.
- A wide P25-P75 spread means the peer group is heterogeneous. **Do not hand the user P50 as a
  target when the spread is wide** - give the range.

## Matching a campaign to a row

Only do this when the question genuinely needs it - see the next section first.

**Goal** comes from the campaign, not from preference:

| Ad product | Goal |
|---|---|
| SP | always `CONVERSION` |
| SD | from the ad group's `sdBidOptimization`: `reach` -> AWARENESS, `clicks` -> CONSIDERATION, `conversions` -> CONVERSION |
| SB | from the campaign's `costType`: CPC -> CONSIDERATION; fixed-price / vCPM -> **no benchmark row exists** |

**Brand and category** come from the campaign's main ASIN - the one with the highest spend in
the window. Its brand gives the brand, its leaf category walked up the tree gives the
category. ASINs of other brands or categories in the same campaign are not matched separately.

Which metrics matter depends on the goal: awareness reads CPM, consideration reads CTR and
CPC, conversion reads ROAS and purchase rate.

## Judging a single campaign: default is no

Two measured facts set this policy:

- Of 285 brand-by-category cells, **120 (42%) have no default node at all** - no category
  level where both the brand's own value and the peer median exist.
- Changing category level or moving to a sibling flips the "better or worse than peers"
  conclusion in **223 of 484 checks (46%)**.

So **check first whether a default-node row exists**. If none does, say this brand has no
usable peer benchmark in this marketplace and answer from the account or from SQP instead.

When a row does exist, a single campaign may use it in only two ways:

| Case | What the benchmark may say |
|---|---|
| Explaining a change ("why did ROAS drop") | Only the **direction** peers moved - did the whole group move or just us. Never a level comparison |
| Setting a target ("is 30% ACOS high", "what should I aim for") | The peer **range** P25-P75 for the same category, ad product and goal. Not P50 as a target when the spread is wide |

Do **not** use it for bid, budget, negative or structure decisions, for ranking campaigns
inside the account, for term-level questions (use SQP), for single-day questions, or for SB
fixed-price / vCPM campaigns.

Before the category is matched to a leaf, a single campaign gets no benchmark at all. Answer
"did the whole market move" from the SQP market volume of its main terms instead. For brand or
account-level questions the brand's default-node row is fine.

If a brand has default nodes in several category branches, answer per branch. Do not merge.

## What is not available

- Five new-customer cost metrics are not returned by the current interface.
- No breakdown by ad format, no total across ad products, no daily grain, no other
  advertiser's private data.
- New-customer metrics other than new-to-brand order share have peer percentiles but **no own
  value** - "is my new-customer ROAS above peers" can only be answered with the peer range.
