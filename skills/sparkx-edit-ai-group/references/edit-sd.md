# Edit SD managed groups - `edit_sd_ai_managed_group`

Updates one or more **SD** groups. Required: `profileId` and `ids` (array of
aiGroupIds, **max 20**).

## Two modes

`edit_sd_ai_managed_group` behaves differently depending on which of `operation` / `smartCreationName` is sent:

- **Legacy full edit (`operation` omitted).** Every non-null field you send is applied
  to all groups in `ids`. Use this only for changing several settings at once. **For a
  single change (e.g. AI on/off) prefer the batch form below** - in pre, a Legacy
  full-edit for a plain SD status change returned a misleading `only supports SD groups`
  error, while the batch `{operation:"STATUS", status:1}` succeeded.
- **Batch operation (`operation` provided).** One operation per request - SD is
  **flat/top-level**: put `operation` and its params directly alongside `profileId`/`ids`
  (no `request` wrapper, no `batchParams`), e.g. `{profileId, ids, operation:"BUDGET",
  budgetType:1, budget:500}`. Operation values are **UPPER_SNAKE_CASE** (prod-confirmed
  2026-08-13); verify the exact enum in the tool schema. See
  [`batch.md`](batch.md) - **the "SD" section** - for the shape, id<->profile validation,
  and three-state (`success` / `partial_failure` / `failed`) result handling. (SP/SB uses
  a different, `request`-wrapped shape.)

- **Rename (`smartCreationName` provided).** A third, exclusive mode — see below.

The rest of this file documents the fields (used by the first two modes).

## Rename - `smartCreationName`, and nothing else

Renaming an SD group is its own mode and **will not combine with anything**: `ids` must hold
**exactly one** id, and no other update field, no `operation`, no `templateId` may be sent.
Change other settings in a separate call.

The name is trimmed, then must be **1-255 code points**, with **no control characters and no
invisible formatting characters** (a zero-width space is rejected, not stripped - so a name
pasted from a doc can fail for something you cannot see). It must be unique within the shop.

**It works whether the group's AI is on or off**, and it is not a settings change in disguise:
campaign budgets and the enabled/paused campaigns stay as they are. Archived campaigns still
linked to the group are detached by the downstream as a side effect - mention that if the user
is counting members.

**Five up-front rejections, none of which change anything:**

| Rejected when | Why it matters |
|---|---|
| the new name equals the current one | A no-op is an error here, not a silent success |
| another group in the profile already uses the name | Unique per shop |
| the group has **no enabled or paused campaigns** | An empty or all-archived group cannot be renamed at all |
| the group is not in that profile, or is not SD | Wrong tool - SP/SB rename is not this parameter |
| the current campaign budgets cannot be verified | Fail Closed: the rename re-sends the budget total, so an unverifiable budget blocks it |

**Reading failures:**

- A budget-shaped error from ai-center (`预算过低` / `预算至少…` / a `{min},{max}` range) means
  **nothing was changed** - safe to retry.
- Code **`124035`** is the one you must not retry blindly: **the rename may already have taken
  effect.** Read the group back before doing anything else.
- A duplicate name reuses the existing rename-conflict message.

On success, `result` carries `aiGroupId`, `previousName` and `newName` - quote `previousName`
back to the user, since a rename is otherwise invisible in later queries.

⚠️ **The operation log only records the rename when the group's AI is on.** Renaming a group
whose AI is off leaves **no log row**, so "who renamed this group" is unanswerable for those
groups - say so rather than reporting that nobody did.

## Type fields decide which value field is valid - never mix

`acosType` / `roasType` / `budgetType` are "mode" selectors. The mode dictates exactly
which companion field to send; sending the wrong one, or both, fails. The tool does not
guard this (MCP bypass) - you must.

**ACOS** (`acosType`):

| `acosType` | Meaning | Send | Do NOT send |
|---|---|---|---|
| `1` | specific value | `acos` (required) | `acosRatio` |
| `2` | recommended | `acosStatus=1` (apply recommended); no `acos` needed | `acos`, `acosRatio` |
| `3` | ratio adjust | `acosRatio` (required) | `acos` |

**ROAS** (`roasType`): same shape - `1`->`roas` (no `roasRatio`); `2`->recommended;
`3`->`roasRatio` (no `roas`).

**Budget** (`budgetType`):

| `budgetType` | Meaning | Send | Do NOT send |
|---|---|---|---|
| `1` | total budget (whole group) | `budget` (required) | `budgetRatio` |
| `2` | campaign daily budget | `budget` (required) | `budgetRatio` |

> **`budgetType=3` (ratio) is not available on SD.** The gateway rejects any value other than `1` or
> `2` (`must be 1 (total budget) or 2 (campaign daily budget)`), and `budgetRatio` has no effect. For
> a proportional change, compute the new amount from the current budget and send it as `budget`.

## Other coupled fields

- **Dynamic budget** (`budgetDynamicStatus=1`) -> also `numType` (`1`=percentage,
  `2`=fixed) and `num` (the value).
- A target ACOS/ROAS value must respect the **x100 scale** (25% -> `25`).

## Other editable fields

| Field | Values |
|---|---|
| `status` | `0`=off, `1`=on |
| `optimizeType` | `1`=drive growth, `2`=maintain stability, `3`=boost volume. Values outside 1-3 are rejected (`Parameter 'optimizeType' must be 1 (drive growth), 2 (maintain stability), or 3 (boost volume)`). Note the tool's own inline description still lists only 1 and 2 — 3 is accepted; the validation is authoritative |
| `targetHarvestStatus` | `0`=off, `1`=on, `2`=on with exact negation |
| `budgetRedistributeStatus` | `0`/`1` |
| `aiPersonality` | `1`-`5` |
| `campaignNameSign` | `0`/`1` |
| `campaignNameRecoveryType` | when turning the label off: `1`=keep current name, `2`=restore original name |
| `remark` | free text, max 200 chars |

## Example - Legacy multi-group edit: adjust ACOS by +10% and turn AI on

```json
{
  "profileId": 3721212165742,
  "ids": [826117, 826120],
  "acosType": 3,
  "acosRatio": 10,
  "status": 1
}
```

Then verify each id via `get_entity_metadata(profileIds=[...], entity='aiGroup', ...)`.

> SD-only. For SP/SB use `save_sp_sb_ai_managed_group` (edit mode) - its `acos` is a
> plain number with **no** `acosType` machinery.
