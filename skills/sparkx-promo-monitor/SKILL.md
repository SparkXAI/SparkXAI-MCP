---
name: sparkx-promo-monitor
description: >-
  During a promotion (Black Friday / Cyber Monday, Prime Day, Prime Big Deal Days, holiday
  events, a brand's own deal), check how the ads are doing right now - spend pace against a
  normal day, which campaigns will run out of budget before the evening peak, which are
  spending without orders or running over the ACOS limit, stock running low, anything paused
  or changed today - and pivot in small capped steps: push winners, slow down losers, push
  specific ASINs, or stay inside a limit; also answers event-day questions like "can I pause
  these targets now?" and "this ASIN restocks next week - keep spending or add budget?". Use
  when the user says "大促期间帮我盯一下", "现在预算够不够要不要加", "黑五今天跑得怎么样",
  "这几个定向现在能停吗", "库存下周才到还能加预算吗", "how is Prime Day going". Not for preparing
  before the event (use sparkx-promo-prep), not for restoring afterwards (use
  sparkx-promo-reset), and not for ordinary days (use sparkx-edit-ads / ad-hoc analysis).
metadata:
  version: 1.0.0
---

# Promo Monitor (大促中盯盘)

## Scope: an orchestration skill

This skill has no MCP tool of its own. It reads with three tools and writes with two existing
skills:

| Step | Tool | Owning skill |
|---|---|---|
| Today by hour, keyword x placement by hour, event days so far | `get_ads_perf` | [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md) |
| Budget usage now, groups, schedules, stock, current values | `get_entity_metadata` | [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md) |
| What changed today, out-of-budget events | `get_operation_log` | [sparkx-query-operation-log](../sparkx-query-operation-log/SKILL.md) |
| Group target / budget, schedule changes | `save_sp_sb_ai_group_schedule` / `save_sp_sb_ai_managed_group` / `edit_sd_ai_managed_group` | [sparkx-edit-ai-group](../sparkx-edit-ai-group/SKILL.md) |
| Budgets, bids, placements, status | `batch_update_ads` | [sparkx-edit-ads](../sparkx-edit-ads/SKILL.md) |

> **Dependency - install all five skills above alongside this one** (and `sparkx-promo-prep`,
> whose `references/change-log.md` defines the change log this skill reads and appends to). Skills install as
> sibling directories under your agent's skills root (`.claude/skills/<name>/` for Claude
> Code; see the installation notes in [README](../README.md)); the `../sparkx-.../` links in
> this file resolve against it. Every write goes through the owning write skill's rules - its
> confirmation protocol, its payload contract, its read-back. This file does not repeat them
> and does not relax them.
>
> **Read each owning skill when its step comes, not all up front**: a query skill (only the
> sections for the query at hand) when you pull that data; the write skills only when you reach
> the preview and the writes.

Auth, error envelopes, pagination, date limits and currency rules are in the base skills'
`references/platform-notes.md`. The points that matter most on an event day:

- **Hourly data is about two hours behind and keeps changing.** First data for an hour appears
  roughly two hours after it ends; orders keep being attributed to earlier hours for days. The
  last hours always look worse on ACOS. See the ads-performance skill's "Hourly / AMS Data".
- **Budget usage moves in steps.** `currentBudgetUsagePercentage` only updates after another
  ~5% of the budget is spent - always quote `usageUpdatedTime` with it. See the entity-metadata
  skill's `budget-usage.md`.
- **Use the store's clock.** Today's date and the current hour come from the store's `timezone`
  (`get_user_authorized_context`), not the machine's - the machine can be a day ahead.

| Reference | Read it when |
|---|---|
| [`references/pace-and-states.md`](references/pace-and-states.md) | Step 2-3: the pulls, the normal-day curve, run-out time, campaign states and their thresholds |
| [`references/moves.md`](references/moves.md) | Step 4: what each goal changes, step sizes, guards, managed groups, the pause and stock questions |
| [`references/example-and-report.md`](references/example-and-report.md) | A full worked conversation; the `structured_report` JSON shape |
| [`references/html-report.md`](references/html-report.md) | Optional customer-facing HTML report; read only when a downloadable, shareable or print-ready report is needed |
| [`references/error-handling.md`](references/error-handling.md) | A write is refused, data is missing, or an answer does not fit the normal flow |

## Output language

The examples (`references/example-and-report.md`) are in Chinese because most customers are. They show structure, not text to
copy: answer in the user's language, and pass `language` to `get_ads_perf` to match.

Default to the Markdown report in chat. If the user asks for a report to download, share, print
or send to a customer, or the detailed tables are too long to scan comfortably in chat, also
create the static HTML report in [`references/html-report.md`](references/html-report.md). The
chat summary and every write confirmation remain in chat; an HTML file never counts as approval.

### Trial and demo documents

When the user asks for a trial run, demo, CSM handoff or example customer deliverable, run this
current workflow again against the data available now and render the resulting
`structured_report`. Do not relabel, restyle or carry forward result tables from an older trial.
An older document may provide the scenario only; re-query every displayed account value and
recompute every recommendation under the current rules. Mark simulated customer answers and
assumptions separately from queried facts, and include the run time, store, scope and data
windows. Trial mode is read-only unless the user separately confirms writes. If the current
workflow stops because today is outside the event window, required answers are missing or data
is unavailable, show that real boundary and next step; never invent event-day results to make
the document look complete. Markdown, HTML and any external document must all come from the same
current-run `structured_report`.

**Words to the customer.** Say "no orders yet", "below target", "lower", "room to gain
traffic"; never "burning", "waste", "worst" or "cut". The state **Burning** keeps its name inside
this skill and is shown as "spending, no orders yet". Lead with what is working, then the
problem with its numbers, then the moves already prepared.

## What it does, in one paragraph

On an event day the questions come every few hours: is the budget going to last until the
evening, which campaigns are selling and starving, which are burning money, is something paused
that should not be, can I stop these targets, can I keep spending on a product that is running
out. This skill reads the store's hourly curve and current budget usage, compares them with a
normal day, puts every campaign into a state, and proposes small, capped moves that fit the
goal the user picks right now - each with its numbers. Nothing is written until the user
confirms, and every change goes into the promo change log so the reset after the event finds it.

## Principles

1. **Ask what the user wants now.** Push, slow down, push specific products, or stay inside a
   limit - the same numbers lead to different moves.
2. **Small steps, several times a day.** Budgets +/-30%, bids +/-15%, top of search +/-25 points
   per check. Run again in a few hours rather than make one big move on provisional data.
3. **Don't judge what has not settled.** Hours less than three hours old are provisional; fewer
   than 20 clicks today is not judged.
4. **Managed groups get group or schedule settings, never fixed bids or budgets on their
   campaigns.** While a schedule is in effect, change its goal and target ACOS on the schedule, not on the group
   (extra money is still the group's total budget - a schedule has none).
5. **Never exceed today's budget (and, with a window total, what is left of it) or a hard
   ACOS / ROAS limit.** No cuts before 10:00 or on
   the last event day unless a campaign is burning money - or the user approves the cuts needed
   to stay inside their budget, stock protection (on the last event day only when the stock
   would run out before the event ends today), or a pause the user explicitly asks for - each
   with the user's yes (`references/moves.md` guard 3). No budget is ever cut below today's spend.
6. **Every write is logged** in the promo change log, so the reset can bring it back.

## Workflow

**Terms, as in prep.** **Event days** (the window) = the warm-up start to the event end - every
one of them is monitored, warm-up days included. **Sale days** = the event start to the event
end only. Without a warm-up the two are the same.

**The first regular check of the day** = the first check at or after 08:00 store time. The
00:05-00:30 day-switch check never counts: yesterday's last hours are not in yet and today has
no data, so it only writes the planned budget decreases and any planned raises the user chose
to defer past midnight (`references/moves.md` section 1).
Everything this file ties to "the first check of the day" - fixing `todayBudget`, the brand
check, the morning raise, the catch-up of missed rows, yesterday's review - runs at the first
regular check.

### Step 1 - Context and questions. STOP until answered.

1. Resolve the store (`get_user_authorized_context`; one `profileId` per run). Compute **today's
   store date and current hour** from its `timezone`.
2. **Use the prep change log if the user has it** ([`../sparkx-promo-prep/references/change-log.md`](../sparkx-promo-prep/references/change-log.md)):
   it carries the event, the window, the event budget and its mode (`budgetMode`: a daily cap or
   a total for the window) with the day roles, the goal, the hard limit, the deal and
   leave-alone lists, the brand names and the scope chosen in prep, and the `planned` per-campaign,
   per-day budget rows (`targetDate`) that the 21:00 check writes from (rows for today still
   `planned` mean a check was missed - write them first, `moves.md` section 1). Confirm them in one line instead of asking
   again. Without it, ask for the event dates first, then the event budget (a cap for every day,
   or a total for the window) and any hard limit - and **start a change log in the prep format**
   (`../sparkx-promo-prep/references/change-log.md`) at the first write: the plan columns from
   the user's answers (`skill = promo-monitor`), and for each object written its `valueBefore`
   read right before the write. That first `valueBefore` is the pre-promo value the cut floor
   (`moves.md` section 1) and the reset use; MCP keeps nothing between conversations, so hand
   the file back after every write and ask for it at the next check.
   **Today's budget** (`todayBudget`): the prep log's `dayBudget` for today; without day roles,
   the daily cap, or for a window total, (total - spent **through yesterday**) / the event days
   left including today - never the remaining after today's spend, which would shrink today's
   budget as today spends (total $10,000 over 2 days, $3,000 spent by 13:00 on day 1: today's
   budget is $5,000, not $3,500); capped by the daily cap if the user also gave one. Fix it at
   the first regular check of the day (below). The window total covers every event day, warm-up included, so
   "spent through yesterday" and **window spent** both count from the **warm-up start** (the
   event start only when there is no warm-up): window spent = a daily pull from that day to
   yesterday plus today's spend so far (`pace-and-states.md` section 2), and **window
   remaining** = total - window spent.
   **Large account and no scope yet** (roughly 500+ enabled campaigns): say how many campaigns
   there are and let the user choose - the whole store, the main campaigns (as prep defines
   them: 80% of the last 14 days' spend; with a prep log, reuse its list), or the products /
   campaigns they name. Store-level pace and
   today's changes always cover the whole store; campaign states, moves and target questions
   stay inside the chosen scope. Never narrow it on your own.
   **Stock**: the platform's figure refreshes once a day; on an event day invite the customer's
   own, more current source (ERP / inventory export, a sheet, a connected inventory tool), worded
   as a way to sharpen the call, not as a shortcoming, and use it first - see [`../sparkx-promo-prep/references/own-stock.md`](../sparkx-promo-prep/references/own-stock.md).
3. **Is today an event day?** With the window known (from the log or the user's answer): if
   today is before the warm-up start or after the event end, **stop the event monitor**. Say
   the date is outside the window; a plain snapshot of today's spend and ACOS is fine, but no
   event pace, no event-budget, bid or schedule moves. Before the event, point to
   `sparkx-promo-prep`; after it, to `sparkx-promo-reset`. Warm-up days count as inside. Only inside the
   window go on.
4. **Read the user's message first and ask only what it leaves open** - multiple choice, at most
   4 questions, options carrying today's numbers, the recommended one first. Later checks the
   same day reuse the answers and do not ask again unless something changed:

| Question | Options |
|---|---|
| **What do you want right now?** (can pick several) | Push harder where it works / Slow down, protect the budget / Push specific ASINs (name them) / Push a category (name it) / Cut today's spend by an amount (name it) / Stay inside my limit (name it) |
| **Has today's total budget changed?** | No / a new number |
| **Anything changed since the last check?** | Something selling out, a deal ended early, a listing problem - in their words |

"Push" and "slow down" together: slow down wins. An unanswered question is not a zero - say what
was not answered and act on that: no total means raises are capped at the prep total, or not
made if there is none.

If the user only asked a narrow question ("can I pause these targets?", "can I add budget to
this ASIN?"), answer that one with the matching section of
[`references/moves.md`](references/moves.md) and offer the full check after.

### Step 2 - Read the store now

Full pulls and formulas: [`references/pace-and-states.md`](references/pace-and-states.md).

1. **Today by hour**: the store's hourly spend for the pace, and per campaign today only (settled
   totals, and the last 3 hours for run-out). The normal-day curve comes once per event from the
   7 days before the warm-up, at store level.
   At the **first regular check of each store day only** (at or after 08:00 - never the
   00:05-00:30 day-switch check, when yesterday is not complete yet), also read yesterday and a
   seven-day baseline for the morning review (during the event: the seven normal days before the
   warm-up): store totals plus the campaigns needed to explain the five largest material changes.
   Later checks in the same conversation reuse it (`references/pace-and-states.md` section 2).
2. **Budget usage now** for every enabled campaign: status, remaining budget, last time out of
   budget, update time.
3. **Today's operation log**: pauses, budget and bid changes, out-of-budget events - by a
   person, by Amazon's side, by AI.
4. **Stock** for the advertised ASINs (sellers only).
5. **Managed groups**: which have a schedule in effect today, and - read from each such schedule,
   not only the change log - its target and budget by performance (read once a day; later checks
   the same day reuse the day's snapshot - `references/pace-and-states.md` section 2).

Then compute the **store pace** (spend so far vs a normal day at the same hour, and the projected
day total vs the budget) and each campaign's **projected run-out hour**.

At the first regular check, begin the customer report with **Yesterday's review / Today's focus**
(at the top, right after the header): yesterday vs the baseline's daily average - labelled with
its dates, "the 7 days before yesterday" or "the 7 normal days before the warm-up" - for spend, sales, orders, CPC, CVR, ACOS and
budget usage (orders, sales and ACOS marked provisional); the top five material campaign
anomalies, measured against the store's own lift so the event itself is not the anomaly, with a
likely cause and an action; then three priorities for today. Recompute rates from sums. This is a compact morning section, not a
second full campaign report.

### Step 3 - Put every campaign into a state

Checked in this order, the first that applies wins (defaults; exact rules in
`pace-and-states.md` section 6):

Every campaign gets exactly one state. All orders and ACOS below are **settled** figures; only
"too few clicks" counts all of today's clicks.

| State | When |
|---|---|
| **Left alone** | On the user's leave-alone list |
| **Managed** | In a running managed group - judged as a group |
| **Too few clicks** | Under 20 clicks today - not judged; if its settled ACOS is already over the limit it goes on the watch list (`watchReason: overLimit`) |
| **Burning** | 30+ settled clicks, no order, half its budget or more gone |
| **Spending, not converting** | 20+ settled clicks, no order |
| **Clearly over the limit** | 20+ settled clicks, settled ACOS over 1.3x the limit - the only ACOS state that leads to a cut |
| **Over the limit, watching** | Settled ACOS over the limit but not clearly over: at or under 1.3x, or 20+ clicks today but under 20 of them settled - no raise, no cut yet |
| **Held** | Settled ACOS over the raise line, at or under the limit - no raise, no cut (over prep's `holdUpperAcos`: flagged `overFloor`, a step down is offered under "slow down") |
| **Winner, running out** | 2+ settled orders, ACOS at or under the raise line, and out of budget now or projected to run out before 21:00 |
| **Selling, under-spending** | ACOS at or under the raise line, projected to use under half its budget |
| **Selling, on pace** | ACOS at or under the raise line |
| **Mixed - keep watching** | None of the above - in practice no settled ACOS yet |

Two lines, both percent ACOS (`pace-and-states.md` section 6): the **limit** (hard limit - the
non-brand limit on non-brand campaigns - else prep's `ceilingAcos`, else the store-level
fallback; never a campaign's own ACOS) decides "clearly over the limit" (1.3x, settled) and
cuts; the **raise line** (prep's `raiseAcos` = min(target, floor, hard limit); for a managed group
while a schedule is in effect, `pace-and-states.md` section 7) decides every raise. A held campaign over prep's `holdUpperAcos` loses money: it is flagged `overFloor`.

Put the **today's changes** first - a pause on something that was selling, or a budget cut, is
often the biggest single cause of a bad event day. Leave out this plan's own writes (prep's and
earlier checks' - they match `written` rows of the change log, prep `change-log.md` Rules) - and
**ask only about the big ones**:

- a campaign paused that had spent $50 or more today;
- budget or bids raised on a product low on stock;
- a budget change, up or down, of $100 or more **and** 30% or more;
- bids cut by 30% or more in a campaign with orders today;
- money moved between campaigns of the same ASIN (one down, one up at the same time - one pair,
  one question).

At most 3 questions (an ASIN's keyword and product-target campaigns are one question). With
more, first offer "keep them all (recommended) / ask about the big ones only / let the check
decide". Smaller changes are kept as they are and listed in the report notes with who made them
(a person / Amazon's side / AI). Never undo any of them; a question answered today is not asked
again today.

### Step 4 - Propose moves

Rules, step sizes and guards: [`references/moves.md`](references/moves.md). Summary:

- **Push**: more budget for winners running out; +15% on proven targets; more top of search where
  it pays - all only at or under the raise line. Managed groups: a larger group total (group at or
  under its raise line and spending close to its effective total; none while that total is
  unknown - `references/moves.md` section 4); a looser target on the schedule if the group converts well under its
  target in effect, never above the limit (the hard limit, else prep's ceiling - the same limit
  as the campaign states).
- **Slow down**: smaller budgets where it does not convert (never below today's spend, so it keeps
  serving, and never below the pre-promo budget without the user's own yes); -15% on targets spending without orders; half the top-of-search boost (never on brand
  campaigns). Managed groups: a tighter target on the schedule.
- **Push ASINs**: the push applied to campaigns where those ASINs are at least half the
  advertised products.
- **Stay inside the limit**: move money from campaigns clearly over the limit to winners at or under the
  raise line.
- **Guards**: no raise for low-stock products; raises scaled so the day stays inside the total;
  no cuts before 10:00 or on the last event day unless a campaign is burning money (30+ clicks,
  no order, half its budget gone) or guard 3 makes an exception
  (the user's budget, stock protection).
- **Stock protection**: when confirmed sellable stock will not last until the next replenishment
  or the event end, first protect brand and proven exact traffic, then offer budget and bid cuts
  on broad/category/competitor traffic - campaign-level cuts only outside running managed groups;
  inside one, offer group-level protection (a tighter target, a lower group total) instead
  (`references/moves.md` section 6). Budget cuts always require the user's confirmation; they
  never go below today's spend (a budget below it stops the campaign silently - to stop spend,
  offer a pause), and go below the pre-promo budget only with the user's explicit yes. Guard 3
  may be set aside for it, group-level protection included, with the user's yes - on the last
  event day only when the stock would run out before the event ends today (`references/moves.md`
  guard 3).

### Step 5 - Preview, write, log

1. **Show the snapshot and the moves** (output template), the moves in **batches** the user
   approves or skips one by one: budget up / bids up / top of search / budget down / spending
   with no orders yet / money for a pushed category. Batches that lower anything are not
   preselected. A batch with many rows leads with its **core rows** - the fewest rows that make
   80% of its money - so the user can approve just those. Rows that need judgement - a pause, a
   group total change, anything on a stock-flagged product - need their own yes.
2. **Write** in this order, each through its owning skill and its confirmation rules: schedule
   and group settings (`sparkx-edit-ai-group`) -> budgets -> bids -> placements -> statuses
   (`sparkx-edit-ads`). Split batches by `campaignType`; stay under the write skills' caps.
3. **Read back** every write and append it to the promo change log (`skill = promo-monitor`,
   `valueBefore` read right before the write, `logField`). When the write came from a `planned`
   day-role row, set that row to `fulfilled` (or `skipped`, with the reason, if a different value
   was written) in the same update - otherwise the next check's catch-up writes it again. Hand
   the file back. Then fill the "Executed and
   not executed" table: every proposed move is shown there as written, failed, needs read-back,
   needs review (`references/moves.md` section 4) or not written, with the reason (waiting for a yes, a guard, declined, changed by someone else).
4. **Say when to check again** (for example 10:00, 14:00, 18:00, 21:00 store time; plus a
   day-switch check at 00:05-00:30 when tomorrow's role is lower than today's or the user
   deferred planned raises past midnight - `moves.md` section 1) and that
   `sparkx-promo-reset` brings everything back after the event.

A waiver such as "apply the ready ones without asking" follows the owning write skill's waiver
rules exactly - the scope is what the user said, and the verification still runs.

## Example

A full worked conversation is in [`references/example-and-report.md`](references/example-and-report.md).

## Output templates

### markdown

```markdown
# 大促中盯盘 · {店铺} · {大促} 第 {k}/{n} 天
**现在**：{date} {hh:mm}（{时区}）· 花费数据到 {latestDataHour}:59，订单已稳定到 {settledThroughHour}:59　**现在的目标**：{冲量 / 放慢 / 推指定 ASIN / 守住上限}　**今天的预算**：{todayBudget}（{每天上限 / 整个大促总额：已花 {spent}，还剩 {remaining}}）　**上限**：{ACOS / ROAS，或“未给”}　**范围**：{全店 / 主力活动 / 你指定的商品}

{仅当天第一次常规检查：}
## 昨日复盘 · 今日重点
| 指标 | 昨日 | {昨天之前的 7 天 / 预热前 7 个正常日}（{起}–{止}）日均 | 变化 |
| 异常对象 | 变化 | 可能原因 | 今天怎么做 |
**今日重点**：{最多 3 条}

## 今日投放进度
| | 今天到现在 | 平时同一时段 | 倍数 | 预计全天 | 预算 |
{店铺一行；有用时每个托管组再各一行}
{品牌检查（当天第一次常规检查）：品牌词 CPC {+x%}，品牌词点击占比 {y%}（平时 {z%}），搜索结果顶部 CPC {+w%}——{没有被抢的迹象 / 可能被抢}}

## 托管组
| 托管组 | 状态 | 已稳定的 ACOS | 当前目标（排期 / 托管组） | 总预算（含按表现调预算后的上限） | 几点花完 |

## 计划预算（来自大促前准备）
| 活动 | 日期 | 当天策略、倍数 | 现在 | 计划 | 状态 |

## 今天的改动
| 时间 | 谁 | 做了什么 | 对象 | 改前 → 改后 | 要确认的 |

## 建议调整
| 对象 | 状态 | 现在 | 建议 | 理由 | 需要你确认 |
{按 托管组（排期 / 总预算）→ 预算 → 出价 → 顶部溢价 → 开关 分组}

## 已执行 / 未执行
{在 Step 5.2-5.3 之后填写；写入之前写“还没有写入”，并列出等你确认的项。}
| 对象 | 改前 → 改后（回读） | 结果 | 未执行原因 / 下一步 |
{结果：已写入 / 失败 / 待回读 / 需人工核对（请在平台上修改） / 未写入（等你确认、被保护规则拦下、你不同意、被别人改过）。“建议调整”里的每一行都要出现在这里。}

## 先观察（这次不动）
| 对象 | 状态 | 为什么现在不动 | 什么时候再看 |

## 库存
| ASIN | 按今天速度还能卖几天 | 大促还剩几天 | 在途 | 保护措施（需你确认） | 备注 |

**下次检查**：{time}。大促结束后：运行 sparkx-promo-reset。

---
_生成时间：{timestamp} · 数据源：SparkX AI MCP · Skill: sparkx-promo-monitor v{version}_
```

Name every object by its name (`campaignName`, `aiGroupName`, keyword text), never by an internal
id; an export adds the **Amazon** id column.

### structured_report

The JSON shape is in [`references/example-and-report.md`](references/example-and-report.md).

### optional HTML report

Build it only from the finalized `structured_report`; do not recalculate or reinterpret the
check while rendering. After writes, update the execution table from read-back before handing
over the final file. Follow [`references/html-report.md`](references/html-report.md).

## Data boundaries

- **Hourly data is campaign-level** (all ad types) and keyword x placement (SP only), at most 7
  days per query. There is no hourly ad group, product target or search term data - target-level
  questions use daily data for the event days so far.
- **AI metrics are not available by hour.** Do not report AI vs manual split from hourly rows.
- **Today's ACOS is provisional.** Orders keep arriving for the clicks of earlier hours; the
  limit test uses settled hours and a 1.3x margin for that reason.
- **Budget usage**: a paused campaign still reports `inBudget`; `budgetSnapshot` can differ from
  the configured `dailyBudget` (on managed campaigns by a lot). Quote the snapshot with the
  remaining amount, and the update time with both.
- **Stock is refreshed once a day**, not live - on an event day it does not show what sold
  since the refresh (see `pace-and-states.md` section 8). Sellers with SP-API only; FBA `0` is not a stock-out when a
  merchant-fulfilled offer exists.
- **No scheduling.** Each check is a conversation turn; MCP cannot fire a write at a set hour.

## Error handling

Situation-by-situation handling (a write refused, data missing, an answer that does not fit) is in [`references/error-handling.md`](references/error-handling.md).

## Not covered

- Before the event - use `sparkx-promo-prep`.
- After the event - use `sparkx-promo-reset` (it restores what this skill changed).
- New campaigns, new keywords, negatives in bulk - use `sparkx-create-campaign` /
  `sparkx-edit-ads` if the user asks.
- Sponsored Brands / Display creative, DSP.
