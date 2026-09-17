# Field reference - managed-group create (exact write field names + enums)

All coded fields are **closed enums**; an unlisted value fails the call with a generic
error and no field-level hint, so validate here before sending. Field **names** also
matter: the tools set `additionalProperties: false`, so a wrong or extra field name is
rejected outright.

> **Read names != write names.** The names `get_entity_metadata` *returns* are not
> always the names the write tools *accept*. E.g. the read side shows
> `budgetDaypartStatus`, but SP/SB writes require **`budgetDaypartActionStatus`**.
> The "Action" suffix is present on some action-space switches and absent on others,
> and SD-create fields differ from SP/SB fields. **When building a write call, use the
> exact names in this file (which mirror the tool inputSchemas), never the read-side
> field names.**

## Shared enums

| Field | Values |
|---|---|
| `aiPersonality` | `1`=非常保守, `2`=保守, `3`=平衡, `4`=激进, `5`=非常激进. **>=3 required when `targetType=3` (volume/冲量)** - front-end rule, not backend-enforced |
| `campaignNameSign` | `0`=off, `1`=on |
| `budgetNumType` / `bidRangeType` | `1`=percentage, `2`=fixed value |
| `*MatchType` (branded/competitor/harvest/negative) | `1`=exact(等于/精确), `2`=phrase(包含/词组) |
| `*ListType` (harvest/negative) | `1`=include/whitelist, `2`=exclude/blacklist |

## SD - `create_sd_ai_managed_group` fields

Flat fields (no nested objects):

| Field | Values / type |
|---|---|
| `status` | **create: `0`=off, `1`=on only** (`2`=cancelled is a lifecycle state, **not** a valid create input) |
| `optimizeType` | `1`=drive growth, `2`=maintain stability |
| `acos` | number, ACOS on the x100 scale (see create-sd.md) |
| `budget` / `budgetChange` | number / boolean (budget applies only when `budgetChange=true`) |
| `budgetDynamicStatus` | **Unsupported for SD creation** - omit or send `0`; non-zero is rejected |
| `numType` / `num` | **Do not send for SD creation**; companions of the unsupported dynamic-budget switch |
| `targetHarvestStatus` | `0`=off, `1`=on, `2`=on with exact negation in source ad group |
| `budgetRedistributeStatus` | `0`/`1` |
| `campaignNameSign` | `0`/`1` |
| `aiPersonality` | `1`-`5` |

## SP/SB - `save_sp_sb_ai_managed_group` `request` fields

Top-level: `aiStatus` (`0`=off, `1`=on - create input is `0`/`1`; a group reads back
as `2`=paused once off), `targetType` (`1`=drive growth, `2`=maintain stability,
`3`=volume, `4`=legacy growth), `campaignType` (`sponsoredProducts`/`sponsoredBrands`),
`acos`, `campaignIds`, `campaignNameSign`, `aiPersonality`, `preAddCampaignNums`.

### `aiActionSettings` (nested) - EXACT names

Each action-space `xxxStatus` is an on/off switch: `0` = off, `1` = on. It does not
identify AI versus Rule/RBA; use the corresponding `aiAutomation` mode field for that.

Bid: `bidDaypartStatus`, `bidPerformanceStatus`, `bidPerformanceStrictAcosStatus`,
`bidAmazonBusinessStatus`, `bidAdPlaceStatus`, `bidAdPlaceRangeStatus`,
`bidRangeStatus`, `bidRangeType`, `bidRange` (`[min,max]`, null=no limit),
`btbRangeStatus`, `btbMin`, `btbMax`, `tosMin`/`tosMax`, `pdpMin`/`pdpMax`,
`rosMin`/`rosMax`.

Struct (**SP only**): `structPauseProductStatus`, `structPauseCampaignStatus`.

Budget: **`budgetDaypartActionStatus`**, **`budgetDynamicActionStatus`**,
**`budgetRedistributeActionStatus`**, `budgetNum`, `budgetNumType`.

Target (**NOT writable via MCP - read-only / platform UI only**):
`targetHarvestActionStatus`, `targetHarvestBlackListStatus`,
`targetHarvestBlackList` (IDs), `targetHarvestListType`, `targetHarvestMatchType`,
`negativeTargetActionStatus`, `negativeTargetBlackListStatus`,
`negativeTargetBlackList` (IDs), `negativeTargetListType`, `negativeTargetMatchType`,
`targetPausedAddStatus` (`0`=off, `1`=on, `2`=on with supplement). The SP/SB tool
**hard-rejects** this entire `targetOptimization` module (target harvest / negative
target / target pause); create defaults it closed. These names may still appear in some
schemas, but they are read-only - inspect them via `get_entity_metadata`, change them in
the platform UI, and never send them as write inputs.

The whole `targetOptimization` module (all fields listed above) and the
`brandOptimization` module - including `brandedStatus`, `brandedList`, `competitorStatus`,
`competitorList`, and any `*BlackList*` status/list field - are **currently unsupported**
(removed from the write path; read-only, platform UI only). Do not send any of these
status, list ID, match-type, or list-type fields; the tool hard-rejects them.

### `aiAutomation` (flattened mode fields) - EXACT names

`aiActionSettings.xxxStatus` controls whether an action space is enabled. When it is
enabled, the corresponding `aiAutomation` field selects the mode.

**⚠️ The mode value reads backwards from intuition: `0` = AI mode (the system decides on its
own), `1` = Rule mode (RBA).** `1` is **not** "enabled" - and Rule mode cannot be configured
through these tools, because a rule needs conditions and actions that this schema doesn't
carry. So: send `0`, or omit the field. Never send `1`.

If the user wants a rule-driven setup, say it has to be built in the platform UI. (You *can*
read an existing rule's full configuration - see `sparkx-query-entity-metadata`. A
rule-based group can be switched to AI, but not the reverse.)

`aiAutomation` is a **flat object** (not nested per rule) on the write side. Each field maps
to one automation rule number:

| `aiAutomation` field | Rule | Paired `aiActionSettings` switch |
|---|---|---|
| `bidDaypartStatus` | 2 - bid dayparting | `bidDaypartStatus` |
| `targetHarvestRuleStatus` | 4 - target harvest (**read-only context; not settable at create**) | `targetHarvestActionStatus` |
| `negativeTargetRuleStatus` | 5 - negative target (**read-only context; not settable at create**) | `negativeTargetActionStatus` |
| `budgetDaypartRuleStatus` | 13 - budget dayparting | `budgetDaypartActionStatus` |
| `budgetPerformanceRuleStatus` | 17 - budget by performance | `budgetDynamicActionStatus` |
| `placementAdjustmentRuleStatus` | 19 - placement adjustment | `bidAdPlaceStatus` |
| `pauseCampaignRuleStatus` | 20 - pause campaign | `structPauseCampaignStatus` |
| `bidPerformanceRuleStatus` | 181 - bid by performance | `bidPerformanceStatus` |
| `targetPauseSupplementRuleStatus` | 182 - target pause / supplement (**read-only context; not settable at create**) | `targetPausedAddStatus` |

One extra field, only meaningful with rule 13:

| Field | Type | Notes |
|---|---|---|
| `budgetDaypartExcuteDays` | string | Comma-separated days for budget dayparting. **`1`-`6` = Mon-Sat, `0` = Sunday.** Default `"1,2,3,4,5,6,0"` (every day). Note the spelling - `Excute`, not `Execute` |

`budgetRedistributeActionStatus` and `bidAmazonBusinessStatus` have no Rule mode; only
their `aiActionSettings` on/off switch applies.

**On read**, `aiAutomation` comes back keyed by rule number (`"2"`, `"4"`, `"181"`, …) rather
than by these field names, and rules running in AI mode are omitted entirely. An empty
`aiAutomation` is ambiguous by itself: read the paired `aiActionSettings` switches to distinguish
off action spaces from enabled action spaces in AI mode. Details are in
`sparkx-query-entity-metadata`.

> Coupling rules (open a switch -> must also send its companion fields) are in
> [`coupling-rules.md`](coupling-rules.md).

## Known value-range caveat

- **Avoid `budgetType=3`** where it appears in edit/action paths - a known P0 that can
  hang the downstream service. Not needed for a basic create.
