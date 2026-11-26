# Reading Automation Rules

Use this guide when the user asks which automation rules are enabled or asks you to explain a
Rule-mode configuration. It translates the MCP response into business meaning without claiming
that the read tool exposes the complete standalone automation-template system.

## 1. Choose the Read Surface

| User question | Query | What it returns | What it does not return |
|---|---|---|---|
| Which rule types are enabled on these campaigns? | `entity: "automationRule"`, filtered by `amazonCampaignId` | Campaign ID plus `enabledRuleTypes` and localized `enabledRuleNames` | Template ID/name, conditions, actions, frequency, applicable objects, account template list |
| Explain this managed group's Rule-mode setup | `entity: "aiGroup"`, filtered by `aiGroupId` | Effective action-space switches and retained `aiAutomation.{ruleType}` configuration | Standalone account-level automation templates |
| Explain a managed-group schedule's embedded rules | `entity: "aiGroup_schedule"`, one profile and one group | Per-schedule effective configuration when the backend returns it | Standalone templates; missing inherited group objectives must be read from the parent group |
| List or inspect standalone automation templates | Not supported by the current metadata entities | - | The Help Center template library and full standalone template configuration |
| Inspect product inventory rules | Not supported by these campaign/managed-group surfaces | - | SKU/product rule associations and inventory-rule configuration |

The Help Center overview still says seven templates, while its current body also documents newer
Budget Rules, Placement Rules, and Campaign activation/pausing. Do not infer coverage from that
count; use the returned rule codes and the capability table below.

## 2. Determine Off, AI, or Rule Mode

Always pair the action-space switch in `aiActionSettings` with the rule entry in
`aiAutomation`. Do not classify mode from either object alone.

| ruleType | Managed-group action space | Paired effective switch |
|---:|---|---|
| `2` | Bid dayparting | `bidOptimization.bidDaypartStatus` |
| `4` | Harvest targets / add search terms | `targetOptimization.targetHarvestStatus` |
| `5` | Add negative targets | `targetOptimization.negativeTargetStatus` |
| `13` | Budget dayparting | `budgetOptimization.budgetDaypartStatus` |
| `17` | Budget rules / boost budget | `budgetOptimization.budgetDynamicStatus` |
| `19` | Placement bid adjustment | `bidOptimization.bidAdPlaceStatus` |
| `20` | Pause campaigns and ad groups | `structOptimization.structPauseCampaignStatus` |
| `181` | Optimize base bids | `bidOptimization.bidPerformanceStatus` |
| `182` | Pause targets | `targetOptimization.targetPausedAddStatus` |

This table is an internal parsing map. In customer output use the localized product names from
[`managed-group-display.md`](managed-group-display.md), never the rule number.

Decision procedure:

1. If the paired switch is `0`, report the action space as off. Any dependent fields omitted by
   the effective-config projection are expected.
2. If the switch is on and `aiAutomation.{ruleType}.status=1` is present, report Rule mode and
   explain the retained configuration.
3. If the switch is on and no retained entry exists for that rule type, report AI mode. AI-mode
   placeholders are removed by the server.
4. If the switch is missing or malformed, say the effective mode cannot be determined from this
   row. Do not turn an empty `aiAutomation` into "all AI" or "all off".

`aiAutomation.{ruleType}.status` describes **mode**, not enabled/disabled state. The paired action
space switch is the enable signal. In particular, never render `status=1` as "enabled": render it
as "Rule mode" and separately report whether the paired switch is on.

`targetPausedAddStatus=2` is an AI-only "pause plus supplement" option. In Rule mode the response
folds it to effective value `1`; describe rule `182` as pausing targets, not supplementing them.

## 3. Read the Rule Tree Safely

- Prefer `ruleTypeText`, `statusText`, and leaf-level `...Text` / `...Formatted` fields. Keep the
  raw value beside the label when precision matters.
- Treat rule arrays as ordered. The Help Center states that when several strategies match, only
  the highest-priority strategy runs; the returned order is therefore meaningful and must not be
  sorted or deduplicated.
- Different condition groups are OR; conditions inside one group are AND. When the raw response
  exposes only connectors such as `operation`/`operationText`, preserve their order and wording
  instead of flattening every item into AND.
- Read `day` together with `exceptDay`, using the store-local execution date `D`. "Past N days"
  excludes today and initially covers `D-N` through `D-1`. `exceptDay=X` removes the latest X
  dates from inside that N-day window, leaving `D-N` through `D-X-1` (`N-X` dates); it does not
  shift the window backward to keep N dates. For example, past 3 days means yesterday, two days
  ago, and three days ago; excluding the latest 1 leaves only two days ago and three days ago.
  Blank/zero `exceptDay` means no additional exclusion.
- `todayPerformance` means the current store day from 00:00 through the execution time.
  `historyPerformance` uses the configured historical lookback.
- Unknown paths and values are intentionally passed through. If a leaf has no confirmed Text
  companion, show the raw key/value and label it as an unconfirmed code; never borrow a label from
  another rule type. The same raw token can have different meanings in different rules.

## 4. Rule-Specific Meaning

### `2` - Bid dayparting

- Primary payload: `updateBid`, with `templateDateType` when present.
- Matrix values are bid coefficients/multipliers, not percentage-point increases. A base bid of
  5 with coefficient 2 produces an effective bid of 10.
- The rule executes at the start of each configured hour. Use `updateBidFormatted` for matrix
  dimensions/coordinates when returned, but retain the raw matrix values.

### `13` - Budget dayparting

- Primary payload: the hourly budget matrix in `condition`; it may also carry
  `templateDateType`, misspelled upstream field `excuteDays`, and budget bounds.
- Business operations can be fixed budget, increase/decrease by percentage, or increase/decrease
  by amount. Decode a cell only when the response provides a confirmed Text value; otherwise show
  its raw operation/value.
- Distinguish the **configured operation** from the **effective budget ratio**. For a percentage
  operation relative to the current daily budget:
  - decrease by `X%` -> effective ratio `100% - X%`;
  - increase by `X%` -> effective ratio `100% + X%`.
  Therefore, "decrease by 98%" means the effective budget is 2% of the current daily budget;
  "decrease by 45%" means 55%. This is not a second rule or a conflicting value.
- When presenting a percentage matrix, title it **Effective budget as a percentage of the current
  daily budget (calculated)** / **相对当前日预算的生效预算比例（计算值）**. Do not call it simply
  "actual delivery percentage": it is a budget limit, not a guarantee that the same percentage
  will be spent or delivered.
- Prefer showing both forms at least once, for example: "00:00-03:00: decrease the current daily
  budget by 98%, so 2% is effective." Treat a displayed interval as `[start, end)`: 00:00-03:00
  covers hours 00, 01, and 02.
- A fixed-budget or amount-based operation stays in currency. Do not force it into a percentage
  matrix without a confirmed base budget.
- An unconfigured hour restores the campaign's current daily budget in SparkX AI. This reset behavior
  means an effective ratio of 100% for percentage presentation and is the key difference from rule
  `17` scheduled budget changes.

### `17` - Budget rules / budget by performance

- `condition.setBudgetOption` is the scheduled-budget portion. A value set at one time continues
  until the next scheduled change; blank hours do not automatically restore the campaign budget.
- `condition.todayPerformance` is the current-day performance portion. It can increase, decrease,
  or set daily budget when conditions match. Ordered strategies are priority order.
- Budget utilization means current-day spend divided by the latest daily budget at execution
  time. The Help Center describes checks every 30 minutes inside configured execution windows.
- Render each strategy as one unit: trigger conditions, budget action, and that action's enabled
  upper/lower bound. `action.switch` controls whether the strategy's bound applies and
  `action.bounds` is the bound value. Directionally corresponding checked flags, when returned,
  support the same presentation. Do not repeat them later as a separate "Budget boundaries"
  section. If the sources conflict, report the inconsistency instead of silently choosing one.
- Keep three sibling customer sections in this order: **Strategies**, **Frequency settings**, and
  **Custom settings**. Custom settings do not belong inside execution time.
- `autoModifySwitch=1` means the custom callback is enabled. At the next store-local 00:00, the
  system sets the campaign budget to the value represented by `autoModifySetting`. For
  `{"type":"amount","value":3}`, say "At 00:00 the next day, set the budget to $3" (using
  the store currency), not "adjust by $3 each time". If `autoModifySwitch=0`, residual
  `autoModifySetting` is not effective and must not be reported as active.

Customer-facing example:

> **按表现调预算：开启；运行方式：规则**
>
> 策略 1：当日 ACOS >= 70% 时，降低预算 40%，调整后预算不低于 $5。
>
> 策略 2：当日 ACOS < 45% 时，提高预算 40%，调整后预算不超过 $15。
>
> 频率设置：每天 00:00-24:00，每 30 分钟检查一次。
>
> 自定义设置：开启；次日 00:00 自动将预算设置为 $3。

### `19` - Placement rules

- Conditions live under `condition.historyPerformance`; `activeModel` describes the applicable
  ad type/object when present.
- A condition can target one placement, while its action array can adjust one or all placements.
  Keep `placementText` and each action's `placementText` separate.
- Increase/decrease is relative to the current placement adjustment: current 55% increased by
  10% is calculated as `55% + 55% * 10%` (subject to configured max/min). A fixed action sets the
  placement adjustment directly.
- The Help Center supports daily/weekly/monthly execution at a chosen whole hour. If the returned
  time fields have no Text/Formatted companion, report their raw values without assuming units.

### `20` - Campaign activation/pausing (new)

- `condition.timedSet` contains scheduled campaign state changes; schedules may be daily, weekly,
  or non-recurring. Scheduled actions can activate or pause.
- `condition.historyPerformance` contains historical-performance strategies. The Help Center's
  current version only performs **pause campaign** for this branch.
- If a campaign is already paused at evaluation time, the performance strategy does not continue.
  Keep scheduled state actions distinct from the rule's top-level `status` mode field.
- Deep rule-20 leaves are currently raw passthrough. Do not translate `setStatus` with the
  top-level Rule/AI status vocabulary.

### `181` - Optimize base bids

- Conditions live under `condition.historyPerformance`. Actions can increase, decrease, or set
  base bids subject to the returned value/bounds configuration.
- Use the action's `actionTypeText`, `baseTypeText`, and bound/switch Text fields when present.
  Use `timePeriodTypeText` and `timePeriod.hourFormatted` for the execution schedule.

### `182` - Pause targets

- Conditions live under `condition.historyPerformance`; the Rule-mode action is pause targeting.
- Use returned condition and time-period Text fields. Do not describe target supplementation in
  Rule mode; that behavior belongs to the AI-only value folded out by the effective projection.

### `4` / `5` - Harvest search terms / add negatives

- These use a legacy raw structure: top-level `condition` arrays plus rule-specific `action`,
  `isSelf`, `campaignAd`, and matching settings. Preserve unconfirmed deep values unless a Text
  field is present, but use the confirmed `isSelf` mapping below.
- `isSelf` controls where a harvested/negative target is added:

  | `isSelf` | UI option | Operational meaning |
  |---:|---|---|
  | `1` | Current campaign (all ad groups) / 当前广告活动（所有广告组） | Add to every ad group in the source campaign. |
  | `3` | Current campaign (current ad group) / 当前广告活动（当前广告组） | Add only to the source ad group. |
  | `2` | Ad groups in specified campaigns / 指定广告活动的广告组 | Add only to the campaign/ad-group bindings listed in `campaignAd`; enumerate those bindings when present. |

  Do not collapse `1` and `3` into "the current campaign" or "self"; they affect different
  numbers of ad groups.
- Help Center meaning: rule `4` adds qualifying search terms as keyword/product targets with a
  configured match method and bid; rule `5` adds qualifying search terms as exact/phrase negative
  targets.
- Standalone rules evaluate on selected weekdays around 03:00 in the store timezone. Do not apply
  that schedule to a managed-group response unless its returned configuration supports it.

## 5. Coverage by Surface

| Rule/code | Standalone campaign enabled-type lookup | Managed-group `aiAutomation` config |
|---|---|---|
| `2`, `4`, `5`, `13`, `17`, `19`, `20` | Yes | Yes, when the paired action space is in Rule mode |
| `3`, `6`, `7`, `8` | Legacy standalone types may appear | No current managed-group mapping |
| `15`, `18` | Targeting-rule types may appear | No current managed-group mapping |
| `181`, `182` | May be returned by the shared type-name provider, but they are managed-group action-space rules | Yes |
| Product inventory rules | Not represented by this campaign lookup | No |

## 6. Recommended Explanation Shape

When the user asks for a **complete managed-group configuration**, first report the entire
action-space matrix from `aiActionSettings`, grouped as Bid / Budget / Targeting / Structure. Show
each supported switch as on or off. For an on rule-capable switch, pair it with `aiAutomation` and
show AI or Rule mode; never infer one sibling switch from another. Then expand every retained Rule
entry using the shape below. This prevents summaries such as "performance + placement + bid range"
from incorrectly implying that all three switches are on.

For each rule, report the customer-facing product name rather than `Rule <number>`:

1. Rule name/code and effective mode.
2. Applicable action space/object, only when exposed.
3. Conditions, preserving group connectors and priority order.
4. Action and bounds.
5. Data period, exclusion period, calculated effective window, and execution schedule.
6. For rules `4`/`5`, the exact `isSelf` scope and any `campaignAd` bindings.
7. Any raw/unconfirmed fields and the read-surface limitation.

Use the managed-group UI action-space label in the main summary: rule `5` is **Add negative
targets / 添加否定定向** there. "Add Negative Keywords / 添加否定词" is the corresponding
automation-template name and may be shown secondarily, but should not replace the action-space
label.

Never claim that a managed-group read is the account's reusable automation template, and never
claim that an enabled-type lookup contains the rule's actual configuration.
