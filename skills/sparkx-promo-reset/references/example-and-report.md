# Promo Reset - worked example and structured report

## Example

> **客户**：把 Prime Big Deal Days 的调整复位一下。
>
> **AI**：先确认几件事：① 从店铺数据看，大促是 10/6–10/7，10/5 和 10/8 也有大量调整——这 4 天都算进来吗？复位方式：不看表现、全部直接复位，还是根据表现分批复位（推荐）？② 大促后还有延续的 Deal 或库存紧张的商品吗？大促后是回到平时，还是按某个目标 ACOS 保利润？每天广告预算多少？③ 你有大促前设置的记录吗（表格，或 10/5 之前导出的批量文件）？
>
> **客户**：10/5–10/8 都算；根据表现分批。没有延续的 Deal。回到平时，每天大约 $3,000。没有记录。
>
> **AI**：10/5–10/8 日志里有 88 个活动的预算改动，全部记为亚马逊后台操作，看不到是谁改的。这些是你们改的吗？
>
> **客户**：是，我们团队改的。
>
> **AI**：那就按你们的改动处理。结合 10/9–10/11 的表现：
> - **立即复位（大促后表现变差）16 个**：例如 Snacks-SP-Exact-Keyword，预算 $100 → $50，大促后 ACOS 119%，既超出店铺平时的 34–41%，也高于目标 41%。这 16 个大促后 3 天合计花了 $1,533。
> - **分几天逐步恢复 13 个**：例如 Noodles-SP-Exact-Keyword，$100 → $78 → $57 → $35，大促后转化率 13.9%，仍高于平时的 8.3–9.7%。
> - **一次恢复到大促前 7 个**：表现正常或几乎没花钱。
> - **需要你决定 49 个**：4 个在 10/8 之后你又改过；45 个是大促期间被调低的，默认不加回去。
>
> 复位后每天花费约 $2,700，在你的 $3,000 以内。下面是写入预览，要执行哪些：(a) 按建议全部执行（推荐）/ (b) 只执行“立即复位” / (c) 先不执行？第一次写入前我会先存好计划文件，它同时也是撤销文件。
>
> {写入预览：每一行今天要写入的值}

## structured_report

```json
{
  "store": {"profileId": "...", "profileName": "...", "timezone": "..."},
  "window": {"start": "...", "end": "...", "clock": "store-local"},
  "mode": "performanceBased|allAtOnce|recapOnly",
  "postWindow": {"start": "...", "end": "..."},
  "targetSource": "log|file|mixed",
  "file": {"name": null, "rowsRead": 0, "matched": 0, "couldNotMatch": [], "unitsConfirmed": null},
  "sources": ["email", "Manual", "MCP"],
  "amazonSideSources": ["Amazon Console"],
  "groups": [{"aiGroupName": "...", "field": "targetType|acos|aiPersonality|bidRange|totalBudget|<action-space switch>", "now": "...", "restoreTo": "...", "basis": "...", "suggestion": "restoreNow|stepDown|restoreOnce|hold|customerDecides|skip", "steps": [], "decisionReason": null, "holdUntil": null, "holdReason": null}],
  "schedules": [{"aiGroupName": "...", "scheduleId": "...", "phase": "single|warmup|event", "startDate": "...", "endDate": "...", "storeDate": "...", "timeType": 1, "origin": "promo|other", "state": "running|ended|unknown|null", "bidAudit": {"state": "withinRange|outsideRange|notVerifiable|noRange|scheduleStillRunning", "rangeType": "fixed|coefficient|none|null", "outsideCount": 0, "checkedCount": 0, "note": "..."}, "note": "..."}],
  "noAction": [{"objectType": "...", "name": "...", "now": "...", "reason": "atOriginal|archived|..."}],
  "items": [{"objectType": "campaignBudget|keywordBid|targetBid|adGroupBid|placement|portfolioBudget|paused|enabled", "targetSource": "log|file", "name": "...", "amazonId": "...",
             "source": "person|mcpMatched|mcpUnmatched|amazonConsole|amazonConsoleConfirmed", "changedBy": "...",
             "prePromo": 50, "now": 100, "restoreTo": 50, "steps": [75, 50], "suggestion": "restoreNow|stepDown|restoreOnce|hold|customerDecides|skip",
             "decisionReason": null, "holdUntil": null, "holdReason": null,
             "reason": "...", "postDays": 3, "postSpend": 0, "postAcos": null, "normalAcos": [34, 41], "targetAcos": 41,
             "binding": null, "savedPerDay": 0, "salesGivenUpPerDay": 0}],
  "notWritable": [{"objectType": "sbAdGroupBid|...", "name": "...", "prePromo": 0, "now": 0, "reason": "..."}],
  "moneyBothWays": {"savedPerDay": 0, "salesGivenUpPerDay": 0, "givenUpRoas": null, "givenUpAboveTarget": false},
  "budgetCheck": {"userDailyBudget": null, "basis": "savings|sumOfBudgets", "dailyAfterRestore": null, "fits": null, "shortBy": null},
  "searchTermsToKeep": [{"searchTerm": "...", "campaignName": "...", "orders": 0, "clicks": 0, "roas": 0, "suggestedExactBid": 0}],
  "execution": {"planFile": null, "checkedFrom": null, "lastChecked": null,
                "counts": {"planned": 0, "held": 0, "inProgress": 0, "done": 0, "needsReadBack": 0, "failed": 0, "stoppedChangedByOthers": 0, "skipped": 0, "customerDecides": 0, "undoPending": 0, "undone": 0, "ended": 0}},
  "storeContext": {"windows": [{"phase": "pre|promo|post", "start": "...", "end": "...", "days": 0, "dailySpend": 0, "dailySales": 0, "dailyOrders": 0, "cpc": null, "cvr": null, "acos": null, "roas": null}], "attributionNote": "..."}
}
```

Field notes:

- `source` says where the change came from: a person, an MCP write matched to the promo
  change log, an MCP write not matched (it stays in "you decide" until the user says it belongs
  to the promo), Amazon's side (`Amazon Console`, author unknown), or Amazon's side confirmed
  by the user (Step 2a).
- `decisionReason` is set only when `suggestion` is `customerDecides`: `lowered`,
  `changedAfterWindow`, `createdInWindow`, `pausedInWindow`, `enabledInWindow`, `aiSwitched`,
  `aiChangedAfter`, `smallRaise` (under 10%), `amazonSide`, `mcpUnmatched`,
  `historyUnreadable`, `fileMismatch`.
- `holdUntil` (store date) and `holdReason` (`dealRunning`, `holidayHold`, `waitForSchedule`)
  are set only when `suggestion` is `hold`; they become the plan file's `holdUntil` /
  `holdReason`. A running schedule is not an item: it is in `schedules` (`state: running`),
  and its plan-file reminder row uses `holdReason: scheduleRunning` (`execution-safety.md`
  section 1).
- `binding` (`true` / `false` / `null` = cannot tell yet) is set only on lowered budgets
  (`pacing-rules.md` section 7) - in both modes.
- `notWritable` lists items with a pre-promo value but no MCP write route (SB ad group default
  bids); the user changes them in the platform.
- `moneyBothWays`, `savedPerDay`, `salesGivenUpPerDay` and `searchTermsToKeep` are filled only in
  "in batches by performance" mode (`pacing-rules.md` section 8; SKILL Step 4); `null` / empty
  in "all at once" mode. `budgetCheck` is `null` when the user gave no daily budget; its
  `basis` is `sumOfBudgets` in "all at once" mode (SKILL Step 4).
- `execution` mirrors the plan file once it exists (`execution-safety.md`): its name, the
  stale-check start (`staleCheckFrom`), the last check, and how many rows are in each status.
  Before the plan file exists every count is 0 and `planFile` is `null`.
- `schedules[]` lists every schedule read. Only `timeType: 1` + `origin: "promo"` rows count:
  a running one gets a plan-file reminder row, and they carry the group's audit. Weekly
  (`timeType: 2`, `state: null` - no dates) and `origin: "other"` rows are information only,
  with `bidAudit: null`; while in effect they delay the group's audit (its promo rows show
  `scheduleStillRunning`, `note` the date it waits for - `restore-list.md` section 5).
- `schedules[].bidAudit` is the group's one audit (`restore-list.md` section 5), the same on each
  of its promo schedule rows. `rangeType` is `none` with `noRange` (bid range off) and `null`
  when the range was not read (`scheduleStillRunning`). It is evidence only, not approval
  to write a bid. `storeContext.windows` is filled in both restore modes, and in a recap-only run
  (`mode: "recapOnly"`, where `items`, `groups` and the rest stay empty), from three named
  windows; every rate is recomputed from summed metrics. The one exception: restoring from a
  file with no promo dates skips the recap - `storeContext` and `postWindow` are `null`
  (`from-file.md` section 4).

## Customer names for each group

One name per value, used the same way in the chat summary, the markdown template, the HTML
report and the example. Never show the raw value.

| `suggestion` (or section) | Customer name | 中文 | What it means |
|---|---|---|---|
| group settings | Managed-group settings | 托管组设置复位 | Objective, target ACOS and other group settings go back first |
| `restoreNow` | Restore now - worse after the promo | 立即复位（大促后表现变差） | Clearly worse than its normal range and its target: back to the pre-promo value today |
| `stepDown` | Step down over several days | 分几天逐步恢复 | Raised 1.5x or more, or still converting above normal: one step a day, today's step only |
| `restoreOnce` | Restore in one step | 一次恢复到大促前 | Performing normally, too little spend to judge, worse on ACOS while SB / SD / Vendor sales are still arriving (raised < 1.5x), or "all at once" mode: back to the pre-promo value today |
| `hold` | On hold until {date} | 暂缓到 {日期} | A deal still running, the holiday hold, or a group setting you chose to keep until its schedule ends (a running schedule itself is listed under schedules) |
| `customerDecides` | You decide | 需要你决定 | Lowered, changed again later, created / paused / enabled in the window, small raises, Amazon-side or unmatched changes |
| `skip` | No action | 无需处理 | Already at the pre-promo value, or archived - listed in `noAction[]` only, never also in `items[]` |
| schedules | Schedule still running / Schedule ended / For information only | 排期仍在生效 / 排期已结束 / 仅供参考 | Checked against the store date; weekly schedules and ones not from this promo are for information only |
| `notWritable` | Change in the platform | 需在平台上修改 | No MCP write route (SB ad group default bids) |

"Restore now" and "Restore in one step" both write the pre-promo value today; the names differ
because the reason differs - say the reason on every row.

In every mode `postWindow` is the store-level post window - the dates of `storeContext`'s `post`
entry (the earliest post days - SKILL.md Step 4), `null` when there are no post days yet. With
`mode: "allAtOnce"`: `storeContext` is still filled (the recap shows in both modes, except a
dateless file restore; it is store-level, three daily queries); each item's
`postDays`, `postSpend`, `postAcos`, `normalAcos` and `targetAcos` are `null`, while `steps` keeps its one
step (the pre-promo value, e.g. `[50]`) like any restore-at-once item, so the result feeds the
plan file, resume and read-back directly; `suggestion` is
only `restoreOnce`, `hold`, `customerDecides` or `skip`; the `reason` of a restored item says
the user chose to restore without judging performance.

`postDays` is how many post-promo days the item was judged on: full days after the window, ending
no later than today - 2, at most 3 (`pacing-rules.md` section 1) - so 0-3. `postSpend` and
`postAcos` are summed over those days. With `postDays` under 3 the item follows the thin-data
rule (not the section 5 decision); with `postDays: 0` both are `null`.

In **either** mode, an item whose `changedBy` is `Amazon Console` carries `suggestion` =
`customerDecides` regardless of what its performance would otherwise suggest, and its
`reason` says the change came from Amazon's side with no known author. In the JSON result
those rows' sources are listed under `amazonSideSources`, separate from `sources`. **The one
exception** is a run where the customer confirmed the `Amazon Console` changes as theirs (Step
2a): then those rows are paced like human rows, `Amazon Console` moves into `sources`, and
`amazonSideSources` is empty.
