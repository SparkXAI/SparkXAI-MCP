# Health check: is the store ready for the event?

Read-only. Eight checks, run for one store. Query details (field names, paging, filters) belong to
the query skills and are not repeated here - this file says **what** to pull and **how to read
it**.

Windows used below (store-local dates). Spend and clicks are final through yesterday (`Y`);
orders and sales are not - they keep being attributed for 7-14 days (SKILL.md "Data
boundaries"). So:

- `Y` = yesterday: the cutoff for spend, clicks, CPC and budget usage (the normal day, the
  busiest day, out-of-budget minutes).
- `D` = two days back: the cutoff for anything judged on orders, sales, ACOS or CVR. It reduces
  the attribution bias; it does not remove it.

| Name | Days |
|---|---|
| Baseline 60 | **Attributed** `D-59` .. `D` for orders, sales, ACOS, CVR and value per click; **traffic** `Y-59` .. `Y` for spend, clicks and CPC only (the busiest day, the 80% main ASINs, clicks per ASIN). Each is 60 days, inside `get_ads_perf`'s 90-day cap. "Baseline 60" alone below means attributed |
| Recent 14 | `D-13` .. `D` for ACOS, orders and CVR; `Y-13` .. `Y` for spend, clicks and budget usage |
| Group 30 | `D-29` .. `D` for managed-group sales, orders and ACOS; `Y-29` .. `Y` for spend and clicks |
| Days to event | today .. the day before warm-up starts |
| Event days `n` | warm-up start .. event end |

## a. Stock vs event demand

1. **Advertised ASINs**: `get_ads_perf`, `factEntity: productAd`, `select: ["productAd.asin_"]`,
   Baseline 60, filter `Spend > 0`. These are the ASINs the push would spend on.
2. **Stock**: the customer's own stock source first, if they gave one
   ([`own-stock.md`](own-stock.md)); for the rest, `get_entity_metadata(entity='asin')` for those ASINs, selecting `asin`,
   `asinTitle`, `asinFbaQuantity`, `asinFbmQuantity`, `asinInventoryDetail`,
   `asinDayAvailability30`. Field meanings are in the entity-metadata skill's field reference
   (inventory section).
3. **Event lift `L`** (how much faster stock sells on event days): the store's reference event
   (check e) - its sales on event days / its average daily sales in the two weeks before. If
   there is no reference event, use the user's expectation; if they gave none, show two scenarios
   (`L = 2` and `L = 3`) and label them as scenarios, not forecasts.
4. **Cover at event pace.** `asinDayAvailability30` is days of cover at the last 30 days' pace.
   With `d0` = days to event and `n` event days:
   - left at warm-up start (normal-pace days) = `cover - d0`
   - event days it lasts = `(cover - d0) / L`

| Result | Flag | Plan effect |
|---|---|---|
| `cover < d0` | **Blocker** - runs out before the event | No raise; tell the user now - this is a stock problem, not an ad problem |
| `(cover - d0) / L < n` | **Warning** - runs out on event day `ceil((cover - d0) / L)` | No raise on campaigns where this ASIN is at least half the products; say which day it runs out |
| otherwise | ok | - |
| `asinDayAvailability30` is null | unknown - null means no sales to project from, not zero stock | Show FBA / FBM quantities; ask if it matters |

- **Inbound stock counts only when the user confirms it arrives before it is needed.** Show
  `inbound` from `asinInventoryDetail` as context ("在途 50 件"); there is no arrival date
  here.
- **FBA quantity `0` is not a stock-out**: a merchant-fulfilled offer (`asinFbmQuantity`) can
  still sell. Report it as a lead.
- **Vendors have no stock fields.** Ask the stock question instead (SKILL.md Step 1).
- **Stock is refreshed once a day**, so cover is as of the latest daily figure. Say so once,
  worded as [`own-stock.md`](own-stock.md) ("How to say it") shows.

## b. Delivery blockers

Things that stop spend on the event regardless of budget.

| What | How | Flag when |
|---|---|---|
| Ended but still enabled | `get_entity_metadata(entity='campaign')`, enabled campaigns, `campaignEndDate` before today | Info: they no longer serve; ask whether any should be extended. Leave them out of the main campaigns |
| Campaign end dates | `get_entity_metadata(entity='campaign')`, enabled campaigns, `campaignEndDate` | today <= `campaignEndDate` <= the event end (an end date already past is the row above, not this one) |
| Recent pauses | `get_operation_log`, last 14 days, one query per entity: `["campaign"]`, `["adGroup"]`, `["productAd"]`, `actionType` `Paused`. Classify `changedBy` as the reset skill does (email / `Manual` = a person; `Amazon Console` = source unknown) | The paused object had spend in Recent 14 before the pause, or is on a focus / deal ASIN. Ask whether it was deliberate |
| Deal ASINs without an active ad | Deal list from Step 1 vs advertised ASINs (check a) | A deal ASIN has no enabled product ad - offer `sparkx-create-campaign` |

A pause is a person's decision until they say otherwise: list it, never re-enable it as part of
prep.

**Read other people's changes in pairs.** Two campaigns changed within minutes of each other,
one down and one up by a similar amount (often the same ASIN or product line), are one
decision: money moved between them. Ask once about the pair, not about each half.

## c. Budget ceilings

### Portfolio caps

1. `get_entity_metadata(entity='portfolio')`: `portfolioBudget`, `portfolioBudgetType`
   (`dateRange` / `monthlyRecurring`), `portfolioEndDate`, state.
2. Spend so far in the cap's period: `get_ads_perf`, `factEntity: campaign`,
   `select: ["portfolio.portfolioId_"]` over the cap's period to date (this month for
   `monthlyRecurring`; the date range for `dateRange`).
3. Need until the event ends = spend so far + the portfolio's normal daily spend x days to
   the warm-up + the portfolio's share of each event day's `dayBudget` (its campaigns' share of
   Recent 14 spend) summed over the event days. It uses the day budgets, not the plan's raises,
   so it runs before the plan exists. **A `monthlyRecurring` cap resets on the 1st**: when the
   event crosses a month end (Black Friday / Cyber Monday into December), compute the need per
   calendar month - this month's days against this month's cap (with spend so far), next
   month's days against a fresh cap - and flag the month that binds.

| Flag | When |
|---|---|
| **Blocker** | `portfolioEndDate` before the event end; the cap is already used up; or, at normal pace, it runs out before the warm-up starts - report it first, before anything else, and offer to raise it now (push-plan section 8) |
| **Warning** | Need until the event ends > cap. Say on which day it would bind |

A portfolio cap stops every campaign in it. Raising it is `portfolio + updateBudget` in
`sparkx-edit-ads` (always confirms) - it is the user's money ceiling, so it always needs its own
yes.

### Campaigns that already run out of budget

On a normal day these are the first to starve on the event.

0. **Mostly managed?** First compute the share of in-scope Recent 14 spend in groups with AI
   running. At about 80% or more, say so at the top of the check: the plan works at group level
   (schedules, group totals, portfolio caps), and the campaign-level steps below - the three-way
   split, bids, top of search - run only on the rest and are reported in one line.
1. **How long out of budget**: `get_entity_metadata(entity='campaign')` with
   `budgetUsageDateStart` / `budgetUsageDateEnd` = Recent 14 and `budgetUsage` in `select` -
   read `outOfBudgetMinutes` (never rank on the percentage; see the entity-metadata skill's
   budget-usage reference). One call covers up to 500 campaigns, so this is the main signal.
2. **Days out of budget (optional)**: `get_operation_log`, `["campaign"]`, `operationType`
   `Campaign Out of Budget`, Recent 14, counting **distinct store days** per campaign. Count only
   rows with `newValue` `CAMPAIGN_OUT_OF_BUDGET`: the same event type also carries
   `PORTFOLIO_OUT_OF_BUDGET` when the campaign stopped because its **portfolio** cap ran out
   (seen in production 2026-11) - that is a portfolio finding (portfolio caps above), not a
   short campaign budget. Use it for a short list of campaigns, not for a whole large store - the
   log grows with every campaign and every day.
3. **Efficiency**: Recent 14 ACOS per campaign from `get_ads_perf`.

A campaign **runs out** when it was out of budget for at least **18 hours** in the 14 days
(about the evening of 3+ days), or on 3+ distinct days when the log was read. Split those by
Recent 14 ACOS against the **raise line** (`raiseAcos` = min(target, floor, hard limit), all as
ACOS - push-plan section 2):

| Flag | When | Plan |
|---|---|---|
| **Budget-short, on target** (starving winner) | Runs out, ACOS under 80% of the raise line | Budget up; bids and top of search may go up |
| **Fast-spending, on target** (starving winner) | Runs out, ACOS from 80% up to the raise line | Budget up; bids unchanged |
| **Hold** | Runs out, ACOS over the raise line but at or under `holdUpperAcos` = min(floor, hard limit) | No raise and no cut - profitable and inside the limit, but short of the target; listed for a review after the event |
| **Over the hard limit** | Runs out, ACOS over the user's hard limit (even if still under the floor) | No raise. Listed with its ACOS and the limit; prep makes no cuts, and on event days the monitor cuts it only when clearly over the limit (1.3x, settled) |
| **Below target** | Runs out, ACOS over the floor but within the hard limit (with neither floor nor hard limit: over the raise line) | No raise - more budget buys more of the same. Listed so the user knows why it gets nothing |

Why ACOS tells the bid room: a campaign's CPC / (value per click x raise line) equals its ACOS /
raise line. So "the click already costs close to what it is worth" is the same as "ACOS close to
the raise line". The 80% line is a rule of thumb.

If `budgetUsage` is null for a large part of the scope (more than about a third), say how many,
and for those campaigns use the operation-log days (step 2) on a short list - never read null as
"in budget".

Within each group, those that run out earliest in the day lose the most event hours. For a short
list, read the times from the operation log (`Campaign Out of Budget`; store-local on a
single-profile query) and group them
as before noon / noon to 18:00 / 18:00 to midnight.

For a campaign in a running managed group the cap is the group's business: flag the **group**
(its campaigns run out of budget) rather than the campaign. **Do not use the minutes for
groups**: on a managed campaign `budgetUsage` follows the AI's hourly allocation
(`budgetSnapshot`), which starts low each day, so the minutes overstate starving. For groups
count the operation-log days (step 2) - there are few groups, so the log stays small.

## d. Managed groups

1. `get_entity_metadata(entity='aiGroup')`: `aiGroupId`, `aiGroupName`, `campaignType`,
   `aiStatus`, `targetType`, `targetAcos`, `aiPersonality`, `totalBudget`, `aiActionSettings`.
   A campaign is AI-managed when its `aiGroupId` is set **and** that group's `aiStatus` is `1`.
2. **Existing schedules**: `get_entity_metadata(entity='aiGroup_schedule')`, one call per SP/SB
   group (exactly one `profileId` and one `filters.aiGroupId` per call). On a store with many
   groups, read them in layers - the tools are rate-limited (about 120 calls a minute each):
   - read schedules for every group that **needs a check**: groups that may get a new
     schedule (SP/SB, AI running, in scope); groups holding a low-stock, leave-alone or
     deal-conflict product or any other blocker - an existing Promotion-sales-boost schedule over
     the event would push it, and must be reported; and groups already on goal `3` with no known
     source. Only groups that need neither may wait;
   - with many groups needing a check, go in batches by spend (largest first) and keep a list of which
     groups were checked and which were not;
   - a group whose schedules were not read gets no new schedule (an overlap would be rejected),
     and the report never says "no overlaps" for groups it did not check.
3. Report per checked group: goal, target ACOS, personality, total budget, existing schedules and
   whether any overlaps the planned warm-up or event window (dates for fixed windows;
   weekdays for weekly ones).
4. **Thirty-day actuals and head-group candidates**: pull Group 30 campaign performance and map
   each campaign to its `aiGroupId`. Sum spend, sales, orders and clicks by running group; compute
   ACOS from summed spend / sales. Do not average campaign ACOS. The user's named focus ASINs or
   groups are head candidates first, if head-eligible - a named group that is not is listed with
   the reason (push-plan section 6). Without a named focus, show the candidate list push-plan
   section 6 defines - head-eligible groups inside the 80% spend set only, capped by the count
   of schedule-eligible groups (all three terms are defined there), with each excluded group of
   that set and its reason - plus each group's sales, orders and ACOS. This is a candidate list, not permission: the user confirms which groups may use
   Promotion sales boost.

| Flag | When |
|---|---|
| **Overlap** | An existing schedule overlaps the window - the new one would be rejected. Name it |
| Already set up | An existing fixed-date schedule covers the window with goal `3` - nothing to do; show it. It counts as a head group (push-plan section 6) |
| AI off (`aiStatus` `0`/`2`) | The group will not act on a schedule; its campaigns are treated as outside groups |
| SD group | No schedules. A goal / ACOS change would be a direct edit, restored after the event |
| Already on goal `3` outside a schedule | Someone set 活动冲量 directly. It will not end by itself - note it for the reset. Under "profitable" its schedules use goal `1`, never `3` (push-plan section 6) |

Read rows are information, not payload: never send a read schedule back to the write tool (see
`sparkx-edit-ai-group` "Never echo a read schedule back as a write payload").

## e. Reference event

The store's own lift is worth more than any rule of thumb.

- **Which event**: the one the user named in Step 1. If they named none, the **most recent**
  event inside the 15-month lookback (Prime Big Deal Days, Prime Day, Black Friday / Cyber
  Monday...). Ask the user for its dates if unsure; do not guess them.
- **Say which one was used**, every time: the event, its dates, the 14-day comparison window,
  and whether the user named it or it is the default ("Reference: Prime Big Deal Days, Oct 6-7,
  against Sep 22-Oct 5 - the most recent event; tell me if you'd rather use another").
- **If the reference barely moved** (spend lift under about 1.1x - the store did not push
  then), its lifts understate an event. Say so and offer another event inside the lookback.
- **If the reference was held back or ran very differently**, its lifts are not this event's
  either. Signs: on its event days the operation log shows `Portfolio Out of Budget` or many
  `Campaign Out of Budget` events; its sales lift is well above its spend lift while CPC barely
  moved (demand was there, money was not); or its event-day ACOS is far above this event's
  ceiling (about 1.5x or more - the lift was bought at a price this plan will not pay). Say
  which sign, and offer another event or ask the user for the multiples.
- **Pull**: `get_ads_perf`, `factEntity: campaign`, `select: ["date"]`, from 14 days before
  that event to its end. Metrics: `Spend`, `Sales`, `Clicks`, `Conversions`.
- **Lift** = event-day daily average / the 14-day pre-event daily average, for spend, sales,
  CPC (`Spend / Clicks`) and conversion rate (`Conversions / Clicks`), each recomputed from sums.

Use it for: `L` in check a, the event CPC in push sizing, and the "can the account absorb this"
estimate. If the store did not run ads then, say so.

## f. Product lines

The view customers ask for ("按产品线给我大促建议").

- `get_ads_perf`, `factEntity: productAd`, `select: ["productLine.productLineParentName_"]`,
  Baseline 60, filter `{"productLine.productLineParentId_": {">": 0}}`. Spend, Sales, ACOS
  recomputed from sums.
- **An ASIN can sit in more than one product line**, so line totals can add up to more than the
  store. Say so when they do; never present the line split as shares of the store total.
- ASINs in no product line: show them as one "No product line" row from a second query without
  the product-line filter (store total minus the tagged ASINs is not safe for the same reason).
- After the plan is built, add each line's share of the planned extra spend (push-plan
  section 7).
- If the store has no product lines, use portfolios; without those, a consistent code in the
  campaign names (a shared prefix such as `NL_` / `PRO_`) if the naming has one; without that,
  group the top ASINs by the product word in their titles (e.g. all "magnesium" ASINs together) or list the top ASINs. Say
  which grouping was used.

## g. Brand, non-brand and competitor terms

Different traffic, different jobs: brand terms are defended, non-brand terms bring new customers
at a lower return, competitor terms have to prove themselves.

1. **Own brands**: the distinct `asinBrand` of the advertised ASINs (check a, from
   `get_entity_metadata(entity='asin')`), confirmed by the user in Step 1, plus the spellings
   shoppers type (a brand name with no spaces, for example) and sub-brand or product-line names
   that carry the brand (show the top non-brand terms by spend and ask which are really brand
   terms). Competitor brands only if the user names them; if the named competitors get almost
   no spend, say so and show the top non-brand terms that contain another brand name.
2. **Classify** search terms (`get_ads_perf`, `factEntity: searchTerm`, `query_`, Baseline 60).
   On a large account pull **class totals** with filters (`ilike` on `query_` - case-insensitive - OR across the confirmed
   spellings) rather than listing every term - the full list runs past the tool's output limit.
   A term is **brand** if it contains an own brand name (ignoring case and spaces),
   **competitor** if it contains a named competitor, otherwise **non-brand**. Product targeting
   (ASIN targets) is its own row.
3. **Report** spend share and ROAS / ACOS per class, recomputed from sums.
4. **Brand defence**: the last 7 complete days against the 7 before, on brand terms - CPC change
   against the store's CPC change, and click change. Flag when brand-term CPC rises 15+ points
   more than the store's, or brand clicks fall more than 10% while the store's do not: someone
   may be bidding on the brand. Both thresholds are rules of thumb.
5. **Campaign brand share** = brand-term spend / campaign spend, Baseline 60: under 10% is a
   **non-brand** campaign, over 90% a **brand** campaign, anything else **mixed**. The plan uses
   it in push-plan section 3.

## h. Guardrails that can block a push

Run these checks before building schedules. They are configuration checks, not permission to
change a limit.

1. **Store budget cap**: read `entity='profile'`. When `profileUseBudgetCap=1`, compare
   `profileDailyBudgetCap` (a decimal string - parse it) with the highest `dayBudget`; report the
   shortfall and ask whether the customer will change it in the platform. Do not describe a
   disabled cap as available budget. `profileUseBudgetCap` can be `null`, and **null is not
   "off"** (field reference): report it as "store budget cap unknown - check in the platform".
   A null switch can come with `profileDailyBudgetCap` `"0.00"` (seen 2026-11) - that is not a
   $0 cap and not "no cap".
2. **Managed-group bid range**: for every group proposed for a schedule, read the effective
   `bidRangeStatus`, `bidRangeType` and `bidRange`. A fixed-value maximum below the group's
   Group 30 CPC or the expected event CPC is a warning that the AI may not be able to bid up.
   A coefficient range is reported as a coefficient (`1.2x`, not `20%`); do not claim a final
   currency ceiling unless the base bid needed to calculate it is available. Placement
   multipliers and Amazon's bidding strategy can still move the final auction bid outside the
   base range, so call it a guardrail, not a guaranteed final bid.
3. **Placement ranges**: when placement adjustment is on (`bidAdPlaceStatus`, ranges under
   `bidAdPlaceRangeStatus`), read the enabled `tosMin`/`tosMax`, `pdpMin`/`pdpMax`,
   `rosMin`/`rosMax` and `btbMin`/`btbMax`, and report them as values - the plan sets no
   placement adjustment for managed groups, so there is no pass / fail. Flag only a range whose
   maximum leaves no room to raise (max equal to min, or 0). Never turn a range on or widen it
   silently. **SB groups do not return these fields** - the read trims them
   for `sponsoredBrands` (`sparkx-query-entity-metadata` `ai-group-effective-config.md`), so an
   SB group's placement range is "check in the platform", never "no range".
4. **Budget management**: automatic budget pacing is the group's `isAutoPacing` (1 = on; it
   overrides budget by performance and dayparting, push-plan section 6). Report another
   controller only when the returned profile/group fields establish it. If the platform's
   budget-management group or its cap is not exposed by this read, say
   "预算管理上限未通过当前接口返回，请在平台确认". Missing data is not "no cap".
5. **Brand protection from automatic negatives**: the read returns only the switches, under
   `aiActionSettings.targetOptimization`: `negativeTargetStatus` (add negatives on / off) and
   `negativeTargetBlackListStatus` (the add-negatives word list on / off - documented as
   read-only in the `sparkx-edit-ai-group` and `sparkx-create-ai-group` field references, not in
   the query field reference; seen in an `aiGroup` read in 2026-11). The list itself
   (`negativeTargetBlackList`, word-library ids) and `negativeTargetListType` are **not**
   returned (read 2026-11), so whether the confirmed own-brand spellings from check g are on it
   can never be checked here. Report per group:
   - add negatives off: nothing to check;
   - on, word list off: "已开启自动添加否定，但没有设置词库——请在平台确认品牌词不会被否定" (a warning);
   - on, word list on: "已设置词库，但当前接口不返回词库内容——请在平台确认它包含你的品牌词";
   - a switch missing from the read: "当前接口无法确认".

   Never report it as passed, and never guess a field name. The brand-mode fields
   (`brandOptimization.brandedStatus`, `brandedList`, competitor fields) describe the group's
   brand / competitor mode, not the add-negatives list. Do not edit managed-group word lists
   through MCP - they are read-only. A schedule cannot carry them either: the server strips
   `brandOptimization` and the word-list fields of `targetOptimization` from a schedule, which
   keeps only its three switches and intensity fields - and an omitted switch is sent as `0`
   (`sparkx-edit-ai-group` SKILL.md, schedule rule 2).
