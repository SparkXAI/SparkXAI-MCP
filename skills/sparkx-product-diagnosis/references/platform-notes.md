# SparkX AI MCP Read Tools — Shared Platform Notes

This file holds behavior that is **common to all 3 read tools** (`get_ads_perf`, `get_entity_metadata`, `get_operation_log`). It ships as `references/platform-notes.md` **inside each skill's own folder** — so this copy travels with the skill you're reading even if a Skill Hub installs/updates/downloads one skill folder at a time, since the reference file is nested under the same folder, not a sibling directory. Every skill that reads platform data (the three read skills plus the report/analysis skills built on them) carries a byte-identical copy for the same reason — this is intentional duplication for delivery robustness, not a mistake. Read this once per session before making tool-selection decisions.

## Auth Flow

All 3 tools authenticate via Bearer Token, handled by a shared pipeline (pre-ratelimit → auth → business ratelimit → error mapping). Each tool method itself only does param validation + business logic.

**Before calling any of the 3 read tools, you must first call `get_user_authorized_context`** to obtain the current token's authorized `profileIds`, `tenantId`, `userId`.

`get_user_authorized_context` response:
```json
{
  "isError": false,
  "toolName": "get_user_authorized_context",
  "userId": "12345",
  "tenantId": "2064",
  "profiles": [
    {"profileId": 4404871489220462, "profileName": "Star-Store-US", "countryCode": "US"},
    {"profileId": 9283746501928374, "profileName": "Star-Store-JP", "countryCode": "JP"}
  ]
}
```

How to use this:
- `profiles[].profileId` → the `profileIds` param for all 3 tools
- `profiles[].countryCode` → resolve "US store" style user references to a profileId
- `profiles[].profileName` → resolve store-name references
- **User didn't specify a store** → default to passing **all** authorized `profileIds` (cross-store aggregate; monetary metrics come back in USD — see Currency below)

**Always source `profileIds` from this call's response verbatim.** Never hand-type an ID, reuse one from an earlier session, or carry one over from a user message without confirming it appears in `profiles[]` — unauthorized IDs now fail the whole request (see below).

## Permission Scopes

Each tool requires a specific OAuth scope on the token. If a call fails with an auth/permission error, this is the likely cause — tell the user their token/role is missing the corresponding scope rather than guessing at a query bug.

| Tool | Required scope |
|---|---|
| `get_ads_perf` | `amazon_sa_performance_data:read` |
| `get_entity_metadata` | `amazon_sa_ads_configuration:read` |
| `get_operation_log` | `amazon_sa_ads_logs:read` |

## profileIds Authorization: All-or-Nothing

**All 3 tools require every requested `profileId` to be authorized. There is no silent intersection — one unauthorized ID fails the entire request.**

- every value in `profileIds` must appear in `get_user_authorized_context`'s `profiles[]`, and must be a positive integer
- if any requested ID is outside the authorized set, the call fails with `isError:true`, `errorType: invalid_params`, message `Requested profileIds contain unauthorized values` — **no partial results, no empty success**
- non-positive or non-numeric values fail with `Parameter 'profileIds' must contain only positive integers`
- `effectiveProfileIds` in the response echoes back the scope that was actually queried; since the request now fails outright on any mismatch, treat this field as a confirmation echo rather than a "did anything get dropped?" check

Practical consequences:
- For "swap store X for all my current stores" style requests, re-call `get_user_authorized_context` and use its list as-is. Don't append or splice IDs from memory.
- A permission change mid-session (store removed from the user's access) turns previously-working calls into hard failures. On `Requested profileIds contain unauthorized values`, re-fetch the authorized context and tell the user which store is no longer in scope — don't retry the same ID list.
- `entity='aiGroup_schedule'` on `get_entity_metadata` is stricter still: it needs **exactly one** authorized `profileId` (see that tool's skill).

## Diagnosing Zero/Empty Results

Any of the 3 tools can legitimately return zero rows for reasons that have nothing to do with "no data exists." Before telling the user "there's no data for that," work through this sequence — don't jump straight to that conclusion from the first empty response:

1. **Check `isError`.** If `true`, this isn't an empty-data situation at all — it's an error (see the error-handling section above). Handle it as an error, not as "no results."
2. **Check `effectiveProfileIds`.** An unauthorized profile can no longer cause a silent empty result — that fails as `invalid_params` with `Requested profileIds contain unauthorized values` (see profileIds Authorization above), so it shows up in step 1, not here. What this field is still good for: confirming you queried the store the user actually meant. If the user asked about "the JP store" and `effectiveProfileIds` holds the US profile, the empty result is a targeting mistake on your side — fix the profile and retry before concluding anything about the data.
3. **Check the date range for T+2 delay effects (`get_ads_perf` only) — but note this is different from a range violation.** If `dateStart`/`dateEnd` genuinely exceed the 90-day span or 15-month lookback, that's a request-construction mistake that should surface as `isError:true` (`errorType: invalid_params`) per the error-handling rules above — it should not come back as a silent empty success. If you're instead seeing `isError:false` with empty/incomplete rows for a *valid* range that includes "today" or very recent days, that's the T+2 delay: recent data genuinely hasn't finished processing yet, which is a legitimate (if unhelpful) empty-but-correct result — not a bug and not "no data exists," just "not processed yet."
4. **Confirm the requested fields/metrics are actually valid for the `factEntity`/`entity` in use** (see the Metrics × Entity Support Matrix). Requesting an unsupported combination is documented as a common source of `invalid_params` errors — so this should also come back as `isError:true`, not a silent empty result. If you're getting empty-but-non-error rows, an invalid metric/entity combination is an unlikely explanation; look at filters and data existence instead (steps 5-6).
5. **Remove your business filters (`filters`) and retry.** If removing filters (state=enabled, spend thresholds, etc.) suddenly returns rows, the entity/data exists but didn't match your filter conditions — the honest answer to the user is "nothing matches your filter criteria," not "you have no data at all." These are different statements — don't conflate them.
6. **If you still get zero rows after 1-5, confirm the entity itself exists** via `get_entity_metadata` (e.g. does this campaign ID actually exist for this profile?). A nonexistent entity and an existing-but-inactive-in-this-window entity warrant different answers to the user.

**Only after working through this sequence** can you responsibly tell the user "there's genuinely no data/activity in that range" — and even then, be specific about what you checked (e.g. "no spend recorded for campaign X between these dates, and the campaign does exist and is enabled") rather than a bare "no data found."

## Error Response Format

**Every error uses a single `errorType` key.** Check `isError:true` first, then read `errorType`; depending on the error, extra fields accompany it (`requestId`, `recoveryHint`, `service`, `dimension`, `retryAfterSeconds`).

**Tool-execution errors** (parameter validation, query failures) — `errorType`:
```json
{
  "isError": true,
  "toolName": "get_ads_perf",
  "requestId": "a1b2c3d4e5f6",
  "errorType": "invalid_params",
  "message": "Parameter 'profileIds' is required and cannot be empty",
  "recoveryHint": "..."
}
```

**Pipeline errors** (auth, rate limit, downstream service) — same `errorType` key, plus error-specific fields:
```json
{
  "isError": true,
  "errorType": "rate_limited",
  "dimension": "tenant",
  "retryAfterSeconds": 30,
  "message": "Rate limit exceeded on dimension [tenant]. Retry after 30 seconds."
}
```

`requestId` is present on responses (success and error) and is the support handle. **When you report a tool failure to the user, include `requestId`** — it's what lets the platform team trace the call. It may be absent in local/dev environments.

**`errorType` enum** (every value uses the `errorType` key):

| identifier | Meaning | Common cause |
|---|---|---|
| `invalid_params` | Bad parameters | Missing required param, bad date format, date span over limit, unauthorized `profileIds`, `pageSize` out of range, illegal `timeGranularity`, null filter value |
| `serialization_error` | Serialization failure | Rare fallback case |
| `rate_limited` | Rate-limited | Token bucket exhausted on one dimension — retry after `retryAfterSeconds` |
| `rate_limit_service_unavailable` | Rate limiter down | The limiter fails **closed**: when it can't check, the request is rejected (429), not let through |
| `token_invalid` | Auth failure (401) | Token expired/invalid |
| `permission_denied` / `scope_missing` / `api_not_authorized` | Auth failure (403) | Token lacks the tool's scope, or the user's role lacks the underlying permission |
| `profile_out_of_range` | Auth failure (403) | Requested profile outside the token's grant |
| `business_error` | Backend / query-execution error (most common) | Read the semantic `message` and branch (unknown field, filter value type mismatch, result set too large, execution timeout, server busy); downstream service errors carry a `service` field (e.g. `Amazon_SA_Service`) |
| `timeout` | Query timeout | Narrow the range and retry |
| `service_unavailable` | Backend data source unavailable | ClickHouse connection pool exhausted — transient, retry shortly |
| `auth_service_unavailable` | Auth service unavailable | Auth check failed closed (503) — transient, retry shortly |

**The configured rate-limit policy** (token-bucket, per 60s window). Whether limiting is switched on is an environment setting, so you may never hit these — but plan against them rather than assuming they're off:

| Layer | Dimension | Budget |
|---|---|---|
| Pre-auth | client IP | 60 / min |
| Pre-auth | token prefix | 300 / min |
| Business | tenant + tool name | read **120 / min**, write 20 / min |
| Business | user + tool name | read **120 / min**, write 20 / min |

The `dimension` field on a `rate_limited` error tells you which bucket you hit: `ip`, `token_prefix`, `tenant`, or `user`. All 3 read tools count as reads (120/min per tool, per tenant and per user). A "loop pages until `hasNextPage=false`" plan over a large account can realistically hit this — pace the loop and raise `pageSize` toward the cap instead of firing many small pages.

**How to handle each error when talking to the user:**
- `invalid_params` → almost always a query-construction bug on the agent's side (bad field name, missing required param, date range too wide, unauthorized profile, out-of-range `pageSize`). Fix the call and retry — don't tell the user "the tool doesn't support this" until you've checked field names/param names against this skill's reference tables.
- `rate_limited` → wait `retryAfterSeconds` before retrying the *same* call. Don't retry in a loop. If it recurs, tell the user the query is being throttled and narrow scope (smaller date range, fewer profiles, fewer pages).
- `rate_limit_service_unavailable` → not your query's fault and not retryable immediately; the platform is failing closed. Tell the user the service is temporarily rejecting requests.
- `token_invalid` / `permission_denied` / `scope_missing` / `profile_out_of_range` → an auth/permission problem, not a query bug. Name the scope the tool needs (see Permission Scopes) and tell the user to have their token/role updated. Retrying the same call won't help.
- `business_error` → **read the `message` and branch — it is semantically translated, do NOT blindly retry**: `unknown field 'X'` → fix the field name against field_reference and retry; `filter value type mismatch` → fix the filter value's type and retry; `result set too large` → narrow the date range / add filters; `execution timeout` → narrow and retry; `server is busy` → wait a few seconds and retry; any other internal error → report as a transient failure and quote `requestId`.
- `timeout` / `service_unavailable` / `auth_service_unavailable` → backend/dependency temporarily unavailable, not a param problem. Retry once; if it persists, tell the user the data source is temporarily unavailable (quote `requestId`).
- `serialization_error` → rare edge case; report as a transient tool error, retry once.

Messages are sanitized server-side: SQL, tokens, signed URLs, internal hostnames, stack traces, and raw table names are redacted (you may see `[SQL_REDACTED]`, `[redacted_token]`, `[internal]`, `[table]`). Don't treat a redaction marker as corruption, and don't try to reconstruct what was removed.

Always check `isError` before reading `rows` — do not assume a response without `isError:false` explicitly checked is safe to parse as data.

## Null Filter Values Are Rejected

**Do not put null in `filters`.** All 3 read tools reject a null filter value (`invalid_params`, naming the field). This is intentional: a null used to be silently dropped, turning the query unconditional and returning **unfiltered full data** — indistinguishable from "the condition matched every row". The classic trigger: you look up an ID, the lookup returns empty, and you splice that empty result straight in as a filter value. **Abort on the empty result** instead.

### Query for genuinely-empty rows (`get_ads_perf` only)

```json
{"filters": {"campaign.campaignName_": {"isNull": true}}}
{"filters": {"campaign.campaignName_": {"isNotNull": true}}}
```

The boolean says whether the test holds, so `{"isNull": false}` equals `{"isNotNull": true}`. `isNull` rows + `isNotNull` rows = the unfiltered whole.

**`get_entity_metadata` has no null-test operator** (its downstream vocab is only eq/ne/in/notin/like/between) — to drop a constraint, just omit the field.

## Pagination Rules

| Tool | Pagination style | Default pageSize | Max pageSize | Out-of-range value |
|---|---|---|---|---|
| `get_ads_perf` | `page` + `pageSize` | 100 | 500 | **Error** |
| `get_entity_metadata` | `page` + `pageSize` | 100 | 500 | **Error** |
| `get_operation_log` | single non-`aiGroup` entity: `page` + `pageSize`; multi-entity or `aiGroup`-only: limit-only | 100 | 1,000 (`aiGroup`-only 10,000) | Clamped silently |

**The two behaviors are different — this bites when you compute `pageSize` instead of hard-coding it.** On `get_ads_perf` and `get_entity_metadata`, a `pageSize` of `0`, a negative number, or anything over `500` fails the call with `invalid_params` (`Parameter 'pageSize' must be between 1 and 500`); `page` ≤ 0 fails with `Parameter 'page' must be greater than 0`. Nothing is clamped for you. So a derived value like `pageSize = min(topN, 500)` must also be floored at 1 — `topN=0` is now an error, not an empty page. `get_operation_log` still clamps (it takes `min(pageSize, max)` and doesn't complain), so don't port either assumption to the other tools.

`get_entity_metadata` with `entity='aiGroup_schedule'` ignores pagination entirely and returns every schedule for the group in one call; its response omits `page`/`pageSize`/`hasNextPage`.

`get_operation_log` has **two modes decided by `entities`**. When `entities` is exactly one non-`aiGroup` entity: **real pagination**; loop `page` while `hasNextPage=true` to retrieve the complete set (raise `pageSize` toward 1,000 to cut round trips). When `entities` is empty/multiple or only `aiGroup`: **limit-only**; a single call caps at `pageSize` (max 1,000, or 10,000 for `aiGroup`-only), always time-descending; check `truncated`. On `truncated=true` you cannot page; first prefer steering the user to a single entity (real pagination), otherwise split the date range into non-overlapping sub-windows and recurse (see `sparkx-query-operation-log`'s "Getting a Complete Count"); adding `resourceIds`/`operationType`/`changeBy` filters is a last resort (changes *what* you're searching for; flag the result as partial).

## Date Range Limits

**⚠️ Illustrative dates**: any concrete date shown in this skill's own example files (e.g. `2026-06-01`) is for format illustration only — it will eventually fall outside the 15-month lookback window as time passes. Always substitute real dates that satisfy the constraints below at call time; never copy an example's literal date value into a live call without checking it's still within range.

| Tool | Max date span | Earliest lookback | Format |
|---|---|---|---|
| `get_ads_perf` (daily) | 90 days | 15 months | `YYYY-MM-DD` |
| `get_ads_perf` (hourly — `timeGranularity: hourly`, or `factEntity: keywordPlacement`) | **7 days** | 15 months | `YYYY-MM-DD` |
| `get_operation_log` | 90 days | 15 months | `YYYY-MM-DD` |
| `get_entity_metadata` | No date limit (no date params at all) | — | — |

**Hourly (AMS) queries are capped at 7 days, not 90.** This applies to `timeGranularity: hourly` (campaign only, SP+SB+SD) and to `factEntity: keywordPlacement` (SP only, hourly by nature). Exceeding it is an error, not a truncation. `hourly` on any entity other than `campaign` is also an error — it is not ignored and does not fall back to daily. `keywordPlacement` additionally uses asymmetric field naming (bare names in the request, `_`-suffixed keys in the response) and a restricted metric set. See `sparkx-query-ads-performance` for the full hourly rules.

These are two **separate** hard constraints on the `dateStart`/`dateEnd` request parameters, not "auto-truncate":
1. **Max span is 90 days, counting both endpoints (inclusive).** Precisely: `dateEnd - dateStart` (as a plain date subtraction) must be **≤ 89**, not ≤ 90 — since both `dateStart` and `dateEnd` count as covered days, a subtraction of 90 actually spans 91 inclusive calendar days, one more than the limit. Think of it as "≤ 90 inclusive calendar days," and derive the subtraction bound (89) from that, not the other way around. **Weekly/monthly aggregation (`select: [..., "toMonday(...) as week"]`) does NOT let you bypass the span limit either way** — it only reduces the number of *rows* a single already-compliant call returns. If the user wants a window longer than 90 days (e.g. "performance over the last 12 months by month"), you **must first split into multiple calls, each spanning ≤90 inclusive days** (a full year typically needs **5** such calls, not 4 — calendar quarters are 91-92 days and don't reliably fit under the 90-day cap, so don't split by quarter; see sparkx-query-ads-performance's aggregation-over-time example for a worked, verified split), and *then*, within each call, optionally use week/month aggregation in `select` to reduce that call's row count. Splitting is mandatory; aggregation is optional and orthogonal.
2. `dateStart` cannot be more than 15 months before today — going further back returns an error, it does not silently clamp the range for you.

If a user's requested range exceeds 90 days, **proactively split it** into sequential ≤90-day calls rather than sending one oversized request and waiting for it to fail.

**Data delay**: ad performance data has a T+2 delay. "Today"'s data is usually incomplete. When the user doesn't specify an end date, default `dateEnd` to **yesterday**, not today.

### Date Format: Query Params vs. Data Fields

**These are two different formats — do not use one where the other is expected.**

| Where | Format | Example |
|---|---|---|
| `dateStart`/`dateEnd` request params (`get_ads_perf`, `get_operation_log`) | `YYYY-MM-DD` | `"2026-06-01"` |
| `date` dimension field returned in `get_ads_perf` rows (daily grouping) | `YYYYMMDD` (no dashes) | `"20240601"` |
| `campaignStartDate`/`campaignEndDate` fields in `get_entity_metadata` (both as returned values and as filter values) | `YYYYMMDD` (Ymd, no dashes) | `"20260101"` |
| `createdDate` field in `get_operation_log` rows | Full timestamp, **timezone varies by entity + `profileIds` count** — see the next section | `"2026-08-24 07:01:06"` |

Concretely: when you *request* a date range, always use `YYYY-MM-DD`. When you *read or filter* the `date`/`campaignStartDate`/`campaignEndDate` data fields, use `YYYYMMDD` with no separators — e.g. `{"campaignStartDate": {">=": "20260101", "<=": "20260131"}}`, not `{"campaignStartDate": {">=": "2026-01-01"}}`. Getting this backwards is a common cause of a filter silently matching nothing or an `invalid_params` error.

### ⚠️ `get_operation_log`'s `createdDate` timezone depends on your request shape

**Confirmed by testing (2026-08): the timezone of `createdDate` is not fixed — it varies with the entity type and with how many `profileIds` you passed.**

| Entity in `entities` | profileIds count | `createdDate` timezone | Example |
|---|---|---|---|
| `aiGroup` | one or many | **UTC** | `2026-08-24 05:58:50` |
| `campaign` / `adGroup` / `target` / `placement` | **one** | **Store-local time** | `2026-08-24 00:01:06` (LA time) |
| `campaign` / `adGroup` / `target` / `placement` | **many** | **UTC** | `2026-08-24 07:01:06` (UTC) |

Verified against a single pause record on a US (`America/Los_Angeles`, UTC-7) profile: requesting one `profileId` returned `00:01:06`, requesting two returned `07:01:06` — exactly the 7-hour LA daylight-saving offset for the *same event*.

**What this means in practice:**

- **The same log entry can carry two different timestamps** depending on how many stores you queried. Adding a second store to a query silently shifts every ad-entity timestamp in the result by that store's UTC offset.
- **Never compare or merge timestamps across a single-profile result and a multi-profile result.** They're in different clocks. If you already pulled single-store data and then widen to all stores, re-pull rather than stitching.
- **Never present `createdDate` as "the store's time" without knowing which branch you're in.** In a multi-profile call, a `2026-08-24 07:01:06` on a US store is 00:01 local — reporting it as "7am" is wrong by a business day's worth of interpretation near midnight.
- **Mixed `entities` mean mixed clocks in one response.** A query with `entities: ["campaign", "aiGroup"]` returns UTC for the aiGroup rows and (if single-profile) store-local for the campaign rows, in one time-sorted list. The sort itself is done on the raw string, so a mixed-clock result is not reliably chronological.
- **Choose deliberately:**
  - Want store-local times the user can match against their own console? Query **one profile at a time** and restrict `entities` to ad entities.
  - Want a comparable cross-store timeline? Query **multiple profiles** (everything comes back UTC) or convert client-side using each row's `countryCode`, and label the output as UTC.
- **When you show a timestamp, label the zone** ("2026-08-24 07:01 UTC" / "2026-08-24 00:01 store time"). An unlabeled timestamp from this tool is ambiguous by construction.

Note this is a property of the log data itself; the MCP layer passes `createdDate` through unchanged and does no conversion.

### Unconfirmed: which timezone the `dateStart`/`dateEnd` *filter* boundary uses

Separate from the above: the platform spec still doesn't state which timezone `dateStart`/`dateEnd` are interpreted in when resolving a day boundary. Given the `createdDate` behavior just described, don't infer it — a request-level boundary in one zone and a returned value in another are entirely possible.

This matters most for boundary-sensitive windows ("yesterday") on non-UTC stores in multi-country queries: you can be off by up to a full day at the edges.

- When precision matters, say you're not certain which zone the boundary uses and treat results near day boundaries as approximate.
- Prefer an explicit reference point ("results for 2026-07-19") over a bare relative date ("yesterday"), so any boundary ambiguity is visible rather than baked into an unlabeled range.

## Currency Rules

Amount fields carry a `currency` indicator, but the exact mechanism differs by tool/entity — read carefully, this is a common source of dollar-amount misinterpretation with multi-store customers.

### get_ads_perf

| Scenario | Outer `currency` | Behavior |
|---|---|---|
| Single profile | That profile's local currency code (e.g. `"JPY"`) | All monetary metrics (Spend/Sales/CPC/etc) in local currency |
| Multiple profiles | `"USD"` | All monetary metrics auto-converted to USD |

**Exception**: the `asin.asinPrice_` dimension field (product list price) is **always local currency** and is NOT affected by the USD conversion above, even in a multi-profile query. If `select` includes `asin.asinPrice_` on a multi-profile call, that one field's value does not match the outer `currency=USD` — cross-reference `profile.countryCode_` to determine its actual currency.

### get_entity_metadata

| Entity | Scenario | Outer `currency` | Per-row `currency` field | Notes |
|---|---|---|---|---|
| campaign/adGroup/portfolio/etc | Single profile | Local currency code | **may also be present** | `dailyBudget` etc in local currency |
| campaign/adGroup/portfolio/etc | any | single: that store's code; multi: **not present** | **always present**, value may be `null` if the profile currency could not be resolved | Config amounts stay in each store's own currency — **not** FX-converted. A `null` here also raises a `meta.hint`; never fall back to USD |
| **asin** | Single profile | Local currency code | **may also be present** | `asinPrice`/`parentAsinPrice` in local currency — the row field is emitted whenever the underlying row has one, regardless of profile count |
| **asin** | Multi profile | **not present** | present **only when the row has one** — the key is omitted rather than set to `null` | Same rule; `asin` was the first entity to work this way. Note the difference from AdsList above, where the key is always present and may be `null` |
| aiGroup / aiGroup_schedule / automationRule | any | **not present** | **none** | Other providers, no currency handling. Currency semantics for these are **not established** — do not infer them (`automationRule` returns no `profileId` at all) |

`asin` multi-profile example:
```json
{
  "isError": false,
  "toolName": "get_entity_metadata",
  "rows": [
    {"asin": "B0XX", "asinPrice": 29.99, "currency": "USD", "profileId": 111},
    {"asin": "B0YY", "asinPrice": 2980, "currency": "JPY", "profileId": 222}
  ]
}
```

**Rule of thumb**: **prefer a row's own `currency` whenever it is present** — it is emitted independently of profile count. Fall back to the outer `currency` only when the row has none. Outer present → all rows share it; outer absent **and** row absent → currency is undetermined, see the handling rule in the skill.

### get_operation_log

Amount-bearing fields (e.g. `previousValue`/`newValue` for a `dailyBudget` change) are always **local currency** — there is no cross-profile USD conversion for logs. Each row carries a `currencyCode` field (e.g. `"USD"`/`"JPY"`) mapped from that row's `countryCode`.

This tool *may* also emit an outer `currency`, inferred from the rows: if every row shares one currency you get that code, if the result mixes currencies you get the literal string **`"mixed"`**, and if no row carries a currency the field is absent. **`"mixed"` is not a currency** — never render an amount as "123 mixed" or sum across rows when you see it; fall back to each row's own `currencyCode` and either report per-store or state that amounts aren't directly comparable.

## Ratio Metric Display Rule

**Two tiers — do not treat every ratio-shaped metric the same way.** Only some fields have confirmed evidence of a ×100/percentage scale in the platform spec; the rest are unconfirmed and must be handled more conservatively.

### Tier 1 — Confirmed ×100/percentage scale

`ACOS` (`Spend/Sales×100`), `CTR` (`Clicks/Impressions×100`), `CVR` (`Conversions/Clicks×100`) — confirmed by their documented formulas and by the tool's own response example (`"ACOS": 17.61`, i.e. 17.61%). `aiGroup.targetAcos_` (`get_entity_metadata`) is confirmed by its explicit label "Target ACOS (percentage)". `UnitSessionPercentage` is confirmed the same way (explicitly labeled "percentage" in the spec). For these fields:

- The number is already ×100-scaled — do not multiply or divide by 100 again.
- **Append a `%` sign when presenting the value to the user**: if the tool returns `"ACOS": 17.61`, say "ACOS is 17.61%". If `targetAcos` returns `35`, say "target ACOS is 35%".
- When constructing a filter, pass the threshold on this same ×100 scale, as a plain number with **no `%` in the JSON**: `{"ACOS": {"<": 20}}` for "ACOS under 20%" — not `{"ACOS": {"<": 0.2}}` (which means "under 0.2%", almost never intended).

### Tier 2 — Unconfirmed scale (needs product team confirmation)

`TACOS`, `ShippedTACOS`, `OrderedTACOS`, `NTBOrdersRate`, `NTBUnitsRate`, `NTBSalesRate`, `ViewableImpressionsRate`, `AdsSalesRate`, `AdsOrdersRate`, `AdsUnitsRate`, `AdsSalesSameSKURate`, `AdsOrdersSameSKURate`, `Video5SecondViewRate` — the platform spec gives only a metric name for these, with **no formula and no example value**, so their scale is not independently verified the way Tier 1 is.

**`AdsCVR` is a special case, not just "unconfirmed"**: its documented formula is `Conversions/Clicks` — explicitly **without** `×100`, unlike `CVR`'s formula which explicitly includes `×100`. This is active evidence that `AdsCVR` may be on a *different* scale (a plain 0–1 ratio) than `CVR`, not merely an assumption gap. Do not treat it as interchangeable with `CVR`.

For all Tier 2 fields:
- Relay the tool's raw value exactly as returned — do not assume it's a percentage, do not multiply/divide by 100, and do not append a `%` sign, since you don't actually know if the number is already ×100-scaled or a 0–1 ratio.
- Do not construct filters against these fields using an assumed percentage scale (e.g. don't guess that `20` means "20%") — if the user wants to filter on one of these, either ask what scale they mean or note the ambiguity, and flag it to the SparkX AI product team for explicit confirmation before the skill can give guidance as confident as Tier 1's.

`ROAS`, `CPC`, `CPA` are **not percentages at all** — they're plain ratios/currency-per-unit values (e.g. `ROAS: 5.68`), not covered by either tier.

## Multi-Profile Row Attribution

When a call spans **more than one** `profileId`, make sure the response can actually be attributed back to a specific store before presenting results — rows with the same campaign/entity name across different stores are otherwise indistinguishable to the user.

- **`get_ads_perf`**: add `"profile.profileId_"` (and usually `"profile.profileName_"`) to `select` whenever `profileIds` has more than one entry, so each row carries its store identity.
- **`get_entity_metadata`**: check whether the entity's returned rows include a `profileId` field (e.g. the `asin` entity does — see its Currency example). If the entity type you're querying doesn't surface `profileId` on its own, either issue one call per `profileId` or cross-reference by combining with a `get_ads_perf`/`asin` call that does carry `profileId`, before presenting a merged answer across stores.
- **`get_operation_log`**: every row already carries `profileId` (see ChangeLogVO fields) — map it to the store's `profileName` using the `profiles` list from `get_user_authorized_context` before describing a change to the user, especially when `entities`/`resourceIds` span multiple stores with same-named campaigns.

## Tool Selection Decision Tree

```
User intent:
├── Has a time range + wants metric data (spend/sales/ACOS/clicks/...)
│   ├── by hour / "which hours convert" / intraday pattern
│   │   └── → get_ads_perf (timeGranularity=hourly, campaign only, ≤7 days)
│   ├── keyword × placement breakdown
│   │   └── → get_ads_perf (factEntity=keywordPlacement, hourly by nature, ≤7 days)
│   └── → get_ads_perf (daily, default)
├── Asking about config/list/status (no metrics, no date range)
│   ├── "what campaigns exist" → get_entity_metadata (entity=campaign)
│   ├── "AI managed group config" → get_entity_metadata (entity=aiGroup)
│   ├── "the managed group's schedule / flights / seasonal plan"
│   │   └── → get_entity_metadata (entity=aiGroup_schedule; one profileId, filters.aiGroupId only)
│   ├── "this group runs on a rule — show me the rule's actual conditions/actions"
│   │   └── → get_entity_metadata (entity=aiGroup) and read aiAutomation.{ruleType}
│   │       (rule-mode config is readable; it is NOT writable through MCP)
│   ├── "product info / ASIN" → get_entity_metadata (entity=asin)
│   ├── "portfolio list" → get_entity_metadata (entity=portfolio)
│   └── "which automation rules are enabled on this campaign" → get_entity_metadata (entity=automationRule)
├── "Who did what" / "what did AI change" / "change history"
│   └── → get_operation_log  (mind the createdDate timezone rules)
└── Needs both metrics AND config
    └── get_ads_perf first for the data → get_entity_metadata to enrich with names/config
```

**Common combined-call patterns**:
- "What's the bidding strategy of the highest-spend campaign?" → `get_ads_perf` (find the top campaign) → `get_entity_metadata` (look up its config)
- "How did the AI managed group perform last week?" → `get_ads_perf` with `select` including `aiGroup.aiGroupName_`
- "What bids did AI change yesterday?" → `get_operation_log` with `changeBy=ai`, `actionType=Bid Increased/Bid Decreased`
- "Why did my ACOS go up?" (root-cause investigation, all 3 tools) → `get_ads_perf` twice to quantify the change and identify the affected campaign(s) → `get_operation_log` on that campaign over the same window to find candidate changes → `get_entity_metadata` for current config context. Report findings as correlation, not proven causation — see the dedicated ACOS root-cause example.

## Implicit Inference Rules

These are semantic mappings the agent should apply automatically when translating natural language into tool params.

### Metric name mapping (get_ads_perf)

| User says | Maps to metric | Note |
|---|---|---|
| Orders / conversions | `Conversions` | **Not** `Orders` — there is no metric literally named `Orders` |
| Spend / ad cost | `Spend` | — |
| Sales / revenue | `Sales` | — |
| Total sales | `TotalSalesAmount` | `asin` entity only |
| TACOS | `TACOS` | `asin` entity only |
| New-to-brand | `NTBOrders` + `NTBSales` | Pick based on what's asked |

### Status/filter inference (get_ads_perf, dimension fields use `entity.field_`; get_entity_metadata, plain camelCase — see each tool's own SKILL.md for the exact field format)

| User says | Inferred filter (ads_perf form) |
|---|---|
| AI-managed / AI ads | `{"aiGroup.aiStatus_": 1}` |
| Ads without AI enabled | `{"OR": [{"aiGroup.aiStatus_": 0}, {"aiGroup.aiStatus_": 2}]}` |
| Active / running ads | `{"campaign.campaignState_": "enabled"}` |
| Paused keywords | `{"target.targetState_": "paused"}` |
| "By portfolio" analysis | add `{"portfolio.portfolioId_": {">": 0}}` (exclude campaigns with no portfolio) |
| "By product line" analysis | add `{"productLine.productLineParentId_": {">": 0}}` |
| SP ads | `{"campaign.campaignType_": "sponsoredProducts"}` |
| SB ads | `{"campaign.campaignType_": "sponsoredBrands"}` |
| SD ads | `{"campaign.campaignType_": "sponsoredDisplay"}` |

### Time inference

**`get_ads_perf` is subject to the T+2 data delay** (see above) — default `dateEnd` to **yesterday** whenever the user doesn't give an explicit end date, since "today"'s ad performance data is usually incomplete.

| User says (get_ads_perf) | Inferred range |
|---|---|
| Last week | `dateStart` = last Monday, `dateEnd` = last Sunday |
| This month | `dateStart` = 1st of this month, `dateEnd` = yesterday |
| Last 30 days | `dateStart` = 30 days ago, `dateEnd` = yesterday |
| Quarter-to-date (QTD) | `dateStart` = 1st day of the current calendar quarter (Jan/Apr/Jul/Oct 1st), `dateEnd` = yesterday |
| Year-to-date (YTD) | `dateStart` = January 1st of the current year, `dateEnd` = yesterday |
| "Since this campaign launched" / "since we started" | **Not a fixed offset — look it up.** First query `get_entity_metadata` (`entity: "campaign"`) for that campaign's `campaignStartDate`, then use that as `dateStart`. **Constrained by the 15-month lookback**: if the launch date is more than 15 months ago, you cannot query the full lifecycle in one range — say so explicitly ("I can only go back 15 months; this campaign launched earlier than that, so this covers the most recent 15 months, not the full history") rather than silently truncating and presenting it as the complete picture |

**⚠️ Check for a reversed range before sending it — this month/QTD/YTD can produce `dateEnd < dateStart` on the first day of the period.** These rules all use "yesterday" as `dateEnd` (per the T+2 rule) but "1st of the period" as `dateStart`. If today is the 1st of the month/quarter/year, `dateStart` = today's date but `dateEnd` = yesterday — which is *before* `dateStart`, an invalid, reversed range. Concretely: querying "this month" on July 1st gives `dateStart=2026-07-01`, `dateEnd=2026-06-30` (reversed). The same happens for QTD on Jan/Apr/Jul/Oct 1st, and for YTD on January 1st. **Always compute `dateEnd` and compare it to `dateStart` before issuing the call.** If `dateEnd < dateStart`, do not send the request — the period genuinely has no completed days to report yet (e.g. "this month" on July 1st has zero elapsed complete days). Tell the user that directly ("this month just started, so there's no completed-day data yet") rather than sending a reversed range and letting it error, or worse, silently swapping the two dates and reporting the wrong period.

**⚠️ QTD/YTD/"since launch" frequently exceed the 90-day single-call cap — check the actual span before issuing one call.** A full quarter is 91-92 days on its own (already over the limit), so QTD past the first ~2 months of a quarter, any YTD beyond Q1, and "since launch" beyond ~3 months **all require the same split-then-merge procedure** as the aggregation-over-time example: split into contiguous ≤90-day windows first, then merge results by re-grouping on whatever time key you aggregated on and recomputing derived ratio metrics (`ACOS`/`CTR`/`CVR`/etc) from the summed base metrics — never average pre-computed ratios across windows. Don't assume "QTD" or "YTD" is safe to send as a single `dateStart`/`dateEnd` pair just because the phrasing sounds like one range — compute the actual day count first.
| Period-over-period / week-over-week (unspecified) | take an equal-length prior period, issue two `get_ads_perf` calls |
| Month-over-month (full calendar months, e.g. "July vs June") | compare the two full calendar months **as-is — do not force equal length** (months are 28-31 days); note the day-count difference to the user, and add each month's daily average if the user cares about rate rather than raw totals |
| Month-to-date-over-month-to-date (e.g. "this month so far vs last month so far") | align to the **same number of elapsed days** in each month (equal length is correct here, unlike full-calendar-month above) |

See the dedicated Period-over-Period and Top Movers example for the full procedure in all cases (join by ID, matching granularity/filters, full pagination before comparing, handling new/disappeared entities, zero-denominator deltas).

**`get_operation_log` has no documented processing delay** — operation logs record changes as they happen, not as a batch-aggregated report. Do **not** apply the same "default to yesterday" rule here.

| User says (get_operation_log) | Inferred range |
|---|---|
| Today's changes / what changed today | `dateStart` = `dateEnd` = **today** (not yesterday) |
| Last week | `dateStart` = last Monday, `dateEnd` = last Sunday |
| This month | `dateStart` = 1st of this month, `dateEnd` = **today** |
| Last 7 days | `dateStart` = 6 days ago, `dateEnd` = **today** |

## Common Pitfalls

- **`like` wildcard handling**: any `%` you include in a `like` pattern is stripped and replaced with an automatic leading+trailing `%` (case-insensitive substring match). Writing `{"like": "%test%"}` and `{"like": "test"}` behave the same — always effectively "contains", not prefix/suffix match.
- **Multi-profile `get_ads_perf` metrics are USD** (except `asin.asinPrice_`, which stays local). **`get_entity_metadata` is the opposite** — its config amounts stay in each store's currency and every row carries its own `currency`; see Currency Rules. When reporting a multi-profile **`get_ads_perf`** figure, say "in USD" explicitly so the user doesn't assume local currency. When reporting **`get_entity_metadata`** amounts, present each row with its own `currency` and **never label the combined result as USD** — group by currency, or convert explicitly and say so.
- **Multi-profile rows need store attribution** — see Multi-Profile Row Attribution above; don't merge same-named campaigns across stores without labeling which store each row belongs to.
- **`get_operation_log` pagination depends on `entities`**: a single non-`aiGroup` entity paginates for real (loop `page` until `hasNextPage=false`); multi-entity or `aiGroup`-only is limit-only. In limit-only mode with `truncated=true`, first prefer steering the user to a single entity (real pagination), otherwise split into non-overlapping date sub-windows until each returns `truncated=false`; if a single day alone is still truncated, say so rather than reporting a partial count as complete.
- **Query-param dates (`dateStart`/`dateEnd`) are `YYYY-MM-DD`; data-field dates (`date`, `campaignStartDate`, `campaignEndDate`) are `YYYYMMDD`** — see Date Format above. These are NOT interchangeable.
- **`get_ads_perf` max span is 90 days on the request itself** — week/month aggregation reduces row count within a call, it does NOT let one call's `dateStart`/`dateEnd` exceed 90 days. Split first, aggregate second.
- **ACOS/CTR/CVR/targetAcos/UnitSessionPercentage are confirmed pre-scaled ×100** (e.g. `17.61` = 17.61%) — don't re-scale, but **do append `%`** when presenting to the user (`"17.61%"`); filters stay on the raw ×100 scale (`{"ACOS": {"<": 20}}`). **TACOS/`*Rate` fields are unconfirmed** — relay the raw value as-is with no `%` and no assumed scale until backend confirms. See Ratio Metric Display Rule above.
- **Metric/field names are case-sensitive** — `Spend` ✓, `spend` ✗, `SPEND` ✗.
- **Field-naming convention differs by tool** — see the "Field Naming Rules" section in each tool's own SKILL.md before constructing `select`/`filters`. Do not assume the two tools share one convention.
- **One unauthorized `profileId` fails the whole call** — no silent dropping any more. Always take IDs verbatim from `get_user_authorized_context`.
- **`pageSize` out of range is an error on `get_ads_perf`/`get_entity_metadata`** (clamped only on `get_operation_log`) — floor any computed `pageSize` at 1 and cap it at the tool's max yourself.
- **Hourly/AMS queries cap at 7 days, not 90** — applies to `timeGranularity: hourly` (campaign only) and `factEntity: keywordPlacement` (SP only). `hourly` on any other entity errors rather than falling back to daily, and `keywordPlacement` requests use bare field names while its responses come back `_`-suffixed.
- **`get_operation_log`'s `createdDate` timezone shifts with the request** (`aiGroup` = UTC; ad entities = store-local for one profile, UTC for many) — always label the zone, never merge single- and multi-profile results. See the timezone section above.
- **`currency: "mixed"` on `get_operation_log` is not a currency** — read each row's `currencyCode` instead of formatting or summing.
- **`get_entity_metadata`'s `aiGroup` response is a projection of what's *currently effective*** — fields belonging to a disabled switch, and rules running in AI mode, are omitted rather than returned with stale values. A missing field means "not in effect", not "not configured" and not "write failed". See that skill for the full rules.
