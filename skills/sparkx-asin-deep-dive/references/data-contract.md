# Data Contract

Call-level rules for the four read tools. Most of this is operational knowledge that only shows up
after a query has silently returned the wrong thing — adapted from the contract Xiaodong's
`asin-full-diagnosis` carried, with the items this skill has verified against a live account marked
as such.

**Field names move between MCP versions.** The error message usually lists the available fields.
Go by the error, not by memory, and never guess a field name.

## 1. Two ID systems — the highest-frequency error

The same entity has two IDs, and each tool takes a different one:

| Where | Which ID |
|---|---|
| `get_entity_metadata` filters and returns | **Internal** ID (short, e.g. `142596476`) |
| `get_ads_perf` filters and returns | **Amazon** ID (long, e.g. `517547567010529`) |
| `get_entity_metadata`'s `amazonCampaignId` / `amazonAdGroupId` | Amazon ID — this is the bridge |

- To cross from metadata to performance: pull `entity='adGroup'` filtered on the internal
  `adGroupId`, read `amazonAdGroupId`, then filter performance on that. Campaign is the same with
  `amazonCampaignId`.
- **Cast both sides to string before joining.** An integer compared to a string drops the pair
  silently — no error, just missing rows.
- **A filter that returns zero rows is an ID-type suspect first.** Do not report "no data" or "no
  operations" until the ID system has been ruled out. This is the single most common way an audit
  concludes an account is idle when it is not.

## 2. Joins that are not allowed

- **`factEntity='searchTerm'` cannot join `productAd` / `asin` / `productLine`.** The call fails
  with `UNSUPPORTED_PERFORMANCE_JOIN`. The route is: `productAd` → internal `adGroupId` →
  `entity='adGroup'` → `amazonAdGroupId` → filter search terms by `adGroup.adGroupId_`.
- What comes back is therefore **ad-group grain**. When the group holds other products, its spend
  cannot be split to this ASIN — call it "the performance of the ad groups containing this ASIN"
  and print the coverage. See `evidence-scope.md`.
- **Never add a `productAd` or `asin` dimension on `factEntity='adGroup'`.** It copies the whole
  group's metrics onto every product in it.

## 3. Per-entity notes

| Entity | What to know |
|---|---|
| `asin` | Business grain: `TotalSalesAmount`, `OrderCount`, `Sessions`. This is the baseline for cross-checking sales, and the denominator TACOS must use |
| `productAd` | ASIN-specific, **SP only** — the promoted-product dimension does not exist for SB or SD |
| `searchTerm` | `queryType` accepts `keyword` **or** `product`; `auto` is rejected outright. **Omit `queryType` to get the full set** — that is currently the only way to retrieve Auto-targeting search terms, and filtering to `keyword` drops them. Isolate them afterwards with `matchType_`. A `matchType='ASIN'` row means the term was matched by product targeting — `query` is still a customer search term, not an ASIN |
| `target` | The only source of product-targeting data. Manual product targeting is `matchType` in `asinSameAs` / `asinExpanded`; `closeMatch` / `looseMatch` / `substitutes` / `complements` are **automatic** entrances and must not be added into a "competitor targeting" total |
| `campaign` | `timeGranularity='hourly'` caps at a **7-day** window and needs `date` and `hour` in `select`. Hourly carries no reliable AI/manual split — take that from daily |
| `placement` | Daily, **90-day span like any other entity**, and **not SP-only** — the enum carries SB values (`SB-Top of Search on-Amazon` and the rest) alongside the SP ones |
| `keywordPlacement` | A different entity: **SP only, hourly by nature, 7-day cap**. Do not carry its restrictions over to `placement` |
| placement data in general | Zero rows means no placement data for the period — say so. Do not infer placement shares from anything else; fall back to same-term CVR plus bid operations as indirect evidence and grade the conclusion B or C |

**Verified live**: on `factEntity='target'`, both `queryType: product` and an explicit
`p.matchType_` filter return the same top rows (they differed by $13 on a $21k target, because
`queryType` merges a target's `asinSameAs` and `asinExpanded` rows). **Prefer the explicit filter
and put `p.matchType_` in the `select`** — then each row states whether it is manual product
targeting or an automatic entrance, instead of leaving the reader to assume.

**These rules are checked against `query-ads-performance`, not inherited.** Two of them read the
other way round in the version this contract was adapted from, and following that version would
have dropped every Auto-targeting search term and capped placement at a week. Where a source skill
and `query-ads-performance` disagree, `query-ads-performance` wins — and where neither is certain,
the call's own error message lists the fields that exist.

## 4. Prefixes and grouping

- A fact entity's own fields take the **`p.`** prefix (`p.query_`, `p.matchType_`, `p.targetId_`).
  Joined entities take the entity name (`campaign.campaignName_`, `adGroup.adGroupState_`).
- **Adding a `select` dimension changes the grouping.** Adding `targetId_` splits one search term
  into one row per target. When reconciling totals, hold `select` fixed.
- Request field names and response key names are not guaranteed to match. Do not feed a response
  key back as a request field.

## 5. Pagination and batching

- `hasNextPage` **can come back empty, and empty does not mean "no more"**. Loop until it is
  explicitly false, or fall back to "this page returned fewer rows than `pageSize`".
- A row count at or near `pageSize` means assume truncation and keep paging.
- Batch filter lists: roughly **40 ASINs** per batch, **50–200 campaign IDs**. Oversized ASIN lists
  are silently truncated to a partial match; oversized campaign lists fail outright.
- Campaign-grain performance **cannot be filtered by `productAd.asin`**. Pull by spend and narrow
  by name or ID afterwards.
- Taking only page one under-counts campaigns and product ads. Check `effectiveProfileIds` in the
  response against what you sent, so a silently dropped profile does not become a missing store.

## 6. Operation log

- **A campaign-level log does not contain target-level or product-level actions.** Auditing bid
  trajectories or AI action space needs `campaign`, `target` **and** `productAd` pulled separately.
- Prefer one non-`aiGroup` entity per call and page to the end. With several entities, check
  `meta.truncated` and split by entity or by date window.
- 90-day span cap. Check timezones before stitching sources: `createdDate`'s zone varies with the
  entity and the number of profiles, and managed-group logs may run on a different clock from
  campaign logs.
- Keep time, object, **previous value → new value**, `changedBy` and `operationType` for every
  operation.
- Keyword-level pauses may not appear in campaign or ad-group logs at all. Absence from the log is
  not absence of the action — fall back to the entity's current state.

### Completeness gate

Before any attribution sentence, record rows and date coverage for each source pulled — campaign
daily, campaign hourly, search terms, placement, and the operation log at each level — with whether
pagination completed. **An incomplete log reads exactly like an inactive account.** If coverage is
partial, the conclusion becomes "not found within the coverage we have", and the gap is named.

## 7. Recomputing metrics

- Recompute from period totals: `ACOS = Spend/Sales`, `CPC = Spend/Clicks`, `CVR = ad orders/Clicks`.
  **TACOS must use `factEntity='asin'`'s `TotalSalesAmount`** — ad sales is not a substitute.
- **Never average daily percentages.** Label the grain of every figure (period total, daily mean,
  single day, hourly).
- A zero denominator is "no orders" or "not computable", never `0%` and never infinity. Percentages
  that arrive pre-scaled (ACOS, CTR, CVR) must not be multiplied by 100 again.
- **Reconcile**: an aggregate query and the paginated detail for the same scope must agree on
  Spend, Clicks, Sales and Conversions. A mismatch means missed pages, inconsistent filters or a
  dimension splitting rows — find it before using either number.
- Orders ≠ Units. Ad orders ≠ total orders. An ASIN's total sales ≠ its ad-attributed sales.
  `orders = clicks × CVR` is arithmetic, not causation.
