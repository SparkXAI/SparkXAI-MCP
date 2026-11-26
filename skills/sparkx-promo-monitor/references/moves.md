# Moves: what to change, by how much, and when not to

Defaults, not facts - show the numbers so the user can override them. Payload shapes belong to
`sparkx-edit-ads` (budgets, bids, placements, statuses) and `sparkx-edit-ai-group` (groups and
schedules) and are not repeated here. States and the limit are defined in
[`pace-and-states.md`](pace-and-states.md).

## 1. Step sizes per check

| Lever | Up | Down |
|---|---|---|
| Campaign daily budget | +30% | -30%, never below today's spend so far (it must keep serving) and never below the campaign's pre-promo budget (below) |
| Keyword / target bid | +15% | -15% |
| Top-of-search adjustment | +25 points | -25 points, or half the current boost on "slow down" |
| Managed group total budget | +30% | -30%; the new total's effective size (section 4 - percentage, or amount with reallocation on / off; the plain total while unknown) never below the group's spend so far today |
| Target ACOS in effect (schedule or group) | +5 points | -5 points: new target = max(target in effect - 5, floor), where floor = min(the group's pre-promo target - the first confirmed `valueBefore` of a `groupSetting` row with `field` `acos` for that group, else the group's own current target (a schedule does not change it) - and the phase's initial target - in this order: prep's `valuePlanned` for the schedule phase in effect (`pace-and-states.md` section 2); else the earliest schedule-snapshot `acos` for that `scheduleId` across the whole promo window (never the day's earliest - a target this skill loosened yesterday would become the new floor); else the `valueAtPlan` of this skill's first row for the group's target; else the target in effect. Never fall back to the pre-promo target alone). A cut never ends above the target in effect: when the floor is at or above it, offer no cut and say why (e.g. a group whose own target 42% was cut to the 35% hard limit on the schedule stays at 35%, never back to 42%) |

One step per object per check. The next check (a few hours later) can take another step.

**Today's spend is an absolute floor for every budget cut** - step moves, the day-switch
decreases, stock protection and cuts the user approves alike. A budget below today's spend stops
the campaign (or group) silently for the rest of the day. If the user wants spend to stop, offer
a pause instead - a pause the user explicitly asks for may break guard 3 (section 5). Only the
pre-promo floor (below) can be overridden with the user's yes.

**Budget cuts stop at the pre-promo budget.** The pre-promo budget is the first confirmed
`valueBefore` for that campaign in the change log (prep `change-log.md`, Rules). With rows but no
confirmed write yet (only `planned` rows), it is their `valueAtPlan`. With no row at all, the
campaign has not been raised for the promo, so the value read right before the monitor's first
write to it counts as pre-promo - say so, and record it as that row's `valueAtPlan` and
`valueBefore` (in a change log the monitor started itself when there was no prep log - SKILL.md
Step 1), so the next conversation still knows it. The reset does not raise a budget that ends
below its pre-promo value (it treats that as a deliberate cut), so a cut below it would outlast
the event. Going lower - for a **Burning** campaign the user wants to slow further - needs the
user's own yes (still never below today's spend); record `reason` "cut below pre-promo, user confirmed", so the reset can show it.

**Next day's budgets by day role.** When the prep log carries `dayRoles`, the day's last check
(21:00) sets tomorrow's budgets for the campaigns the prep plan raises (including brand and mixed
campaigns whose first raised day is the event start). **Read them from the log**: the
`planned` rows with `targetDate` = tomorrow carry each campaign's final budget, already scaled
to fit the user's extra money (prep `push-plan.md` section 3 "Fit the total"). Do not recompute
them with "Recent 14 average x multiple x 1.15" - that skips the scaling and the order in which
prep spent the money.

- Show the planned value next to the campaign's current budget, say tomorrow's role and
  multiple, and let the user change them.
- **After writing a planned row**, set it to `fulfilled` in the same update of the change log
  (`skipped` with the reason if a different value was written - prep `change-log.md`, Rules). A
  row left `planned` is picked up again by the next check's catch-up.
- **Recompute only when there is no planned row** for that campaign and day (an older log, or a
  campaign added after prep). After an event day, start from **yesterday**: a campaign that ran
  out of budget yesterday with yesterday's ACOS at or under the raise line (`pace-and-states.md`
section 6 - the same line prep used, not the floor) gets max(current budget,
  yesterday's spend x 1.2); if it ran out before 18:00, multiply by 24 / the run-out hour, at most
  2x the current budget. A campaign that did not run out gets no raise. Before the first event
  day there is no event day to start from: Recent 14 average daily spend x tomorrow's multiple x
  1.15. Either way, scale down so tomorrow's total raises stay inside tomorrow's `dayBudget`, and
  say the value is recomputed, not from the plan. (A read-only backtest on Black Friday 2025 -
  one store, Saturday to Cyber Monday: the yesterday-based value was off by about 25% on
  campaigns that did not run out, against 45-49% for the Recent 14 rule, and covered 66-76% of
  the campaigns that ran out before 18:00 the next day, against 52-60%. The day multiples there
  were the actual ones, so real use will miss by more.)
- **When the planned value no longer fits** (the campaign is over the raise line today, the last
  settled days show it cannot spend the planned budget, or it ran out early yesterday and the
  yesterday-based value above is higher than the plan), change it only with the user's yes, and
  record the new value and the reason; a campaign over the raise line today gets no raise.
- **Guard 1 does not scale planned values on its own.** If writing tomorrow's planned raises at
  21:00 would push today's projected spend past `todayBudget`, list the planned rows with the
  amount by which they exceed it and ask: write them now anyway, write them after midnight (the
  day-switch check, when they no longer count against today), or lower them. Never shrink a
  planned value silently.
- **Catch up missed days.** At the first regular check of a day (SKILL.md Step 1 - never the
  day-switch check), look for `planned` rows with `targetDate` = today that are still
  `planned` (last night's 21:00 or day-switch check did not run). Show them first and write
  them, with the same rules (stale check against `valueAtPlan`, limit, stock guard), before any
  step move; say which check was missed. Rows whose `targetDate` has already passed are not
  written - mark them `skipped` with that reason. **Prep's own rows** (bids, top of search, prep
  budget days: `writeOn` `preWarmup` / `eve` / a date, no `targetDate`) still `planned` after
  their day are listed too and asked about once - write now or skip - as prep `push-plan.md`
  section 8 says.

A budget write takes effect at once and MCP cannot schedule one, so:

- **Raises** may be written at 21:00. The extra room also applies to tonight's last hours, so it
  counts against today's budget (guard 1).
- **Decreases** (tomorrow's role is lower, e.g. the day after a peak) are never written at
  21:00 - that would starve the rest of today. Write them at a **day-switch check between 00:05
  and 00:30 store time**, down to the new day's role level, never below the pre-promo value in
  the change log and never below that day's spend so far. MCP cannot run it by itself: at 21:00
  tell the user which budgets come down and that someone has to run the check after midnight
  ("continue the promo monitor"). If nobody does, those budgets stay at yesterday's level until
  the next check - say so, with the amount. Guard 3 ("no cuts before 10:00") does not apply to this
  planned step: it follows the plan, not today's results.
- **The day-switch check** writes the planned decreases **and** any planned raises the user
  chose to defer past midnight (guard 1 item above). Schedule it whenever tomorrow's role is
  lower or raises were deferred, and at 21:00 list what it will write. Rows it does not write
  stay `planned` and are caught up at the first regular check.
- Campaigns in a running managed group get no campaign budget; the group follows its schedule
  or a group-total change the user approves.

These are not step moves: write them as their own batch and log them like any other.

## 2. Moves by goal

| Goal | Moves |
|---|---|
| **Push harder** | Winners running out: budget up. Selling but under-spending: budget is not what holds them back - bid up their proven targets and raise top of search instead. Proven targets (3+ orders at or under the raise line in the 60 days before warm-up - the prep skill's definition) in winning campaigns: bid up. Top of search up where it converts better than the campaign (the prep "justified boost" rule). Managed groups short of budget (`pace-and-states.md` section 7): group total up, only if the group spends close to its effective total (section 4 - a total several times the group's spend is not the limit, say so); converting well under the target in effect (settled ACOS at or under 0.8x the target, 20+ settled clicks): target +5 points, never above the limit (`pace-and-states.md` section 6: the hard limit, else prep's ceiling, else the store-level fallback) - so repeated +5 steps stop there |
| **Slow down** | Burning and not-converting campaigns: budget down. Held campaigns with `watchReason: "overFloor"` (losing money, still inside the limit): one budget step down, offered for the user's yes. Targets with 20+ clicks today and no order: bid down. Top-of-search boost halved on campaigns clearly over the limit, except brand campaigns (their top of search is never lowered). Managed groups over their target (`pace-and-states.md` section 7) or with settled ACOS over the limit on 20+ settled clicks: target -5 points |
| **Push ASINs** | The "push" moves, only on campaigns where the named ASINs are at least half the advertised products. A named ASIN with no enabled ad: offer `sparkx-create-campaign` (not part of this check) |
| **Any goal** | **Burning** campaigns are always listed. Under "slow down" and "stay inside the limit" their budget goes down; under "push" the cut is offered for the user to decide, not proposed by default |
| **Cut by an amount** | Slow-down moves until today's projected spend drops by the amount the user named: budgets down on the lowest-ROAS campaigns first, one step each, never below today's spend, below the pre-promo budget only with a yes, never brand campaigns. Say how much the moves cut and what is left |
| **Push a category** | Map the category to ASINs by `asinBsrCategoryName` (`get_entity_metadata(entity='asin')`), confirm the list with the user, then the "Push ASINs" moves |
| **Stay inside the limit** | Money moves, it is not added: budget down on campaigns clearly over the limit, the same amount up on winners at or under the raise line. Managed groups: the "slow down" target step |

"Push" and "slow down" together: slow down wins.

**Stretch when money is short.** When today's budget leaves no room for raises but winners will
run out before the evening peak: lower their bids 10%, so the same budget lasts longer and still
catches traffic. Lower their top-of-search boost by 25 points only when the day's top-of-search
check shows its CPC clearly up (`pace-and-states.md` section 2, about +20% or more) - otherwise
the boost stays. **Never lower top of search on a brand campaign** (prep `brandClass: brand`),
and if the brand check shows a possible attack, leave brand campaigns' bids alone too. Do not raise top of search on a short
day - its CPC rises most on event days. If even no change projects past today's budget, lower
the budgets of the lowest-ROAS campaigns (one step, never brand campaigns).

**The morning check carries the most money.** At the first regular check of an event day (SKILL.md Step 1), raise (one
step) the budgets of winners that ran out before 18:00 yesterday (`lastOutOfBudgetTime`, or
yesterday's `Campaign Out of Budget` events) and are still at or under the raise line
(`pace-and-states.md` section 6): a raise in the morning
covers the whole day, one at 19:00 only its last hours.

**One budget source per campaign per day.** A campaign whose budget for today the plan set gets
that value and nothing more that day from the rules above. The plan set it when there is a
day-role row for today (prep's `planned` value, or the value the user approved instead), or a
written prep budget row that covers today: `objectType` `campaignBudget`, `skill = promo-prep`,
no `targetDate` (e.g. the warm-up-start budget, `writeOn` `preWarmup`) - it covers from its
write until the campaign's next `targetDate` row, else to the event end (prep `push-plan.md`
section 8). No morning step on top, no "winner running out" step unless the user
approves it as a new override - which then replaces the plan's value, it does not add to it.
Say which source set each budget.

## 3. Guards (apply after the moves)

1. **Today's budget.** Today's projected spend after the moves must stay inside `todayBudget`
   (SKILL.md Step 1). With a window total, also: window spent + the rest of today's projected
   spend + the dayBudgets of the days still to come must stay inside the total. A raised group total counts at its effective size (section 4: percentage, or amount with budget reallocation on / off, while budget by performance is on; while that size is unknown, at the plain total - say the real cap may be higher). Scale the step raises down to fit; report what is left. Prep's planned day-role budgets are not scaled here - they are asked about (section 1).
2. **Raise line and hard limit.** No raise on anything over the raise line (`pace-and-states.md`
   section 6) - over it but not clearly over the limit (1.3x, settled) is held or watched, not cut; no target the monitor loosens goes
   above the limit. A schedule target the user confirmed in prep is capped only by the hard limit (and floor ACOS under
   "profitable") - it is not a breach of this guard (`pace-and-states.md` section 6). There is no event-day exception that raises a campaign between the raise line and the
   floor.
3. **No cuts before 10:00, and none on the last event day**, unless the campaign is **Burning**.
   Early hours under-report orders, and cutting on the last day loses the strongest traffic.
   **When guards 1 and 3 collide** - the day projects past `todayBudget` (or the user's new
   budget is below what is already spent) and only cuts would bring it back: the user's budget
   comes first, but not silently. Show the overspend in money, and the smallest set of cuts that
   fits it (lowest-ROAS campaigns first, never brand campaigns, never below today's spend), and
   ask. With a yes, those cuts may break guard 3; without one, write no cuts and say plainly that
   the day will end about that much over budget.
   **Stock protection is the other exception** (section 6, "Protect stock"): a running-out
   product loses more than early-hour noise does, so its bid and budget cuts are allowed before
   10:00; on the last event day only when the stock would run out before the event ends today;
   always with the user's yes. Group-level stock protection (target -5 points, a lower group
   total) counts as a cut here. On the last event day before 10:00 the last-day condition
   decides. Say that guard 3 is being set aside and why.
   **A pause the user explicitly asks for** is the third exception (section 5).
4. **Low stock.** No raise on a campaign where a stock-flagged ASIN is at least half the
   products - and no raise of a managed group's total or target when such campaigns carry at least half
   of the group's spend.
5. **Left alone** campaigns are never written.
6. **Today's changes by someone else** (operation log) are shown and asked about, never undone
   by this skill.
7. **A target in effect above the hard limit** (a group or schedule set before the limit was
   given): list it and offer to bring it down to the limit - it needs a yes; never raise it.
   Not for a target the user already declined to tighten in prep (a confirmed schedule row whose
   `reason` names the decline - prep change-log.md): never re-offer that. The "slow down" target
   -5 for a group running over the limit (section 2) is a separate, performance-based step the user
   asked for by choosing "slow down", and still applies.

## 4. Managed groups: change the schedule while it is in effect

A dated schedule runs the group with its **own** goal, target ACOS and AI personality for its
window. While it is in effect:

- **Target ACOS**: change it **on the schedule** (`save_sp_sb_ai_group_schedule`, updating that
  schedule's `id`; **keep its original `startDate` and `endDate`** - the schedule is already
  running, so its start is in the past. `sparkx-edit-ai-group`'s "startDate >= tomorrow" check
  is for new schedules; never move the start to tomorrow, which would drop today and could
  overlap another schedule. The save API accepts an update by `id` to any active schedule. If
  the write is still refused, change nothing and tell the user; a fixed-date update carries goal, ACOS and personality - follow
  `sparkx-edit-ai-group` "Scheduling"). Build the update from the write contract, not from the
  read row, and carry the schedule's action space as that skill describes - on a fixed-date
  schedule an omitted per-action-space setting falls back to the schedule's personality instead
  of keeping its old value. The tool expects the **full** schedule config on an update,
  including `aiActionSettings` and `aiAutomation`; a read row can return `aiAutomation` as
  `null` and shows only what is in effect. If the schedule's full action space and automation
  cannot be rebuilt with certainty, do not send a partial update - mark the row "needs review"
  (`needsReview` in `moves.status` and `executed.result`) and tell the user to change the target in the platform. Editing the group's own target does not change today's behaviour,
  and it would stay changed after the event.
- **Budget**: a schedule has no budget field. More money is the group's **total budget**
  (`sparkx-edit-ai-group`), which rescales every enabled campaign in the group and stays until
  the reset restores it.
- **Effective total**: when budget by performance is on - the schedule's
  `aiActionSettings.budgetOptimization` while one is in effect (read from the schedule itself,
  `pace-and-states.md` section 2; prep turns it on for the groups it marks `groupClass: head` -
  use that mark, never guess head groups), else the group's own - the AI may spend up to, a day:
  percentage (`numType` 1): total x (1 + `num` / 100), whatever the reallocation switch;
  amount (`numType` 2) with budget reallocation on (`budgetRedistributeStatus` 1, same source):
  total + `num`; amount with reallocation off: total + `num` x the group's enabled campaigns
  (`enabledCampaignCount`, counted from the campaign read by `aiGroupId`), because each enabled
  campaign may rise by the amount (`sparkx-edit-ai-group` `coupling-rules.md`, "Performance budget
  ... and budget reallocation are linked": two campaigns, total $300, +$20 -> $340 off, $320 on).
  Read `budgetDynamicStatus` 1 = on (prep `push-plan.md` section 6). "The group spends close to
  its total" compares today's spend with this effective total, and guard 1 counts a raised
  total at this size. **Unknown size** (on, but the read leaves out `numType` / `num` - rule 17
  in Rule mode; or, in amount mode, the reallocation switch or the enabled-campaign count cannot be
  read; `effectiveTotalKnown: false` in the report): propose no group-total raise and
  say why - the AI may already spend above the plain total by an amount nobody can see; guard 1
  and the cut floor use the plain total.
- **Never** set fixed bids, campaign budgets or placements on campaigns in a running group - the
  AI rewrites them.

No schedule in effect: change the group's target or total directly. Both stay until the reset
restores them; say so. SD groups have no schedules: direct edits only.

## 5. "Can I pause these targets now?"

The user names targets (often ones the platform or the AI suggested pausing). Judge each on the
event days so far (daily `target` data) and the 30 days before warm-up:

| Finding | Answer |
|---|---|
| Branded term (contains the store's brand), or 1+ order on the event days, or 2+ orders in the 30 days before | **Keep.** Say what it sold |
| In a running managed group | **Leave it to the group's AI** unless the user insists; the AI manages targets in its group |
| Clicks on the event days at least 2x the store's clicks per order (and 20+), no order on the event days or in the 30 days before | **Pause or bid down - user's choice.** On an event day prefer bid -15%: pausing stops it entirely, a lower bid keeps some reach. Pausing is reversible (`updateStatus` back to enabled); archiving is not and is not offered here |
| Fewer clicks than that | **Too early.** Put it on the watch list; check again at the next check or after the event |

Pausing is a cut: guard 3 applies (not before 10:00, not on the last event day, unless the
target is burning money). A pause the user explicitly asks for - including one offered instead
of a budget cut below today's spend (section 1) - may break guard 3 with that explicit yes; say
so. Pausing goes through `sparkx-edit-ads` (keyword / target `updateStatus`), logged like any other
move so the reset can list it.

## 6. "This ASIN restocks next week - keep spending, or add budget?"

1. Read the ASIN's stock (`asinFbaQuantity`, `asinFbmQuantity`, `asinInventoryDetail`,
   `asinDayAvailability30`) and today's sales lift `Lt` (`pace-and-states.md` section 8).
2. Days left at today's pace = `asinDayAvailability30 / Lt`. Ask the user how many days until
   the restock is **sellable** (arrival plus receiving), `R`.

| Situation | Answer |
|---|---|
| Days left >= event days left and >= `R` | **Keep going.** It can take more budget if its campaigns are winners running out |
| Days left < `R`, or (with no confirmed replenishment) days left < event days left | **Protect stock.** Do not add budget. Keep brand terms and the best-converting exact keywords; first lower bids on broad / category / competitor / product targeting. Also offer a campaign-budget cut sized to make the stock last to `min(R, event end)` - one step at a time, never below today's spend (to stop spend, offer a pause), below the pre-promo budget only with the user's explicit yes (logged with `reason` "cut below pre-promo, user confirmed", section 1, so the reset shows it). The budget cut is never preselected; guard 3 is handled as section 3 says. Say the projected stock-out day before and after the proposal. **Campaigns in a running managed group** get none of these campaign-level cuts - the AI owns their bids and budgets and would rewrite them (section 4). Offer group-level protection instead, each for the user's yes: the target in effect -5 points (on the schedule while one is in effect), or a lower group total (it rescales every campaign in the group, so say what else it slows). This skill never takes campaigns out of a group (nothing would log or restore it); the user may do that in the platform themselves |
| Days left < event days left but confirmed sellable replenishment arrives first | Keep going only to the replenishment date; show the inbound assumption and ask the user to confirm it. If receiving slips, use the protection row above |
| Stock already at 0 (FBA and FBM), or its ads stopped spending today with budget left | Amazon normally stops showing ads for a product that cannot be bought, so spend on it stops by itself. Nothing to pause; after the restock, check the ads serve again |
| No stock data (vendor, no SP-API) | Say so; ask the user for units on hand and daily units sold, and use those |

Stock is refreshed once a day (it does not include what sold since the refresh) and `inbound`
has no arrival date - the answer depends on the user's `R`; when the margin is thin, ask the
user for the stock they see now, or for their own stock source (prep's `own-stock.md`).
