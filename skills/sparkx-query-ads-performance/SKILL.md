---
name: sparkx-query-ads-performance
description: >-
  Query advertising performance metrics: spend, clicks, sales, ACOS, ROAS, etc.
  For analyzing ad performance, comparing time periods, ranking by entity, trend analysis.
  Keywords: ad data, performance, spend analysis, ACOS, sales, conversion rate,
  campaign performance, adGroup comparison, keyword analysis, ASIN ads, search term report,
  daily/weekly/monthly trends, top N ranking, week-over-week, year-over-year,
  hourly data, by hour, intraday, AMS, Amazon Marketing Stream, keyword placement,
  vendor, seller, distributorView, sellingProgram, shipped revenue, ordered revenue, TACOS
metadata:
  version: 1.3.0
---

# Query Ads Performance Skill

## MCP Tool

This skill maps to MCP tool: **`get_ads_perf`**. Required scope: `amazon_sa_performance_data:read`.

Profile scope is resolved from the authenticated bearer token. `profileIds` is **required** — always call `get_user_authorized_context` first to obtain authorized profile IDs, then pass one or more into `profileIds`. **Every requested ID must be authorized: one unauthorized value fails the entire call** with `invalid_params` / `Requested profileIds contain unauthorized values` — nothing is silently dropped and you never get a partial result (see Platform-Wide Rules below). Take the IDs verbatim from `get_user_authorized_context`; don't hand-type them or reuse them from an earlier session. If the user didn't specify a store, pass **all** authorized `profileIds`. Never pass `tenantId` or `userId`; the server derives them from the token.

**`userContext` (required)**: Must pass a non-empty string on every call. Preserve the user's original query as much as possible, plus the agent's reason for calling this tool. Summarize if too long, max 100 characters.

## Platform-Wide Rules

**Before using this tool, read [`references/platform-notes.md`](references/platform-notes.md)** — it covers auth flow, permission scopes, error handling, pagination/date-limit tables, the Ratio Metric Display Rule (ACOS/CTR/CVR/TACOS), currency rules, the tool-selection decision tree, and implicit inference rules shared across all 3 read tools. That file ships inside this same skill folder, so it travels with this skill regardless of how it's packaged/installed. This SKILL.md only covers what's specific to `get_ads_perf`.

## When to Use

Use this tool when the user needs any of the following:
- Query ad performance data (spend, clicks, conversions, ACOS, etc)
- Filter and aggregate data by time range (daily, weekly, monthly trends)
- Group and rank by entity dimension (Campaign, AdGroup, Keyword, ASIN)
- Get top N rankings or performance leaderboards
- Compare time periods (week-over-week, month-over-month, before/after AI management)
- Analyze ad ROI and cost efficiency

See the Tool Selection Decision Tree above if the user's ask might belong to `get_entity_metadata` or `get_operation_log` instead.

## Core Concepts

### Fact Entity (factEntity)

The query subject determining aggregation granularity:
- `campaign`: campaign level (the only entity that supports `timeGranularity: hourly`)
- `adGroup`: ad group level
- `target`: keyword/targeting level (requires `queryType`: `keyword` / `product` / `auto`)
- `searchTerm`: search term level. `queryType`, when specified, only accepts `keyword` / `product` — **`auto` is rejected outright**. **Omitting `queryType` entirely is valid** and returns the full unfiltered search-term set (manual keyword/product terms mixed with Auto-matched terms) — this is currently the only way to retrieve Auto-targeting search terms; filter by `matchType_` to isolate them (see field-reference.md and the search-term example)
- `placement`: ad placement level
- `productAd`: product ad level
- `asin`: ASIN business data level (adds business metrics like TotalSalesAmount, TACOS)
- `keywordPlacement`: keyword × placement joint level, sourced from Amazon Marketing Stream (AMS) — **hourly by nature, SP only, max 7-day span**. See Hourly / AMS Data below

Passing an unsupported value fails with `invalid_params`; the enum above is the complete list.

### Dimension Entities

Auxiliary tables for joining and aggregating — referenced via `select`/`filters`, not declared separately:
- `campaign`, `adGroup`, `target`, `asin`, `parentAsin`, `aiGroup`, `portfolio`, `productLine`, `profile`, `automationRule`
- System auto-JOINs based on fields in select/filters, no manual specification needed

## DSL Parameter Format

```json
{
  "userContext": "User's original query + agent's reason for calling",
  "factEntity": "entity_type",
  "dateStart": "YYYY-MM-DD",
  "dateEnd": "YYYY-MM-DD",
  "metrics": ["metric_list"],
  "profileIds": [1234567890123456],
  "select": ["dimension_field_list"],
  "groupBy": ["same as select, only needed if select contains a custom aggregate expression"],
  "filters": {},
  "orderBy": [{"field": "field_name", "direction": "DESC"}],
  "page": 1,
  "pageSize": 100,
  "queryType": "keyword",
  "timeGranularity": "daily",
  "language": "en"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| profileIds | array[long] | **Yes** | — | Profile IDs from `get_user_authorized_context` -> `profiles[].profileId`. **All must be authorized** — one unauthorized value fails the whole call |
| factEntity | string | **Yes** | — | Fact entity type. Enum: `campaign` / `adGroup` / `target` / `searchTerm` / `placement` / `productAd` / `asin` / `keywordPlacement` |
| dateStart | string | **Yes** | — | Start date `YYYY-MM-DD`. Max span vs `dateEnd` is 90 inclusive calendar days (see platform-notes.md for the precise off-by-one-safe definition) — **7 days for hourly/AMS queries**; cannot be more than 15 months before today |
| dateEnd | string | **Yes** | — | End date `YYYY-MM-DD`. Default to yesterday if user gives no end date (T+2 data delay) |
| metrics | array[string] | **Yes** | — | Metric fields (non-empty). Must be valid for the chosen `factEntity` — see Metrics × Entity Support Matrix below |
| userContext | string | **Yes** | — | User's original query + reason, max 100 chars |
| select | array[string] | No | [] | Dimension fields, format `entity.field_`; omit for global aggregate (no grouping) |
| groupBy | array[string] | No | same as select | GROUP BY fields. Only needed explicitly when `select` contains a custom aggregate expression — otherwise auto-filled from raw dimension fields in `select` |
| filters | object | No | {} | Filter conditions — supports simple value / operator / AND-OR nesting |
| orderBy | array[object] | No | [] | `[{"field": "Spend", "direction": "DESC"}]` (direction ASC or DESC, default DESC) |
| page | int | No | 1 | Page number (1-based). **`page` ≤ 0 is an error**, not a fallback to 1 |
| pageSize | int | No | 100 | Rows per page, **max 500**. **Out of range (≤0 or >500) is an error**, not clamped — floor any computed value at 1 |
| queryType | string | No | — | Meaningful only for `factEntity: target` (semantically required there: `keyword`/`product`/`auto`) and `factEntity: searchTerm` (optional — `keyword`/`product` filter to that source, `auto` errors, **omitting it returns everything, manual + Auto mixed**). On any other `factEntity` (e.g. `campaign`) it's accepted but silently has no effect — verified, not an error |
| timeGranularity | string | No | daily | `daily` / `hourly`. **`hourly` is only valid with `factEntity: campaign`**; any other value or entity combination is an error. See Hourly / AMS Data below |
| language | string | No | **en** | Enum translation language: `zh` / `en` / `ja`. An unrecognized value silently falls back to `en`, so set it explicitly to match the user's language |

## Field Naming Rules

- **Dimension fields** (in select/filters): must have entity prefix and `_` suffix
  - Example: `campaign.campaignName_`, `aiGroup.aiStatus_`, `asin.asin_`
- **Metric fields** (in metrics/filters): no `_` suffix, case-sensitive, capitalized as documented
  - Example: `Spend` ✓ — not `spend` or `SPEND`
- **date field**: no `_` suffix, no entity prefix
  - Example: `date` — note this field is returned in **`YYYYMMDD`** format (e.g. `"20240601"`), different from the `dateStart`/`dateEnd` request params' `YYYY-MM-DD` format. See Date Format above.
- **SearchTerm fields** (no entity prefix, but keep `_` suffix): unlike every other entity, searchTerm dimension fields drop the `entity.` prefix
  - Example: `query_`, `matchType_`, `targetId_`, `adGroupId_`, `campaignId_`
- **KeywordPlacement fields** — **write bare names in the request, read `_`-suffixed names in the response.** This entity is the second exception to the convention, and it's asymmetric:
  - In `select` / `filters` / `orderBy`, write the bare name: `keywordId`, `keywordText`, `matchType`, `placement`, `campaignId`, `adGroupId`. These six are explicitly mapped and are the form to use.
  - In the returned rows, the keys come back suffixed: `keywordId_`, `keywordText_`, `matchType_`, `campaignId_`, `adGroupId_`, plus `placement`, `hour` (0-23), `date`, `profileId_`. So you request `keywordText` and read `keywordText_`.
  - **Don't echo the response form back into a request.** A `keywordPlacement.<field>` reference is translated literally, so it only works if it happens to match the underlying column exactly — `keywordPlacement.keywordText_` resolves, but `keywordPlacement.placement_` fails (that column is `placement`, with no underscore). The bare form has no such trap. Also don't carry these bare names into any other `factEntity`.
  - **`campaignType` filters are a no-op here** — the data source is SP-only, so a `campaignType` filter is dropped rather than pushed down: filtering for `sponsoredProducts` changes nothing, and filtering for `sponsoredBrands`/`sponsoredDisplay` gives you an empty result that means "wrong entity", not "no data". Don't use this entity to compare ad types.
- **Custom aggregate expressions**: prefix raw columns with `p.`
  - Example: `sum(p.impression) as total_impressions`
- Dimension fields are evaluated in `WHERE`; metric fields are evaluated in `HAVING`

**⚠️ This convention is specific to `get_ads_perf`.** `get_entity_metadata` uses plain camelCase with no prefix/suffix (`campaignState`, not `campaign.campaignState_`) — do not mix the two conventions.

## Time Aggregation (in `select`)

Do not just write `week`/`month` as bare field names — use the exact ClickHouse expression and alias it:

| Granularity | Expression |
|---|---|
| Daily | `date` |
| Weekly (Monday start) | `toMonday(parseDateTime32BestEffort(date)) as week` |
| Monthly | `toStartOfMonth(parseDateTime32BestEffort(date)) as month` |
| Quarterly | `toQuarter(parseDateTime32BestEffort(date)) as quarter` |
| Yearly | `toYear(parseDateTime32BestEffort(date)) as year` |

**This does not raise the 90-day cap.** If the user's window exceeds 90 days, first split into multiple calls each with `dateStart`/`dateEnd` spanning ≤90 days — aggregation only reduces the row count *within* each of those calls.

## Hourly / AMS Data

Hour-level data comes from Amazon Marketing Stream (AMS) and is reachable two ways. Both are capped at a **7-day span** — not 90.

| What you want | How | Ad types | Constraints |
|---|---|---|---|
| Campaign metrics by hour | `factEntity: "campaign"` + `timeGranularity: "hourly"` | SP + SB + SD | span ≤ 7 days |
| Keyword × placement metrics | `factEntity: "keywordPlacement"` | **SP only** | hourly by nature — **do not pass `timeGranularity`**; span ≤ 7 days; restricted metric set |

**Rules that produce hard errors (not warnings, not silent fallbacks):**

- `timeGranularity` accepts only `daily` and `hourly` (case-insensitive; omitted/empty means `daily`). Anything else → `Parameter 'timeGranularity' must be 'daily' or 'hourly', got: X`.
- `hourly` with any `factEntity` other than `campaign` → `Parameter 'timeGranularity=hourly' is only supported for factEntity=campaign. Current factEntity: X`. It is **not** ignored and does **not** fall back to daily. There is no hourly adGroup, target, searchTerm, placement, productAd, or asin data — if the user asks for "hourly keyword performance", the answer is `keywordPlacement` (keyword × placement), not `target` + hourly.
- `daily` on `keywordPlacement` is not supported either — the entity has no daily rollup. Just omit `timeGranularity`.
- Span over 7 days on either path → a date-range error (`keywordPlacement is hourly granularity, date range cannot exceed 7 days (got N days)`). For "hourly pattern over the last month", either aggregate by hour-of-day across several ≤7-day calls (and say you sampled), or step back to daily granularity and tell the user hourly is limited to a 7-day window.

**Reading hourly results:**

- **Select `hour` explicitly.** `timeGranularity: "hourly"` changes the source table but does not inject an hour grouping into the response. For an intraday curve, include both `date` and `hour` in `select`; omitting `hour` aggregates the hourly source back to the remaining selected dimensions.
- With `hour` selected, rows carry `hour` (0-23) alongside `date`; group by it to build an intraday curve, and remember each row is one hour of one day — averaging hours across days requires you to divide by the number of days, not the number of rows.
- The T+2 delay still applies. The most recent hours of "today" and often all of yesterday are incomplete. Don't present a partial final day as a real dip.
- `keywordPlacement` uses an asymmetric field naming convention (bare names in the request, `_`-suffixed keys in the response) — see Field Naming Rules.

**`keywordPlacement` supports a restricted metric set.** The underlying stream table only carries base SP hourly data, so:

| Metrics | Behaviour |
|---|---|
| `Impressions`, `Clicks`, `Spend`, `Sales`, `Conversions`, `Units`; the Same/Other-SKU variants (`SalesSameSKU`, `ConversionsSameSKU`, `UnitsSameSKU`, `SalesOtherSKU`, `ConversionsOtherSKU`, `UnitsOtherSKU`); derived `CTR`, `CVR`, `CPC`, `CPA`, `ACOS`, `ROAS` | **Available** |
| `AISpend`, `AISales` | Accepted but return **`0`** |
| `AIACOS`, `AIROAS` | Accepted but return **`null`** |
| NTB family, DPV / video / viewability / vCPM / impression-share, ASIN business metrics | **The query fails** — the underlying table has no such column |

Two different failure modes, so handle them differently: the AI values are **placeholders, not real zeros** — never report AI performance from this entity and never use them as a denominator (use `factEntity: campaign` for AI attribution). The last row isn't a "returns empty" case at all: requesting one of those metrics breaks the whole call, so don't include them — ask for them at campaign / adGroup / target level instead.

## Supported Dimension Fields, Metrics × Entity Matrix, and Metrics Reference

**See [`references/field-reference.md`](references/field-reference.md)** for the complete field dictionary: all dimension fields by entity (Campaign, AdGroup, Target, SearchTerm, Placement, ProductAd, ASIN, ParentAsin, ProductLine, Portfolio, AI Group, AutomationRule, Profile), the Metrics × Entity Support Matrix, and the full Metrics Reference (including derived ratio formulas and user-to-field mapping).

## Core Metrics Combo

When user says "core metrics":
```
["Impressions", "Clicks", "Spend", "Sales", "Conversions", "ACOS", "ROAS", "CTR", "CVR", "CPC", "CPA"]
```

For ASIN business analysis, additionally (asin entity only):
```
["TotalSalesAmount", "OrderCount", "TACOS"]
```

## Filter Syntax

```json
{
  "campaign.campaignState_": "enabled",
  "campaign.campaignId_": [123, 456],
  "campaign.campaignName_": {"like": "%test%"},
  "Spend": {">": 100},
  "AND": [
    {"campaign.campaignState_": "enabled"},
    {"Spend": {">": 100}}
  ],
  "OR": [
    {"Sales": {">": 1000}},
    {"ACOS": {"<": 20}}
  ]
}
```

Note the `ACOS` threshold above is `20`, not `0.2` — `ACOS`/`CTR`/`CVR` are confirmed returned pre-scaled ×100 (e.g. `17.61` means 17.61%), so `{"ACOS": {"<": 20}}` means "ACOS under 20%". `TACOS`'s scale is not independently confirmed — see the Tier 2 note in Ratio Metric Display Rule above. Using `0.2` would be a common construction mistake for the confirmed Tier 1 fields.

Supported operators: `>`, `<`, `>=`, `<=`, `=`, `in`, `like`

Nested example:
```json
{
  "AND": [
    {"campaign.campaignState_": "enabled"},
    {"OR": [
      {"Spend": {">": 100}},
      {"Sales": {">": 1000}}
    ]}
  ]
}
```

Dimension-field filters run in `WHERE`; metric-field filters run in `HAVING`.

**Do not pass null as a filter value** — it returns `invalid_params`. To match rows where a field is genuinely empty use the explicit form `{"field": {"isNull": true}}` or `{"isNotNull": true}` (the boolean says whether the test holds, so `{"isNull": false}` = `{"isNotNull": true}`). See platform-notes "Null Filter Values Are Rejected".

**`like` wildcard note**: any `%` you write is stripped and replaced with an automatic leading+trailing `%` — the match is always "contains" regardless of where you place `%` in the pattern.

## Response Structure

```json
{
  "isError": false,
  "toolName": "get_ads_perf",
  "data": {
    "rows": [
      {
        "campaign.campaignName_": "Brand-SP-Auto",
        "date": "20240601",
        "Impressions": 12500,
        "Clicks": 320,
        "Spend": 156.80,
        "Sales": 890.50,
        "ACOS": 17.61,
        "ROAS": 5.68
      }
    ],
    "rowCount": 1
  },
  "meta": {
    "page": 1,
    "pageSize": 100,
    "hasNextPage": false,
    "effectiveProfileIds": [4404871489220462],
    "currency": "USD"
  },
  "requestId": "a1b2c3d4e5f6"
}
```

**Everything is nested.** `rows` and `rowCount` live under **`data`**; pagination, currency and
hints live under **`meta`**. Only `isError`, `toolName` and `requestId` are top level. Reading
`response.rows` returns nothing - it is `response.data.rows`. `meta` keys are **omitted when
they do not apply** (not set to null), and `meta` itself is omitted when entirely empty.

| Field | Type | Description |
|---|---|---|
| `isError` | boolean | Top level. Whether the call errored — check this before reading rows |
| `toolName` | string | Top level |
| `requestId` | string | **Top level.** Trace ID for this call. **Quote it when reporting a failure to the user** so the platform team can trace it. May be absent in local/dev environments |
| `data.rows` | array[object] | Result rows — each row has the select dimension fields + metric fields |
| `data.rowCount` | int | Row count on the current page |
| `meta.page` | int | Current page number |
| `meta.pageSize` | int | Rows per page |
| `meta.hasNextPage` | boolean | Whether more pages exist — loop `page` while true |
| `meta.effectiveProfileIds` | array[long] | Profile IDs the query actually ran against — an echo of your request (unauthorized IDs fail the call outright rather than being dropped here). Verify it's the store the user meant |
| `meta.currency` | string | Currency of monetary metrics: the profile's local code for a single profile, `USD` for multiple |
| `meta.hint` | string | Present when something was adjusted silently — read it |

On error, the response instead follows the shared error envelope described in Platform-Wide Rules above — all errors use a single top-level `errorType` (tool and pipeline alike, e.g. `rate_limited` / auth failures).

## Notes

- Each page returns up to `pageSize` rows (max 500); use `page` for pagination and check `hasNextPage`. An out-of-range `pageSize`/`page` is an **error**, not clamped — floor computed values at 1
- `profileIds` is **required**. Always call `get_user_authorized_context` first. If the user doesn't name a store, pass all authorized `profileIds`
- **Every requested `profileId` must be authorized** — one bad value fails the whole call (`Requested profileIds contain unauthorized values`); nothing is silently dropped
- Hourly/AMS data (`timeGranularity: hourly` on campaign, or `factEntity: keywordPlacement`) is capped at a **7-day** span, and `keywordPlacement` returns `AISpend`/`AISales` as `0` and `AIACOS`/`AIROAS` as `null` — never read AI performance from it
- User says "Orders" -> convert to "Conversions"
- User says "ASIN" -> default to child ASIN, use `asin.asin_`
- Max date span 90 days on the `dateStart`/`dateEnd` request itself, max lookback 15 months — split longer windows into multiple ≤90-day calls first; week/month aggregation only reduces row count within each call, it does not raise the 90-day cap
- `dateStart`/`dateEnd` request params use `YYYY-MM-DD`; the `date` field returned in rows uses `YYYYMMDD` — don't mix them
- Default `dateEnd` to yesterday when unspecified (T+2 data delay)
- Always mind data volume to avoid query timeout
- `groupBy` is auto-filled from raw dimension fields in `select`; only pass it explicitly when `select` contains a custom aggregate expression
- Multi-profile queries auto-normalize monetary metrics to USD, **except** `asin.asinPrice_` which stays local currency
- **`get_entity_metadata` is deliberately different**: its money is configuration (budgets, bids, caps) and stays in each store's own currency, never normalized. So do not compare a budget from there with a `Spend` from here across stores without converting one side
- When `profileIds` has more than one entry, add `profile.profileId_`/`profile.profileName_` to `select` so rows can be attributed to a store
- Only request metrics valid for the chosen `factEntity` — check the support matrix above
- `ACOS`/`CTR`/`CVR` (confirmed Tier 1) are pre-scaled ×100 — don't re-scale, but append `%` when presenting to the user; filters use the raw ×100 number with no `%`. `TACOS`/`*Rate` fields (Tier 2) are unconfirmed — relay as-is with no `%`
- On error, check `errorType` and handle per the guidance above rather than assuming the question is unanswerable

## Reference Docs

- Shared cross-tool behavior (auth, errors, pagination, dates, currency, ratio-metric display rule, decision tree, inference rules): [`references/platform-notes.md`](references/platform-notes.md)
- Field dictionary (dimension fields by entity, metrics support matrix, metrics reference): [`references/field-reference.md`](references/field-reference.md)
- **Ad-type-dependent metrics** (which metrics require `campaignType` filter or specific `factEntity`): [`references/ad-type-dependent-metrics.md`](references/ad-type-dependent-metrics.md) — **must consult before querying**: NTB/Video/DPV/vCPM-attribution metrics (SB+SD only, not SP); AI metrics (campaign entity only); TopOfSearchIS (campaign+target only); ASIN business metrics (asin entity only, no cross-join with ad entities). When a query mixes universal and type-specific metrics, split into separate calls.
- Enum i18n (ZH/EN/JA display labels for all enum values — use this when presenting enum fields to the user or translating between API values and localized display text): [`references/enum-i18n.md`](references/enum-i18n.md)
- Query examples:
  - [Top-N campaign performance](references/example-campaign-performance.md)
  - [Time aggregation (weekly/monthly/quarterly) and splitting windows >90 days](references/example-aggregation-over-time.md)
  - [Hourly / AMS queries (intraday campaign curve, keyword × placement)](references/example-hourly-ams.md)
  - [Keyword target query](references/example-keyword-target-query.md)
  - [Search term query](references/example-search-term.md)
  - [ASIN business metrics query](references/example-asin-query.md)
  - [AI managed group performance](references/example-ai-group-performance.md)
  - [AND/OR nested filters](references/example-nested-filters.md)
  - [Global (store-level) aggregation](references/example-global-aggregation.md)
  - [Multi-profile comparison](references/example-multi-profile-comparison.md)
  - [Period-over-period comparison and Top Movers (WoW/MoM, join by ID, handle new/disappeared entities, zero-denominator deltas)](references/example-period-comparison-top-movers.md)
  - [ACOS root-cause investigation (chaining get_ads_perf → get_operation_log → get_entity_metadata)](references/example-acos-root-cause-investigation.md)
  - [Cross-entity ratio aggregation (never average ACOS/CTR/CVR — sum base metrics then recompute)](references/example-cross-entity-ratio-aggregation.md)
