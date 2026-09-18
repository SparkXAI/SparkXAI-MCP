---
name: sparkx-query-entity-metadata
description: >-
  Query advertising entity metadata: name, status, configuration, settings (no time range or metrics).
  For finding entity lists, getting config details, discovering ad structure relationships.
  Keywords: campaign list, campaign name, status query, AI group settings, ASIN info,
  ad group config, portfolio list, keyword list, product line, entity search,
  which ads, enabled/paused status, budget settings, bidding strategy, automation rules,
  managed group schedule, flight, seasonal plan, rule mode config, RBA rule conditions
metadata:
  version: 1.4.1
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

**✅ To count matching rows, read `meta.total` - do not page.** `total` is the exact number of rows matching your filters, independent of `pageSize`. `data.rowCount` is only the current page's length and is never a total.

`total` is **omitted** when the downstream cannot supply one (notably `asin`, and `aiGroup` when its total is missing). In that case you can still count, in this order of preference: page to the end (`pageSize` max 500, continue while `meta.hasNextPage` is `true`) and sum `data.rowCount` — paging is exact, so the sum is the real count, but say it is "as read in this query" rather than quoting it like a server-side total; or narrow `filters` until everything fits one page and use that page's `rowCount`. For the entities that suppress pagination entirely, the single response *is* the full set, so its `rowCount` is the count. Entities that suppress pagination (`automationRule`, `aiGroup_schedule`, and the five suggestion entities `amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid`) return every requested row and carry no `total` / `page` / `hasNextPage` at all.

**Note**: This tool does NOT involve time range or performance metrics. For spend, clicks, ACOS etc, use `get_ads_perf`.

**Note**: This tool does NOT return historical point-in-time snapshots — it only returns the entity's *current* configuration. There is no `asOfDate`-style parameter, and this tool has no date parameters at all. If the user asks "what was the daily budget on 2026-03-26", that specific historical value cannot be retrieved with this tool; only the current value is available. Say so explicitly rather than guessing.

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
| profileIds | array[long] | **Yes** | — | Profile IDs from `get_user_authorized_context` -> `profiles[].profileId`. **All must be authorized**; `aiGroup_schedule` needs exactly one |
| entity | string | **Yes** | — | Entity type to query. Enum: `profile` / `campaign` / `adGroup` / `target` / `keyword` / `negativeKeyword` / `negativeTarget` / `productAd` / `portfolio` / `placement` / `aiGroup` / `aiGroup_schedule` / `asin` / `automationRule` / `amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid`. The last five have their own contract — see "Suggestion entities". Note: productLine info is nested inside `asin` entity results, not a separate `entity` value |
| userContext | string | **Yes** | — | User's original query + reason, max 100 chars |
| filters | object | No | {} | Filter conditions. Field names are **camelCase**, no `entity.` prefix, no `_` suffix (e.g. `campaignState`, not `campaign.campaignState_`) |
| orderBy | array[object] | No | [] | `[{"field": "fieldName", "direction": "DESC"}]` |
| select | array[string] | No | all fields | Return **only** these top-level fields (no nested paths), in the given order — **plus `currency`, which is always kept when the row has one**. Unknown fields are ignored (reported via `meta.hint`). Does not affect pagination. See "Trimming fields with `select`" below |
| page | int | No | 1 | Page number (1-based). **`page` ≤ 0 is an error**, not a fallback to 1. Ignored for `automationRule`, `aiGroup_schedule` and the five suggestion entities |
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

**See [`references/field-reference.md`](references/field-reference.md)** for the complete field dictionary: entity enum values and backing providers, and all per-entity field tables (profile, campaign, adGroup, target, productAd, portfolio, placement, aiGroup, aiGroup_schedule, asin, automationRule) with filterable fields, enums, and usage examples.

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

Two server-side transformations are applied to `aiActionSettings` / `aiAutomation` before you see them. Both remove fields. **A missing field means "not in effect right now" — it does not mean "not configured", and it never means "a write failed".**

**1. Trimmed by ad type.** The response only carries what's configurable for that `campaignType`:

| campaignType | What's absent |
|---|---|
| `sponsoredProducts` | nothing (full set); automation limited to the supported rule set |
| `sponsoredBrands` | `structOptimization`; and in `bidOptimization`: `bidAdPlaceStatus`, `bidAdPlaceRangeStatus`, `tosMin/tosMax`, `pdpMin/pdpMax`, `rosMin/rosMax`, `bidAmazonBusinessStatus`, `btbMin/btbMax`, `btbRangeStatus`; plus `targetPausedAddStatus` |
| `sponsoredDisplay` | `bidOptimization`, `structOptimization`, `brandOptimization`; in `budgetOptimization`: `budgetDaypartStatus`, `budgetDynamicStatus`, `numType`, `num`; the `negativeTarget*` family and `targetPausedAddStatus`; **all** automation rules |

If `campaignType` is missing or unrecognized, nothing is trimmed.

**2. Projected to what's actually effective.** On top of the trim:

- A switch that is **off** drops its dependent fields. `bidAdPlaceStatus=0` → no `tosMin/tosMax/pdpMin/pdpMax/rosMin/rosMax`. `btbRangeStatus=0` → no `btbMin/btbMax`. `bidRangeStatus=0` → no `bidRangeType`/`bidRange`. `brandedStatus=0` → no `brandedMatchType`/`brandedList`/`competitor*`; `competitorStatus=0` → no `competitorMatchType`/`competitorList`.
- A rule running in **AI mode** (`status=0`, or absent) is **omitted from `aiAutomation` entirely** — the system decides on its own, so there's no rule config to show.
- **Never interpret an empty `aiAutomation` by itself.** It can mean that all *enabled* rule-capable action spaces are AI-driven, that those action spaces are off, or a mixture of both. Read the paired `aiActionSettings` switches first; only an on switch with no retained Rule entry identifies AI mode for that action space.
- A rule running in **Rule mode** (`status=1`) keeps its config but drops AI-panel-only parameters (e.g. rule 181 drops `bidPerformanceStrictAcosStatus`; rule 17 drops `numType`/`num`).
- `targetPausedAddStatus=2` is reported as `1` in Rule mode (the AI-only sub-option is folded away).

**`aiAutomation.{ruleType}.status` is a mode discriminator, not an enable switch.** Never
translate `status=1` as "enabled" or `status=0` as "disabled". The paired
`aiActionSettings.*Status` switch determines whether the action space is on; when it is on,
`status=1` means Rule mode and an omitted Rule entry means AI mode.
**How to talk about this to a user:**

**Before presenting a managed-group configuration, read
[`references/managed-group-display.md`](references/managed-group-display.md).** It defines the
customer-facing language, UI grouping, setting labels, and rule names. Backend object names are
not product section names.
- Report what's present as the live configuration. For anything absent, say "not currently in effect" and, if relevant, name the switch that gates it — don't say "not set" and don't guess at a stored value.
- If the user asks "did my change save?", verify by reading the **switch** you set, then its dependents. Absent dependents under an off switch are expected, not evidence of failure.
- Don't diff two `aiGroup` reads field-by-field and call every disappearance a regression — flipping one switch off legitimately removes a whole family of fields from the response.
- If the user asks for the **full / complete managed-group configuration**, do not compress
  sibling controls into a phrase such as "bid adjustment + placement + range". Group the
  returned switches by the UI's Bid / Budget / Targeting / Structure sections and report each
  supported switch separately, including off switches. For every on, rule-capable switch, report
  AI vs Rule mode and then its dependent values. A field trimmed because the ad type does not
  support it is "unsupported / not exposed for this ad type", not "off".
- Map `targetType` through the managed-group display guide and preserve the UI's selected objective
  label in the user's language. For example, a Chinese answer for `targetType=2` says **保持订单稳定**.
  "控制成本" is only the surrounding category, and a returned English label such as "Optimize
  ROAS" must not replace the selected Chinese option.
- For managed groups and their schedules, display `aiPersonality` as the numeric level only, for
  example **AI 人格：4**. Do not replace or supplement it with `aiPersonalityText` labels such as
  "激进", "略激进", or "Aggressive".
- Treat bid-range values according to `bidRangeType`: numeric amount vs percentage. Never call a
  displayed currency range a coefficient, and never infer that placement adjustment is on merely
  because bid range is on.
- Do not show backend field names or rule numbers in a normal customer answer. Use localized UI
  names from the display guide. Raw keys/codes belong only in a separate technical appendix when
  explicitly requested.
- `brandOptimization` is not an action-space category. Present it separately as Brand/non-brand/
  competitor mode / 品牌/非品牌/竞品模式.

### Reading rule-mode (RBA) rule configuration

There are two different read surfaces; do not conflate them:

- `entity: "automationRule"` returns only the enabled `ruleType` codes and localized names for specified Amazon campaign IDs. It does **not** return template IDs/names, conditions, actions, frequency, applicable objects, or account-level template lists.
- `entity: "aiGroup"` (and, when present, `aiGroup_schedule`) returns the managed group's embedded action-space Rule configuration under `aiAutomation.{ruleType}`. This is not the account's standalone automation-template library.

When a managed group runs an action space in **Rule mode**, its effective configuration is readable under `aiAutomation.{ruleType}`: conditions, actions, condition items, time periods, and (for dayparting rules) the hour matrix. Rule types you may see: `2` bid dayparting, `4` target harvest, `5` negative target, `13` budget dayparting, `17` budget by performance, `19` placement adjustment, `20` pause campaign, `181` bid by performance, `182` target pause/supplement.

**Before explaining any rule configuration, read [`references/automation-rule-reading.md`](references/automation-rule-reading.md).** It defines the action-switch/mode decision, capability boundary, rule-specific business semantics, condition priority, and safe rendering procedure.

- Well-understood leaves carry a `...Text` companion for display (metric names, logical connectors, action types, placements, periods, hour labels). Leaves whose value domain isn't confirmed are passed through **raw, with no Text** — relay those verbatim and don't invent a label for them.
- The same raw value can mean different things in different rules (e.g. `amount` under rule 17 is a budget action, under rule 19 it's a placement bid action). Never carry a label across rule types.
- **This is read-only.** There is no MCP tool that writes RBA rule configuration — see `sparkx-edit-ai-group`. You can show a user their rule setup and explain it; you cannot offer to change it here. Also note the direction constraint: a rule-based group can be switched to AI, but not the reverse.

## `entity: campaign` - audience configuration arrives on its own

What the campaign list itself knows about an audience is just two fields - `audienceId` and
`audienceBidPercentage`. When `audienceId` is non-empty, the server looks that audience up and
merges its configuration into the same row: **you do not query it separately, and there is no
audience-detail entity**. The lookup is batched across profiles, so many stores cost one extra
call, not one per row.

**`audienceId` is always present.** An unbound campaign carries `""`, not a missing key - so
`audienceId != ""` is the test for "is an audience bound", and `audienceBidPercentage: 0` is
**not** (0 legitimately means "bound, no uplift").

Fields merged in: `audienceName`, `audienceType`, `proximityLevel`, `autoUpdate`,
`updateFrequence`, `audienceCount`.

**`audienceSegmentType` is NOT one of them, and is not on the campaign row at all.** Which of
the two audience pools a campaign is bound to - a custom AMC audience
(`SPONSORED_ADS_AMC` / 提高针对自定义 AMC 人群的竞价) or an Amazon-built one
(`BEHAVIOR_DYNAMIC` / 提高针对亚马逊人群的竞价) - **cannot be read from here**. A live check
against a bound campaign returned that field empty. It exists only as a filter on
`entity: amcAudience`, echoed back on that entity's own rows.

**And you cannot infer it from a name.** `get_ads_perf(factEntity='campaignAudience')`
resolves audience names for **both** pools - it reads them from the report table, not from AMC
- so seeing a name there says nothing about the type. A live campaign bound to the
Amazon-built audience "High interest based on shopping history" showed its name there
normally. The enrichment on *this* row is a different matter: it resolves only audiences
created and synced here, so its absence is ambiguous and its presence is not something to
build a write on either. When a write needs the type, see `edit-ads`, which has the procedure for establishing
it.

**Read them carefully - `meta.hint` says as much:**

- **The enums are raw, not display text** - the product has official labels for all of them,
  and those are what a user should see:

| Field | Raw value | English | 中文 | 日本語 |
|---|---|---|---|---|
| `audienceType` | `target` | Rule-based Audience | 基于规则的受众 | ルールベースのオーディエンス |
| | `lookalike` | Lookalike Audience | 相似受众 | 類似オーディエンス |
| `proximityLevel` | `MOST_SIMILAR` | Most Similar | 最相似 | 最も類似 |
| | `SIMILAR` | Similar | 相似 | 類似 |
| | `BALANCED` | Balanced | 平衡 | バランス |
| | `BROAD` | Broad | 广泛 | 広範 |
| | `MOST_BROAD` | Most Broad | 最广泛 | 最も広範 |
| `updateFrequence` | `daily` | Daily | 每日 | 毎日 |
| | `weekly` | Weekly | 每周 | 毎週 |
| | `biweekly` | Biweekly | 每两周 | 隔週 |

  The field itself is **Audience type / 受众类型**, **Proximity Level / 邻近度级别** and
  **Auto update frequency / 自动更新频率**; the group is **Audience Configuration /
  受众配置**. Note `proximityLevel` is upper snake case while `updateFrequence` is lower case -
  match on the raw value, don't normalize case and hope.

- **`proximityLevel` only means anything when `audienceType` is `lookalike`.** Rule-based
  audiences return an empty string for it, which is then dropped from the row entirely.
- **Auto-update is `autoUpdate` (`0`/`1`), not the presence of `updateFrequence`.** A disabled
  audience can still carry a stale frequency value, so reading the frequency as "it updates"
  is wrong.
- **The targeting rule itself (`expression`) is not included here.**
- `audienceCount` is the audience size - the number worth checking before paying an uplift.

**A row with an audience but no configuration is "unknown", not "broken".** Only AMC audiences
created and synced on this platform carry configuration: Amazon behavioural audiences,
audiences created outside the platform, and audiences whose sync has not finished have none,
and a lookup call can also simply fail. All of those produce a `meta.hint` counting the
affected rows. **Do not report those campaigns as having no audience, or as having an invalid
one** - the binding is real; only its description is missing.

**SD campaigns never get this.** Sponsored Display supports neither audience pool,
so its `audienceId` is always blank and no lookup is attempted.

### "Which campaigns have no audience bound?"

Both conditions filter **server-side**. One query answers it:

```json
{
  "entity": "campaign",
  "profileIds": [4404871489220462],
  "userContext": "Find SP/SB campaigns without an audience bound",
  "filters": {
    "audienceId": "",
    "campaignType": {"in": ["sponsoredProducts", "sponsoredBrands"]}
  }
}
```

- **`{"audienceId": ""}` is a real condition**, not an empty one - the empty string is what an
  unbound campaign actually stores, and the downstream matches on it.
- **The `campaignType` half is not optional.** Sponsored Display has no audience
  targeting of either kind, so every SD campaign carries `audienceId: ""` forever. Filtering on the audience
  alone reports the entire SD estate as "missing an audience".
- **`meta.total` is the answer to "how many"** here, because both conditions were applied
  server-side - it is the count of unbound SP/SB campaigns. You only need to page if the user
  wants the *list*: raise `pageSize` (max 500) and continue while `meta.hasNextPage` is
  `true`.

To go the other way - which campaigns use a *particular* audience - filter
`{"audienceId": "<id>"}` with the same `campaignType` pairing.

The reverse question - *which* campaigns do have one, with performance attached - is
`get_ads_perf(factEntity='campaignAudience')`. **Do not derive the unbound set from it by
subtraction.** Whether a campaign appears there is decided by an inner join onto the audience
report table, and `campaign.audienceId` plays no part in it - so a campaign that is genuinely
bound can be missing entirely (observed: 273 bound campaigns on one profile, `total: 0`).
Subtracting would report all of them as unbound. `audienceId != ""` on this entity is the
only answer to "is an audience bound".

## Suggestion entities - a different contract from everything above

Five entities exist to feed **campaign creation** rather than reporting: `amcAudience`,
`keywordGroup`, `suggestedKeyword`, `suggestedTarget`, `suggestedBid`. They come from their
own providers and share a contract that breaks most of the habits the other entities teach:

- **Exactly one `profileId`.** Not "one or more" - a list of two is rejected. Recommendations
  are scoped to a single store.
- **`filters` is mandatory**, and what it must contain differs per entity (below). These are
  not optional narrowing filters; the query cannot run without them, and **none of them has a
  list-all form**.
- **No pagination at all.** `page` / `pageSize` / `hasNextPage` / `total` are absent from
  `meta`: the downstream pages internally and the tool returns every row it got. Do not try
  to page, and do not treat a large result as truncated.
- **No sorting, and no comparison operators.** There is no `>=` / `like` vocabulary here.
  A **list-valued** filter - `asin`, and `keyword` on `suggestedBid` - accepts three
  interchangeable shapes: a bare string, an array, or `{"in": [...]}`. **Single-valued
  filters do not**: `matchType`, `targetingType`, `campaignType` and `audienceSegmentType`
  must resolve to exactly one value. `campaignType` and `audienceSegmentType` will accept a
  one-element array or `{"in": [...]}` and reject anything longer (`accepts a single value
  only, got N`), so just send a plain string and avoid the question.
- **They are recommendations, not account state.** Nothing here describes what you already
  run - `suggestedKeyword` does not tell you which keywords exist on a campaign. Use the
  ordinary `keyword` / `target` entities for that.

### `amcAudience` - targetable audiences you may bind to a campaign

Required `filters.campaignType`: `sponsoredProducts` or `sponsoredBrands` (**SD is not
valid here**). Optional `filters.audienceSegmentType`: `SPONSORED_ADS_AMC` (the default) or
`BEHAVIOR_DYNAMIC`; either filter accepts a single value only.

Also optional: **`filters.keyword`** narrows by audience **name** - use it when the user names
an audience instead of making them pick from a long list.

Returns `audienceId`, `audienceName`, and `audienceSegmentType` echoed back on every row.

⚠️ **Send that echoed `audienceSegmentType` back on every write that uses this
`audienceId`** - when you create a campaign, and when you change the audience bid on an
existing one. The two segment types are separate pools. An `audienceId` taken from one pool
and submitted with the other is accepted, stored locally, and **never applies on Amazon** -
nothing rejects it, so carry the pair together from this row to the write.

This entity is the only place the type is available. It is not on the campaign row, so for a
campaign that is already bound you have to find which pool its `audienceId` sits in by
querying this entity once per value, or ask the user.

### `keywordGroup` - keyword-group suggestions for an ad group

Required `filters.asin` (one or more) - the suggestions are derived from the advertised
products, so there is nothing to compute without them.

Returns `keywordText`, `keywordGroupText`, `suggestedBid`, and where the downstream supplies
a range, `suggestedBidRangeStart` / `suggestedBidRangeEnd`.

⚠️ **`suggestedBid: 0` means no suggestion was obtained**, not "bid zero". The downstream
swallows the error and the value is passed through raw. Never carry a `0` into a create
request - fall back to the ad group's default bid, or ask.

### `suggestedKeyword` - keyword suggestions

Required `filters.asin`. Returns `keywordText`, `matchType`, `suggestedBid`,
`suggestedBidRangeStart` / `suggestedBidRangeEnd`, `keywordTranslation` and
`recommendationRank`. Rank is the downstream's ordering - respect it rather than re-sorting
by bid.

### `suggestedTarget` - product **and** category suggestions

Required `filters.asin`. **Two kinds of row come back in one list**, told apart by
`targetType`:

| `targetType` | Fields |
|---|---|
| `product` | `asin` |
| `category` | `categoryId`, `categoryName`, `categoryParentId`, `categoryPath`, `canBeTargeted` |

`rowCount` is the two kinds summed. **Keep both by default** - the product rows are
recommended ASINs to target, and silently dropping them answers a narrower question than the
user asked. Filter to one kind only when they asked for one kind ("给我推荐的品类"), and say
which kind you kept.

⚠️ **`canBeTargeted: false` rows come back too.** They are context for the category tree, not
usable targets - filter them out before offering anything to the user or putting it in a
create request.

### `suggestedBid` - a bid for a keyword, or for auto targeting

Required `filters.asin`, plus **one of two mutually exclusive modes**:

- **Keyword bids**: `filters.keyword` **and** `filters.matchType`. Supplying `keyword`
  without `matchType` is rejected.
- **Auto-targeting bids**: `filters.targetingType: "auto"`. Optional
  **`filters.biddingStrategy`** is passed through to the suggestion request - send the
  strategy the campaign will actually use, since the suggested bid depends on it.

Neither mode given is an error naming both. Returns `suggestedBid` plus
`suggestedBidRangeStart` / `suggestedBidRangeEnd`, with `keywordText` + `matchType` in
keyword mode and `targetGroup` in auto mode.

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

**4. The operator set is exactly** `in`, `notin`, `like`, `!=`, `ne`, `>=`, `<=`. Anything else
is rejected, including **`eq`** - equality is expressed by assigning the value directly
(`{"campaignState": "enabled"}`), not by `{"eq": ...}`. An empty operator object and a `null`
operator value are both rejected too.

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
`productPage` / `restOfSearch`. Rows with no adjustment value are still skipped.)

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
    "hint": "Amounts remain in each profile's local currency. Use each row's currency and do not compare or sum across currencies without explicit conversion."
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
| `>=`, `<=` | Range | between | `{"dailyBudget": {">=": 10, "<=": 100}}` — may be combined; this is the **only** legal two-operator combination |
| `>`, `<` | **Rejected** | — | Strict comparison is not supported; use `>=` / `<=` and drop boundary rows yourself. See "Filter, sort and paging rules" |

**Note on `like`**: any `%` you include is stripped and replaced with an automatic leading+trailing `%` — the match is always "contains" regardless of where you place `%`.

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
| `requestId` | string | **Top level.** Trace ID — quote it when reporting a failure to the user. May be absent locally |
| `data.rows` | array[object] | Result rows — fields depend on `entity` |
| `data.rowCount` | int | Row count **on the current page**, never a total |
| `meta.page` / `meta.pageSize` | int | Pagination state, echoing your request (they echo it even on a zero-row response). **Absent** for `aiGroup_schedule`, `automationRule` and the five suggestion entities (`amcAudience` / `keywordGroup` / `suggestedKeyword` / `suggestedTarget` / `suggestedBid`), which are non-paginated |
| `meta.total` | int | **Exact** number of matching rows - use this to count, never page for it. **Omitted** when the downstream supplies none (`asin`; `aiGroup` when unknown) and on non-paginated entities |
| `meta.hasNextPage` | boolean | Whether more pages exist. **Absent** for the non-paginated entities |
| `meta.effectiveProfileIds` | array[long] | Profile IDs the query ran against — an echo of your request (unauthorized IDs fail the call outright), minus duplicates |
| `meta.currency` | string | **Single**-profile query only — that store's resolved currency code. **Omitted on a multi-profile query** (and whenever a row's currency is unresolved); use each row's own `currency`. See "Money is per store" |
| `meta.hint` | string | Read it. May contain **several sentences joined together** - e.g. the multi-profile currency notice, `Page order is not stable.` for `placement`, an unresolved-currency warning, and `Unknown select fields ignored: [...]` |

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
