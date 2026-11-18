# Pace and states: reading the store on an event day

All times are the store's (`timezone` from `get_user_authorized_context`). `h` = the current
store hour. Query details belong to the query skills; this file says what to pull and how to
read it. Thresholds are defaults - show the numbers so the user can override them.

## 1. Two kinds of "recent"

| Term | Hours | Used for |
|---|---|---|
| **Latest data** | today through the latest hour that ended at least 2 hours ago (hourly data runs about two hours behind and keeps filling in after that; the hour still running and the one just ended are incomplete) - at 13:20, through the 10:00-10:59 hour | Spend and pace |
| **Settled hours** | hours that ended at least 3 hours ago (at 13:20, through the 09:00-09:59 hour) | Orders, ACOS, "not converting" - orders keep arriving for earlier hours |

Neither is final: orders keep being attributed for days (up to 14 on Vendor profiles). Say once per report that today's ACOS
is provisional and will improve.

## 2. Pulls

| What | How |
|---|---|
| Today by hour, store level | `get_ads_perf`, `factEntity: campaign`, `timeGranularity: hourly`, `select: ["date", "hour"]`, `dateStart` = `dateEnd` = today. Metrics `Spend, Sales, Clicks, Conversions`. Store pace (section 4) |
| Today per campaign | Today only - never the six days before per campaign (a 2,288-campaign store would return about 380,000 rows): the settled per-campaign pull in section 6 (one row per campaign), plus, for the run-out rate (section 5), `select: ["hour", "campaign.campaignId_"]` for today with `filters: {"hour": {">=": x - 2, "<=": x}, "Spend": {">": 0}}` (`x` as in section 4) - three hours, not seven days. Page with a stable order (spend, then id) |
| Six days before today, store level (fallback only) | The store-level hourly pull for `dateStart` = today - 6, `dateEnd` = today - 1, only when the normal-day curve below has no data (section 3) |
| Normal-day curve (once per event) | The same hourly pull at store level (`select: ["date", "hour"]`) for the 7 days before the warm-up started (`dateStart` = warm-up start - 7, `dateEnd` = warm-up start - 1). Keep it for the whole event |
| Yesterday review (first regular check of the store day only - at or after 08:00, never the 00:05-00:30 day-switch check) | Daily campaign data for yesterday and a seven-day baseline: the seven complete days before yesterday, or, when yesterday was an event day, the seven normal days before the warm-up (the curve's days - event days are no baseline). Pull store totals first; then campaign totals only for yesterday and the baseline, paged and ordered by spend. Metrics: `Spend`, `Sales`, `Clicks`, `Conversions`; recompute CPC, CVR and ACOS from sums. Add yesterday's budget-usage fields from the campaign metadata read when available. Keep only the five largest material anomalies in the customer report; later checks reuse the result |
| Window spent (window total only) | `get_ads_perf`, `factEntity: campaign`, `select: ["date"]`, `dateStart` = the **warm-up start** (the event start only when there is no warm-up - the window total covers the warm-up days too), `dateEnd` = yesterday, metric `Spend` (store level, daily). `windowSpent` = that sum + today's spend so far from the hourly pull. On the first day of the window skip this pull (the start would be after the end, which the tool rejects): the earlier window spend is 0 and `windowSpent` is today's spend so far. Never report today's spend alone as the window spent, and never start the sum at the event start when there was a warm-up - the warm-up's spend would be counted as still available |
| Brand and top-of-search check (first regular check of the day, and before any stretch) | `get_ads_perf` today so far against the 7 normal days: brand-term CPC and share of store clicks (`factEntity: searchTerm`, `ilike` on the brand names from prep), and top-of-search CPC (`factEntity: placement`). One line each: "brand CPC +4%, share steady - no sign of attack"; "top of search CPC +22%" - it decides whether a stretch lowers top of search |
| Budget usage now | `get_entity_metadata(entity='campaign')`, enabled campaigns, `budgetUsageDateStart` = `budgetUsageDateEnd` = today, `budgetUsage` in `select` with `campaignName`, `amazonCampaignId`, `dailyBudget`, `budgetType`, `aiGroupId`, `campaignType` |
| Today's changes | `get_operation_log`, today, one entity per query: `["campaign"]`, `["adGroup"]`, `["productAd"]`, `["target"]`, `["placement"]`, `["portfolio"]`, `["aiGroup"]` (placement adjustments and portfolio caps are not under `["campaign"]`). **Always filter** - an unfiltered bid or budget query also returns the hourly AI / dayparting rows (tens of millions on a large store) and truncates: status queries with `actionType` `Paused` / `Enabled`; campaign budgets with `changeField: dailyBudget` (never `currentBudget`, the AI's hourly allocation); bids with `changeField: bid`; out-of-budget with `operationType: Campaign Out of Budget`; placement and portfolio-cap queries by their entity - the same shapes as the reset's `restore-list.md` section 1. If a query still truncates, split the day into hour ranges by timestamp; never report a partial list as complete. Keep status changes (`Paused`, `Enabled`), **budget changes in both directions** (a raise is needed for "budget added to a product low on stock" and for money moved between campaigns - SKILL.md Step 3), **bid changes in both directions** (a cut can explain lost traffic, a raise on a low-stock product spends stock; the rest are shown as counts, SKILL.md Step 3 says which to ask about), placement and portfolio-cap changes; and `Campaign Out of Budget` events - counting only `newValue` `CAMPAIGN_OUT_OF_BUDGET` as the campaign's own budget, while `PORTFOLIO_OUT_OF_BUDGET` means its portfolio cap ran out. **Drop this plan's own writes first** (rows that match a `written` change-log row - prep `change-log.md`, Rules); they are not someone else's change. SP/SB managed-group (`aiGroup`) rows are timestamped in **UTC** - convert with the store's timezone before deciding what happened "today" (query one extra day to cover the offset). SD group rows use an undocumented server clock: query a day either side and, for a row near midnight, say "today or yesterday" rather than guessing |
| Stock | `get_entity_metadata(entity='asin')` for advertised ASINs (or the prep log's flagged ones): `asinFbaQuantity`, `asinFbmQuantity`, `asinInventoryDetail`, `asinDayAvailability30` |
| Managed groups and schedules | `get_entity_metadata(entity='aiGroup')`, then `entity='aiGroup_schedule'` (one group and one profile per call) for every in-scope SP/SB group with a schedule in effect today - the log's schedule rows below say which, and every in-scope group the log does not cover is read to find out. The schedule read is the only source of the target in effect and of budget by performance (`aiActionSettings.budgetOptimization`: `budgetDynamicStatus` / `numType` / `num` / `budgetRedistributeStatus`, `moves.md` section 4). **Read once a day**: the first regular check of the store day reads them and stores a schedule snapshot with the change log it hands back (the `schedule_snapshot` sheet, or the companion CSV - columns in prep `change-log.md` Rules). Later checks the same day reuse that snapshot and re-read a group only when today's operation log shows a schedule or group change for it since the snapshot, this skill wrote to that group, the snapshot is missing, or the user says the platform settings changed. Every write still re-reads its object first (the stale check), so reuse never weakens a write. The prep change log gives only the **confirmed target**: schedule rows (`objectType` `schedule`) with `field` = `acos`, `valuePlanned` = the target, one row per `phase`, `scheduleWindow` = start-end, `status` `planned` / `written`; the row whose `scheduleWindow` covers today is the phase in effect. Head groups are those with `groupClass: head` on these rows. Many groups: batches by spend; on `rate_limited` wait `retryAfterSeconds` (reads are about 120 calls a minute per tool) and say which groups were not read. A schedule is **in effect** when today is inside its fixed window |
| Target level, when asked | Event days so far: `get_ads_perf`, `factEntity: target` (daily). Today by hour for SP keywords: `factEntity: keywordPlacement` (SP only, 7-day cap, restricted metrics) |

Classify who made a change the way the reset skill does: an email or `Manual` is a person;
`Amazon Console` is Amazon's side, author unknown; `AI` and the rule sources are automation.

### Yesterday review - anomaly selection

Compare yesterday with the **daily average** of the baseline days (the table above: the seven
days before yesterday, or the seven normal days before the warm-up when yesterday was an event
day). Never average daily ACOS, CPC or CVR: sum the days first, then calculate each rate.

**Take the store's own lift out first.** On an event day every campaign spends far above a
normal day, so the raw change makes every campaign an "anomaly". Expected yesterday for a
campaign = its baseline daily value x the store's lift (yesterday's store spend / the baseline's
store daily spend; the same with sales). Rank material campaign changes by how far yesterday
sits from that expectation in money (spend or sales), then by efficiency; do not surface tiny
percentage swings on low volume.

**Yesterday's orders, sales and ACOS are provisional** - they keep being attributed for days
(longer on Vendor profiles), so yesterday's ACOS reads high. Label them "provisional", and do
not call a campaign a loser on yesterday's ACOS alone; spend, clicks, CPC and budget usage are
final. Keep at most five rows and attach the most direct
evidence available: budget ran out, budget/bid/status changed, CPC moved, CVR moved, or stock is
short. If the cause is not established, say "needs checking" rather than inventing one.

End with at most three priorities for today: protect a winner that ran out, contain a material
loser, resolve a stock or delivery blocker, or check a large unexplained change. This section is
generated once per store day and does not itself authorize a write.

**Once per day, within what MCP can keep.** Later checks in the same conversation reuse it. MCP
keeps nothing between conversations: a new conversation later the same day asks once whether
the user still needs it - regenerate it on yes (one more pull), otherwise leave it out and say
so.

## 3. The normal-day curve

Use the 7 normal days before the warm-up started (the "normal-day curve" pull above), not the
six days before today: during the event those are event days and give no baseline. Only if that
pull has no data, fall back to the six days before today and say the curve is an event-day
curve.

- `share(x)` = average over those days of (spend from 00:00 through hour `x`) / (that day's
  spend). This is the share of a day's spend normally gone by hour `x`.
- Normal spend by hour `x` = average daily spend of those days x `share(x)`.

## 4. Store pace

With `x` = the latest hour that ended at least 2 hours ago (section 1) - never the hour still
running, which reads the pace backwards:

| Number | Formula |
|---|---|
| Spend so far | today's spend through hour `x` |
| Ratio to normal | spend so far / normal spend by hour `x` |
| Projected day | spend so far / `share(x)` |

The curve gives the **shape** of a day. On an event day judge pace against **today's expected
spend** - `todayBudget` (SKILL.md Step 1): projected day / `todayBudget`. Then compare the projected day with
`todayBudget`: above it -> say when it would reach the
total; well below it (under 70%) -> there is room for the "push" moves.

Do not project before 08:00, or when `share(x)` is under 10% - too little of the day has passed.

## 5. Campaign run-out hour

For a campaign with a daily budget:

1. **Remaining** = `budgetUsage.remainingBudget` (against `budgetSnapshot`, which on a managed
   campaign is the AI's current allocation, not `dailyBudget`). If `budgetStatus` is
   `outOfBudget`, it has run out - read `lastOutOfBudgetTime` for when.
2. **Rate** = the campaign's spend per hour over its last 3 hours with data.
3. **Run-out hour** = the time of `usageUpdatedTime` + remaining / rate.

Mark it as an estimate. When the result is past midnight, say "will not run out today" rather
than a time. Skip it when `budgetUsage` is null (unavailable - never 0%; then compare today's
projected spend with `dailyBudget` instead), when usage is under about 5% (the snapshot may not
have refreshed yet), when the rate is 0, and for lifetime budgets (`budgetType` `lifetime` - remaining is for the budget's
whole life, not the day).

## 6. States

**Mostly managed?** If about 80% or more of the in-scope spend is in groups with AI running,
lead with the group states (section 7) and skip only the campaigns in those running groups
(state 2) - their rows would all read "managed". Every other campaign (outside groups, or in a
group with AI off) still gets its state: the remaining spend can be hundreds of campaigns with
burning ones and winners running out among them. Say how many were judged each way.

Per campaign, for today. Two lines, both percent ACOS (a ROAS `r` is ACOS `100 / r`):

| Line | What it is | Used for |
|---|---|---|
| **Limit** | The user's hard ACOS limit - for a campaign the change log marks `brandClass: nonBrand`, the `nonBrandLimit` when one was given; else the prep ceiling (`ceilingAcos` in the change log); else, with neither, the **store's** ACOS over the 60 days before warm-up x 1.25 for "maximum sales" or x 1.00 for "profitable" / no goal given - prep's no-target rule. Never a campaign's own ACOS: that would let a campaign that always loses money pass. Say which was used | "Clearly over the limit" (state 6, at 1.3x the limit), cuts, and the cap on any target **the monitor loosens**. A schedule target the user confirmed in prep (the change log's schedule rows, section 2) is **not** capped by it: prep caps schedule targets with the hard limit only (and floor ACOS under "profitable"; `sparkx-promo-prep` push-plan section 6), so a confirmed target above this limit is not a breach, and no goal steps it back toward the limit on that ground |
| **Raise line** (`raiseAcos`) | The prep log's `raiseAcos` for this campaign (a running managed group: section 7) - min(target, floor, hard limit), prep `push-plan.md` section 2; for a `brandClass: nonBrand` campaign, `nonBrandRaiseAcos` when the log has it (else min(`raiseAcos`, `nonBrandLimit`)). Without a prep log: the same formula on the user's answers; with no target and no floor, the limit | Every raise: states 9-11, budget and bid raises, top of search, group totals, tomorrow's recomputed budgets |
| **Floor** (`holdUpperAcos`) | The prep log's `holdUpperAcos` - min(floor ACOS, hard limit), floor ACOS as prep defines it (margin, else the user's minimum ROAS, else the hard limit; prep `push-plan.md` section 2); for a `brandClass: nonBrand` campaign `nonBrandHoldUpperAcos` (else min(`holdUpperAcos`, `nonBrandLimit`)). Without it: none | State 8's `watchReason: "overFloor"` - held but losing money |

The raise line is never above the limit. **The limit keeps a 1.3x margin on event days**:
today's ACOS is provisional (section 1), so state 6 (clearly over the limit) is the only state
that leads to a cut for ACOS. Prep lists a campaign over the user's hard limit before the event;
on event days it is cut only once it is clearly over the limit.

**One state per campaign.** Checked in this order - the first that applies wins. The key in
brackets is the `state` value in the structured report; there is no other state value.
Every rule that uses orders or ACOS uses **settled** figures - settled clicks, settled orders,
settled ACOS = settled spend / settled sales (section 1 and below) - never today's full-day
totals. Only state 3 counts all of today's clicks.

| # | State (`state`) | Rule | What happens |
|---|---|---|---|
| 1 | Left alone (`leftAlone`) | On the user's leave-alone list (whole-word match on the name, so "PD" never matches an ASIN) | Never written |
| 2 | Managed (`managed`) | In a running managed group (`aiGroupId` set and the group's `aiStatus` is `1`) | Judged at group level, section 7 |
| 3 | Too few clicks (`tooFewClicks`) | Under 20 clicks today | Not judged. If its settled ACOS is already over the limit, add `watchReason: "overLimit"` and put it on the watch list |
| 4 | Burning (`burning`) | 30+ settled clicks, no settled order, and half its budget or more already gone | Cut (`moves.md`), even before 10:00 |
| 5 | Spending, not converting (`notConverting`) | 20+ settled clicks, no settled order | Slow-down moves |
| 6 | Clearly over the limit (`clearlyOverLimit`) | 20+ settled clicks, settled ACOS over 1.3x the limit | The only ACOS state that leads to a cut |
| 7 | Over the limit, watching (`overLimitWatching`) | Settled ACOS over the limit, not state 6: at or under 1.3x the limit, or over it on under 20 settled clicks (today has 20+ clicks - fewer is state 3 with `watchReason: "overLimit"`) | No raise, no cut yet. Watch list with the settled ACOS, the limit and the 1.3x mark |
| 8 | Held (`held`) | Settled ACOS over the raise line, at or under the limit | No raise, no cut. If the settled ACOS is also over `holdUpperAcos` (it loses money but is still inside the limit), add `watchReason: "overFloor"`: under "slow down" or "stay inside the limit" it may get one budget step down with the user's yes (guard 3 applies) |
| 9 | Winner, running out (`winnerRunningOut`) | 2+ settled orders, settled ACOS at or under the raise line, and out of budget now or run-out hour before 21:00 | Push moves |
| 10 | Selling, under-spending (`underSpending`) | Settled ACOS at or under the raise line and projected to use under half its budget (with `budgetUsage` null: projected spend / `dailyBudget`) | Push moves (bids, top of search - not budget) |
| 11 | Selling, on pace (`onPace`) | Settled ACOS at or under the raise line | Push moves |
| 12 | Mixed - keep watching (`mixed`) | None of the above - in practice 20+ clicks today but no settled ACOS yet (no settled sale, and under 20 settled clicks) | No move; check again |

A rate on under 100 clicks is shown with a "low volume" note and never called good or bad on its
own. Recompute every ACOS from summed spend and sales.

**Settled means settled - never judge states 4-12, or state 3's `watchReason`, on today's
full-day totals.** Orders for the
last hours are still arriving, so a full-day ACOS marks far too many campaigns "clearly over the limit"
(a trial on a 2,288-campaign store flagged about 200 that way). Take the per-campaign figures
summed over the settled hours only. The light way to get them: one `get_ads_perf` call for
today, `factEntity: campaign`, `timeGranularity: hourly`, `select: ["campaign.campaignId_"]`
only (no `date` / `hour`), `filters: {"hour": {"<=": <last settled hour>}, "Spend": {">": 0}}`,
ordered by spend - it returns **one row per campaign** with its settled totals (in the trial,
3 pages of 500 covered the 804 main campaigns). If the scope is still too large, narrow it with
the user (SKILL.md Step 1). Until settled per-campaign
figures exist, report "clearly over the limit" as a watch item, never as a move.

## 7. Managed groups

Sum each running group's campaigns.

**A group's raise line**: while a schedule is in effect, min(the schedule's target in effect,
floor ACOS, the limit (section 6)) - leaving out any that does not exist; with no schedule in
effect, prep's `raiseAcos` for the group (section 6). "Short of budget" and every group-total
raise use it. A confirmed schedule target above the limit stays not a breach (section 6), but
the group raises nothing above the limit.

| Group state | Rule |
|---|---|
| Short of budget | Its campaigns ran out of budget today (out-of-budget events, or `budgetStatus` `outOfBudget`) and the group's settled ACOS is at or under the group's raise line (above) |
| Over its target | Settled ACOS over 1.3x the target in effect (the schedule's target if a schedule is in effect, else the group's) with 20+ settled clicks |
| On track | Otherwise |

The group's own AI moves bids and budget between its campaigns; this skill only changes the
group's total budget and the target in effect (see `moves.md`).

## 8. Stock at today's pace

For each advertised ASIN with stock data:

- Today's sales lift `Lt` = today's ad sales so far / normal ad sales by the same hour (from the
  curve, using sales instead of spend). If it cannot be computed, use the prep lift.
- Days of cover at today's pace = `asinDayAvailability30 / Lt`.
- **Stock is refreshed once a day**, so during the day it does not move while the event sells
  fast. Take off the part of today already sold: cover left = cover at today's pace -
  `share(x)` (section 3; use the sales curve). Show the result, not a caveat; word the
  daily figure as prep's `own-stock.md` ("How to say it") does.
- **A sell-out shows up before the stock does.** If an ASIN's ads stop spending in the middle of
  the day while its campaigns still have budget, it may have sold out since the refresh -
  Amazon normally stops ads for a product that cannot be bought. Say so as a lead and check
  the next refresh.
- Flag when cover left is shorter than the event days left (including today). Show `inbound` from
  `asinInventoryDetail` as context - it has no arrival date.
