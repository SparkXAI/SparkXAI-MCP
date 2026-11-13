# Bulk / batch operations

Batch edits are **operation-based**: one `operation` per request, applied to a list of
group ids. **The two tools wrap the request differently - don't share one shape.**

`operation` values are **UPPER_SNAKE_CASE** (`STATUS`, `BUDGET`, `TARGET_TYPE`, `ACOS`,
`ROAS`, `TARGET_HARVEST`, `DYNAMIC_BUDGET`, `CAMPAIGN_NAME_SIGN`, `AI_PERSONALITY`,
`BID_OPTIMIZATION`, `STRUCT_OPTIMIZATION`, `BUDGET_DAYPART`, `BUDGET_DYNAMIC_ACTION`,
`BUDGET_REDISTRIBUTE`, `TARGET_HARVEST_ACTION`, `NEGATIVE_TARGET`, `BRAND_TARGET`,
`TARGET_PAUSED_ADD`). Prod pre-env testing (2026-08-13) confirmed
`{"operation":"STATUS", ...}` succeeds. **Enum spelling has differed between builds, so
read the routed tool's schema enum and copy the exact value** rather than trusting this
list blindly.

**Prefer the batch form for a single SD flat change - don't default to a Legacy full
edit.** With `operation` omitted, `edit_sd_ai_managed_group` takes the Legacy full-edit
path, which in pre returned a **misleading `only supports SD groups` error** for a plain
SD status change; sending `{operation:"STATUS", status:1}` (or `2`) succeeded. So toggle
SD status via the batch operation shape, not Legacy.

## SD - `edit_sd_ai_managed_group` (flat, top-level)

No `request` wrapper, no `batchParams`. `operation` and its params sit **at the top
level** next to `profileId`/`ids`:

```json
{
  "profileId": 123456,
  "ids": [1001, 1002],
  "operation": "BUDGET",
  "budgetType": 1,
  "budget": 500
}
```

Every SD operation (including `budgetRedistribute` etc.) uses the flat SD fields at the
top level. Send only the fields that operation needs. (SD `ids` max **20**.)

## SP/SB - `save_sp_sb_ai_managed_group` (wrapped)

Everything inside `request`; **Flat** operation params go in `batchParams`,
**Action-space** operation params go in `aiActionSettings` / `aiAutomation`:

```json
{
  "request": {
    "profileId": 123456,
    "operation": "STATUS",
    "ids": [2001, 2002],
    "batchParams": { "status": 2 }
  }
}
```

- **Flat** ops -> `batchParams`: `STATUS`, `BUDGET`, `TARGET_TYPE`, `ACOS`, `ROAS`,
  `TARGET_HARVEST`, `DYNAMIC_BUDGET`, `CAMPAIGN_NAME_SIGN`, `AI_PERSONALITY`.
- **Action-space** ops -> `aiActionSettings` / `aiAutomation`: `BID_OPTIMIZATION`, `STRUCT_OPTIMIZATION`, `BUDGET_DAYPART`, `BUDGET_DYNAMIC_ACTION`, `BUDGET_REDISTRIBUTE`.
  - **Target-switch operations (SP/SB):** `TARGET_HARVEST_ACTION`
    (`aiActionSettings.targetHarvestStatus`, `0`/`1`/`2`) and `TARGET_PAUSED_ADD`
    (`aiActionSettings.targetPausedAddStatus`, `0`/`1`, **SP groups only**) are accepted, but only as a
    switch: a call that carries neither the switch nor an `aiAutomation` is rejected (with
    `aiAutomation` alone it goes through, but only rule modes change and no switch is written), and
    word-list details can't be set.
    `TARGET_PAUSED_ADD` with any SB id fails the whole batch.
  - **Do not use on SP/SB:** `NEGATIVE_TARGET` (Negative Target is AI-only and a batch can't check each
    group's rule 5 mode - edit those groups one by one with `negativeTargetStatus`) and `BRAND_TARGET`
    (needs word lists). Both are rejected before anything is written.
    (`TARGET_HARVEST_ACTION` / `targetHarvest` are also valid on the **SD** tool.)

> **Naming**: the server's canonical codes are camelCase (`budget`, `status`, `targetType`,
> `acos`, `roas`, `targetHarvest`, `dynamicBudget`, `campaignNameSign`, `aiPersonality`,
> `bidOptimization`, `structOptimization`, `budgetDaypart`, `budgetDynamicAction`,
> `budgetRedistribute`, `targetHarvestAction`, `negativeTarget`, `brandTarget`,
> `targetPausedAdd`). Deserialization ignores case and underscores, so the UPPER_SNAKE_CASE
> names above work too. An unrecognized value fails with `Unknown BatchOperationType: x`.

> **⚠️ Only some target-related batch operations are rejected on SP/SB.** `save_sp_sb_ai_managed_group`
> refuses `NEGATIVE_TARGET` and `BRAND_TARGET` before anything is written (see above). Tell the user
> to edit negative-target switches group by group, or change brand / competitor settings in the
> platform. `TARGET_HARVEST_ACTION` and `TARGET_PAUSED_ADD` are accepted as plain switches. The gateway
> does **not** check rule 4's mode for `TARGET_HARVEST_ACTION`, so read each group's `aiAutomation`
> first and tell the user if turning harvest on will resume a Rule-mode harvest. To only turn
> harvesting on/off, use `targetHarvest`.
> On SD, `NEGATIVE_TARGET`, `BRAND_TARGET` and `TARGET_PAUSED_ADD` are not supported by
> `edit_sd_ai_managed_group`; `TARGET_HARVEST_ACTION` is accepted there.
>
> **The runtime tool description of `save_sp_sb_ai_managed_group` is out of date here**: it says
> `negativeTarget` takes its switch from `aiActionSettings`, but the gateway rejects batch
> `NEGATIVE_TARGET`. Follow this file, not the tool description.

> **Never send `templateId` and `operation` together - which one wins depends on the tool.**
> SD: `templateId` wins and the batch operation is ignored. SP/SB: `operation` wins and the
> template is ignored.

## Flat operation parameter map

Use this map for SD at the top level and for SP/SB inside `batchParams`:

| `operation` | Send only these operation parameters |
|---|---|
| `BUDGET` | `budgetType` + `budget` when type is 1/2, or `budgetType` + `budgetRatio` when type is 3 (**SP/SB only** - `edit_sd_ai_managed_group` rejects type 3) |
| `STATUS` | `status` |
| `TARGET_TYPE` | `optimizeType`; include only its documented companions (`acosStatus`, or `budgetDynamicStatus` + `numType` + `num`) when required by the selected target |
| `ACOS` | `acosType=1` + `acos`; `acosType=2` + `acosStatus=1`; or `acosType=3` + `acosRatio` |
| `ROAS` | `roasType=1` + `roas`; `roasType=2` alone for recommended mode; or `roasType=3` + `roasRatio` |
| `TARGET_HARVEST` | `targetHarvestStatus` |
| `DYNAMIC_BUDGET` | `budgetDynamicStatus`; when enabling, also `numType` + `num` |
| `CAMPAIGN_NAME_SIGN` | `campaignNameSign`; when disabling, also `campaignNameRecoveryType` |
| `AI_PERSONALITY` | `aiPersonality` (`1`-`5`; at least `3` for volume mode). **Legacy accounts only** - rejected where personality is set per action space; that route is `actionSpaceIntensity`, see [`ai-personality.md`](ai-personality.md) |
| `actionSpaceIntensity` | `actionSpaces` (list of action-space names, or `["all"]`) + `intensity` (`1`-`5`, required). **Per-action-space accounts only.** `["all"]` with any SB id in `ids` fails the whole batch - see [`ai-personality.md`](ai-personality.md) |

The containers differ, but the mutual-exclusion rules do not: never send both
`budget` and `budgetRatio`, `acos` and `acosRatio`, or `roas` and `roasRatio`.

## Hard rules (both tools)

- **One operation per request.** Don't change two different things in one call.
- **Only that operation's params, in the right place.** Stray fields can make the
  downstream pick the wrong branch.
- **`ids` max is 20 - both tools.** More than 20 ids per call is rejected by the backend
  (prod-confirmed 2026-08-13), as is an empty `ids`. Over 20 -> split into batches of at
  most 20 ids and run them serially, reading back after each.
- **Validate `ids` against the profile.** The backend enforces profile authorization and
  **rejects cross-profile batches** (`profileId ... is not authorized for the current
  user`). Still read each group first and confirm all are under this profile and in the
  token's scope; keep every batch single-profile.
- **Which groups can share one batch:**
  - **SP + SB can be mixed** for operations both support.
  - **SP-only operations** (`structOptimization`) must **exclude SB**
    ids - split them out; don't run them against SB. (`TARGET_PAUSED_ADD` is SP-only too:
    any SB id fails the whole batch.)
  - **SD is always the other tool** (`edit_sd_ai_managed_group`) - never in the same call.
    A wrong-tool/wrong-type call is rejected (`campaignType must be sponsoredProducts or
    sponsoredBrands`), but split by `campaignType` from metadata first.
- Support still follows the ad type - see [`action-space-matrix.md`](action-space-matrix.md)
  (SB has no AI BidDaypart; `budgetRedistribute`/`bidAmazonBusiness` are `noRule`).
- **Word-list fields are unsupported:** do not use `BRAND_TARGET` or send branded,
  non-branded, competitor, negative-target blacklist, or target-harvest blacklist
  fields, even if the routed schema still exposes them.

## Result is three-state - and success ids aren't always given

A batch can partially succeed with **`isError:false`**:

| State | Envelope | Shape |
|---|---|---|
| all success | `isError:false` | `status:"success"`, `result:{success:N, fail:0}` |
| **partial** | **`isError:false`** | `status:"partial_failure"`, `result:{success, fail}`, `failedItems:[{aiGroupId, error}]` |
| all failed | `isError:true` | `error:"..."` |

Handling `partial_failure` - **the failed set isn't always enumerated**:

1. **If `failedItems` is populated:** failed ids come from it; succeeded ids = requested
   ids - failed ids. Report both (failed ids with their `error`), then verify the
   succeeded ids by reading them back.
2. **If `failedItems` is empty** (the Legacy path can return `partial_failure` with no
   items): you **cannot** infer which ids succeeded from the counts. **Re-query all
   requested ids** and compare each group's target field to what you sent - classify
   per id from the read-back, then report. Don't say "verify only the successes" here,
   because you don't yet know which succeeded.

Never describe a partial success as a full success.

**One known cause of silent per-item failure**: if `ids` contains a group whose `targetType`
is `4` (**budget utilization priority** - a live, gated variant of Drive growth, **not** a legacy
goal), an `AI_PERSONALITY` or budget-increase style operation comes back as **fail for that
item** - no error, just not applied. The reason is the mode itself: it locks the running AI
personality to `5` and forces budget increase off, so there is nothing for those operations to
change. Two consequences: read each group's `targetType` before batching personality/budget
operations and exclude the `targetType=4` ones up front, and when you see unexplained `fail`
entries, check for this before assuming a transient problem. Say *why* they were excluded -
"that group runs budget utilization priority" - never "that group uses an old objective".

## Multiple requested changes

One request may contain several user-visible changes, but one batch call may contain
only one `operation`. Execute the resulting calls serially for the same group set and
read back after each call. Do not run them concurrently or blindly retry a timeout.
