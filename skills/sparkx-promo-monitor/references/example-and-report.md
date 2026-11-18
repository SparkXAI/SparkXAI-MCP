# Promo Monitor - worked example and structured report

## Example

> **客户**：黑五第一天，现在跑得怎么样？要不要加预算？
>
> **AI**：（按你的大促前准备记录：11/20–12/1，每天 $4,500，ACOS 不超过 35%。）现在是洛杉矶时间 13:20。
> 你现在想：继续冲量、放慢、重点推某几个 ASIN，还是守住 35%？$4,500 有变吗？有没有快卖完的？
>
> **客户**：继续冲。预算不变。没有新情况。
>
> **AI**：截至 11:00（最新的小时数据），店铺花了 $1,640，是平时同一时段的 2.6 倍。按这个速度全天约 $4,300，在 $4,500 以内。
> - **今天有改动**：08:12 有人（你的账号）暂停了 B0xxxxx 的 2 个商品广告，这个 ASIN 昨天广告卖了 11 件。是有意的吗？
> - **快花完预算的好活动（3 个）**：例如 “Dog Food - Exact” 今天 ACOS 22%、14 单，$250 只剩 $38，按现在的速度 14:00 左右花完。建议 $250 → $325（+30%）。
> - **托管组（2 个预算不够）**：“Dog Food AI” 转化后 ACOS 24%，排期目标 30%，组里的活动 12:05 预算花光。建议总预算 $900 → $1,170。
> - **花钱不出单（4 个定向）**：今天 20–46 次点击、0 单。你选的是继续冲，这几个先不动，18:00 再看。
> - **点击太少，先不判断**：31 个活动。
>
> 这些加起来全天多花 $410，仍在 $4,500 以内。下面是分批的写入预览，要执行哪些：(a) 全部（推荐）/ (b) 只改活动预算 / (c) 先不执行？
>
> {写入预览：输出模板里的“建议调整”表，按批次列出}

## structured_report

```json
{
  "store": {"profileId": "...", "timezone": "...", "storeType": "seller|vendor"},
  "now": {"date": "...", "hour": 13, "latestDataHour": 10, "settledThroughHour": 9},
  "generatedAt": "...",
  "scope": {"type": "store|mainCampaigns|named", "campaigns": 0, "ofCampaigns": 0, "named": []},
  "event": {"name": "...", "start": "...", "end": "...", "day": 1, "days": 12, "dayType": "warmup|sale"},
  "goal": ["push", "slow", "asins", "limit"],
  "budget": {"mode": "dailyCap|windowTotal", "eventBudget": 0, "dailyCap": null, "todayBudget": 0, "windowSpent": null, "windowRemaining": null},
  "limitAcos": null, "limitBasis": "hardLimit|nonBrandLimit|ceiling|storeFallback|null",
  "raiseAcos": null, "holdUpperAcos": null,
  "brandCheck": {"brandCpcChange": null, "brandClickShare": null, "brandClickShareNormal": null, "topOfSearchCpcChange": null, "verdict": "steady|possibleAttack|unknown", "note": "..."},
  "yesterdayReview": {"generated": true, "date": "...", "baselineStart": "...", "baselineEnd": "...", "metrics": [{"name": "spend|sales|orders|cpc|cvr|acos|budgetUsage", "yesterday": null, "baselineDailyAvg": null, "changePct": null}], "anomalies": [{"campaignName": "...", "change": "...", "evidence": "...", "todayAction": "..."}], "todayPriorities": ["..."]},
  "groups": [{"aiGroupName": "...", "state": "shortOfBudget|overTarget|onTrack", "targetInEffect": 0, "targetFrom": "schedule|group", "acosSettled": null, "settledClicks": 0, "totalBudget": 0, "effectiveTotalBudget": null, "effectiveTotalKnown": true, "budgetRedistributeStatus": null, "enabledCampaignCount": null, "ranOutAt": null}],
  "plannedBudgets": [{"campaignName": "...", "targetDate": "...", "role": "warmup|early|peak|between", "multiple": 0, "current": 0, "planned": 0, "status": "planned|fulfilled|skipped|missed", "note": null}],
  "pace": {"spendSoFar": 0, "normalByThisHour": 0, "ratio": 0, "projectedDay": 0},
  "changedToday": [{"time": "...", "who": "person|amazonSide|ai|rule", "entity": "...", "name": "...", "from": "...", "to": "..."}],
  "campaigns": [{"name": "...", "amazonId": "...", "state": "winnerRunningOut|burning|notConverting|clearlyOverLimit|overLimitWatching|held|onPace|underSpending|mixed|tooFewClicks|leftAlone|managed",
                 "watchReason": "overLimit|overFloor|null", "spendToday": 0, "ordersSettled": 0, "acosSettled": null, "budget": 0, "remaining": null, "usageUpdatedTime": "...", "runOutHour": null}],
  "moves": [{"objectType": "scheduleTarget|groupTotalBudget|campaignBudget|keywordBid|targetBid|placement|status", "name": "...", "now": 0, "proposed": 0, "reason": "...", "status": "ready|needsYes|needsReview"}],
  "executed": [{"objectType": "...", "name": "...", "before": 0, "after": 0, "result": "written|failed|needsReadBack|needsReview|notWritten", "reason": "waitingForYes|guard|declined|changedByOthers|null"}],
  "watch": [{"name": "...", "state": "...", "why": "..."}],
  "stock": [{"asin": "...", "coverDaysAtTodayPace": null, "eventDaysLeft": 0, "restockSellableInDays": null, "inbound": null, "protection": {"budgetCut": null, "bidCuts": [], "requiresConfirmation": true}}],
  "nextCheck": "..."
}
```

Field notes:

- `latestDataHour` is the last hour used for spend and pace; `settledThroughHour` the last
  hour used for orders and ACOS (`pace-and-states.md` section 1). At 13:20 they are 10 and 9.
- `limitBasis` says which rung of `pace-and-states.md` section 6 set `limitAcos`.
- `brandCheck` is the first-regular-check-of-the-day line (`pace-and-states.md` section 2); `null`
  values when the brand names are not known.
- `yesterdayReview.generated` is true only at the first regular check of the store day (at or
  after 08:00, never the day-switch check). Later checks in the same conversation reuse it; a
  new conversation the same day regenerates it only if the user asks (`pace-and-states.md`
  section 2). `baselineStart` / `baselineEnd` are the seven days before yesterday, or the seven
  normal days before the warm-up when yesterday was an event day; orders, sales and ACOS for
  yesterday are provisional.
- `groups` holds the managed-group states (`pace-and-states.md` section 7), with
  `effectiveTotalBudget` the total with budget by performance (`moves.md` section 4; `null` when
  it is off or unknown) and `effectiveTotalKnown` `false` only when budget by performance is on
  but its size cannot be read (no group-total raise is proposed); `budgetRedistributeStatus` and
  `enabledCampaignCount` are what the amount-mode size used (`null` in percentage mode or when off); `plannedBudgets`
  the prep `planned` rows for today and tomorrow and what happened to them (`missed` = a
  `planned` row whose day has come and no check wrote it - `moves.md` section 1).

**Customer names.** Campaign states use the names in `pace-and-states.md` section 6
(`burning` is shown as "Spending, no orders yet"); group states: "Short of budget", "Over its
target", "On track". Moves: `ready` -> "Ready", `needsYes` -> "Needs your confirmation".
Moves and executed: `needsReview` -> "Needs review - change it in the platform". Executed: `written` -> "Applied and verified", `failed` -> "Failed", `needsReadBack` ->
"Awaiting verification", `notWritten` with `reason` `waitingForYes` -> "Waiting for your
confirmation", `guard` -> "Blocked by a safety rule", `declined` -> "Not applied, as you chose",
`changedByOthers` -> "Changed by someone else - not overwritten". Watch list: "Watch".
`effectiveTotalKnown: false` -> "Cap with budget by performance: unknown, may be higher". Never
show a raw value.

For Chinese: `burning` -> `花了钱还没出单`; group states `预算不够` / `超过目标` / `正常`;
`ready` -> `可执行`, `needsYes` -> `等你确认`, `needsReview` -> `需人工核对，请在平台上修改`; `written` -> `已执行并核对`, `failed` ->
`执行失败`, `needsReadBack` -> `待核对`, `waitingForYes` -> `等你确认`, `guard` ->
`被安全规则拦下`, `declined` -> `按你的选择未执行`, `changedByOthers` -> `被别人改过，本次未覆盖`;
watch list `继续观察`; `effectiveTotalKnown: false` -> `按表现调预算后的上限未知，可能更高`.
