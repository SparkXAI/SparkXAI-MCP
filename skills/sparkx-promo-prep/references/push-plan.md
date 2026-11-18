# Push plan: how big, where the money goes, when to write

Every number here is a default rule of thumb, not a fact about the account. Show the numbers in
the plan so the user can override any of them. Payload shapes belong to the write skills -
`sparkx-edit-ai-group` for groups and schedules, `sparkx-edit-ads` for budgets, bids,
placements and portfolios - and are not repeated here.

Windows (Baseline 60, Recent 14, event days `n`) are defined in
[`health-check.md`](health-check.md).

## 1. Size the push

**Day budget first.** Every amount in this file is per day. Before anything else, turn the
user's answer into a budget for each event day (`dayBudget`), by `budgetMode`:

| `budgetMode` | With day roles | Without day roles |
|---|---|---|
| `dailyCap` | min(normal day x that day's multiple, the cap) | the cap, every day |
| `windowTotal` | the total shared by the multiples ("Day roles" below) | the total / the number of event days |

With `windowTotal`, check that the dayBudgets add up to no more than the total. **The peak day**
below is the day with the largest dayBudget. Never read a window total as one day's budget.

| Quantity | How |
|---|---|
| Normal day | Average daily spend over the 14 days through yesterday (`Y-13` .. `Y`) |
| Push multiple | The peak day's `dayBudget` / normal day |
| Event CPC | Recent 14 CPC x the CPC lift of the store's reference event (health-check e). No reference event: Recent 14 CPC, labelled "大促 CPC 通常更高" |
| Clicks per ASIN | The peak day's `dayBudget` / event CPC / the advertised ASINs that make up 80% of Baseline 60 (traffic) ad spend. With hundreds of ASINs, counting every ASIN makes the number meaningless |
| What the account can absorb | Busiest day of Baseline 60 (traffic) **leaving out the reference event's days and its warm-up**, x the spend lift of the reference event (or `L`). Counting the event day itself applies the lift twice (a trial store: $910,000 a day instead of $165,000) |

**Tier** - judged on both numbers, never on the size of the account:

| Tier | When | Raise step (budgets / bids / top of search) |
|---|---|---|
| Conservative | multiple under 1.5x, **or** under 20 clicks per ASIN | budgets up to 1.3x, bids +15%, top of search +50 points at most |
| Balanced | in between | budgets up to 1.6x, bids +30%, top of search +100 points at most |
| Aggressive | multiple 3x or more **and** 75+ clicks per ASIN | budgets up to 2x, bids +50%, top of search +150 points at most |

**The cut-offs are rules of thumb, not fitted to data.** The 1.5x / 3x multiples and the 20 / 75
clicks per ASIN come from an earlier tentpole skill and have not been backtested. That skill
divided by every advertised ASIN; here the divisor is the main ASINs only, so the clicks number
runs higher than the original rule assumed and reaches 20 / 75 more easily. When either cut-off
decides the tier, say it is a default and let the user change it.

A "profitable" goal or a hard limit caps the tier at balanced. Say the two numbers that set the
tier: "$4,500 是平时的 2.5 倍，每个主力 ASIN 大约能分到 46 次大促点击".

If a day's `dayBudget` is more than the account can absorb, say so plainly - the extra money will
stay unspent unless the account adds reach (new campaigns, more keywords), which is not part of
prep.

### No event budget given

Do not pick an amount for the user, and do not stop at "no budget, no raises" either. Offer
three daily caps (`budgetMode` `dailyCap`) built from the store's own normal day and let the user pick one (or
give their own):

| Option | Daily cap |
|---|---|
| Conservative | normal day x 1.3 |
| Balanced | normal day x 2 |
| Aggressive | normal day x 3 |

For each option show the amount, the clicks per main ASIN it buys, the tier those two numbers
actually give (a 2x budget is still conservative when it buys under 20 clicks per ASIN; 3x with
under 75 clicks per ASIN is balanced), and whether it is more than the account can absorb. Then
size the plan on the option picked, exactly as if the user had given that amount. Until they
pick, the health check still runs and the schedules can be previewed, but nothing is written -
no raise and no schedule - unless the user says to push with today's budgets only. Example:

> "你没有给大促日预算。店铺平时一天约 $1,800，给你三档参考：保守 $2,340（平时的 1.3 倍，每个主力
> ASIN 约 25 次点击）；平衡 $3,600（2 倍，约 38 次）；激进 $5,400（3 倍，但每个 ASIN 只有约 58 次点击，
> 实际按平衡档加，而且超过了账户一天大约能花的 $4,900）。选哪一档，还是你自己定个数？"

### Day roles: not every event day is the same

An event is not one day repeated. Black Friday and Cyber Monday are peaks; the early-deal days
before them and the weekend between them sell less. Give each event day a role and a multiple
of a normal day, so the money goes to the days that sell most.

| Role | Example (Black Friday / Cyber Monday) |
|---|---|
| Warm-up | The days before the sale starts |
| Early-deal days | The sale's first day up to the day before the first peak |
| Peak | Black Friday, Cyber Monday; the first day of Prime Day |
| Between peaks | The weekend between Black Friday and Cyber Monday |

**Where the multiples come from**, in this order - say which one was used:

1. The user's own numbers.
2. The store's same event last year, day by day: each day's **total store sales** (ads and
   organic) / the daily average of the 14 days before it. Total sales, not ad spend: where ad
   budgets ran out last year, ad spend shows the cap, not the demand. A total-sales field that
   comes back as 0 for every day (seen on Vendor profiles) is **unavailable**, not zero sales.
3. Neither: **ask the user for a multiple per role**, offering the reference event's lifts as a
   starting point - its event-day spend lift for the event days and its own warm-up days' lift
   for the warm-up (not the event lift). Only if the user leaves it to you, use those two
   numbers and say that the event days are not told apart. With a daily cap, one flat multiple
   usually puts every day at the cap - say so rather than presenting the table as a plan.

Never present another store's or the platform's figures as this store's own.

**Expected spend on a day** = normal day x that day's multiple; the day's `dayBudget` is that,
limited by the user's budget as the next paragraph shows. Where the budget cuts a day short, say how much demand is left over and which money is
kept longest - brand terms (health-check g) first, then campaigns that run out of budget before
noon, then before the evening, then the rest by ACOS; the raise at the bottom of that order is
cut first. No campaign goes below its current budget to make room.

**Daily cap or total?** Ask once whether the event budget is a cap for every day or a total
for the whole window.

- **Daily cap**: each day's budget = min(normal day x that day's multiple, the cap).
- **Total for the window**: share it by the multiples - a day's budget = total x that day's
  multiple / the sum of all days' multiples. If the user also gave a daily cap, cut any day
  above it to the cap and share what was cut over the other days the same way (repeat until no
  day is above it). If normal day x multiple, summed over the window, is below the total, use
  normal day x multiple for each day and report the rest as headroom - do not inflate days to
  spend it.

**Show the day-role table and let the user change it before any budget is sized** - the
multiples are estimates, and the user may know a deal day or a stock arrival that changes them:

| Role | Dates | Multiple | Day budget (`dayBudget`) | Source |
|---|---|---|---|---|

> "大促的每一天并不一样。按店铺去年黑五期间每天的总销售额：提前促销日约是平时的 1.4 倍（广告约
> $2,500/天），黑五 2.4 倍（$4,320，你给的 $4,500 够用），中间周末 1.9 倍，网一 2.3 倍。哪天你更
> 清楚，比如某天有 Deal，直接改这个数。"

## 2. The ceiling, the target, the floor - and the one raise line

Every ACOS here is a percent number. Every ROAS is converted first (ACOS = 100 / ROAS). The
**raise line** at the end of this section is the only number any "may this be raised?" check
uses - budgets, bids, top of search, group totals, in prep and in the monitor.

**The ceiling** is the default target when the user gives none, and the monitor's limit when
there is no hard limit. It does **not** cap the schedules' target ACOS: loosening the target to
a multiple of the group's 30-day ACOS is what the event phase is for, so only the hard limit
(and, for "profitable", the floor) caps a schedule - section 6.

| Situation | Ceiling |
|---|---|
| Hard ACOS limit given | That limit. A ROAS floor `r` becomes ACOS `100 / r` - ACOS is a percent number everywhere in these tools (ROAS 3 -> ACOS 33.33, not 0.333) |
| Goal "maximum sales", target known | Target ACOS x 1.15 |
| Goal "profitable", target known | Target ACOS |
| No target | Baseline 60 store ACOS x 1.25 (max sales) / x 1.00 (profitable) |

"Target known" = the managed group's `targetAcos` for its own campaigns and schedule, or a target
the user gave. Recompute every ACOS from summed spend and sales.

**Target and floor - two lines, not one, both as ACOS.** Compare in one unit only: convert every
ROAS to a percent ACOS first (ACOS = 100 / ROAS), then compare ACOS with ACOS. A lower ACOS is
better, so "beats" means "at or under".

| Line | As ACOS (percent) |
|---|---|
| **Target ACOS** | The user's target ACOS, or 100 / their target ROAS; with neither, the ceiling above |
| **Floor ACOS** - the most a sale may cost before it loses money | Margin x 100 (break-even: a 30% margin is ACOS 30, the same as ROAS 3.33), or 100 / the ROAS the user will not go below; with neither, the hard ACOS limit; with none of these there is no floor |

**The raise line** (`raiseAcos`):

`raiseAcos = min(target ACOS, floor ACOS, hard ACOS limit)` - leaving out any of the three that
does not exist. For non-brand campaigns and keywords, a separate non-brand limit (Step 1)
takes the place of the hard limit. If the floor is the lowest of the three (the target itself
loses money), say so.

**The top of the hold band** (`holdUpperAcos`):

`holdUpperAcos = min(floor ACOS, hard ACOS limit)` - leaving out either that does not exist
(the non-brand limit again takes the hard limit's place). With neither there is no hold band.
A campaign past the user's hard limit is never "held", even when it is still under the floor.

Examples: target 25, floor 30, hard limit 35 -> raise line 25, hold up to 30; ACOS 28 is held,
32 is below target. Target 25, floor 40, hard limit 35 -> raise line 25, hold up to 35; ACOS 37
is over the hard limit although it still makes money.

| ACOS (Recent 14, or the item's own window) | What prep does |
|---|---|
| At or under `raiseAcos` | May be raised (sections 3-5 decide how much) |
| Over `raiseAcos`, at or under `holdUpperAcos` | **Hold**: no raise and no cut - list it for a review after the event |
| Over the hard limit | **Over the hard limit**: no raise. Prep makes no cuts - list it with its ACOS and the limit for the user. On event days the monitor watches it and cuts only once its settled ACOS is over 1.3x the limit on 20+ settled clicks ("clearly over the limit", monitor `pace-and-states.md` section 6) |
| Over the floor, within the hard limit (or with no hard limit) | **Below target** (health-check c): no raise |
| Over `raiseAcos` with no floor and no hard limit | **Below target**: no raise |

Record `ceilingAcos`, `targetAcos`, `floorAcos`, `raiseAcos` and `holdUpperAcos` in the change
log, and each campaign's `brandClass` (section 3, health-check g) - one value for the store
when the user gave the target, otherwise one per managed group (its own target sets it) plus one
for campaigns outside groups. The monitor uses the same line (its `pace-and-states.md` section 6).

## 3. Budgets

### Managed groups (AI running)

Campaign budgets inside a running group are not edited one by one: the AI moves money between
them hour by hour.

- **The schedule carries no budget.** If a group needs more money for the event, that is a
  direct change to the group's **total budget** through `sparkx-edit-ai-group`. Editing the
  total rescales every enabled campaign's daily budget proportionally; it does not end by
  itself; `sparkx-promo-reset` restores it after the event.
- **Raise a group's total when** its campaigns are starving winners by the health-check c rule **and** the group's Recent 14 ACOS is at or under the raise line (section 2) **and** the
  group actually uses its total: its Recent 14 average daily spend is at least about half of
  `totalBudget` - a daily figure, the sum of the group's enabled campaigns' daily budgets
  (`sparkx-query-entity-metadata` field reference, `totalBudget`); when the total is several
  times what the group spends, it is not the limit - a starving campaign inside it is short of
  the AI's hourly allocation, not of the group's money. Say so and do not raise it. New total =
  current x the tier's budget step.
- Otherwise leave the total alone: the group already has room, and the schedule's goal and
  target are what change its behaviour.

### Campaigns outside managed groups

Eligible: enabled, not on the leave-alone list, not flagged by the stock check, and either
- Recent 14 ACOS at or under the raise line (section 2) with at least 2 orders, or
- a "starving winner" from health-check c (budget-short or fast-spending).

Campaigns that run out of budget follow their health-check c group:

| Group | Budget | Bids and top of search |
|---|---|---|
| Budget-short, on target | Up | May go up (sections 4 and 5) |
| Fast-spending, on target | Up, so it lasts through the evening peak | **Not raised** - each click already costs close to what it is worth; a higher bid buys the same clicks at a higher price |
| Hold / below target (over the raise line) | **Unchanged** - more budget buys more clicks that already cost more than the raise line allows | Not raised. Not lowered either: prep makes no cuts; on event days the monitor lowers bids on targets spending without orders |

**Budgets that are seldom used up are not raised.** A campaign that does not run out (under the
health-check c line of 18 hours in Recent 14) gets a budget raise only when its expected event
spend - Recent 14 average daily spend x the day's multiple (without day roles: the push
multiple) x 1.15 - is above its current budget; with day roles the formula under "New budget"
already gives that. The plan says so explicitly: in "Not raised", name the **three largest by
Recent 14 spend** that get no raise for this reason, each with its average daily spend and its
budget, and say that the budget is not what limits them - check bids and traffic first
(`notRaised.why: budgetNotLimiting`). Source: the ops team's 2026 BFCM manual p7
("预算经常花不完的，先查出价和流量，别急着加预算").

**New budget.** With day roles: the budget for a day = the campaign's Recent 14 average daily
spend x that day's multiple x 1.15 (room so it does not run out at the expected pace), never
below the current budget. Compute it for **every event day** and run "Fit the total" on each
day. The **final** figure per campaign per day (after the fit) is what the user confirms and
what goes in the change log: the day prep owns is written by prep, every later day becomes a
`planned` row with `targetDate`, which the monitor writes (section 8 says which day is whose). The monitor does not recompute them. Without day roles: current x the tier's budget step. Starving winners
first - those that run out earliest in the day first - then by Recent 14 sales (last 14 days
count double against the rest of Baseline 60 when ranking). The 1.15 is a rule of thumb.
**Never lower a budget in prep.**

### Brand, non-brand and mixed campaigns

By the campaign's brand-term share (health-check g):

- **Brand campaigns** are defended, not pushed: their budget must not run out on event days, and
  their top-of-search adjustment is never lowered.
- **Non-brand campaigns** go first: with a warm-up their raises are written the day before
  warm-up starts (section 8), to reach shoppers who have not bought the brand. Warm-up ROAS runs lower because it
  buys first-time customers; judge it by new-to-brand orders (SB and SD only - SP does not report
  them), not by ROAS.
- **Brand and mixed campaigns** wait for the eve; with day roles their event-start budget comes
  from the monitor's 21:00 check that evening (section 8).
- If the user gave a separate limit for non-brand terms (Step 1), it replaces the hard limit in
  the raise line for non-brand campaigns and keywords (section 2).

### Fit the total

Compare **the money the plan adds**, not the sum of all budgets, with **the extra money the
user allows**:

- extra money allowed on a day = max(0, that day's `dayBudget` - normal day) (the whole
  store's normal day, section 1). When it is 0 - the user's budget for that day is not above a
  normal day - add nothing that day; prep still never lowers an existing budget;
- money added = the sum of every raise (new budget - current budget, for campaigns and group
  totals) **plus, for each head group that gets budget by performance (section 6), the extra
  it lets the AI spend on top of the group total**: group total x the increase percentage
  (a $900 total at +100% can add up to $900). It is a maximum, not a forecast - show it as its
  own line, and if it does not fit, lower the percentage (never below the group's current one)
  before scaling the campaign raises.

Fit each day on its own (without day roles every event day has the same dayBudget, so one
check covers them all).

Do not compare the sum of all budget ceilings with the day budget: in many stores the
budgets already add up to far more than the store spends (a trial store had $169,000 of daily
budgets against $83,000 of daily spend), so that test would block every raise. If the money
added is more than the extra allowed, scale the raises down proportionally, never below the
current budget. Budgets are ceilings and campaigns rarely all reach them, so the event's real
spend will be lower - the monitor skill moves money during the day. Report what is left of the
extra money as headroom.

**When the scope is narrower than the whole store**, the extra money allowed is still the
whole-store figure above (the user's total covers the whole store), and only in-scope raises
count against it - unless the user says the total is meant for the scope only; say which was
used.

## 4. Bids (campaigns outside managed groups)

Bids inside a running managed group are the AI's; do not set them.

**Check the bid you read is the bid that runs.** Bid automation, dayparting and AI overrides
change the bid sent to Amazon (`keywordCurrentBid` when above 0). If the bid read is far from
the keyword's actual CPC (3x or more either way), the cap below cannot be applied to it - skip
the keyword and say why.

| Keyword / target, Baseline 60 | Raise |
|---|---|
| Proven: 3+ orders and ACOS at or under the raise line | the tier's bid step |
| Promising: 2 orders and 10+ clicks, ACOS at or under the raise line | half the tier's bid step |
| Anything else | none |

**Cap: what a click is worth.** Value per click = Sales / Clicks over Baseline 60 (for a deal
product, x `(1 - discount)`). The most a click can cost and stay at the raise line =
value per click x raise line. Amazon can pay more than the bid: the top-of-search adjustment
multiplies it, and "dynamic bids - up and down" (`autoForSales`) can raise it by up to 100% on
top of search. So keep

`new bid x (1 + top-of-search %) x (2 if autoForSales else 1)  <=  value per click x raise line`

and lower the raise until it fits. Do not raise - and say so - when:

- the current bid already exceeds the cap;
- the keyword's **actual CPC** over Baseline 60 (Spend / Clicks) is already at or above
  value per click x raise line - Amazon is already paying the most the click is worth;
- the raise left after the cap is under 5% of the current bid - not worth a change.

No raise on keywords / targets whose campaign advertises mainly a stock-flagged ASIN.

Optional, shown as "review" rows only: keywords / targets with clicks at least 2x the store's
clicks per order (and at least 20) and no order in Baseline 60. Event traffic multiplies their
waste; prep does not cut them, but the user may choose to.

## 5. Top of search (campaigns outside managed groups)

Pull placement performance (`get_ads_perf`, `factEntity: placement`) over Baseline 60 and the
current adjustment (`placement.multiplier_`, a percentage).

- Judge only campaigns with **100+ top-of-search clicks** in Baseline 60.
- **Justified boost** = top-of-search conversion rate / the campaign's conversion rate - 1.
  Converting 1.6x the campaign average justifies up to +60%.
- New adjustment = min(current + the tier's step, justified boost), and never lower than now.
- Skip where top-of-search ACOS is over the raise line (section 2), or the campaign is stock-flagged.
- Placement field names differ between SP and SB and between the read and write sides - follow
  `sparkx-edit-ads`. **An SB placement write switches the campaign to custom bidding** (it turns
  Amazon's bid optimisation off) - say so before writing one.

Show "justified vs set" per campaign.

## 6. Managed-group schedules (SP/SB)

Two terms, used the same way in this file, health-check d and SKILL.md:

| Term | Meaning |
|---|---|
| **Schedule-eligible** | SP/SB, AI running (`aiStatus` `1`), in scope, not on the leave-alone list, no unresolved blocker, and its existing schedules were read (health-check d) |
| **Head-eligible** | Schedule-eligible, 5+ attributed Group-30 orders, Group-30 ACOS not over the hard limit (with no hard limit: at or under the group's ceiling, section 2), and no low-stock ASIN (health-check a) |
| **80% spend set** | The schedule-eligible groups ranked by Group-30 spend, from the top, until they make up 80% of the schedule-eligible groups' Group-30 spend |

For every schedule-eligible group, build **dated (`timeType` 1) schedules** from that group's
own current settings (its "all time" settings: `get_entity_metadata(entity='aiGroup')`). Never
put the whole account on Promotion sales boost. First show the head-group candidates from
`health-check.md` d and let the user confirm them: groups the user names, or that hold named
focus ASINs, first - **these must be head-eligible too**. A named group that is not is listed
with the reason (fewer than 5 orders, over the hard limit or the ceiling, low stock) and stays
non-head unless the user, told the reason, still insists; a group that is not schedule-eligible
gets no schedule at all. Otherwise the candidates are the **head-eligible groups inside the 80%
spend set** - never a group outside it, however few are left. List every group of the set that
is not head-eligible, with its reason; when none of the set is head-eligible, propose no head
group and say why. **The cap and the "one or two" rule count schedule-eligible groups** - the
share of the managed account that would be pushed - while only head-eligible groups can fill
it: **never more than a third of the schedule-eligible groups** (rounded up, at least 1). In a
store where spend is concentrated, 80% of spend can be most of the groups. When the cap cuts the
list, take the groups by spend from the top, say how many 80%-candidates were left out, and let
the user add more. Head groups may use goal `3`; the other schedule-eligible groups follow the
"Other schedule-eligible group" column.
**With only one or two schedule-eligible groups, propose no head group by default**: the cap
would make one group (the whole managed account) or one of two (half of it) a head group, which
is the whole-account push this rule avoids. Say why, and make a group a head group only when the
user explicitly asks for it. With the goal "profitable" there are no head groups (below).
**A group flagged "Already set up"** (health-check d: an existing goal-`3` schedule covers the
window) **is a head group**: it counts among the schedule-eligible groups and takes one slot of
the cap, so with only one or two schedule-eligible groups no other head group is proposed.

Never apply one set of fixed values to every group. A target starts from the group's **actual
30-day ACOS**, not from another group's target. When the group has fewer than 5 attributed
orders, zero sales, or no Group-30 row, the actual ACOS is too thin: fall back to its current
target ACOS and label the fallback. The action space is each group's own. A field not listed
below is copied from the group's current value.

### The two phases

Schedules cover the event window only and end by themselves when it ends - there is no
wind-down schedule. The **event phase** is always proposed; a **warm-up phase** only when the
user confirmed a warm-up, and then its dates are exactly the warm-up: from the warm-up start to
the eve. After the event end every schedule has expired and the groups are back on their
all-time settings; the reset skill handles everything written directly.

| Field | Head group - event | Other schedule-eligible group - event | Warm-up (only with a confirmed warm-up) |
|---|---|---|---|
| Dates | The sale days the user confirmed, or Amazon's announced window with its source - never assumed | Same event dates | The confirmed warm-up start to the eve - the same days the plan calls warm-up |
| Goal (`optimizeType`) | `3` 活动冲量 (Promotion sales boost) | `1` 推动增长 (Drive growth); a group on goal `2` keeps `2` (below) | Head group: `1` 推动增长 (Drive growth), or `2` when the group is on goal `2` now - goal `3` is for the event phase only. Other group: same as its event phase. "Profitable": the group's current goal - `1` if it was on `3` |
| Target ACOS (`acos`) | max(current target, base x **1.5**); the multiplier up to x2 only when the user chooses it | max(current target, base x the multiplier): defensive group x **1.0** by default (up to x1.2); other group x **1.2** by default (up to x1.5) | max(current target, base x1.0 for a defensive group, x1.2 otherwise), and never looser than that group's event target - under "profitable" too |
| AI personality | **max(current, 4)** - see below | unchanged | unchanged |
| Budget by performance | on - see below | unchanged | unchanged |
| Budget increase | percentage, **max(current, 100%)**; up to 200% if the user wants more | unchanged | unchanged |
| Rest of the action space | unchanged | unchanged | unchanged |

- `base` = the group's Group-30 actual ACOS when it has 5+ attributed orders and sales > 0;
  otherwise its current target ACOS. `acos` is a percent number (30 = 30%); round to two
  decimals. A group with neither a usable actual ACOS nor a current target is not computed -
  list it for the user to give a target; a target they give is used as given, with no
  multiplier (`scheduleBase` `userTarget`).
- **Base over the hard limit**: a group whose Group-30 actual ACOS (the base) is over the hard
  limit gets no looser target - the schedule keeps its current target (tightened only as "the
  user's lines win" below says), and the group is listed under `notRaised` with `why`
  `overHardLimit`.
- A **defensive group** is one the user identifies as brand defence, or whose confirmed brand
  terms dominate its spend - under "maximum sales" and "profitable" alike. Show the defensive
  groups in the plan for the user to correct. Do not infer "defensive" from a low ACOS alone.
- **Never tighter than now.** An event or warm-up target is at least the group's current
  target: a group whose actual ACOS runs well under its target (actual 15, target 30 -> 15 x 1.5
  = 22.5) would otherwise be tightened for the event. Show when the current target set the
  value ("current target kept - actual ACOS is well under it").
- **The user's lines win over "never tighter".** When the group's current target is already
  above the hard limit (or, for "profitable", above the floor), the schedule target is the
  limit (or the floor) - lower than now. Mark the row "needs yes": "its current target 42% is
  above your 35% limit, so the event schedule would tighten it to 35%". If the user says no, the
  schedule keeps the current target, logged as a confirmed `planned` row like any other
  (`change-log.md`), so the monitor does not offer the cut again.
- The table's bold multipliers are the recommended starting values. Show the allowed range and
  ask once whether to stay at the low end (recommended) or use a higher value. Never silently
  choose x2 because the account is large.
- **Only the hard limit caps a schedule**: no phase's target goes above the user's hard ACOS
  limit (or `100 / ROAS floor`, a percent number). The ceiling (section 2) does not silently
  replace the user's limit. **Without a hard limit**, a computed target above the ceiling is
  listed group by group with both numbers and is written only with the user's explicit yes for
  those groups; a general "apply all" does not cover them. On "no", or no answer for those
  groups, the target is the ceiling - a normal `planned` row with `cutBy` `ceiling`. Show any
  group where a cap cuts the target.
- **"Maximum sales", a non-head group on goal `2`** (保持订单稳定, Optimize ROAS) keeps goal `2` on its event
  and warm-up schedules by default; the plan names it. Switch it to goal `1` only with the user's
  yes.
- **"Profitable" goal**: there are no head groups and no goal `3`. Every group keeps its
  current goal (or goal `2` when the user explicitly chooses it - a group already on goal `2`
  stays there); a group already on goal `3` outside a schedule (health-check d) gets goal `1` on
  its schedules, never `3`, and the plan flags it. Personality and budget by performance stay
  unchanged (they push spend). The target follows the "Other schedule-eligible group" column - defensive
  group (identified as above) x1.0 (up to x1.2 with the user's choice), other group x1.2 (up to x1.5) - so "profitable"
  is never looser than "maximum sales" for a brand-defence group; then it is capped by floor
  ACOS and hard limit, leaving out any that does not exist (section 2). Show every cap. When
  "profitable" came from an unanswered goal question (SKILL.md Step 1), say so in the plan
  header - "no Promotion sales boost, because no goal was given; say 'maximum sales' to use it".
- A group on `targetType` `4` (Drive growth - budget utilization priority) is a valid group
  goal, but a schedule accepts goals `1`-`3` only: mark the group "needs review" and ask which
  goal the schedule should use.
- Dates the user has not given are asked for, never guessed. No schedule runs past the event
  end.
- The multiplier ranges follow the 2026 BFCM operating guide: only head core groups use
  Promotion sales boost; defensive and other groups stay on Drive growth; start at the low end
  and adjust after 2-3 days. The user-confirmed hard limit and stock/blocker checks still win.
  They are **event** values and deliberately looser than the platform's everyday recommended
  range. `recommendedAcos` on `aiGroup` (only when `select` includes it) gives `{acos, minAcos,
  maxAcos}`: `acos` is the lower of the group's last-14-day ACOS and the prior window's (or the
  profile + ad type ACOS when the group has none), and `minAcos` / `maxAcos` apply the
  multipliers of the group's **current** `targetType` to it (1: x1.0-1.2, 2: x0.8-1.0, 3:
  x1.2-1.5) - not the schedule's goal (`sparkx-query-entity-metadata` field reference). When it
  is read, show it next to the proposed target so the user sees both.
- **The monitor relies on the change log here**: a schedule target the user confirmed in prep
  is capped on event days only by the hard limit (and the floor under "profitable"), not by the
  ceiling - so every schedule phase row records its confirmed `acos` (`change-log.md`).

### Personality: only up, never down

- **Head groups only**, event phase: **max(current, 4)**. A group below 4 goes to 4; a group
  already at 4 or 5 keeps its value - never lower a 5 to 4. Other schedule-eligible groups keep their
  current personality in every phase.
- Accounts with per-action-space personality: apply the rule to **each of the 12 action
  spaces separately** (bid dayparting at 5 and add-negatives at 3 become 5 and 4). Other
  accounts: the group-level `aiPersonality`.
- On a dated schedule an omitted personality falls back to the schedule's `aiPersonality`
  (`sparkx-edit-ai-group` `ai-personality.md`), so send the full set.
- Warm-up: unchanged.

### Budget by performance

**Head groups only**: other schedule-eligible groups keep their current budget-by-performance setting.

A normal 20% budget increase cannot keep up with an event: groups with AI running spend 1.6-4.4x
their pre-event level on event days. Turning budget by performance on with a 100%-200% increase
lets the AI add up to 2-3x a day's budget when campaigns perform and run short. Like
personality, only up: a group already above 100% is not lowered. A group on a fixed amount
(`numType` 2) is converted to a percentage first; if it cannot be converted, list it for the
user. It ends with the schedule - nothing to restore.

Where it lives: in the schedule's own `aiActionSettings.budgetOptimization`, and a schedule's
values are its own (a read in 2026-11: a Prime Day schedule at `num` 30 on a group at 10). **The
read and the write use different names**: reads return `budgetDynamicStatus` (1 = on),
`numType` (1 = percentage, 2 = fixed amount) and `num`; the SP/SB write takes
`budgetDynamicStatus` + `budgetNumType` + `budgetNum` (`sparkx-edit-ai-group`
`coupling-rules.md`) - build the write from that skill's contract, never by echoing the read.
The top-level `budgetDynamicStatus` / `numType` / `num` on the write request are legacy copies;
the values inside `aiActionSettings` win. If the group's budget-by-performance rule (rule 17) is
in Rule mode, the read leaves out `numType` / `num` (`sparkx-query-entity-metadata`
`ai-group-effective-config.md`), so "max(current, 100%)" cannot be computed: list the group for
the user instead of guessing.

A group whose budget group has **automatic budget pacing** on ignores budget by performance and
dayparting, and its personality is locked at 5 at run time: mark it in the plan, do not block it.

### Before writing

- **Dated schedules only.** A weekly schedule cannot carry its own goal, target or personality.
- `startDate` at least tomorrow; window at most 365 days; never echo a read schedule row back;
  never send `isActive`.
- **At most 4 dated or weekly schedules per group** (5 with "all time") - a platform rule; the MCP write path does not check it, so count the group's schedules first. When a group has no room:
  1. list its dated schedules that have already ended (they will never run again) for deletion
     - delete only after the user confirms, and log each deletion as a `scheduleDelete` row
     (change-log.md) with the deleted schedule's id, window, goal and target, so the record shows
     what was removed;
  2. still short: with room for one schedule only, keep the **event phase** and drop the
     warm-up phase (say so); with no room, skip the group and say why. **Never delete a weekly
     schedule for the promo** - it is the user's standing setup (dayparting and the like),
     nothing restores it afterwards, and the reset skill does not recreate schedules. If the user
     wants room, they remove or shorten it in the platform themselves.
- **Overlap with an existing schedule**: name the existing schedule and its dates. Never
  overwrite or shorten the existing one. Offer to shorten the **new** phase so it no longer
  overlaps (for example start the event phase the day after the existing one ends); without a
  yes, skip that phase - and the group when the event phase itself cannot fit. The same rule is
  in `error-handling.md`.
- **SD groups** have no schedules: skip them and list them.

### Write one group first

1. Show the plan as one table per group: group name, each phase's dates, goal, target ACOS
   now -> new, personality now -> new (per action space where it applies), budget by
   performance and budget increase, ended schedules to delete.
2. After the user confirms, write **one** group and ask the user to check it in the platform.
   The MCP write path does not yet run all the cross-field checks the platform page does
   - a known gap - so the first group is the check.
3. Only after the user says it looks right, write the rest; end with the groups written,
   skipped and failed, each with its reason.

### What to say when asked

- Under Promotion sales boost, during site-wide events (Prime Day, Black Friday / Cyber Monday,
  from 2 days before) the AI pauses automatic negatives, and dayparted budget is not split by
  hour even if it is on - there is no need to switch either off by hand.
- A group in a budget group with automatic budget pacing: see above.

The schedules end by themselves - nothing to restore. A group total budget raised in section 3
does not; say so in the plan.

## 7. Product-line share of the push

For each budget change, extra daily money = new budget - current budget (for a group: new
total - current total). Spread it over product lines by the campaign's (or group's) Baseline 60
spend share per product line (`factEntity: productAd` with the campaign and product-line
dimensions). Report each line's share of the total extra money. An ASIN in two lines counts in
both - say so if it happens.

## 8. When each change is written

| Change | Write | Why |
|---|---|---|
| Managed-group schedules | After the event budget is settled and before the first phase starts (start >= tomorrow); one group first, the rest after the user checks it (section 6) | They start and stop on their own dates |
| Group total budgets | The day before the group's first schedule phase starts (the warm-up phase when it has one, else the event phase) | Takes effect immediately and stays until restored |
| Other direct group settings (turning AI on, an SD group's goal or target) | The same day as the group totals: the day before the warm-up start, else the eve | Take effect immediately and stay until the reset restores them |
| A same-day goal / target change (a schedule cannot start today - error-handling.md) | Today, right after the user's yes | The only way to cover today; logged for the reset |
| Portfolio caps | **As soon as the user says yes** when the cap would bind before or during the warm-up; otherwise before the day it would bind | A cap that runs out stops every campaign in the portfolio, and the eve may be too late |
| Campaign budgets, bids, top of search | By the table below | Take effect immediately; a week of event-level bids on normal traffic wastes money |
| Budgets for later day roles | By the monitor, from prep's `planned` rows (`targetDate`): raises at the day's last check (21:00), decreases at a day-switch check at 00:05-00:30 | A direct write cannot be dated and takes effect at once; prep writes only the first day's budgets and records the rest as the plan |

**Direct campaign raises: who writes what, and when.** This table is the only rule; SKILL Step 4
and Step 5 and the examples follow it. "Eve" = the day before the event start. "Pre-warm-up" =
the day before the warm-up start. The brand class is the campaign's `brandClass`
(health-check g); a campaign with no class is treated as mixed. "Without day roles" means a
one-day event, or the user chose one budget for every event day instead of the day-role table.

| Day roles | Warm-up | Class | Budgets | Bids and top of search |
|---|---|---|---|---|
| No | No | Any | Prep, on the eve - one budget for every event day; the monitor does not rewrite it | Prep, on the eve |
| No | Yes | Non-brand | Prep, pre-warm-up - one budget for the warm-up and the event | Prep, pre-warm-up |
| No | Yes | Brand, mixed | Prep, on the eve - unchanged through the warm-up | Prep, on the eve |
| Yes | No | Any | Event start: prep, on the eve. Later days: the monitor, from `planned` rows | Prep, on the eve |
| Yes | Yes | Non-brand | Warm-up start: prep, pre-warm-up. Later days, the event start included: the monitor, from `planned` rows | Prep, pre-warm-up |
| Yes | Yes | Brand, mixed | Unchanged through the warm-up (no warm-up rows). Event start and later: the monitor, from `planned` rows - the event start at the eve's 21:00 check | Prep, on the eve |

- **One owner per budget day.** Prep never writes a budget day that the table gives to the
  monitor. If prep is resumed on the eve and finds the event start's row still `planned`, it
  tells the user to run the monitor's 21:00 check instead of writing the budget itself.
- **With a warm-up, prep runs twice**: pre-warm-up for the non-brand rows (and the group
  totals), and on the eve for the brand and mixed bids and top of search (and, without day
  roles, their budgets). Say both dates in the plan.
- **Fit the total (section 3) follows the same split**: on warm-up days only the non-brand raises
  count against the extra money allowed. Warm-up money the brand and mixed campaigns do not use
  is reported as headroom.
- Without a warm-up, no day is "pre-warm-up": every class follows the "No warm-up" rows.

MCP cannot schedule direct writes. If the user runs prep more than a day early, write the
schedules, keep the rest as a plan, and tell them to say "继续大促准备" on each
day the table above names (the day before warm-up first, when there is one, then the eve).
On that day **re-read the current values first**: a value someone changed since the plan was
built (current != `valueAtPlan`) is shown again, not overwritten.

**A prep row whose day has passed** (`writeOn` `preWarmup` / `eve` / a date before today, still
`planned` - prep was not resumed in time) is not dropped silently: the next run of either skill
lists it first. Prep resumed late, or the monitor's first regular check of the window, shows
each such row with what it would have done and asks once for all of them: write now (with the
`valueAtPlan` check), or mark `skipped` with the reason "day passed". A bid or top-of-search
raise for days already gone is still useful from today on; a warm-up-only budget is not once
the warm-up has ended.
