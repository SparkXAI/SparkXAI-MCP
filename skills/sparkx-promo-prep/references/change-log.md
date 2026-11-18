# The promo change log

One file per store and event, written by `sparkx-promo-prep` and appended to by
`sparkx-promo-monitor`. MCP keeps no state between conversations: this file is how the next
step knows what was planned, what was written and what each value was before. Hand the updated
file to the user after every write (CSV or Excel).

`sparkx-promo-reset` does not need it - it rebuilds everything from the operation log, where
every write made through MCP carries `operationSource` = `MCP` (advertising entities and managed
groups, schedule saves and group deletes included; older managed-group delete and schedule rows
may show `PAGE`).
The file is a cross-check for the reset and the resume state for prep and monitor. It is also
how the reset tells the promo's MCP writes from other MCP work: without it, the reset asks the
user before restoring MCP rows.

## Columns

One row per object + field.

| Column | Content |
|---|---|
| `runId` | One id for the event plan (e.g. store + event + creation time) - an identifier only, never parsed for times |
| `profileId`, `timezone` | The store and its IANA timezone |
| `event`, `eventStart`, `eventEnd`, `warmupStart` | As confirmed in prep Step 1 |
| `budgetMode` | `dailyCap` (the event budget is a cap for every day) or `windowTotal` (a total for the whole window) |
| `eventBudget` | The amount the user gave: per day for `dailyCap`, for the whole window for `windowTotal` |
| `dailyCap` | With `windowTotal`: a per-day cap the user also gave, else empty |
| `goal`, `hardLimit`, `nonBrandLimit` | `max` / `profit`; the hard ACOS (or ROAS) limit; a separate limit for non-brand terms, if any |
| `ceilingAcos`, `targetAcos`, `floorAcos`, `raiseAcos`, `holdUpperAcos` | All as percent ACOS (a ROAS is stored as 100 / ROAS). `ceilingAcos` = the ceiling (push-plan.md section 2) - the monitor's limit when there is no hard limit; `raiseAcos` = min(target, floor, hard limit) - the one threshold for every raise in prep and the monitor; `holdUpperAcos` = min(floor, hard limit) - the top of the hold band. One store value, or per managed group plus one for campaigns outside groups when each group's own target sets it |
| `nonBrandRaiseAcos`, `nonBrandHoldUpperAcos` | Only when a `nonBrandLimit` was given: the same two lines with the non-brand limit in the hard limit's place (push-plan.md section 2), at the same level (store, or per group). Campaigns with `brandClass: nonBrand` use these instead of `raiseAcos` / `holdUpperAcos` - in prep and in the monitor |
| `brandClass` | On campaign rows: `brand` / `nonBrand` / `mixed` from health-check g, so the monitor applies `nonBrandLimit` to the same campaigns |
| `dealAsins`, `leaveAlone` | Deal ASINs with their dates and discount; campaigns never to touch |
| `brandNames`, `competitorBrands` | As the user confirmed them (health-check g) |
| `groupClass`, `groupClassSource` | On managed-group schedule rows: `head` / `defensive` / `other` (under "profitable" only `defensive` / `other` - push-plan section 6); source = named focus, user confirmation, or the spend-based candidate rule. A candidate is never recorded as confirmed until the user agrees |
| `group30Acos`, `group30Orders`, `scheduleBase`, `scheduleMultiplier` | The evidence for a schedule target: actual Group-30 ACOS and orders; `scheduleBase` = `group30Actual`, `currentTargetFallback` or `userTarget` (a target the user gave for a group with neither); the confirmed multiplier from push-plan section 6 |
| `referenceEvent` | The event, its dates and its comparison window |
| `dayRoles` | The day-role table the user confirmed (date, role, multiple, the day's budget), so the monitor sets each next day's budgets from it |
| `scope` | The scope the user chose in prep Step 1 (whole store / main campaigns / named products), with its rule, the date it was computed and the campaign ids, so the monitor reuses the same set. The reset does not narrow by it - it restores every promo change it finds |
| `skill` | `promo-prep` or `promo-monitor` |
| `objectType` | `schedule`, `scheduleDelete` (an ended dated schedule deleted to make room - `valueBefore` holds its id, window, goal and target; nothing to restore, it would never run again), `scheduleTarget` (the monitor changing a running schedule's target ACOS), `groupTotalBudget`, `groupSetting`, `portfolioBudget`, `campaignBudget`, `keywordBid`, `targetBid`, `placement`, `status` (a pause or enable by the monitor; `field` = `state`) |
| `writeRoute` | e.g. `save_sp_sb_ai_group_schedule`, `campaign+updateBudget` |
| `internalId`, discriminators | Everything the write needs (`campaignType`, `matchType`, `aiGroupId`, ...) |
| `amazonId`, `name` | What the user sees |
| `field` | e.g. `dailyBudget`, `keywordBid`, `topOfSearch`, `targetType`, `acos` |
| `logField` | The operation log's `changeField` for this write, so a later run can match the log row to this one: `dailyBudget` (campaign budget), `bid` (keyword and target bids), the placement's write field (`topAdjustment`, `restOfSearchAdjustment`, ... - the placement row's `writeField`), `optimizeType` (group goal; the write sends `targetType`), `acos`, `aiPersonality`, `amount` (portfolio cap), `state` (status). Empty when not known - the match then uses object, value and time only |
| `valueAtPlan` | The object's value read when the plan was built (prep) or when the monitor first proposed the row - set on every row, written or not. A resumed run compares the current value with it before writing a row that is still `planned`; the monitor's pre-promo floor uses it when the object has no confirmed write yet |
| `valueBefore` | The value read just before this write. For a schedule: empty (it is new). Empty on a row that has not been written yet |
| `valuePlanned` | What the plan says: the **final** value after prep's fit-the-total scaling, not the pre-scaling figure |
| `targetDate` | For day-role budget rows: the event day this value is for (store date). Empty for changes that are not tied to one day |
| `writeOn` | `now` / `preWarmup` (the day before warm-up starts) / `eve` (the day before the event start) / a date - push-plan.md section 8 |
| `writtenAt` | ISO 8601 with offset, empty until written |
| `writeResult`, `readBackValue` | `ok` / `failed` / `ambiguous`, and what read-back showed |
| `scheduleId`, `scheduleWindow`, `phase` | For schedules: the id read back after creation, start-end, and `phase` (`warmup` / `event`; one row per phase) |
| `reason` | The one-line reason shown to the user, with its numbers |
| `status` | `planned` (confirmed, not written yet - every row of a confirmed plan starts here; prep writes it on its `writeOn` day, or the monitor writes a day-role row), `written`, `failed`, `needsReadBack`, `skipped`, `changedByOthers`, `fulfilled` (a `planned` day-role row that a later monitor row wrote - the write itself is that later row). When **prep** writes one of its own `planned` rows it fills `valueBefore`, `writtenAt`, `writeResult` and `readBackValue` on that same row and sets its status - no second row |

The plan columns (`budgetMode` to `dayRoles`) are the same on every row; they are what the
monitor reads instead of asking again.

## Rules

- **Schedule snapshot (monitor only).** The monitor's once-a-day read of the managed-group
  schedules (monitor `pace-and-states.md` section 2) is stored next to the change rows, never as
  one: in Excel a separate sheet `schedule_snapshot`; in CSV a companion file
  `<change-log name>-schedule-snapshot.csv` handed over with the log. One row per group per read:
  `storeDate`, `readAt`, `aiGroupId`, `aiGroupName`, `scheduleId`, `timeType`, `startDate` /
  `endDate` (or the weekdays of a weekly schedule), `optimizeType`, `acos`, `budgetDynamicStatus`,
  `numType`, `num`, `budgetRedistributeStatus`, `enabledCampaignCount` (empty = not returned). A
  re-read adds rows; for a group and store day the latest `readAt` wins. For one `scheduleId`, the
  earliest row across the whole promo window gives the phase's initial `acos` (the day's earliest
  row only shows where that day started). Prep and reset ignore it.
- **`valueBefore` is read right before the write**, not taken from the plan. Compare it with the
  **latest confirmed value this plan wrote** for that object + field (the latest
  `readBackValue` of a `written` row, prep's or the monitor's) - or, if the plan has not written
  it yet, with the row's `valueAtPlan`. If it differs, someone changed it since: show the
  row again and ask; never overwrite silently (`changedByOthers`).
- **The plan's own writes are not "someone else's change".** Every write made through MCP is
  logged with `operationSource` = `MCP`. Before treating an operation-log row as another
  person's change (the monitor's "changed today", any stale check), drop the rows that match a
  `written` row of this file: same object, `changeField` = its `logField`, `newValue` = its
  `readBackValue`, and a time within 10 minutes of its `writtenAt` (converted to the row's
  clock: store-local for ad entities on a one-store query, UTC for SP/SB managed groups; SD
  groups by order and value only).
- **The first `valueBefore` for an object + field is the pre-promo value - among confirmed
  writes only.** Count only rows whose write is confirmed: `status = written`, or a
  `needsReadBack` row whose read-back shows the written value. `planned`, `fulfilled`,
  `failed`, `skipped` and `changedByOthers` rows are not writes (or not writes this plan made),
  so their `valueBefore` is never a restore target. "First" means the **earliest `writtenAt`**,
  not the row order in the file. Later rows (the monitor's) keep their own `valueBefore` but
  never replace it.
- **An `ambiguous` write is `needsReadBack`**, never `written`. Read back first next time,
  and settle it (`written` or `failed`) before anyone builds a restore target from the file.
- **Day-role budgets are planned per campaign and per day.** When the confirmed plan has day
  roles, prep writes only the budget day push-plan.md section 8 gives it - the warm-up start
  for non-brand campaigns when there is a warm-up, the event start when there is none; brand and
  mixed campaigns with a warm-up get no prep-written day - and records **one `planned` row per
  monitor-owned day for every campaign the plan raises** (not for every campaign in the store),
  whether or not prep itself writes any of its days. For brand and mixed campaigns with a
  warm-up that means rows from the event start on - prep writes none of their budgets, so
  without these rows nobody would raise them:
  `targetDate` = that day, `writeOn` = the date the monitor writes it, `valuePlanned` = the
  final budget after the fit-the-total scaling (push-plan.md section 3). The monitor reads these
  rows instead of recomputing them. When it writes one, it appends its own row
  (`skill = promo-monitor`, `valueBefore` read right before the write, its own `writtenAt` and
  `status`) and, **in the same update of the file**, sets the planned row to `fulfilled` - never
  to `written`: the planned row has no `valueBefore`, and the write must be counted once. If it
  writes a different value, the planned row becomes `skipped` and the new row's `reason` says
  why. A planned row left `planned` after its write would be written again by the next check's
  catch-up.
- **Schedules**: one row per phase with `field` = `acos` and `valuePlanned` = the target ACOS
  the user confirmed. Without a hard limit, a target above the ceiling without its own yes is
  planned at the ceiling, the cut named in `reason` (push-plan.md section 6). A current target
  above the hard limit (or the floor) that the user declined to tighten is planned at that
  current target, the decline named in `reason`. The row being in the confirmed plan is
  the confirmation: the monitor caps such a target only by the hard limit (and the floor under
  "profitable"), not by the ceiling - and never re-offers a tightening the user declined. Record the window and the schedule id from the read-back. They end on their own;
  the reset compares each window's end date with the store's current date and lists a schedule
  as ended only after that date has passed.
