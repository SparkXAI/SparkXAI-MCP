# Action-space & budget coupling rules (SP / SB / SD)

The first bullets cover SP/SB `aiActionSettings`; sections further down also cover SD and
the group-total-budget behavior. `aiActionSettings` is not just on/off switches - several switches are meaningless (or
fail / fall back to unintended defaults) unless you also send their companion fields.
When enabling one, include the whole set. These are front-end-enforced linkages; MCP
won't enforce them, so you must. (Exact field names: `field-reference.md`.)

- **Dynamic budget** (`budgetDynamicStatus=1`) -> also `budgetNumType`
  (`1`=percentage / `2`=fixed) and `budgetNum` (the value). Value bounds (the batch path
  uses `budgetDynamicStatus`/`numType`/`num`): `num > 0`; `numType=1` (percentage)
  `num <= 1000`; `numType=2` (fixed) `num <= 100000`.
  **Use percentage mode (`1`) whenever the operation spans stores in different currencies** -
  a fixed amount has no single meaning across currencies, and nothing on the backend stops
  you from applying one uniformly. If the user asks for a fixed increase across a
  mixed-currency set, either convert per store and write per store, or switch them to a
  percentage and say why.
- **Bid range** (`bidRangeStatus=1`) -> also `bidRangeType` and `bidRange` `[min,max]`
  (array length exactly 2, both ends numbers, **min strictly < max** - equal ends are rejected with
  `Parameter 'aiActionSettings.bidRange' min must be less than max when bidRangeStatus=1`, so
  "pin the bid to exactly X" cannot be expressed as `[X, X]`; say so rather than widening the
  range yourself). Each end is bounded by `bidRangeType`:
  - `bidRangeType=1` (coefficient): each end `0.01`-`100`.
  - `bidRangeType=2` (fixed bid, marketplace currency): each end `> 0`; the site's own min/max
    bid limits are checked downstream.

  Changing only `bidRangeType` re-checks the existing `bidRange` against the new unit. A one-sided
  range saved on the platform is kept as-is if you don't touch it, but you cannot send a `null` end.

  ⚠️ **`bidRangeType=1` is a bid COEFFICIENT, not a percentage** (`1.15` = 1.15x the base bid).
  The platform's own "Optimize base bids" readback settled the unit: a group sent
  `bidRange: [-50, 15]` came back as *"If the targeting bid is $1.00, the optimized bid range is
  expected to be 0.00~15.00"* - the `15` means **15x** the base bid. The gateway now rejects
  values outside `0.01`-`100` with `... is a multiplier of the base bid when bidRangeType=1; each
  bound must be between 0.01 and 100`, which catches the `-50` case, but a percentage such as `15`
  still passes the range check and means 15x.

  What this means for you:

  - **Never convert a percentage into this field.** A user asking for "between -50% and +15%"
    wants `[0.5, 1.15]`, not `[-50, 15]`. Confirm the unit whenever a coefficient is above 2: a
    value like `15` creates a 0x-15x range, which is not a restriction at all.
  - **The range is not a hard limit on the final bid.** Placement adjustments and the bidding
    strategy apply on top, so the final bid can fall outside it.
  - **Read the result back in the UI, not from this API.** The read-back repeats the request;
    the "Optimize base bids" panel shows what was actually stored.
  - **BidDaypart and BidAdjustment share this one `bidRange`** - if both are on it applies to
    both, so a coefficient chosen for one silently governs the other.
- **B2B range** (`btbRangeStatus=1`) -> `btbMin`/`btbMax`: `btbMin >= 0`, `btbMax <= 900`,
  min <= max, at least one end non-null.
- **Placement ranges** (`bidAdPlaceRangeStatus=1`) -> **at least one** of the `tos*`/
  `pdp*`/`ros*` min/max pairs non-null (don't enable the switch with all null); each pair
  `min >= 0`, `max <= 900`, min <= max.

  ⚠️ **Only the ranges you touch are re-validated; the rest go back unchanged.** On edit, the server
  fills `aiActionSettings` from the group's current config and repairs only the sub-configs you
  mention, so a `tos*` / `pdp*` / `ros*` / `btb*` / `bidRange` value you omit is sent back as it
  was. When you change a range or its switch, send the complete set of values for it, and **read
  the group back afterwards and check the ranges actually landed** - a success response does not
  prove they did.
  On a new group, a range that is switched on while the action switch it depends on is off
  (`bidRange` needs `bidPerformanceStatus` or `bidDaypartStatus`; the placement range needs
  `bidAdPlaceStatus`) is still saved, and the response `summary` says it is not in effect - relay
  that to the user.

## Performance budget (按表现调预算) and budget reallocation (预算重新分配) are linked

**按表现调预算** (`DYNAMIC_BUDGET`) - the value is an **increase cap on top of the current
budget, NOT a target**. Mode `1`=percentage (`+num%`), `2`=fixed (`+$num`). **Fields by
path:** SP/SB action space `budgetDynamicStatus`+`budgetNumType`+`budgetNum`; SD
`budgetDynamicStatus`+`numType`+`num`; batch = per the `DYNAMIC_BUDGET` schema.

**预算重新分配** (`BUDGET_REDISTRIBUTE`) - a switch that **changes the scope of 按表现调预算**.
**Fields by path:** SP/SB action space `budgetRedistributeStatus`; SD
`budgetRedistributeStatus`; batch = per the `BUDGET_REDISTRIBUTE` schema.

**Scope - worked example.** A group with two enabled campaigns at **$100** and **$200**
(group total **$300**), 按表现调预算 value = **20**:

| 预算重新分配 | mode | how it applies | group max |
|---|---|---|---|
| OFF | fixed 20 | each campaign +$20 ($100->$120, $200->$220) | **$340** |
| OFF | percent 20% | each campaign +20% ($100->$120, $200->$240) | **$360** |
| ON | fixed 20 | whole group ($300 + $20) | **$320** |
| ON | percent 20% | whole group ($300 + 20%) | **$360** |

- **OFF = per enabled campaign** (each campaign's own daily budget may rise by the cap).
- **ON = whole group** - you can only determine the **group-level** cap; you **cannot**
  infer how much each individual campaign will end up with.
- **Fixed vs percentage give different results** once campaign budgets differ - the
  single-campaign "$100 -> $120" case hides this, so always distinguish the two modes.
- **Whether to ask:** at **create**, the user must specify the mode (fixed/percent) and
  预算重新分配 on/off. At **edit**, read the current 预算重新分配 first and **keep it unless
  the user asked to change it** (state it in the preview). **Only ask** when the mode, the
  scope, or the user's intent is still ambiguous. Either way, always make clear the number
  is an *increase* (not a target) and show the full impact before executing.

## Group total budget (托管组总预算) rescales campaigns proportionally

托管组总预算 / group total budget = the **sum of the group's enabled campaigns' daily
budgets** (`totalBudget` / `totalDailyBudget` on read reflect this).

> **It is a sum, not a separate cap.** `totalDailyBudget` reads like an extra group-level
> ceiling sitting above the campaigns, and there is no such thing here: nothing enforces it
> independently, and the group spends whatever its members spend.
>
> **But it is writable, and writing it is a real lever** — editing the group total
> **proportionally rescales every enabled campaign's daily budget** to the new total. So
> "lower the group budget to contain spend" does work; what it is not is a cap you can set
> and forget. Before writing it, state the blast radius in the preview: **which campaigns
> change and to what**, because every enabled member moves, not just the ones the customer
> had in mind. It is not an isolated field.

## Strict ACOS / ACOS priority mode (`bidPerformanceStrictAcosStatus`)

Page name **"ACOS 优先模式 / ACOS priority mode"** (a.k.a. Strict ACOS / strict ROAS). It's
a **checkbox under 按表现调价 (bid-by-performance)** that makes the AI cut bids harder and
faster when ACOS is badly off target. Field: `bidPerformanceStrictAcosStatus` (`0`/`1`).

- **SP only** - SB and SD do not support it; don't send it for them.
- **Requires ALL of these together, or it will NOT trigger** (don't claim it's active
  otherwise): `targetType=2` (Maintain Stability / 保持订单稳定) **and** `bidPerformanceStatus=1`
  (performance bidding on, AI mode) **and** an AI personality of at least `3` on performance
  bidding. Enabling it means setting/confirming all three; a personality of 1-2 never
  triggers it. **Which field carries that personality depends on the account.**
  - **Legacy accounts**: the group-level `aiPersonality`.
  - **Accounts that set personality per action space**: `bidPerformanceAiPersonality`.
    The group-level `aiPersonality` is still returned by a read on these accounts, but it
    is read-only and **no longer drives this rule** - don't evaluate the condition from it.
  - **When you can't tell**: a missing `*AiPersonality` field does **not** prove the
    account is legacy - a failed capability lookup returns the legacy shape too. Treat the
    rule as **not satisfied** unless one of the two readings clearly meets `>= 3`, and say
    which reading you used. See [`ai-personality.md`](ai-personality.md).
- **Auto Pacing wins:** if the group's `isAutoPacing` is on, Strict ACOS is **paused** until
  Auto Pacing is turned off. Read `isAutoPacing` and tell the user if it will be suppressed.
- **Scope:** affects **base bid only** (not targeting / budget / negatives); no weekday
  scheduling (date-range only).
- **Early Access / permission-gated:** the account/group may not have it enabled. If the
  switch doesn't stick on read-back, tell the user it's Early Access (access-controlled) -
  don't report it as a silent failure of your call.
- **It's a tradeoff** - it can **underspend budget and reduce orders** in exchange for
  hitting ACOS. **Confirm this tradeoff with the user before enabling**, and don't turn it
  on by default for every stability-target group.

## Target switches and word-list fields

**Word-list settings are not supported.** That covers branded, non-branded, competitor,
negative-target blacklist, and target-harvest blacklist settings. **Do not send their status, list
ID, match-type, or list-type fields for SP, SB, or SD**, even if the routed schema exposes them.
Tell the user to configure word lists in the platform.

**Three target action switches are supported** (SP/SB, inside `aiActionSettings`):

| Field | Values | Rule |
|---|---|---|
| `targetHarvestStatus` | `0` off, `1` on, `2` on and also add harvested terms as exact negatives | 4 |
| `negativeTargetStatus` | `0` / `1` | 5 |
| `targetPausedAddStatus` | `0` / `1`; **SP only** (non-zero on SB is rejected); never send the read-side `2` | 182 |

- Out-of-range values are rejected. Precedence is your value > template > the group's current
  value. On a normal create an omitted switch is `0`; on a **template** create a switch the template
  doesn't set falls to the downstream default, which is **on** (send an explicit `0` to keep it
  off); on edit it is unchanged. ⚠️ **`targetPausedAddStatus` is the exception: it is SP-only.** On an SB group the server forces it to `0` on every create and edit path, so it never lands on - do not tell an SB customer that all three switches came on. Sending only
  these switches does not replace the default / template action-space config.
- **Target Harvest (rule 4) and Negative Target (rule 5) support AI mode only**, because word lists
  can't be configured here. (1) A template whose rule 4 or 5 is in Rule mode (`status=1`) is rejected
  on create and on edit. (2) On edit, turning `targetHarvestStatus` / `negativeTargetStatus` from off
  to on is rejected while that rule is in Rule mode on the group; set it to `0` in the same request
  (`aiAutomation.targetHarvestRuleStatus` / `negativeTargetRuleStatus`), or use the platform.
  (3) Batch `NEGATIVE_TARGET` is rejected. Switches that are already on, and the other action
  spaces, are not checked.

## Disabling an action space doesn't clear its follow-up fields

Turning an action space off (its `*Status=0`) only updates that status - the backend does
**not** zero out the range/companion values you set before (confirmed 2026-08-14). To
change a follow-up value you must re-send it.
