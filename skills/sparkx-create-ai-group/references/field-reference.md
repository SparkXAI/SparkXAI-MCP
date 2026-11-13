# Field reference - managed-group create (exact write field names + enums)

All coded fields are **closed enums**; an unlisted value fails the call with a generic
error and no field-level hint, so validate here before sending. Field **names** also
matter: the tools set `additionalProperties: false`, so a wrong or extra field name is
rejected outright.

> **⚠️ No action-space switch has an `Action` suffix.** Earlier versions of this file
> claimed SP/SB writes needed `budgetDaypartActionStatus`, `budgetDynamicActionStatus`,
> `budgetRedistributeActionStatus`, `targetHarvestActionStatus` or `negativeTargetActionStatus`.
> **Those names do not exist** — not in the tool inputSchema, not in the payload sent
> downstream, not on the read side. The real names are `budgetDaypartStatus`,
> `budgetDynamicStatus`, `budgetRedistributeStatus`, `targetHarvestStatus`,
> `negativeTargetStatus` — the same names the read side returns.
>
> **Why this mattered:** a wrong field name is **rejected**, not dropped: schema validation
> fails the call before the tool runs (`isError: true`, `Tool (...) input validation failed: ...`).
> A call built on the old names never answers `success` with the switch unchanged — if such
> calls fail, fix the names. If you have call templates saved from an earlier version of this
> file, check them.
>
> What **does** differ is **SD-create fields vs SP/SB fields** — those are genuinely
> different field sets. When building a write call, use the exact names in this file and
> check the ad type's column.

## Shared enums

| Field | Values |
|---|---|
| `aiPersonality` | `1`=保守, `2`=较保守, `3`=中庸, `4`=较激进, `5`=激进（这是读接口与页面实际显示的文案，`2` 的 `aiPersonalityText` 是「较保守 / Moderately Conservative」而非「保守」；部分写侧工具描述仍写成「very conservative ... very aggressive」，那是错的）. **>=3 required when `targetType=3` (volume/冲量)** - front-end rule, not backend-enforced. ⚠️ **Group-level only, and rejected outright on accounts that set personality per action space** - check [`ai-personality.md`](ai-personality.md) before sending it |
| `campaignNameSign` | `0`=off, `1`=on |
| `budgetNumType` | `1`=percentage, `2`=fixed value |
| `bidRangeType` | `2`=fixed value (each end `> 0`). `1`=**bid coefficient** (`1.15` = 1.15× the base bid), **not a percentage** — never convert `+15%` into `15`. Each end must be `0.01`-`100` (rejected otherwise). Same range also governs bid dayparting; see [`coupling-rules.md`](coupling-rules.md) |
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
`3`=volume, `4`=drive growth with **budget utilization priority** - an aggressive variant
of `1`, gated and SP-only, and it locks the runtime AI personality to `5` while this field
still reads back the stored value; see [`enum-i18n.md`](enum-i18n.md)),
`campaignType` (`sponsoredProducts`/`sponsoredBrands`),
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

Budget: **`budgetDaypartStatus`**, **`budgetDynamicStatus`**,
**`budgetRedistributeStatus`**, `budgetNum`, `budgetNumType`.

Target (**only the three action switches are writable via MCP; word-list settings are
platform-only**):

- Writable in `aiActionSettings`: `targetHarvestStatus` (`0`=off, `1`=on, `2`=on and also add
  harvested terms as exact negatives), `negativeTargetStatus` (`0`/`1`), `targetPausedAddStatus`
  (`0`/`1`; **SP only**, non-zero on SB is rejected; the read-side value `2` is never sent).
  Out-of-range values are rejected. An omitted switch is `0` on a normal create and follows the
  template in template mode; your value wins over the template. **Template create caveat:** the
  zero-fill applies to a normal create only. On a template create, a switch you omit that the
  template doesn't set is left to the downstream default, which is **on** - send an explicit `0`
  for any switch the user wants off. ⚠️ **`targetPausedAddStatus` is the exception: it is SP-only.** On an SB group the server forces it to `0` on every create and edit path, so it never lands on - do not tell an SB customer that all three switches came on. Target Harvest (rule 4) and
  Negative Target (rule 5) are AI-mode only - see [`coupling-rules.md`](coupling-rules.md).
- Not writable: `targetHarvestBlackListStatus`, `targetHarvestBlackList` (IDs),
  `targetHarvestListType`, `targetHarvestMatchType`, `negativeTargetBlackListStatus`,
  `negativeTargetBlackList` (IDs), `negativeTargetListType`, `negativeTargetMatchType`. These names
  may still appear in some schemas and read back from `get_entity_metadata`; create defaults them
  closed. Change them in the platform UI and never send them as write inputs.

The whole `brandOptimization` module - including `brandedStatus`, `brandedList`,
`competitorStatus`, `competitorList` - and the word-list fields above are **currently
unsupported** (read-only, platform UI only). Do not send any of these status, list ID,
match-type, or list-type fields; the tool hard-rejects them.

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
| `targetHarvestRuleStatus` | 4 - target harvest (AI-only: send `0` or omit) | `targetHarvestStatus` |
| `negativeTargetRuleStatus` | 5 - negative target (AI-only: send `0` or omit) | `negativeTargetStatus` |
| `budgetDaypartRuleStatus` | 13 - budget dayparting | `budgetDaypartStatus` |
| `budgetPerformanceRuleStatus` | 17 - budget by performance | `budgetDynamicStatus` |
| `placementAdjustmentRuleStatus` | 19 - placement adjustment | `bidAdPlaceStatus` |
| `pauseCampaignRuleStatus` | 20 - pause campaign | `structPauseCampaignStatus` |
| `bidPerformanceRuleStatus` | 181 - bid by performance | `bidPerformanceStatus` |
| `targetPauseSupplementRuleStatus` | 182 - target pause / supplement (send `0` or omit) | `targetPausedAddStatus` |

One extra field, only meaningful with rule 13:

| Field | Type | Notes |
|---|---|---|
| `budgetDaypartExcuteDays` | string | Comma-separated days for budget dayparting. **`1`-`6` = Mon-Sat, `0` = Sunday.** Default `"1,2,3,4,5,6,0"` (every day). Note the spelling - `Excute`, not `Execute`. ⚠ Currently not saved by the SP/SB save — passing it has no effect |

`budgetRedistributeStatus` and `bidAmazonBusinessStatus` have no Rule mode; only
their `aiActionSettings` on/off switch applies.

**On read**, `aiAutomation` comes back keyed by rule number (`"2"`, `"4"`, `"181"`, …) rather
than by these field names, and rules running in AI mode are omitted entirely. An empty
`aiAutomation` is ambiguous by itself: read the paired `aiActionSettings` switches to distinguish
off action spaces from enabled action spaces in AI mode. Details are in
`sparkx-query-entity-metadata`.

> Coupling rules (open a switch -> must also send its companion fields) are in
> [`coupling-rules.md`](coupling-rules.md).

## Known value-range caveat

- **Avoid `budgetType=3`.** `edit_sd_ai_managed_group` rejects it (only `1` and `2` are valid). The
  SP/SB batch accepts it, but it is a known-risky value that can hang the downstream service. Not
  needed for a basic create.
