---
name: sparkx-promo-prep
description: >-
  Prepare Amazon Ads for Black Friday, Cyber Monday, Prime Day or another promotion. Check
  stock, budget caps, schedules and delivery blockers; size the plan to the customer's budget;
  propose role-appropriate managed-group schedules (活动冲量 / promotion sales boost only for
  confirmed head groups) plus budget, bid and placement changes outside groups; then preview
  and log confirmed writes. Use for "黑五要来了帮我备战", "Prime Day 前广告该怎么调", "大促前检查一下店铺"
  or "get my ads ready for Black Friday". Use sparkx-promo-monitor during the event and
  sparkx-promo-reset afterwards; use the edit skills for ordinary changes unrelated to a promo.
metadata:
  version: 1.0.0
---

# Promo Prep (大促前准备)

## Scope: an orchestration skill

This skill has no MCP tool of its own. It reads with three tools and writes with two existing
skills:

| Step | Tool | Owning skill |
|---|---|---|
| Baseline performance, reference event, product lines, placements | `get_ads_perf` | [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md) |
| Campaigns, groups, schedules, portfolios, stock, budget usage | `get_entity_metadata` | [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md) |
| Who changed what recently (paused ads, budget cuts) | `get_operation_log` | [sparkx-query-operation-log](../sparkx-query-operation-log/SKILL.md) |
| Event schedules and group settings | `save_sp_sb_ai_group_schedule` / `save_sp_sb_ai_managed_group` / `edit_sd_ai_managed_group` | [sparkx-edit-ai-group](../sparkx-edit-ai-group/SKILL.md) |
| Budgets, bids, placements, portfolio caps | `batch_update_ads` | [sparkx-edit-ads](../sparkx-edit-ads/SKILL.md) |

> **Dependency - install all five skills above alongside this one.** Skills install as
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
`references/platform-notes.md` - read it once from any of the three query skills. The
cross-tool points that matter here:

- **Ids differ by tool.** `get_ads_perf` rows carry Amazon ids; `get_entity_metadata` rows and
  every write use internal ids. Join on the Amazon id (`amazonCampaignId` on campaign
  metadata); write with the internal id.
- **One store per run.** Plans, budgets and the store's clock are per store. Amounts are in the
  store's own currency.

| Reference | Read it when |
|---|---|
| [`references/health-check.md`](references/health-check.md) | Step 2: the pre-event checks - queries, thresholds, what each finding means |
| [`references/push-plan.md`](references/push-plan.md) | Step 3: sizing the push, managed-group schedules, budget / bid / placement rules, timing |
| [`references/own-stock.md`](references/own-stock.md) | The customer has a more current stock source (ERP / inventory export, a sheet, a connected tool) - invite it, read it, use it first |
| [`references/change-log.md`](references/change-log.md) | Step 4: the change log this skill writes and hands to the monitor and reset skills |
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
workflow stops because required answers or data are missing, show that real stop and next step;
never invent later-stage results to make the document look complete. Markdown, HTML and any
external document must all come from the same current-run `structured_report`.

## What it does, in one paragraph

Before a big event most of the work is a checklist people do from memory, a day late: is there
enough stock to last the event, will a portfolio cap or a campaign end date stop spending on
day one, which confirmed head groups should use "活动冲量" (promotion sales boost) without
putting the whole account into that mode, which campaigns already run out of budget on a normal day and will starve on
the event. This skill runs that checklist on the store's own data, then sizes the push to the
money the user will actually allow, and prepares it: **a dated, role-appropriate schedule for
each schedule-eligible SP/SB managed group** (the schedule settings switch themselves off, while bids
are audited after the schedule ends), and
**budget, bid and top-of-search changes for campaigns outside managed groups**, each with the
numbers behind it. Nothing is written until the user confirms, and every write is logged so
the monitor and reset skills can pick up where this one stops.

## Principles

1. **Ask before planning.** The event window, the budget the user allows, the goal and any hard
   ACOS limit change the whole plan (Step 1). Dates and budget are never filled from defaults;
   an unanswered goal or target gets the fallback Step 1 names, said in the plan header.
2. **Check before pushing.** A push into a stock-out, a portfolio cap or a paused ad group
   wastes the event (Step 2). Blockers are reported first.
3. **Managed groups get group settings, never fixed bids or budgets on their campaigns.** The
   AI rewrites those; a dated schedule is the lever, and it ends on its own.
4. **Size the push to the user's money and to what the account can absorb.** Say both numbers.
   A hard ACOS / ROAS limit is a ceiling, never exceeded.
5. **No cuts before the event.** Prep raises, schedules and flags. It does not pause, add
   negatives, lower budgets or lower bids - event traffic needs reach, and a cut is a separate
   decision (on event days, the monitor's).
6. **Every write is logged.** The change log is what the monitor and the reset skill build on.

## Workflow

**Two terms, used the same way here and in the monitor.** **Event days** (the window) = every
day from the warm-up start to the event end - the days the event budget, day roles and the
monitor cover. **Sale days** = the event start to the event end only - the dates of the event
phase of a schedule. Without a warm-up the two are the same. The **eve** is the day before the
event start.

### Step 1 - Ask first. STOP until answered.

Resolve the store first (`get_user_authorized_context`; one `profileId` per run) and note its
`timezone` and seller / vendor type. Then pull the store's daily spend for the last 60 days
(`get_ads_perf`, `factEntity: campaign`, `select: ["date"]`) so the questions can carry
context ("a normal day is about $1,800 of ad spend").

**Large account? Tell the user and let them choose the scope.** Read the size first: the
number of enabled campaigns (`get_entity_metadata(entity='campaign')`, enabled, `pageSize: 1`,
read `meta.total`) and the number of ASINs with ad spend in the last 60 days. Above roughly
**500 enabled campaigns or 200 advertised ASINs**, a full check means many large pulls (budget
usage alone is one page per 500 campaigns). Say the numbers and ask, in the same message as the
questions below, which scope to cover:

- the whole store;
- the campaigns that make up most of the spend (say how many make up 80% of the last 14 days'
  spend, e.g. "312 of 2,288 campaigns");
- specific products, campaigns or brands the user names.

"Main campaigns" always means the campaigns that make up 80% of the last 14 days' spend,
leaving out campaigns whose end date has passed;
record that rule, the date and the campaign ids in the change log. Never narrow the scope on
your own. Whatever is chosen, say it in the plan header and keep every
later step inside it.

Ask, and wait. **Multiple choice, at most 4 questions a round**, every option carrying the
store's own numbers ("a normal day is about $8,200 - 2x is about $16,400?"), the recommended
option first. Read the user's message first and ask only what it leaves open.

**Round 1 - the four questions that shape the plan.** Dates and budget **block**: without them
no plan is built (dates) or nothing is written (budget - three amounts are offered instead).
Goal and target do not block: if they stay unanswered after round 1, the stated fallback is
used and named in the plan header.

| # | Question | What it decides | Not answered |
|---|---|---|---|
| 1 | **Which event and which dates**, and how many warm-up days before it? | The schedule window (the warm-up schedule = the warm-up days), the lead-in, which days the budget is for | **Stop**: "I need the event dates to build the plan" - never guessed |
| 2 | **How much can ads spend per event day, in total?** (a number, or "N times normal") A cap for every day, or a total for the whole window? Optional: the month's total | Push size, and whether quiet days' money can go to the peaks | Three amounts to pick from (`references/push-plan.md` section 1); nothing is written until one is picked |
| 3 | **Goal**: maximum sales / sales but stay profitable? **Any hard limit** - "ACOS no more than 35%", "ROAS at least 3"? | The hard limit caps the schedules' target ACOS; with the target and floor it sets the raise line | Goal "profitable" (the safer one), no hard limit |
| 4 | **Target ACOS (or ROAS) for the event, and your margin** (or a ROAS you will not go below)? Or keep each managed group's own target? | The target and the floor (margin x 100 as an ACOS; else 100 / the ROAS named) - `references/push-plan.md` section 2 | Each managed group's own target for its campaigns; for the rest, the "No target" row of push-plan section 2 - the store's 60-day ACOS x 1.25 for "maximum sales", x 1.00 for "profitable"; no floor |

**Round 2 - optional, asked together after round 1** (each has a default, stated in the plan):

| Question | What it decides | Not answered |
|---|---|---|
| **Deals, coupons, focus products or product lines?** Anything to leave alone (campaigns you set up for the event yourself)? | Where extra money goes first; what is never touched | No deal adjustment; nothing left alone beyond what the health check finds |
| **Your brand names** (and competitors' brands, optional). A separate limit for non-brand terms? | Which searches are defended (brand) and which are pushed in the warm-up (non-brand) | The advertised ASINs' `asinBrand` values (health-check g), shown for confirmation; no non-brand limit |
| **Which past event to learn from?** By default the most recent one (name it with its dates, e.g. "Prime Big Deal Days, Oct 7-8") | The event CPC, how much the account can absorb, how fast stock sells on event days | The most recent one in the data range |
| **Stock you already know about** - something low, or arriving before the event? | Overrides the stock check where the data is a snapshot | The platform's daily snapshot |

Round 2 can go in the same message as the health check's open questions (Step 2) rather than
as a third round.

Rules for the answers:

- **Event dates are the user's or Amazon's, never a guess.** If the user names an event without
  dates, say what you know with its source and ask them to confirm. Never fill the gap with last
  year's dates or a "typical" pattern. Fixed calendar days (Black Friday is the fourth Friday of
  November, Cyber Monday the Monday after) are facts; Amazon's sale window around them is not.
- **An unanswered question is not a zero.** "Not sure" or no reply means *not answered*: say so
  in the plan header and act on it - no event budget means three amounts are offered to pick from, and until the user picks
  nothing is written - no raise, no group-total lift, no schedule; the other fallbacks are the
  "Not answered" column above.
- **Invite their own stock source.** The platform's stock refreshes once a day; if the
  customer has a more current one (ERP / inventory export, a sheet, a connected inventory
  tool), ask them to attach or point to it and use it first - see
  [`references/own-stock.md`](references/own-stock.md).
- **Typed lists from a file are welcome.** If the user has a promo calendar, inventory sheet or
  sales goal sheet, read the ASINs, discounts, dates and stock from it and confirm what you read
  in one short table instead of asking them to type it.

### Step 2 - Health check (read-only)

Full queries and thresholds: [`references/health-check.md`](references/health-check.md).

**Two numbers first.** Check c needs the raise line and each event day's budget, so compute
them now from the Step 1 answers - they do not depend on the plan: the raise line and hold band
(Step 3.2, `references/push-plan.md` section 2) and the day budgets (`dayBudget`, Step 3.1 -
from the user's multiples or last year's event; with neither yet, the reference event's lifts,
labelled provisional). With no event budget given, use normal day x the reference event's spend lift as
a provisional `dayBudget` for check c only, say so, and redo check c once the user picks an
amount. Step 3 shows the day-role table for confirmation and reuses these numbers.

Eight checks, reported in this order, blockers first. Start by saying how much of the in-scope
spend is in managed groups with AI running: at about 80% or more, the plan is group-level and the
campaign-level checks are reported briefly (`references/health-check.md` c, step 0).


| # | Check | Flags |
|---|---|---|
| a | **Stock vs event demand** for every advertised ASIN | Will run out before the event ends -> no push, and say how many days it lasts; low and not arriving in time -> push only the rest |
| b | **Delivery blockers** | Enabled campaigns whose ad groups or product ads are paused, ended campaigns, campaign end dates inside the event, recent pauses on core ASINs |
| c | **Budget ceilings** | Portfolio caps or portfolio end dates that would stop spend on event days; campaigns that already run out of budget on normal days, sorted into the five flags of `references/health-check.md` c (budget-short, fast-spending, hold, over the hard limit, below target) |
| d | **Managed groups** | Each SP/SB group's goal, target ACOS, 30-day actual ACOS, personality and total budget; head-group candidate vs other group; existing schedules and overlaps with the warm-up and event windows; groups with AI off; SD groups (no schedules) |
| e | **Reference event** | The past event the user named, or by default the most recent one inside the data range: spend, CPC and conversion lift vs the two weeks before. Always say which event and which dates were used |
| f | **Product lines** | Spend, sales and ACOS by product line for the last 60 days, and the share of the event push each would get |
| g | **Brand, non-brand, competitor** | Spend share and ROAS of each; signs someone is bidding on the brand; each campaign marked brand / non-brand / mixed |
| h | **Guardrails** | Store budget cap; managed-group bid ranges that would block the planned push, and placement ranges with no room to raise; visible budget-management controls; whether confirmed own-brand terms are protected from automatic negatives. A control not exposed by the read tool is reported as "check in the platform", never as passed |

**Settle the open questions before the plan**, in one round: other people's changes (read in
pairs - `references/health-check.md` b), restock dates, whether the budget is a daily cap or a
total. The user answers each, or marks it "to ask the customer"; the plan uses the answers and
lists only the questions still open.

Present the check as a short list with numbers, then ask whether to build the plan. A blocker is
something only the user can fix (stock, a listing, a portfolio they manage elsewhere) or a
change they must approve; say which.

### Step 3 - Build the plan

Full rules and formulas: [`references/push-plan.md`](references/push-plan.md). In order:

1. **Size the push.** First turn the user's budget into a budget for each event day (`dayBudget`, by `budgetMode` - `references/push-plan.md` section 1); a window total is never one day's budget. Normal day = average daily spend of the last 14 complete days. Push
   multiple = the peak day's budget / normal day. Clicks per main ASIN = the peak day's budget /
   event CPC / the ASINs that make up 80% of ad spend. Tier: **conservative** under 1.5x or under 20 clicks per ASIN;
   **aggressive** at 3x or more **and** 75+ clicks per ASIN; **balanced** in between. A
   "profitable" goal or a hard limit never goes past balanced. Also estimate what the account can
   absorb (`references/push-plan.md` section 1 - the busiest normal day, leaving out the
   reference event and its warm-up, x the event lift) and say plainly when the budget is more
   than it can spend.

   **Then give each event day a role** (warm-up, early-deal, peak, between peaks) and a multiple
   of a normal day - from the user, the store's total sales day by day in the same event last
   year, or - when neither exists - the user's multiple per role, starting from the reference
   event's lifts (its event-day lift, and its warm-up lift for the warm-up; only when the user
   leaves it to you, those two numbers). **Show the table, say where the multiples come
   from, and let the user change them** before any budget is sized
   (`references/push-plan.md` "Day roles").
2. **Set the ceiling and the raise line** (`references/push-plan.md` section 2, every ROAS
   converted to ACOS first). Ceiling: a hard limit is the ceiling. Without one: the target ACOS
   (managed-group target or the user's) +15% for "maximum sales", the target itself for
   "profitable"; with no target, the store's 60-day ACOS +25% / +0%. The ceiling is the default
   target and the monitor's limit; it does not cap schedule targets (Step 3). **Raise line** =
   min(target ACOS, floor ACOS, hard limit) - the only threshold for every budget, bid,
   top-of-search and group-total raise. Over the raise line but within min(floor, hard limit): hold (no raise,
   no cut).
3. **Managed groups (SP/SB, AI running): classify first, then build dated schedules from each
   group's own settings** (`references/push-plan.md` section 6). The user confirms the head
   groups: named groups and groups for named focus ASINs first, if head-eligible (one that is not
   is listed with the reason and stays non-head unless the user, told it, insists); otherwise the
   head-eligible groups inside the top 80% of Group-30 spend (excluded high-spend groups listed
   with the reason; none eligible -> no head group), at most a third of the schedule-eligible groups (none by default with
   only one or two) - the terms and the rule in push-plan section 6 - with their sales, orders
   and ACOS shown. Event phase: head groups use goal `3`; other schedule-eligible groups use goal
   `1` (a group on goal `2` keeps it unless the user says yes to `1`).
   With the goal "profitable" no group uses goal `3` and there are no head groups: every group
   keeps its current goal (goal `1` for a group on goal `3` outside a schedule, flagged), with
   x1.0 for defensive groups (user-named or brand-term-dominated, shown for correction) and x1.2 for the rest (push-plan section 6) - and when that goal
   came from an unanswered question, the plan header says so.
   Target ACOS starts from each group's actual 30-day ACOS and the group's multiplier;
   sparse groups fall back to their current target. **Never below the group's current target**
   (an event target is never tighter than normal), unless that target is already above the hard
   limit, or under "profitable" above the floor (then the limit or the floor, with its own yes;
   on "no", the current target, logged as confirmed). A group whose 30-day ACOS is over the hard
   limit keeps its current target. Every new value is capped by the user's hard limit and
   requires confirmation; without a hard limit, a target above the ceiling needs its own yes - on "no" or no answer it is
   the ceiling.
   Schedules cover the event window only: the event phase, plus a warm-up phase on exactly the
   confirmed warm-up days. There is no wind-down schedule - every schedule expires at the event
   end. Personality and budget-by-performance changes apply only to head groups. Groups
   with no room for more schedules, overlapping schedules, an empty target (until the user gives one), or SD: listed,
   not written. Never before tomorrow. A **group total budget** raise is a separate, direct change
   only when the total itself limits the group - it does not end on its own; the reset skill
   restores it.
4. **SD managed groups** have no schedules: a goal or target change is a direct edit that the
   reset skill restores later. Offer it; do not do it by default.

   **Groups with AI off** (`aiStatus` `0` / `2`) get no schedule - it would not take effect.
   Say so plainly (especially when every group is off), treat their campaigns as outside
   groups, and offer - not default - turning the AI on with a dated schedule. That is the
   user's decision. If they turn it on: those campaigns leave step 5 (no direct budget, bid or
   placement changes - the AI owns them), and the AI switch is logged as a `groupSetting` row so
   the reset lists it after the event.
5. **Campaigns outside managed groups** (or in a group with AI off): raise budgets of campaigns
   that earn it - budget-short and fast-spending ones first, below-target ones not; brand
   campaigns kept from running out, non-brand ones first in the warm-up - raise bids on proven
   keywords and targets (not in fast-spending campaigns), raise top of search only where it
   converts better than the campaign as a whole - each only at or under the raise line, and
   capped by what a click is worth at the raise line. Nothing for ASINs flagged in the stock check, nothing for leave-alone campaigns.
6. **Portfolio caps** that would bind on event days: raise them, or list them for the user.
7. **Fit the total.** The money the raises add must fit in the extra money the user allows
   on each day (that day's budget - a normal day); scale raises down if it does not.
   Then say how much of the extra money the plan actually uses ("the plan adds $1,980 a day of
   the $37,400 you allowed above a normal day") and why the rest is not used - budgets that are
   not the limit, bids already at what a click is worth, more than the account can absorb.
   Never let the user assume the whole event budget will be spent; what does not fit is
   reported as headroom, never hidden.

### Step 4 - Preview, then write

1. **Show the plan** in the output template: answers, health check, push size, then one table
   per write type. Every row carries its reason with numbers.
2. **Check the write tools first.** Before offering any write, confirm this session has the
   tool for every kind of write in the plan: `batch_update_ads` (budgets, bids, placements,
   portfolio caps), `save_sp_sb_ai_group_schedule` (schedules), `save_sp_sb_ai_managed_group`
   (SP/SB group settings and totals), `edit_sd_ai_managed_group` (SD group changes). A kind
   whose tool is missing is not offered - say which; with none of them, keep the plan as the
   deliverable and offer no write option. Otherwise **ask which parts to
   apply.** The user may take all, only the schedules, only the ready rows,
   or none (plan only). Changes that need the user's own judgement - a group's total budget, an
   SD group edit, a raise on a campaign the stock check flagged - need their own yes.
3. **When to write.** Schedules can be written now: they start on their own date (`startDate` at
   least tomorrow). Direct budget, bid and placement raises take effect immediately, so each is
   written on the day `references/push-plan.md` section 8 gives it - the only timing rule, by
   day roles x warm-up x brand class: non-brand raises the day before warm-up, brand and mixed
   raises on the eve. With day roles prep writes only the budget day that table gives it and
   records one `planned` row per monitor-owned day for every campaign the plan raises (brand and
   mixed ones included, even when prep writes none of their days), with the final
   budget after step 7 (`references/change-log.md`); the monitor writes those (raises at 21:00,
   decreases after midnight). If the user runs prep early, write the schedules now and tell them
   to come back on the day the table names for the direct changes. **Offer the timing as a
   choice**: on the days in section 8 (recommended) / write the raises now - with what that
   costs (the money the raises add per day x the days until they would start) / only the
   schedules now / not yet. (Come back with "继续大促准备").
   **Hand over the change log as soon as the plan is confirmed**, before any write and also when
   the answer is "not yet": every confirmed row as `planned`, with its final value and `writeOn`
   (`references/change-log.md`). "继续大促准备" resumes from that file - re-read the
   current values and write the rows due that day - and never recomputes the plan, so the
   numbers stay the ones the user confirmed.
4. **Write in this order**, each through its owning skill and its confirmation rules. Schedules
   (`sparkx-edit-ai-group`; **one group first**, the rest after the user has checked it in the
   platform - section 6) can go in on any day before they start. Everything else is a direct
   change and goes in only on the day section 8 gives it, in this order: group total budgets and
   other group settings (`sparkx-edit-ai-group`) -> portfolio caps -> campaign budgets -> bids ->
   placements (`sparkx-edit-ads`). Writing the schedules early never brings a group total
   forward with them. Split batches by `campaignType` and keep each under the write skills'
   caps.
5. **Read back** every written object and record it in the change log
   ([`references/change-log.md`](references/change-log.md)): value before, value written,
   read-back value. Hand the file to the user - it is the starting point for the monitor and for
   the reset after the event.

A waiver such as "apply all of it without asking again" follows the owning write skill's waiver
rules exactly - the scope is what the user said, and the verification still runs.

### Step 5 - Hand over

End with the timeline in the store's timezone. Every direct write in it follows
`references/push-plan.md` section 8:

- **Day before warm-up** (only with a warm-up): group total budgets; non-brand campaigns'
  budgets, bids and top of search.
- **Warm-up start**: managed-group schedules switch on. Run the monitor on warm-up days too -
  they count as event days for it, and with day roles it writes the warm-up days' budgets.
- **Event eve**: brand and mixed campaigns' bids and top of search, and their budgets without
  day roles; without a warm-up, every class's raises. With day roles and a warm-up, the event
  start's budgets come from the monitor's 21:00 check that evening, not from prep.
- **Event days** (warm-up days included): run `sparkx-promo-monitor` 3-4 times a day (for example 10:00, 14:00, 18:00,
  21:00 store time); the 21:00 check raises the next day's budgets by its role. On a night
  when the next day's role is lower (the day after a peak), add a day-switch check at
  00:05-00:30 store time to step budgets down - without it they stay high until the next check. Don't throttle the
  first hours of day one.
- **After the event**: every schedule ends on its own at the event end and the groups are back
  on their all-time settings. Run `sparkx-promo-reset` for direct changes and to audit bids - a
  schedule ending restores the normal group settings, but current bids may take another AI cycle
  to return to the normal range.

## Example

A full worked conversation is in [`references/example-and-report.md`](references/example-and-report.md).

## Output templates

### markdown

```markdown
# 大促前准备 · {店铺} · {大促}
**大促时间**：{start} ~ {end}（{预热开始}起预热，{时区}）　**目标**：{冲销量 / 保利润}　**上限**：{x}%（{你设定的硬上限 / 你的目标 +15% / 你的目标 / 店铺近 60 天 ACOS +25% / 店铺近 60 天 ACOS——写明是哪一种，并说明它是默认目标、也是盯盘上限（您确认的排期目标不受它限制）}）
**本次加码门槛**：只给 ACOS 不高于 {raiseAcos}% 的对象加码。ACOS 在 {raiseAcos}%–{holdUpperAcos}% 之间的保持不变；超过你设定上限 {h}% 的列出但不加码。{如需说明：该门槛综合了目标 ACOS、保本 ACOS 和你设定的最高 ACOS；详细计算放在“计算依据”，不要在摘要中展示公式。}
**大促预算**：{金额}，{每天上限 / 整个大促总额}，高峰日 {dayBudget}（平时 {normal} 的 {倍数} 倍）　**加码力度**：{保守 / 平衡 / 激进}　{每个 ASIN 的点击数}
**范围**：{全店 / 主力活动：N 个中的 n 个，占花费 x% / 你指定的商品}
**参考大促**：{大促}（{日期}），对比它之前 14 天（{日期}）——{你指定的 / 默认最近一次}
{没回答的问题，以及按什么处理}

## 一眼看清
**立即 / 按日期修改**（每类一行，写数量和增加的金额）：排期、托管组总预算、广告组合上限、活动预算、出价、顶部溢价，以及各自什么时候写（现在 / 大促前一天 / 某日；后续每天的预算由盯盘写）。
**风险与待确认**（阻碍项排最前）：库存预警、需要你单独确认的项、跳过的对象及原因、剩余空间、因问题没回答而做的假设。

## 你的回答
| 我们问了 | 你说 | 方案据此 |

## 体检
| # | 检查项 | 发现 | 建议 |
{阻碍项排最前。每条带数字：“B0xx：按大促速度只够 9 天，没有在途库存”}

## 加码力度
| | 数值 | 怎么算 |
{平时一天、大促预算和高峰日预算、倍数、大促 CPC、每个 ASIN 的点击数、账户能消化多少、参考大促的提升}

## 每日投放安排
| 当天策略 | 日期 | 倍数 | 当天预算（你确认的是这个） | 预计每天花费 | 来源 |
{说明倍数从哪来；客户可以改任何一个}

## 托管组 · 大促排期
| 托管组 | 分组 | 近 30 天实际 ACOS（订单） | 阶段 | 日期 | 投放目的 | 目标 ACOS 现在 → 新 | AI 人格 现在 → 新 | 按表现调预算 | 要删的已结束排期 | 状态 |
## 托管组直接修改（大促结束后需要恢复）
| 托管组 | 修改项（总预算 / 投放目的 / 目标 / 开启 AI） | 现在 | 大促 | 写入时间 | 理由 |
## 活动预算
| 活动 | 现在 | 大促（首日） | 后续每天（日期：预算） | 写入时间 | 理由 |
## 出价
| 关键词 / 定向 | 活动 | 现在 | 大促 | 写入时间 | 理由 |
## 搜索结果顶部溢价
| 活动 | 现在 | 大促 | 数据支持到 | 写入时间 | 理由 |
## 广告组合上限
| 广告组合 | 上限 | 已用 | 大促需要 | 写入时间 | 建议 |
## 这次不加码的
| 对象 | ACOS | 对照的线 | 原因（保持 / 超过你的上限 / 低于目标 / 库存 / 不要动 / ...） |
## 剩余空间
| 日期 | 允许多花的钱 | 方案用掉 | 剩下 | 为什么没用完 |
## 按产品线
| 产品线 | 近 60 天花费 | 销售额 | ACOS | 加码占比 |
## 时间线
{预热开始、大促前一天、大促期间盯盘时间、大促后复位}

---
_生成时间：{timestamp} · 数据源：SparkX AI MCP · Skill: sparkx-promo-prep v{version}_
```

Name every object by its name (`campaignName`, `aiGroupName`, keyword text), never by an internal
id; an export adds the **Amazon** id column (see the base skills' platform-notes -> "Naming
things in your answer").

### structured_report

The JSON shape is in [`references/example-and-report.md`](references/example-and-report.md).

### optional HTML report

Build it only from the finalized `structured_report`; do not recalculate or reinterpret the
plan while rendering. Follow [`references/html-report.md`](references/html-report.md).

## Data boundaries

- **Stock is refreshed once a day**, not live, and only for Seller profiles with SP-API
  authorisation. Say it once, the way [`references/own-stock.md`](references/own-stock.md)
  ("How to say it") words it.
  Vendors have none: ask. FBA quantity `0` is not proof of a stock-out (a merchant-fulfilled
  offer can still sell). Inbound stock has no arrival date here - ask the user when it lands.
- **Event lifts come from the store's own reference event** (the one the user named, or the
  most recent) **when it exists.** Without one, say so and
  use the user's expectation; do not quote an industry figure as the store's own.
- **Schedules are SP/SB only.** SD groups have no schedule tool.
- **A schedule cannot carry a group total budget**, but it does carry its own budget by
  performance (`aiActionSettings.budgetOptimization`), which ends with the schedule. A group
  total change is direct, rescales every enabled campaign in the group and stays until
  restored.
- **Sales attribution keeps filling for days**: 7 days for SP on a Seller profile, 14 days for
  SP on a Vendor profile and for SB and SD (see the ads-performance skill's field reference).
  The last days of any baseline look worse on ACOS. Spend and clicks are final through
  yesterday, so spend-based numbers end yesterday; ACOS-based judgements end two days back,
  which reduces the bias but does not remove it - say so when a recent ACOS decides something.
- **No scheduling of direct writes.** MCP writes take effect at once; only managed-group
  schedules start and end on their own dates.
- **Thresholds are defaults, not facts.** Tier cut-offs, the +15% / +25% ceilings, raise
  percentages and the stock-cover rule are rules of thumb listed in the references - show the
  numbers so the user can override.

## Error handling

Situation-by-situation handling (a write refused, data missing, an answer that does not fit) is in [`references/error-handling.md`](references/error-handling.md).

## Not covered

- Event days - use `sparkx-promo-monitor`.
- After the event - use `sparkx-promo-reset`.
- Creating new campaigns for deal ASINs - use `sparkx-create-campaign` (offer it when a deal
  ASIN has no active ad).
- Pausing, negatives, budget or bid cuts - not part of prep; use `sparkx-edit-ads` if the user asks.
- Sponsored Brands / Display creative and DSP planning.
