# Building the restore list

How to turn the operation log into "what a person changed for the promo, and what it was
before". Read the operation-log skill's SKILL.md first - pagination modes, the 90-day span,
truncation handling and the `createdDate` timezone rules all apply here and are not repeated.

## 1. One store, one window, several queries

- **One `profileId` per run.** Ad-entity timestamps are store-local only for a single
  profile; with several they turn UTC and the window boundaries shift.
- **Query from the window start to today**, not to the window end - you need the rows after
  the window to find items changed again later, by any source (they become "you decide").
  On a large store the part after the window can run to thousands of rows (a trial store had
  8,448 bid changes in the month after a promo). Then query the window first, and check the
  post-window part only for the objects on the list, in batches, with the same `entities` /
  `actionType` as the window query: `resourceIds` with `idEntity: campaign` and the campaigns'
  **Amazon** ids for the campaign, placement, target and ad-group queries (internal campaign
  ids return 0 rows **without an error**); `idEntity: aiGroup` with the **internal** group ids
  for managed groups. Portfolio caps take **no** `resourceIds` - `idEntity: portfolio` returned
  0 rows with both id kinds in a 2026-11 test; query the store's portfolio rows and match
  `entityId` (internal portfolio id) client-side. Never build "changed again later" from a
  partial page - say what was not checked.
- **One entity per query** - necessary for paging, **not sufficient**. If the `entities` +
  `actionType` / `operationType` combination still spans more than one of the server's
  resource groups, `page` is silently ignored and each branch returns its own first batch (see
  the operation-log skill, "Mode A"). So **read the mode from the response**, never from the
  request: `page` / `hasNextPage` in it -> loop `page` while `hasNextPage`; `limit` / `truncated`
  instead -> it is limit-only, and a "page 2" returns the same rows. When it truncates, narrow
  until it does not - `changeField`, a single `actionType` / `operationType`, consecutive
  non-overlapping date slices that together cover the whole range (never a range that drops days),
  `resourceIds` in batches - and say which slices were pulled. A multi-entity query is
  always limit-only, and managed-group rows are not narrowed by `actionType`, so they crowd out
  everything else and the result truncates.
- **No `changeBy` filter.** Classify sources yourself (section 2).
- **Always pass `changeField`** on the budget and bid queries (`dailyBudget` for campaign
  budgets; the bid field for bids - read it off one row first). Without it the bid query also
  returns the hourly bid overrides: tens of millions of rows on a large store, which cannot be
  paged.

| What | `entities` | Filter | Keep rows whose `changeField` is |
|---|---|---|---|
| Campaign budgets | `["campaign"]` | `actionType`: `Budget Increased`, `Budget Decreased` | `dailyBudget` |
| Placement multipliers | `["placement"]` | `actionType`: `Placement Increased`, `Placement Decreased` | the placement field the row reports |
| Keyword / target bids | `["target"]` | `actionType`: `Bid Increased`, `Bid Decreased` | the bid field the row reports (`bid` for keywords and auto targets, seen in production 2026-11) |
| Ad group default bids | `["adGroup"]` | `operationType`: `AdGroup Bid Increased`, `AdGroup Bid Decreased` | the bid field the row reports |
| Portfolio budget caps | `["portfolio"]` | `operationType`: `Budget Cap Increased`, `Budget Cap Decreased` | `amount` (seen in production 2026-11) |
| Paused during the promo | `["campaign"]`, `["adGroup"]`, `["productAd"]`, `["target"]` (one query each) | `actionType`: `Paused` | - (state rows; they go to "you decide", never restored automatically). `Paused` also covers paused **negative** keywords / ASINs / brands (they come back under `["target"]`) - drop those: pausing a negative widens targeting and is not a promo pause of a live ad |
| Enabled during the promo | `["campaign"]`, `["adGroup"]`, `["productAd"]`, `["target"]` (one query each) | `actionType`: `Enabled` | - (state rows; "you decide", never paused automatically). Something switched on for the promo keeps spending after it. Keep a person's rows and MCP rows that match a confirmed `status` row in the promo change log; drop enabled **negatives** (they narrow targeting) and objects created in the window (already listed as created). Rows read `operationType` `Campaign Enabled` / `Keyword Targeting Enabled` ..., `previousValue` `paused` -> `newValue` `enabled`. On/off switching from a dayparting tool shows as `Amazon Console` at a pace no person works at (one production store: 820 `Campaign Enabled` rows in under 3 months) - the "Amazon Console" rules below apply: recommend leaving that type out |
| Managed-group settings | `["aiGroup"]` | none (limit-only, `pageSize` up to 10,000; if `truncated`, split the window into consecutive non-overlapping day slices covering all of it) | `optimizeType`, `acos`, `aiPersonality`, `bidRangeMin`, `bidRangeMax`, any action-space switch, and any budget field |
| Lowered budgets: is the new budget binding? | `["campaign"]` | `operationType`: `Campaign Out of Budget`, post-promo days only | - (count events per campaign, only `newValue` `CAMPAIGN_OUT_OF_BUDGET`; `PORTFOLIO_OUT_OF_BUDGET` means the portfolio cap stopped it) |
| Created during the promo | `["campaign"]`, `["target"]` | `actionType`: `Added` | - |

**An empty managed-group result is not proof of no changes.** That query returns an empty list
when it fails internally, instead of an error. Cross-check with
`get_entity_metadata(entity='aiGroup')`: a group still on `targetType: 3` with no history, and
no dated schedule in effect today that carries goal `3`, means the history is unreadable ->
"you decide". `sparkx-promo-prep` gives goal `3` only to head groups, only on the event
schedule: other groups get goal `1` (a group already on goal `2` keeps it); under the goal
"profitable" every group keeps its current goal (goal `3` becomes `1`); with only one or two
schedule-eligible groups there are no head groups by default. So a group on `3` outside a running event schedule stands out.

**Managed-group rows are special.** SP/SB group rows are UTC (convert the window with the
store's `timezone` from `get_user_authorized_context`). **SD group rows use the server's own
clock, which is not documented**: widen the SD query window by a day on each side, never
convert those times to UTC, and decide "inside the window" and "first change" by the order of
the rows and their values - when a row sits near a window edge and its day is uncertain, put
the item in "you decide" and say why. All group rows can come back with `profileId` and
`campaignName` null, so identify the group by `entityId` (= `aiGroupId`) against
`get_entity_metadata(entity='aiGroup')` for this store. Their `operationType` strings in
production (2026-10) were not the ones in the operation-log skill's enum table - e.g. "The
objective of managed group AI has been adjusted", "The target value of managed group AI has
been adjusted", "The min bid has been adjusted", "Set max bid" - so **do not filter managed
groups by `operationType`**; pull them unfiltered and select by `changeField`.

**Schedule rows are not group settings.** A group row with a non-empty `aiGroupScheduleId` was
made on a schedule (a schedule save, or the monitor changing a running schedule's target), and so
is anything the promo change log records as `objectType` `schedule`, `scheduleTarget` or
`scheduleDelete` (an ended schedule prep deleted - nothing to restore). Those end with the
schedule (section 3, "Dated schedules"): never restore the group's own `acos`, `optimizeType`
or personality from them. A row with an empty `aiGroupScheduleId` is a direct group-setting
change only when it also matches no schedule save in the change log (same group, value and a
time within the matching tolerance of section 2) - an empty id does not prove there was no
schedule behind it (`sparkx-query-operation-log` SKILL.md, `aiGroupScheduleId`).

## 2. Which rows are a person's

| `changedBy` | Counts by default |
|---|---|
| an email address | yes - a user acting in the platform |
| `Manual` | yes - also a platform user |
| any operator with `operationSource` = `MCP` | only when it matches a confirmed-write row in the promo change log ("Matching a log row to the change log" below) - MCP is also used for ordinary work. Without the change log: show the count and ask once whether they belong to the promo; until then "you decide". Rows this reset run wrote itself are removed by the stale check |
| `Amazon Console` | **no by default - a source, not an operator.** Came from Amazon's side, author unknown. List separately as source-unknown with `suggestion: customerDecides`; restore only per-item on the user's say-so - **unless** the customer confirmed for this run that these changes were theirs ("Amazon Console" below), then they count like `Manual` |
| `AI`, `Automation`, `AI-Custom Rule`, `Budget Management`, `Lock Ranking`, `API`, `Labels`, `System` | no - unless the user asks to include them; then name the added sources in the list header |

Why not `changeBy: manual` on the query: **the server rejects it** (case-insensitive, in `IN`,
`NOT_IN` or mixed). It used to match only the literal value `Manual` (plus a platform-source
restriction), so changes attributed to a user's email disappeared — in a production test
(2026-10) every human promo change in one store was email-attributed and `manual` returned none
of them. Omit `changeBy` and classify client-side.

Classify on `changeField` as well as `changedBy`: `Amazon Console` also appears on status events
such as `Campaign Out of Budget`, which are not settings anyone changed.

### Amazon Console: the two cases that change how you ask

**(Nearly) every setting change in the window is `Amazon Console`** (count setting changes
only - leave out status events such as `Campaign Out of Budget`). Then the default list is empty
and the whole promo lands in "you decide" - useless to the customer. This happens when a team
works in Amazon's own console, or through a tool that writes via Amazon. Say so with the counts
("这段时间有 1,063 项改动，全部记为亚马逊后台") and ask **once** whether those
changes were theirs. Only on a clear yes, treat the `Amazon Console` rows of this run like human
rows - they get the normal pacing - and name the source in the list header as "亚马逊后台（已由你确认）". Without that yes, the per-item rule stands.

**A tool, not a person, keeps changing it.** If an object type keeps being changed after the
window at a pace no person works at (for example bids changed hundreds of times a day), say it
looks like an automated bid tool and recommend leaving that type out of the restore - restoring
would fight the tool. The customer decides. **This holds even after the customer confirmed the
`Amazon Console` rows as theirs**: ask about the tool-paced type separately ("about 600 bid
changes a day keep coming from Amazon Console - include those?"). A portfolio cap that changes
every hour is the same case: a pacing tool, not a person's ceiling.

### Matching a log row to the change log

A log row matches a change-log row when all of these hold:

| | Log row | Change-log row |
|---|---|---|
| Object | `entityId` (internal id; for a placement, `entityId` = the campaign + the placement field) | `internalId` |
| Field | `changeField` | `logField` - or, in an older file without it, the mapping below |
| Value | `newValue` | `readBackValue` (or `valuePlanned` when the read-back is missing), compared as numbers |
| Time | `createdDate`, in the row's clock | `writtenAt` converted to that clock - store-local for ad entities on a one-store query, UTC for SP/SB managed groups - within **10 minutes**. SD group rows have no known clock: match by object, field and value, and by order |

Older change logs carry only `field`. Map it: `dailyBudget` -> `dailyBudget`; `keywordBid`,
`targetBid` -> `bid`; a placement -> the placement's write field (`topAdjustment`,
`restOfSearchAdjustment`, ... - the log reported the write field itself in a 2026-11 test);
`targetType` -> `optimizeType`; `acos`, `aiPersonality` -> the same; a portfolio cap ->
`amount`. Anything else: match on object, value and time only, and say the match is weaker.

A change-log `needsReadBack` row cannot be settled by reading the object now - people and the
monitor have changed it since. Settle it against the log instead: a matching MCP row (same
object and field, `newValue` = `valuePlanned`, near `writtenAt`) means the write applied; with
none, treat the row as unconfirmed.

**AI's hourly budget rows are not promo changes.** In a managed group, AI rewrites the day's
spendable budget every hour - `changeField: currentBudget`, ramping from a few dollars at
midnight up to the cap. A few days produce hundreds of rows. Only `dailyBudget` (the cap a
person sets) is restored.

## 3. Pre-promo value, current value, and the buckets

Group rows by object + field: (`entity`, `entityId`, `changeField`; for placements also the
placement). Sort ascending by `createdDate` (the log is newest first).

- **Pre-promo value** = `previousValue` of the **first human row inside the window**. Everything
  after it inside the window is promo-time churn, including a blanket "set everything to $100"
  on the last day.
- **Creation rows are not pre-promo values.** An empty / null `previousValue` means the object
  or setting was created then. For budgets, bids, target ACOS and objective a `0` means the
  same thing (e.g. target ACOS `0 -> 31.15` when a group is created). **For placement
  multipliers `0` is a real value** (no uplift) - keep it. When the **first** row of a field in
  the window is a creation row, that field has no pre-promo value: it counts as created in the
  window ("you decide"). Never take the next row's `previousValue` instead - that is a
  promo-time value.
- **Current value**: read it with `get_entity_metadata` (campaign `dailyBudget`, keyword
  **`keywordBid`** / target **`targetBid`**, ad group `defaultBid`, `portfolio`
  `portfolioBudget`, campaign placement rows, `aiGroup` `targetType` / `targetAcos` /
  `aiPersonality` - or the per-action-space personality fields on accounts that have them -
  / `aiActionSettings`). For bids this is the field a write changes and read-back checks
  (`sparkx-edit-ads` `write-keyword.md`: read `keywordBid` back, never `keywordCurrentBid`) -
  use it for `valueBeforeRun`, `expectedCurrentValue` and read-back. `keywordCurrentBid` is only
  for the bid audit of section 5. The log's last `newValue` is a cross-check, not the source of
  truth.

Check the rows of this table **in order** - the first that applies wins:

| Situation | Bucket |
|---|---|
| The campaign is archived | Skip - it cannot be written; count it |
| Current = pre-promo | Skip (count it) - already restored, whoever did it |
| Current < pre-promo (numeric fields) | Lowered -> you decide, with the "is it binding" note. **Never written upward** as part of "restore all": a later lower value is a newer decision. If the promo change log shows the cut came from the monitor (`skill = promo-monitor`, `reason` "cut below pre-promo, user confirmed"), say so and offer to restore it to the pre-promo value as its own yes |
| Changed again **after** the window - by any source (a person, Amazon's side, a rule, AI, a tool) except this run's own writes | You decide - do not overwrite a newer decision |
| A managed group's AI was switched on or off in the window (the group's on/off row, whatever `changeField` the log reports for it) | You decide - list who switched it and when; never switch it back on your own |
| AI changed the same field after the last human change (bids in a running group) | You decide - AI is managing it and may move it again |
| The object was created inside the window | You decide - pause or keep; there is no "before" |
| Current value != the log's last value | You decide - something changed it outside what the log shows |
| Raised by less than 10% (budgets and bids) | You decide - probably routine adjustment, not a promo change; list the count and their daily spend, restore only what the user picks |
| Current > pre-promo (numeric fields) | Raised -> pace it ([`pacing-rules.md`](pacing-rules.md)). If the campaign is paused, say a restore changes nothing until it is enabled |
| Objective / switch differs from pre-promo | Restore with the group settings |

**Dated schedules.** A group that used a dated schedule for the promo shows schedule rows, not
setting changes, and the schedule reverts on its own when it ends. Judge **each schedule**, not
the group, and check its end date before saying anything:

1. Read `get_entity_metadata(entity='aiGroup_schedule')` for every group that had schedule rows
   in the window, is in the promo change log, or is still on goal `3` - **including a group due
   the section 5 audit whose schedules the change log already covers**: only this read shows the
   weekly and other schedules in effect. Exactly one `profileId` and one `filters.aiGroupId` per
   call, rate-limited (about 120 calls a minute); say which groups were not read. The change
   log's `scheduleId` / `scheduleWindow` is a cross-check. Take the store's current date from its
   `timezone`.
   **Only dated schedules (`timeType=1`) are judged.** A weekly schedule (`timeType=2`) has no
   start or end date (`sparkx-query-entity-metadata` field reference): list it as information
   only - not "you decide", no reminder row, no audit (on its weekdays it still delays the
   group's audit, section 5). A dated schedule is **from the promo** when the promo change log
   has it, it was saved inside the window (section 2), or its dates overlap the window - even if
   it was saved before the window or has no log row. Any other (dates entirely outside the
   window, not in the change log, not saved in the window) is information only too - no reminder
   row, no audit of its own (while in effect it still delays the group's audit, section 5).
2. A schedule whose `endDate` is **before** today is **ended**: list it as "已随排期结束".
   Its goal, target, personality and schedule action space need no restore, but its group's bids
   get the check in section 5 because ending a schedule does not force every current bid back
   into the normal range immediately.
3. A schedule whose `endDate` is today or later is **still in effect**: list it separately as
   "排期仍在生效，{日期}结束", with its goal and target. `sparkx-promo-prep` builds no schedule
   past the event end, so this is a schedule someone else made or extended, or a reset run
   inside the window; check who saved it (section 2). It is not restored and not called expired.
   Tell the user when it ends.
   A promo schedule (step 1) gets a reminder row in the plan file - `held`, `holdReason:
   scheduleRunning`, `holdUntil` = the end date, never written; after that date "继续复位"
   with the same file confirms it ended, runs section 5 for that group, records the
   result in the row's `bidAudit` and then marks it `ended` - or keeps it `held` while another
   schedule delays the audit (section 5; `execution-safety.md` sections 1 and 3). The group's direct setting rows (point 5) are judged now as usual; only if the user
   wants one left alone until the schedule ends is that **setting row** held
   (`waitForSchedule`) and judged like any held row afterwards.
   Ending it early means deleting that schedule (`save_sp_sb_ai_group_schedule` with
   `operation: "delete"` and its `id`, following `sparkx-edit-ai-group` "Scheduling"); only
   when the user asks for that schedule by name, never from a read row.
4. A dated schedule whose end date cannot be read goes to "you decide" (a weekly one is
   information only - step 1).
5. **The schedule does not cover direct changes.** If the same group's total budget, bid range,
   action-space switches or AI on/off were also changed directly in the window, those still
   follow the table in section 3 as their own rows. A group is never skipped as a whole because
   it had a schedule.

## 4. From a log row to a write

Every write goes through its owning skill, with internal ids and discriminator fields from
`get_entity_metadata` - the log's `entityId` is a hint, never the write id without checking.

| Log row | Write | Notes |
|---|---|---|
| `campaign` / `dailyBudget` | `sparkx-edit-ads`: `campaign` + `updateBudget`, `budget.type: setTo` | One `campaignType` per batch. For a campaign inside a managed group this is the campaign's own daily budget - do **not** edit the group total, which rescales every enabled campaign |
| `placement` | `sparkx-edit-ads`: `campaign` + `updatePlacementBid` | Take the write field from the placement row's `writeField` (`get_entity_metadata(entity='placement')`). In a 2026-11 test the log's `changeField` was already the write field (SP `topAdjustment`, `restOfSearchAdjustment`); the `placementTypes` filter and the operation type use the label `topSearchAdjustment`, which is SP `topAdjustment` / SB `topOfSearchAdjustment`; SB also uses `homeAdjustment`, `detailPageAdjustment`, `otherAdjustment`; SP `productPageAdjustment`. Values are absolute percentages 0-900 (SB integers only); send only the placements you restore. **On SB the write also sets `bidOptimization=false`** (custom bidding) - tell the user first. The Amazon Business adjustment is logged on the campaign entity, not under `["placement"]`, and has no write route here - out of scope |
| `target` bid | `sparkx-edit-ads`: `keyword` + `updateBid` or `target` + `updateBid` | Resolve the row (keyword vs target, `matchType`, `campaignType`) from metadata first |
| `adGroup` default bid | `sparkx-edit-ads`: `adGroup` + `updateBid` | **SP and SD only** - SB has no default-bid route: list an SB row with its pre-promo value for the user to change in the platform. One `campaignType` per batch; always confirms; the server checks the bid against the marketplace range and the campaign's daily budget (SD: strictly under half of it) - the pre-promo bid fitted the pre-promo budget, so write budgets first (SKILL.md Step 5 order), and read the error rather than guessing a bound |
| `portfolio` budget cap | `sparkx-edit-ads`: `portfolio` + `updateBudget` | Always confirms. A cap is the user's money ceiling for every campaign in the portfolio - restore it with the budgets, and keep the portfolio's budget type and dates as they are now unless those were changed in the window too |
| `Paused` rows | none by default | Someone stopped it during the promo - a decision, not an adjustment. List it under "you decide" with who paused it and when; re-enable only items the user names, through the owning `updateStatus` route in `sparkx-edit-ads` |
| `Enabled` rows | none by default | Someone switched it on during the promo. List it under "you decide" with who enabled it, when, and its post-promo spend (performance-based mode); pause only items the user names, through the same `updateStatus` route |
| `aiGroup` / `optimizeType` | `sparkx-edit-ai-group`: SP/SB `targetType`; SD `optimizeType` | `1` 推动增长, `2` 保持订单稳定, `3` 活动冲量, `4` 推动增长（预算优先消耗；推动增长的激进变体，不是旧值；仅 SP）(a group goal, but a schedule cannot carry it). SD groups use the SD tool and shape - e.g. its `acos` needs `acosType` - follow that skill |
| `aiGroup` / `acos` | `acos` | Same percent scale on both sides (`248.115` in the log = 248.115%) |
| `aiGroup` / `aiPersonality` | `aiPersonality` - or, on accounts with per-action-space intensity, the per-action-space `*AiPersonality` fields (the group-level field is rejected there; `sparkx-edit-ai-group` `ai-personality.md`) | `targetType 3` requires `aiPersonality >= 3`: when restoring both, send them in the same request. Restore each action space's own pre-promo value |
| `aiGroup` / `bidRangeMin`, `bidRangeMax` | `aiActionSettings` bid range | Written as one `[min, max]` pair (both required, **min strictly < max** - equal ends are rejected). A log row usually changes one bound: rebuild the pair from the current value plus the restored bound. Keep the group's current `bidRangeType`. If a pre-promo bound was unset (`0` or empty, shown as "Set max bid"), do not guess how to clear it - show it and let the user decide or change it in the platform |
| `aiGroup` total budget | `sparkx-edit-ai-group` group budget | Editing the total rescales every enabled campaign's daily budget proportionally. If the promo change was to the group total (an aiGroup budget row, or all of a group's campaign budgets moving together at one timestamp by one person), restore the **total** and do **not** also restore those campaign rows one by one. If unclear which the user changed, ask. **Other campaign rows in that group** (budgets a person raised on their own) are re-based by the total write: right after it, re-read those campaigns, set each row's `expectedCurrentValue` to the re-read value and `rebasedAt` to the group write's time - **never `valueBeforeRun`**, which stays the undo value - treat the `dailyBudget` rows logged at the group write's time as this run's own (`execution-safety.md` section 2), and show those rows again in the preview with their new "now" before writing them |
| `aiGroup` / other action-space switches | `sparkx-edit-ai-group` | Follow that skill's action-space and coupling rules; when unsure, list it as "you decide" |

SP/SB group edits merge onto the current configuration: send only the restored fields. SD
groups use the other tool and shape - follow `sparkx-edit-ai-group`.

## 5. Bid audit after a dated schedule ends

This is an audit, not an automatic restore. **Run it once per group**, after the group's last
promo schedule (warm-up or event - section 3 step 1) has ended, and only when no schedule of
that group, promo or not, is in effect today: the `aiGroup` read returns the currently
effective configuration, so while a schedule runs it shows the schedule's bid controls, not the
group's own. A dated schedule is in effect from its `startDate` to its `endDate`; a weekly one
(`timeType=2`) only on the days in its `weekDays` (read encoding `1`=Monday ... `7`=Sunday),
checked against today's weekday in the store's timezone.

**When another schedule blocks the audit**, record `scheduleStillRunning` and keep the group's
reminder row `held` (`holdReason: scheduleRunning`) - never `ended`, which would drop the audit.
A group whose promo schedules have all ended gets that row now (its last promo schedule's id and
window). `holdUntil` = the day before the first day no schedule of the group is in effect: a
dated schedule's end date; for a weekly one, the day before the next day not in its `weekDays`.
A weekly schedule on all seven weekdays never leaves room: once the promo schedules have ended,
record `notVerifiable` with the note "check the bids in the platform" and set the row `ended`.

1. Read the group's all-time effective bid controls (`aiGroup`): bid-range status, type and
   bounds, plus the enabled placement ranges. With `bidRangeStatus=0` the read has no
   `bidRangeType` / `bidRange` (`sparkx-query-entity-metadata` `ai-group-effective-config.md`):
   record `noRange` - the group has no bid range, nothing to compare - and skip step 2. Then
   read the current keyword/target bids for the group's campaigns. Scope the read to those
   campaigns; do not scan the whole account.
   **Which bid field**: a keyword's live bid is `keywordCurrentBid` when it is above 0 (the AI's
   override), else `keywordBid`; a product target's is `targetBid` (a decimal string - parse
   it). Never audit `keywordBid` alone in an AI-managed group: the AI moves
   `keywordCurrentBid`, so a raised bid would be invisible and the audit would read
   "within range" falsely. If every keyword of the group reads `keywordCurrentBid` 0 while its
   AI is running, the AI's live bids are not recorded in this read
   (`sparkx-query-entity-metadata` field reference): mark the keywords `notVerifiable`, not
   `withinRange`.
2. With a **fixed-value** bid range, count and list current bids above the all-time maximum (and
   below the minimum when that matters), largest spend first. A **coefficient** range is always
   `notVerifiable`: the base bid it multiplies is not reliably readable, so no currency
   boundary can be computed - say so and point to the platform. Placement multipliers and Amazon bidding strategy can make the final
   auction bid differ from the base range, so do not call this a final-bid guarantee.
3. Say that the schedule settings have reverted but current bids may need another AI optimization
   cycle to move back. Recommend rechecking after the next cycle. Do not write fixed bids inside
   a running AI-managed group: the AI can overwrite them.
4. Only when the user explicitly asks to change named bids, show a separate preview through
   `sparkx-edit-ads` and use its confirmation rules. Before the preview, say that the audit read
   the live bid (`keywordCurrentBid` when above 0) while `sparkx-edit-ads` writes and reads back
   `keywordBid`: the AI's live bid may stay out of range, and the AI may rewrite it. After the
   write, run this audit again for those keywords - never take the edit's read-back as proof
   the live bid is in range. This is not a schedule restore row and is never preselected by
   this skill.
5. Record the audit as `withinRange`, `outsideRange`, `notVerifiable`, `noRange` or
   `scheduleStillRunning`, with counts and the evidence used - in the report (`bidAudit`) and,
   for a schedule that has a reminder row, in that row's `bidAudit` column of the plan file
   (`execution-safety.md` section 1). It does not become a restore-plan write row unless the
   user separately approves a bid edit.
