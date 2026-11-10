---
name: sparkx-query-entity-metadata
description: >-
  Query advertising entity metadata: name, status, configuration, settings (no metrics; the only
  dated part is campaign budget usage).
  For finding entity lists, getting config details, discovering ad structure relationships,
  and for how much budget a campaign has left right now.
  Keywords: campaign list, campaign name, status query, AI group settings, ASIN info,
  ad group config, portfolio list, keyword list, product line, entity search,
  which ads, enabled/paused status, budget settings, bidding strategy, automation rules,
  managed group schedule, flight, seasonal plan, rule mode config, RBA rule conditions,
  budget usage, budget usage rate, remaining budget, how much budget is left, out of budget,
  over budget, budget status, budget capped, in-budget time, when did it run out of budget,
  预算使用率, 当前预算使用率, 剩余预算, 预算还剩多少, 超预算, 预算状态, 预算内时长,
  最近超预算时间, 预算跑满
metadata:
  version: 1.4.10
---

# Query Entity Metadata Skill

## MCP Tool

This skill maps to MCP tool: **`get_entity_metadata`**. Required scope: `amazon_sa_ads_configuration:read`.

Profile scope is resolved from the authenticated bearer token. `profileIds` is **required** — always call `get_user_authorized_context` first to obtain authorized profile IDs, then pass one or more into `profileIds`. **Every requested ID must be authorized: one unauthorized value fails the entire call** with `invalid_params` / `Requested profileIds contain unauthorized values` — nothing is silently dropped (see Platform-Wide Rules below). If the user didn't specify a store, pass **all** authorized `profileIds`. Never pass `tenantId` or `userId`; the server derives them from the token.

**`entity='aiGroup_schedule'` is stricter: it requires exactly one `profileId`.** See the dedicated section below.

**`userContext` (required)**: Each call must include a non-empty string. Preserve the user's original query as much as possible, plus the agent's reason for calling this tool. Summarize if too long, max 100 characters.

## Platform-Wide Rules

**Before using this tool, read [`references/platform-notes.md`](references/platform-notes.md)** — it covers auth flow, permission scopes, error handling, pagination tables, the Ratio Metric Display Rule (including `targetAcos`), currency rules, the tool-selection decision tree, and implicit inference rules shared across all 3 read tools. That file ships inside this same skill folder, so it travels with this skill regardless of how it's packaged/installed. This SKILL.md only covers what's specific to `get_entity_metadata`.

## When to Use

Use this tool when the user needs any of the following:
- Query entity metadata (name, status, config, etc)
- Find entity lists (e.g. all enabled campaigns, AI group list, portfolios with a budget set)
- Get entity configuration info (budget settings, bidding strategy, AI group targets, current keyword bid)
- Discover ad structure relationships (which AdGroups under a Campaign, ASIN ownership, which automation rules are enabled on a campaign)
- Search entities by condition (name fuzzy match, status filter, bid/budget threshold filter)
- Count entities (e.g. how many campaigns, how many portfolios have a budget)
- **Answer budget-consumption questions about campaigns** - "how much budget is left right
  now", "which campaigns are out of budget", "when did this campaign last run out", "how much
  of last week was it capped". These need `budgetUsageDateStart` / `budgetUsageDateEnd`; see
  "`entity: campaign` - budget usage" below. **`get_ads_perf` cannot answer them** - subtracting
  its `Spend` from a configured budget is wrong twice over: today's `Spend` is still
  accumulating, and `dailyBudget` is not the figure Amazon computes the usage rate against

**✅ To count matching rows, read `meta.total` - do not page.** `total` is the exact number of rows matching your filters, independent of `pageSize`. `data.rowCount` is only the current page's length and is never a total.

`total` is **omitted** when the downstream cannot supply one (notably `asin`, and `aiGroup` when its total is missing). In that case page to the end and sum `data.rowCount`, or narrow until one page fits. Entities that suppress pagination include `automationRule`, `aiGroup_schedule`, the five suggestion entities, `sdCategory`, and `categoryBrand`. The first seven and `categoryBrand` return every requested row. `sdCategory` instead caps output at 500 and reports `meta.truncated` / `meta.total`; narrow it rather than treating the cap as complete.

**Note**: This tool does NOT return performance metrics. For spend, clicks, ACOS etc, use `get_ads_perf`. It is also date-free **with one exception**: campaign **budget usage** takes `budgetUsageDateStart` / `budgetUsageDateEnd`. Budget consumption is not a performance metric and does not live in `get_ads_perf` - "how much budget is left today" is answered **here**, from Amazon's own figure, not by subtracting a delayed `Spend` from a configured budget.

**Note**: This tool does NOT return historical point-in-time snapshots — it only returns the entity's *current* configuration. There is no `asOfDate`-style parameter. If the user asks "what was the daily budget on 2026-03-26", that specific historical value cannot be retrieved with this tool; only the current value is available. Say so explicitly rather than guessing. **The one exception is campaign budget usage**: `budgetUsageDateStart` / `budgetUsageDateEnd` summarize budget status over a past window — see "`entity: campaign` - budget usage" below. They describe budget state only, not configuration history, so they still cannot answer "what was the budget set to".

See the Tool Selection Decision Tree above if the user's ask might belong to `get_ads_perf` or `get_operation_log` instead.

## Required Parameter: `entity`

Unlike `get_ads_perf` (which infers tables from `select`), `get_entity_metadata` requires you to **explicitly declare which entity you're querying** via the `entity` parameter. Omitting it is the most common cause of a failed call (`errorType: invalid_params`).

## DSL Parameter Format

```json
{
  "userContext": "User's original query + agent's calling reason",
  "entity": "campaign",
  "profileIds": [1234567890123456],
  "filters": {},
  "orderBy": [{"field": "fieldName", "direction": "ASC"}],
  "select": ["campaignId", "campaignName", "campaignState"],
  "page": 1,
  "pageSize": 100
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| profileIds | array[long] | **Yes** | — | Profile IDs from `get_user_authorized_context` -> `profiles[].profileId`. **All must be authorized**. `aiGroup_schedule`, `amcAudience`, `keywordGroup`, `suggestedKeyword`, `suggestedTarget`, `suggestedBid`, `sdCategory`, `categoryBrand`, `brandEntity`, `store`, `sdAudience`, `asset`, and `pageAsins` require exactly one profile |
| entity | string | **Yes** | — | Entity type to query. Enum: `profile` / `campaign` / `adGroup` / `target` / `keyword` / `negativeKeyword` / `negativeTarget` / `productAd` / `portfolio` / `placement` / `aiGroup` / `aiGroup_schedule` / `asin` / `automationRule` / `amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid` / `sdCategory` / `categoryBrand` / `brandEntity` / `store` / `sdAudience` / `asset` / `pageAsins`. The last twelve have specialized contracts below — the final five in [`references/sb-sd-creation-entities.md`](references/sb-sd-creation-entities.md). Note: productLine info is nested inside `asin` entity results, not a separate `entity` value |
| userContext | string | **Yes** | — | User's original query + reason, max 100 chars |
| filters | object | No | {} | Filter conditions. Field names are **camelCase**, no `entity.` prefix, no `_` suffix (e.g. `campaignState`, not `campaign.campaignState_`) |
| orderBy | array[object] | No | [] | `[{"field": "fieldName", "direction": "DESC"}]`. Non-empty sorting is rejected for `aiGroup_schedule`, `automationRule`, `keywordGroup`, `suggestedKeyword`, `suggestedTarget`, `suggestedBid`, and `amcAudience`. `asin` accepts one rule with a supported field and `ASC`/`DESC`; see [field reference](references/field-reference.md) for inventory eligibility limits. Never infer global Top N from a single sorted page. |
| select | array[string] | No | all fields | Return **only** these top-level fields (no nested paths), in the given order — **plus `currency`, which is always kept when the row has one**. Unknown fields are ignored (reported via `meta.hint`). Does not affect pagination. See "Trimming fields with `select`" below |
| page | int | No | 1 | Page number (1-based). **`page` ≤ 0 is an error**, not a fallback to 1. Ignored for `automationRule`, `aiGroup_schedule`, the five suggestion entities, `sdCategory`, `categoryBrand`, `brandEntity`, `store`, `sdAudience`, and `pageAsins`. `asset` pages normally |
| pageSize | int | No | 100 | Rows per page, max 500. **Out of range (≤0 or >500) is an error**, not clamped — floor any computed value at 1 |

## Trimming fields with `select`

When you only need a few fields, pass `select` to return just those — it noticeably shrinks the response and saves tokens. Rules:

- Field names use this tool's **plain camelCase** (e.g. `campaignState`) — **not** `get_ads_perf`'s `entity.field_` format.
- **Top-level fields only** — nested paths are not supported.
- Output order follows `select`; fields absent from a row are simply omitted; unknown field names are ignored and surfaced in `meta.hint` (with the first row's available fields).
- `select` **does not affect pagination** (`page`/`pageSize`/`hasNextPage` behave the same).
- ✅ **`currency` is the one field `select` never drops.** On a multi-profile read the server re-adds each row's `currency` after applying your projection, so you cannot accidentally strip the only thing that makes the amounts interpretable.
- ⚠️ **`profileId` is NOT preserved that way — list it yourself.** On any multi-profile query with `select`, always include `profileId`; without it two stores on the same currency produce rows you cannot tell apart, and you lose the only handle for attributing a row back to a store.
- ⚠️ **A `select` of ids alone produces rows you cannot phrase an answer from.** Answers are
  given by name, not by id (see `references/platform-notes.md` -> "Naming things in your
  answer"), so whenever the rows will be shown to a user, include that entity's label field -
  `campaignName`, `adGroupName`, `portfolioName`, `aiGroupName`, `asinTitle`, `keywordText`,
  `targetText` - plus the entity's `amazon*Id` if an id was asked for. There is no second
  chance: a field left out of `select` is simply absent from the response.
- ⚠️ **The `{field}Text` companion fields are NOT auto-included under `select`.** `select` is a strict projection: only the fields you list come back. If you still need the human-readable enum label (or will translate enums), you **must list both** the field and its `Text` companion, e.g. `["campaignState", "campaignStateText"]`. Selecting only `campaignState` returns the raw value `"paused"` — you won't get `"Paused"`.

## ⚠️ Field Naming Differs From `get_ads_perf`

This is the single most important thing to get right. `get_ads_perf` dimension fields use `entity.field_` (prefix + underscore suffix). **`get_entity_metadata` fields do NOT** — they are plain camelCase field names with no prefix and no suffix:

| Tool | Example |
|---|---|
| `get_ads_perf` (select/filters) | `campaign.campaignState_` |
| `get_entity_metadata` (filters/orderBy) | `campaignState` |

Do not copy the `get_ads_perf` field format into this tool — it will fail.

## `entity` Enum Values, Fields by Entity

**See [`references/field-reference.md`](references/field-reference.md)** for the complete field dictionary: entity enum values and backing providers, and all per-entity field tables, including `sdCategory` and `categoryBrand`, with filterable fields, enums, and usage examples.

**See [`references/sb-sd-creation-entities.md`](references/sb-sd-creation-entities.md)** for the five entities that exist to feed Sponsored Brands and Sponsored Display creation: `brandEntity`, `store`, `pageAsins`, `asset`, `sdAudience`. They return Amazon-side ids you cannot construct, two of them only work in sequence, and `sdAudience` cannot be paged despite the hint that says otherwise.

## `entity: aiGroup_schedule` — managed-group schedules (special contract)

Reads the schedule ("flights", seasonal plans) of **one** AI managed group. Its calling contract is different from every other entity — the generic rules in this file do not apply as-is.

```json
{
  "userContext": "Show the schedule for managed group 29123",
  "entity": "aiGroup_schedule",
  "profileIds": [2618208845223116],
  "filters": {"aiGroupId": 29123}
}
```

| Rule | Detail |
|---|---|
| `profileIds` | **Exactly one**, and authorized. Zero/many → `aiGroup_schedule query requires exactly one authorized profileId` |
| `filters` | **Must contain `aiGroupId` and nothing else.** Missing → `aiGroup_schedule query requires filters.aiGroupId`; extra keys → `aiGroup_schedule query only supports filters.aiGroupId` |
| `aiGroupId` value | A single positive integer. `29123`, `[29123]`, and `{"in": [29123]}` are all accepted; multiple IDs are not |
| Pagination | **Ignored.** Returns every schedule for that group in one call. The response omits `page`, `pageSize`, `hasNextPage` |
| `orderBy` | Ignored |

Consequences for how you use it:
- **Don't try to page it**, and don't apply the "count by looping pages" rule from the counting section above — `rowCount` here *is* the total number of schedules for the group.
- **One group per call.** To cover several groups, call once per `aiGroupId`, serially.
- Get `aiGroupId` from `entity: aiGroup` first (or from the user). It's the internal ID, same as `aiGroup.aiGroupId`.
- To find schedules across stores, loop stores one at a time — you cannot pass multiple `profileIds`.

Schedules define time-boxed overrides of the group's settings: a fixed date window (`timeType=1`) or a weekly repeat (`timeType=2`). Weekly schedules inherit `optimizeType`/`acos`/`aiPersonality` from the parent group rather than carrying their own — so when reporting a weekly schedule, read those three from the group, not the schedule row. Writing schedules is a separate tool (`save_sp_sb_ai_group_schedule`, SP/SB only) and is out of scope for this read skill.

## `entity: aiGroup` — you get the *currently effective* config, not the raw record

**`entity: aiGroup` returns the *currently effective* config, not what was configured.** Read [`references/ai-group-effective-config.md`](references/ai-group-effective-config.md) before reporting any managed-group setting. These three cost you a wrong answer with no error, so they stay here:

- **A missing field means "not in effect right now"** - not "not configured", and never "a write failed".
- **`aiAutomation.{ruleType}.status` is a mode discriminator, not an enable switch.** A rule can be on and still be absent from `aiAutomation`.
- **Never read an empty `aiAutomation` on its own** as "no automation".

## `entity: campaign` - audience configuration arrives on its own

**Campaign rows carry their bound audience, and its configuration is merged in for you.** Read [`references/campaign-audience.md`](references/campaign-audience.md) before answering anything about audiences. The guards that fail silently:

- **`audienceId != ""` is the only test for "is an audience bound".** The key is always present, and **`audienceBidPercentage: 0` is ambiguous** - bound-with-no-uplift and unbound both read `0`. Never derive the unbound set by subtraction.
- **`audienceSegmentType` is on the row but can come back empty** - treat empty as unknown, never as a pool.
- **A row with an audience but no configuration is "unknown", not "broken"** - do not report it as unbound or invalid.
- **An SD campaign's blank `audienceId` does not mean SD has no audiences** - SD targets them one level down, as a `T00030` target. Read its targets, not this field.
- **Auto-update is `autoUpdate` (`0`/`1`), not the presence of `updateFrequence`**, and the enriched enums are **raw values, not display text**.

## `entity: campaign` - budget usage arrives only when you ask for it

**Budget consumption is available on campaign rows, but only when you pass the two date parameters.** Read [`references/budget-usage.md`](references/budget-usage.md) before answering "how much budget is left" or "which campaigns are capped". Six guards stay here because each one produces a confident wrong answer rather than an error:

- **`budgetUsage: null` is never 0% and never "in budget"** - archived campaign, no Amazon Marketing Stream data, or a failed lookup. `meta.hint` counts each; report those rows as unavailable.
- **A `select` that omits `budgetUsage` silently cancels the lookup** - the dates are still validated, but nothing is fetched and `meta.hint` says nothing. If you pass `select` at all, `"budgetUsage"` must be in it.
- **Never rank or threshold on `outOfBudgetPercentage`.** Its denominator is the whole selected window, so a campaign with little history is diluted and sinks below an older one that was capped less. Rank on `outOfBudgetMinutes`.
- **Never combine `budgetUsage` with `dailyBudget` / `currentBudget`.** The percentage is against `budgetSnapshot`, which on a managed campaign can differ from `dailyBudget` by two orders of magnitude.
- **`currentBudgetUsagePercentage: 0` alongside spend today is normal.** It is the latest value, not a window aggregate - but it only moves per ~5% of budget consumed, so **quote `usageUpdatedTime` with it** instead of calling it live or stale.
- **`lastOutOfBudgetTime: null` means "no record in the last 30 days", not "never"**, and a non-null value is the **start** of the last capped period, not proof it is capped now.

## Category and brand ids for product targeting

`sdCategory` returns the marketplace category tree flattened into rows. It requires exactly
one profile and at least one narrowing filter: non-blank `keyword`, `parentCategoryId`, or
`level`. `targetableOnly` alone is not enough. Filters are single-valued; pagination and
sorting are ignored. Category ids are strings. More than 500 matches sets
`meta.truncated=true` and `meta.total`; narrow again and never guess unseen ids.

`categoryBrand` requires exactly one profile and a single `filters.categoryId` from
`sdCategory`; optional `keyword` narrows brand names. It returns string `brandId`,
`brandName`, and a copyable `targetExpression`. The chain is:
`sdCategory -> categoryBrand -> create_sp_ad_group/create_sp_sb_campaign`.

These entities use the td-api category service. `service_unavailable` with
`service: td-api` means its platform credential was rejected: do not retry and never invent
category or brand ids.

## Suggestion entities - a different contract from everything above

**The suggestion entities (`amcAudience`, `keywordGroup`, `suggestedKeyword`, `suggestedTarget`, `suggestedBid`) follow a different contract from every entity above.** Read [`references/suggestion-entities.md`](references/suggestion-entities.md) before calling one - it carries the mandatory filter per entity, and getting that wrong is an error you will see. What you will **not** see is:

- **They are recommendations, not account state.** `suggestedKeyword` does not tell you which keywords a campaign actually runs; use the `keyword` / `target` entities for that.
- **A missing `suggestedBid` means no suggestion was obtained** - not a bid of zero.
- **An empty auto-mode result is not proof the products cannot be advertised.**
- **Request and response field names differ** on these entities; do not assume what you sent is what comes back.

## Filtering by an id: the field decides the id space, and a mismatch fails silently

**Both id spaces are filterable.** What matters is that the field and the value agree, and
**the only reliable signal is the field name the value came out of** - per entity. Two
tempting shortcuts are both wrong:

- **Not digit length.** Length is an observation about today's data, not a contract.
- **Not which tool returned it.** `get_operation_log` rows carry `entityId` (internal) *and*
  `amazonEntityId` / `amazonCampaignId` / `amazonAdGroupId` (Amazon) side by side. "It came
  from the log, so it is an Amazon id" is false.

**The per-entity field tables in
[`references/field-reference.md`](references/field-reference.md) are the source of truth.**
The examples below are orientation, not a lookup table - check the entity you are actually
querying:

| Example field | Holds |
|---|---|
| `campaignId`, `adGroupId`, `targetId`, `keywordId`, `productAdId`, `negativeKeywordId`, `negativeTargetId`, `aiGroupId` | the **internal** id (`aiGroupId` has no Amazon counterpart) |
| `amazonCampaignId`, `amazonAdGroupId`, `amazonKeywordId`, `amazonTargetId`, `amazonAdId`, `amazonPortfolioId` | the **Amazon** id |

⚠️ **`portfolioId` means opposite things on different entities** - and this is exactly why
the field name has to be read *per entity* rather than pattern-matched:

| Where | `portfolioId` holds |
|---|---|
| on `campaign` | the **Amazon** portfolio id (the value that matches `portfolio.amazonPortfolioId`) |
| on `portfolio` | the **internal** portfolio id |

So filtering by an Amazon id is perfectly normal, and is the documented way in when that is
the id you hold: filter on `amazonCampaignId`, then take the matched row's internal
`campaignId` for anything that needs it.

**The failure mode is putting a value in a field belonging to the other space**, e.g. taking
`amazonCampaignId` off a performance or log row and passing it as `campaignId`. That filter
is valid and passes every check - it simply matches nothing, so you get **`0` rows and no
error**. An empty result then reads exactly like "this entity cannot be filtered by
campaign", which is the wrong conclusion to hand the user.

- **Track which field each id came out of**, and carry that with it. When a value has been
  copied between steps and you are no longer sure, re-read it rather than guessing.
- **Which ids a row carries varies by entity - look it up rather than assuming.** For
  AdsList entities that have an Amazon counterpart, a row exposes the id pair for that
  entity; parent references are generally internal-only. An `adGroup` row has `adGroupId`
  and `amazonAdGroupId` but **no `amazonCampaignId`**, and its `campaignId` is the internal
  parent id - so to report that parent in Amazon terms you query the campaign entity. Not
  every entity fits the pattern: `aiGroup` has no Amazon id at all, and `placement` does
  return `amazonCampaignId` alongside the internal one. The per-entity tables in the field
  reference are the only reliable answer.
- **Before reporting an empty result**, check the field/value pairing. Say "no rows matched"
  only after that, and never generalise it into "filtering is not supported here".

**This is a wrong-*value* failure, not a wrong-*field* one** - the distinction matters,
because the next section is about the opposite case. A filter **field** that is not in the
entity's whitelist throws; a **value** belonging to the other id space passes every check and
just matches nothing. Loud failures you will see. This one you have to look for.

⚠️ **`automationRule` accepts only `amazonCampaignId`** - it **requires** that filter and
has no internal-id equivalent. That is a restriction specific to it, not the general rule.

## AdsList filter and sort rules (enforced - you get an error, not a silent fallback)

**Scope: the AdsList entities only** - `profile`, `campaign`, `adGroup`, `target`, `keyword`,
`negativeKeyword`, `negativeTarget`, `productAd`, `portfolio`, `placement`. `aiGroup`,
`aiGroup_schedule`, `asin`, `automationRule` and the five suggestion entities (`amcAudience`,
`keywordGroup`, `suggestedKeyword`, `suggestedTarget`, `suggestedBid`) come from other
providers and **do not share these validations**: `aiGroup`, for instance, silently takes only the first `orderBy` rule and
treats any direction other than `ASC` as descending, with no whitelist check at all. Do not
assume an error will catch a bad sort there.

The AdsList service used to fail silently on several of these. **It now rejects them**, so a
request that would once have quietly returned the wrong rows returns an error instead. Build
requests to these rules rather than discovering them at runtime.

**1. Paging and `total` (this one applies to every paginated entity).** `meta.total` is the
exact number of matching rows - use it directly, **do not page through results to count
anything.** `meta.hasNextPage` is derived from `total` when the downstream supplies one; when
it does not, `total` is omitted and `hasNextPage` falls back to "this page came back full", so
a completely full last page can report `hasNextPage: true` and cost one extra empty request.
`automationRule`, `aiGroup_schedule` and the five suggestion entities (`amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid`) are not paginated at all and carry none of these.

**2. Only `>=` and `<=` exist.** `>` and `<` are **rejected**:
`Strict comparison operators > and < are not supported ... do not substitute them unless
intended.` If you need a strict bound, use the inclusive one and drop the boundary rows
yourself.

**3. One operator per field**, except the `>=` + `<=` pair, which may be combined into a
range. Anything else is rejected (`supports only one operator, except the combined inclusive
>= and <= range`).

**3b. A range must be closed - a lone `>=` or a lone `<=` is rejected.** `One-sided range
filters are not supported for AdsList field '<field>'. A closed inclusive range requires both
>= and <= bounds. Do not invent a missing bound or remove the requested restriction.` Take the
error at its word: when the user asked for "budget over 50", do not silently add an upper
bound you made up, and do not drop the condition and report unfiltered rows as if they matched.
Either supply a bound you can justify (the entity's own maximum, a figure the user gave) and
say which one you used, or page the rows and apply the threshold yourself.

**4. The operator set is exactly** `in`, `notin`, `like`, `!=`, `ne`, `>=`, `<=`. Anything else
is rejected, including **`eq`** - equality is expressed by assigning the value directly
(`{"campaignState": "enabled"}`), not by `{"eq": ...}`. An empty operator object and a `null`
operator value are both rejected too.

**4b. `campaignState` and `costType` values are validated, case-sensitively.** A bad value is
rejected with `Invalid <field> '<value>'. Allowed values (case-sensitive): [...]` instead of
silently returning nothing, so `"Enabled"` and `"ENABLED"` now fail rather than looking like
"no campaigns". `campaignState` accepts `enabled` / `paused` / `archived`; `costType` accepts
`cpc` / `vcpm`, plus the empty string.

Two things about `costType` that the value list does not show:

- **`cpc` means "not vcpm", not "stored as cpc".** SP campaigns store an empty `costType`, so
  an equality match on `cpc` would miss all of them. The filter is rewritten to `!= vcpm`, the
  same definition the campaign page uses, and campaign rows report a blank stored value back
  as `cpc`. The empty string is accepted as a filter value for the same reason - it is the
  only enum field where blank is legal.
- **Selecting both values is not a filter.** `{"costType": {"in": ["cpc", "vcpm"]}}` covers
  every campaign, so the condition is dropped before the call. Excluding both
  (`{"notin": ["cpc", "vcpm"]}`) matches nothing and is rejected outright:
  `Filter 'costType' excludes both cpc and vcpm, which matches no campaign`.

**5. `orderBy` is validated.** It throws on: more than one rule (`AdsList supports exactly one
orderBy rule`), any sort on `placement`, a field that is not sortable for that entity, or a
direction other than `ASC` / `DESC`. So a bad sort field no longer silently degrades to the
default order - the call fails, which is what you want before reporting a "Top N".

**6. `like` is always "contains".** Every `%` you write is stripped. A literal `%` cannot be
matched. **Exact matching is still available** - pass the bare value, which maps to equality:
`{"campaignName": "Exact Campaign Name"}` (a bare array maps to `in`).

**7. `placement` has no sorting and an unstable page order.** `orderBy` on it is rejected, and
`meta.hint` says `Page order is not stable.` Never take "Top N placements" from its page order.
(The earlier gap where Sponsored Brands adjustments were not returned **has been fixed**: SB
now expands to `topOfSearch` / `home` / `detailPage` / `other`, SP to `topOfSearch` /
`productPage` / `restOfSearch` / `siteAmazonBusiness`. Rows with no adjustment value are
still skipped.) `topOfSearch` means a different placement on SP than on SB — see
`references/enum-i18n.md`.

## Money is per store

Monetary fields returned by the **AdsList entities** - campaign daily budget, ad group
default bid, target/keyword bid, portfolio budget, profile budget cap - are **configuration**
values set per marketplace, so **they stay in each profile's local currency and are not
FX-converted.**

(This covers the **AdsList entities and `asin`** only. `aiGroup`, `aiGroup_schedule` and
`automationRule` come from different providers and their currency semantics are **not
established** - do not infer them either way.)

- **Always prefer a row's own `currency` when it is present** - it is emitted whenever the
  underlying row has one, on single- and multi-profile reads alike. `meta.currency` is only a
  fallback for rows that carry none.
- **Single profile**: `meta.currency` is that store's currency code and covers rows that have
  no `currency` of their own.
- **Multiple profiles**: `meta.currency` is **omitted**, and each row is **expected** to carry
  its own `currency` - use the row's own value. `meta.hint` says the same thing.
- **On AdsList entities the key is always present, but the value may be `null`** when the profile or its currency could not be resolved (a `meta.hint` says so too). On `asin` the key is
  simply omitted in that case. Then look the row's `profileId` up in `get_user_authorized_context`. **If it is
  still unknown, stop**: do not assume USD, do not compare or total that amount against
  another row, and do not reuse it as the basis of a write. Say the currency could not be
  determined.
- **Never compare or sum amounts across currencies.** Group by currency, or convert
  explicitly and say that you did. A single "total budget" spanning a EUR store and a USD
  store is not a number you can state.
- *Transitional*: an older build labelled the whole multi-profile result `USD` **without**
  converting these config amounts. If you meet that, ignore the envelope label and attribute
  per row.
- **Before writing an amount, re-read it with a single `profileId`.** That is the only form
  where the value and its currency are unambiguous. This applies to `previousBid`, to a
  `setTo` amount, and to the base of any percentage change.

**`get_ads_perf` is deliberately different.** Its money is *performance* (`Spend`, `Sales`,
`CPC`, `CPA` ...) and multi-profile queries **do** normalise it to USD so stores can be
compared. So a `dailyBudget` from this tool and a `Spend` from that one are **not
comparable across stores** without converting one of them. (Within a single store both are
that store's currency and compare fine.)

A multi-profile read looks like this - note there is **no `meta.currency`**:

```json
{
  "isError": false,
  "toolName": "get_entity_metadata",
  "data": {
    "rows": [
      {"profileId": "111", "campaignId": 1, "dailyBudget": "100.00", "currency": "USD"},
      {"profileId": "222", "campaignId": 2, "dailyBudget": "10000", "currency": "JPY"}
    ],
    "rowCount": 2
  },
  "meta": {
    "effectiveProfileIds": [111, 222],
    "hint": "Amounts remain in each profile's local currency. Use each row's currency and do not compare or sum across currencies without explicit conversion. Limit conclusions to this query's scope. Missing fields are not zero, and empty results do not prove that no matching business data exists. Do not present partial or paginated results as complete. Distinguish returned facts from analytical inferences; state limitations or query further when evidence is insufficient."
  }
}
```

$100.00 and ¥10,000 are **not** addable, and the larger number is not the larger budget.

## Filter Syntax

Field names are **camelCase, no prefix/suffix** (different from `get_ads_perf`!).

```json
{
  "campaignState": "enabled",
  "campaignId": [123, 456],
  "campaignName": {"like": "%test%"}
}
```

**There are no `AND` / `OR` nodes on this tool.** `filters` is a flat field map: every key is
treated as a field name, so an `AND` or `OR` key is sent downstream as a field and rejected
(`filters field not in whitelist`). Consequences:

- **Multiple fields are implicitly ANDed** - just list them, as above.
- **`OR` across different fields cannot be expressed.** Run one query per branch and merge the
  rows yourself. **Do not de-duplicate on the internal id alone** - it is not unique across
  stores, ad types or the physical tables behind some entities. De-duplicate using **that
  entity's documented identity fields**. For entities that have an internal id, use at least
  `profileId` + that internal id, adding `campaignType` and the entity's own discriminator
  (`matchType`, `businessType`) where the entity returns them. Exceptions:
  - `profile` - identity is `profileId` (no internal id of its own)
  - `asin` - `profileId` + `asin` + `sku` (no internal id; one ASIN can have several SKUs)
  - `placement` - `profileId` + `campaignId` + `placement`
  - `automationRule` - `amazonCampaignId` (it returns no `profileId`)
- `OR` over *one* field's values is just `in`: `{"campaignState": ["enabled", "paused"]}`.
- (`get_ads_perf` *does* support `AND` / `OR` nodes. Do not carry its filter shape over here.)

**Supported operators**:

| Operator | Meaning | Backend op | Usage |
|---|---|---|---|
| `=` (bare value) | Equals | eq | `{"campaignState": "enabled"}` |
| `!=` | Not equals | ne | `{"campaignState": {"!=": "archived"}}` |
| `like` | Fuzzy match | like (case-insensitive) | `{"campaignName": {"like": "%test%"}}` |
| `in` | In list | in | `{"campaignState": {"in": ["enabled", "paused"]}}` |
| `notin` | Not in list | notin | `{"campaignState": {"notin": ["archived"]}}` |
| `>=` + `<=` | Closed range | between | `{"dailyBudget": {">=": 10, "<=": 100}}` — the **only** legal two-operator combination, and the only way to use either bound: **a lone `>=` or `<=` is rejected** |
| `>`, `<` | **Rejected** | — | Strict comparison is not supported; use `>=` / `<=` and drop boundary rows yourself. See "Filter, sort and paging rules" |

**Note on `like`**: any `%` you include is stripped and replaced with an automatic leading+trailing `%` — the match is always "contains" regardless of where you place `%`.

**`ilike` is not supported by this tool.** The filter operators accepted here are `in`, `notin`, `like`, `!=` / `ne`, `>=` and `<=`; anything else is rejected as `Unsupported filter operator for field '<field>': [...]`, which echoes what you sent and does **not** list the allowed set. Do not carry `ilike` over from `get_ads_perf` - the two tools handle text matching differently; here `like` already matches case-insensitively (see the table above), so there is nothing for `ilike` to add.

## Enum "Text" Companion Fields

For enum-valued fields, the response **automatically appends a human-readable `{field}Text` companion field** — but **only when you do NOT use `select`**. If you pass `select`, this auto-append does not happen; you must list each `xxxText` field explicitly (see "Trimming fields with `select`" above). Example (no `select`):
```json
{
  "campaignState": "enabled",
  "campaignStateText": "Enabled",
  "campaignType": "sponsoredProducts",
  "campaignTypeText": "Sponsored Products",
  "biddingStrategy": "autoForSales",
  "biddingStrategyText": "SP Dynamic bids - up and down"
}
```

Fields that get this treatment: all `*State` fields (campaignState/adGroupState/targetState/portfolioState/productAdState/keywordState/negativeKeywordState/negativeTargetState), all `*ServingStatus` fields, `campaignType`, `biddingStrategy`, `targetingType`/`targetMatchType`/`matchType`, `placement`, `costType`/`budgetType`/`portfolioBudgetType`, `aiStatus`/`aiTargetType`/`aiPersonality`, `asinInventoryStatus`/`asinSpEligibilityStatus`/`asinIsDelete`, generic `xxxStatus` (0/1) flags, `countryCode`, `isAiCreate`/`sdBidOptimization`/`profileUseBudgetCap`, `negativeTargetType`.

**Never require a `Text` companion to exist.** `businessType` and `tableType` are *not*
translated — there is no `businessTypeText`. And the set of `Text` columns for a page is
decided from the **first row only**: if row 0 happens to omit a key, no row in that page
gets its `Text` column. Render the values you actually received.

Customer-display exception: for managed-group `aiPersonality`, keep the raw numeric level `1`-`5`
as the displayed value. Do not substitute its `Text` companion; see the managed-group display guide.

**Exception**: `automationRule.enabledRuleNames` is already a human-readable string array — there is no separate `Text` field for it.

## Response Structure

```json
{
  "isError": false,
  "toolName": "get_entity_metadata",
  "data": {
    "rows": [
      {
        "campaignId": 826117,
        "amazonCampaignId": "298539385213868",
        "campaignName": "Brand-SP-Auto-US",
        "campaignType": "sponsoredProducts",
        "campaignState": "enabled",
        "biddingStrategy": "autoForSales",
        "targetingType": "auto",
        "dailyBudget": "50.00",
        "currentBudget": "0.00",
        "profileId": "4404871489220462",
        "portfolioId": 12345,
        "aiGroupId": 501
      }
    ],
    "rowCount": 1
  },
  "meta": {
    "page": 1,
    "pageSize": 100,
    "hasNextPage": false,
    "effectiveProfileIds": [4404871489220462],
    "currency": "USD",
    "hint": "Limit conclusions to this query's scope. Missing fields are not zero, and empty results do not prove that no matching business data exists. Do not present partial or paginated results as complete. Distinguish returned facts from analytical inferences; state limitations or query further when evidence is insufficient."
  },
  "requestId": "a1b2c3d4e5f6"
}
```

**Everything is nested.** `rows` and `rowCount` live under **`data`**; pagination, currency and
hints live under **`meta`**. Only `isError`, `toolName` and `requestId` are top level. Reading
`response.rows` returns nothing - it is `response.data.rows`. `meta` keys are **omitted when
they do not apply** (not set to null). A successful read always has `meta.hint`: any
entity-specific warning comes first, followed by the shared interpretation boundary.

| Field | Type | Description |
|---|---|---|
| `isError` | boolean | Top level. Whether the call errored — check this before reading rows |
| `toolName` | string | Top level |
| `requestId` | string | **Top level.** Trace ID — quote it when reporting a failure to the user. May be absent locally |
| `data.rows` | array[object] | Result rows — fields depend on `entity` |
| `data.rowCount` | int | Row count **on the current page**, never a total |
| `meta.page` / `meta.pageSize` | int | Pagination state, echoing your request (they echo it even on a zero-row response). **Absent** for `aiGroup_schedule`, `automationRule` and the five suggestion entities (`amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid`), which are non-paginated |
| `meta.total` | int | **Exact** number of matching rows - use this to count, never page for it. **Omitted** when the downstream supplies none (`asin`; `aiGroup` when unknown) and on non-paginated entities |
| `meta.hasNextPage` | boolean | Whether more pages exist. **Absent** for the non-paginated entities |
| `meta.effectiveProfileIds` | array[long] | Profile IDs the query ran against — an echo of your request (unauthorized IDs fail the call outright), minus duplicates |
| `meta.currency` | string | **Single**-profile query only — that store's resolved currency code. **Omitted on a multi-profile query** (and whenever a row's currency is unresolved); use each row's own `currency`. See "Money is per store" |
| `meta.hint` | string | Always present on success. Read every sentence. Entity-specific notices may include currency, unstable order, unresolved fields, truncation or unknown select fields; the shared interpretation boundary is appended last |

On error, the response instead follows the shared error envelope described in Platform-Wide Rules above (all errors use a single top-level `errorType`, tool and pipeline alike). A missing `entity` param surfaces as `errorType: invalid_params`.

## Notes

- `entity` is **required** — this is the #1 cause of failed calls. Do not call this tool without it. Enum includes `aiGroup_schedule` (managed-group schedules)
- Each page returns up to `pageSize` rows (max 500); use `page` to page and `meta.hasNextPage` to continue. **To count rows use `meta.total` when present; when it is absent, page to the end and sum `rowCount`** — see "Filter, sort and paging rules". Exceptions: `automationRule`, `aiGroup_schedule` and the five suggestion entities (`amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid`) ignore pagination entirely. An out-of-range `pageSize`/`page` is an **error**, not clamped
- `profileIds` is **required**. Always call `get_user_authorized_context` first. If the user doesn't name a store, pass all authorized `profileIds`
- **Every requested `profileId` must be authorized** — one bad value fails the whole call. `aiGroup_schedule` additionally requires exactly one
- `aiGroup` results are a **projection of the currently effective config** (trimmed by ad type, then reduced to what's actually in effect) — an absent field means "not in effect", not "unset" and not "write failed". See the dedicated section above
- Rule-mode (RBA) rule configuration **is readable** under `aiGroup`'s `aiAutomation.{ruleType}`; it is **not writable** through any MCP tool
- No `dateStart`/`dateEnd` or `metrics` needed — and no historical/point-in-time snapshot capability either (no date params of any kind on this tool)
- `groupBy` is not applicable here — this tool returns entity rows, not aggregates
- User says "ASIN" -> default to child ASIN, use entity `asin`, field `asin`
- `profile` **can** be queried standalone as its own entity
- `automationRule` **requires** `amazonCampaignId` in filters, and does not support sort/pagination
- `automationRule` is an enabled-type lookup, not a template/configuration query. There is no current metadata entity for listing the account's standalone automation templates or reading their full configuration
- Product inventory rules are associated at SKU/product level and are not exposed by the campaign-scoped `automationRule` entity or managed-group `aiAutomation`; do not report them as absent based on either query
- `campaignStartDate`/`campaignEndDate` are **strings with no guaranteed format** — a live sample held both `"20260101"` and `"2026-01-01"`, `""` occurs, and **both shapes can appear in one result set**. So **do not filter a date range on them across campaigns** (a filter matches one shape and silently drops the other) — narrow with other filters, page to the end, parse client-side. Before reusing either value as `dateStart`/`dateEnd` on the other two tools, parse it and emit `YYYY-MM-DD` - one of the two shapes already is that, the compact one needs converting, and you cannot tell which you have without looking
- For campaign rows, `campaignId` is the internal integer ID used by managed-group write tools; `amazonCampaignId` is the Amazon ID used to link performance/log data. Never substitute one for the other
- `asin` was the first entity to carry a per-row `currency`; multi-profile reads now follow that same pattern across entities — always prefer a row's own `currency` over any envelope-level value
- When querying across multiple `profileIds`, verify whether the entity's rows carry a `profileId` field (e.g. `asin` does); if not, query per-profile or cross-reference before merging
- `targetAcos` (aiGroup entity) is confirmed ×100/percentage, same as performance `ACOS` — don't re-scale, but append `%` when presenting it
- Only use field names listed in this doc's per-entity tables; never invent field names
- Field naming here (camelCase, no prefix/suffix) is **different** from `get_ads_perf` (`entity.field_`) — do not mix the two conventions
- **Do not pass null as a filter value** — it returns `invalid_params`. This tool has no `isNull`/`isNotNull` operator; to drop a constraint, simply omit the field.
- On error, check `errorType` and handle per the guidance above

## Reference Docs

- Shared cross-tool behavior (auth, errors, pagination, currency, ratio-metric display rule, decision tree, inference rules): [`references/platform-notes.md`](references/platform-notes.md)
- Field dictionary (entity enum values, per-entity field tables, filterable fields, enums): [`references/field-reference.md`](references/field-reference.md)
- Per-entity deep dives — the entry point above keeps only the guards that fail silently; the full contract for each is here:
  - [`entity: aiGroup` effective config](references/ai-group-effective-config.md)
  - [`entity: campaign` audience configuration](references/campaign-audience.md)
  - [`entity: campaign` budget usage](references/budget-usage.md)
  - [Suggestion entities](references/suggestion-entities.md)
  - [SB / SD creation entities (`brandEntity` / `store` / `pageAsins` / `asset` / `sdAudience`)](references/sb-sd-creation-entities.md)
- Enum i18n (ZH/EN/JA display labels for all enum values — use this when presenting enum fields to the user or translating between API values and localized display text): [`references/enum-i18n.md`](references/enum-i18n.md)
- Automation-rule reading guide (query-surface boundary, mode detection, rule semantics, conditions/actions/schedules): [`references/automation-rule-reading.md`](references/automation-rule-reading.md)
- Managed-group customer display (localized UI labels, product sections, rule names, output shape): [`references/managed-group-display.md`](references/managed-group-display.md)
- Query examples:
  - [Basic entity list query](references/example-meta-only.md)
  - [Filtered campaign list](references/example-campaign-filter.md)
  - [AI group metadata query](references/example-ai-group-metadata.md)
  - [AI group schedule query (`aiGroup_schedule`)](references/example-ai-group-schedule.md)
  - [ASIN metadata (with parent ASIN + product line)](references/example-asin-metadata.md)
  - [Enabled automation-rule type lookup](references/example-automation-rule.md)
