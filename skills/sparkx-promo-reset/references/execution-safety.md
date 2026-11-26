# Execution safety: plan file, stale check, resume and undo

The detail behind SKILL.md Step 5. Read it before the first write of a run, and again before
continuing or undoing a reset. SKILL.md keeps the rules that may never be skipped; this file
says exactly how to carry them out.

## 1. The plan file - undo file and resume state in one

Before the first write, re-read the current value of every item about to change
(`get_entity_metadata`) and give the user a file (CSV / Excel), one row per object + field:

| Column | Content |
|---|---|
| `runId` | One id for this restore run (e.g. store + window + creation time) - an identifier only, never parsed for times |
| `profileId`, `timezone` | The store and its IANA timezone (e.g. `America/Los_Angeles`) |
| `staleCheckFrom` | The point from which "nobody else wrote since" is checked for rows not yet written. **Record it immediately before the first restore-list log query starts**, and use that one value for every row of the run - never the time the queries finished or the plan file was created, or a change made in between would be in neither the list nor the check. A change caught by both the list and the check stops that item, which is the safe side. ISO 8601 with offset, e.g. `2026-10-12T09:30:00-07:00` |
| `objectType`, `writeRoute` | e.g. `campaignBudget` / `campaign+updateBudget`, `aiGroup` / `save_sp_sb_ai_managed_group` |
| `internalId`, discriminators | Everything the write needs: `campaignType`, `matchType`, `businessType`, `aiGroupId`, `profileId` (string) ... |
| `amazonId`, `name` | What the user sees |
| `field` | e.g. `dailyBudget`, `targetType`, `topAdjustment` |
| `prePromoValue` | The restore target |
| `targetSource` | `log` (built from the operation log) or `file` (from the customer's upload - see [`from-file.md`](from-file.md)) |
| `valueBeforeRun` | Current value before this run's first write - **the undo value** |
| `steps` | Every planned value, in order (one entry for a one-time restore) |
| `lastCompletedStep` | `0` at creation; the index of the last step confirmed by read-back |
| `expectedCurrentValue` | What the object should hold now if nobody else touched it - **`valueBeforeRun` at creation** |
| `writtenAt` | When the last step was written, ISO 8601 with offset like `staleCheckFrom` (empty at creation) |
| `writeResult`, `readBackValue` | Outcome of the last write (`ok` / `failed` / `ambiguous`) and what read-back showed |
| `rebasedAt` | Set when a group-total write this run made rescaled this campaign row: the group write's time. The row's `expectedCurrentValue` was re-based then; `valueBeforeRun` never changes. Empty otherwise |
| `holdUntil`, `holdReason` | For a `held` row: the store date after which it is looked at again, and why - `dealRunning` (the deal's end), `holidayHold` (the user's date), `scheduleRunning` (a schedule row; its end date, or the date its group's bid audit waits for - `restore-list.md` section 5) or `waitForSchedule` (a group setting row the user chose to keep until the group's schedule ends). Empty otherwise |
| `bidAudit` | Schedule reminder rows (`scheduleRunning`) only: empty while the promo schedule runs; `scheduleStillRunning` while another schedule delays the audit; then the group's bid-audit result (`restore-list.md` section 5) - `withinRange`, `outsideRange`, `notVerifiable`, `noRange` or `scheduleStillRunning`, with checked and outside counts, e.g. `outsideRange 12/340`. Empty on every other row |
| `status` | See section 3; `planned` at creation, or `held` for an item that waits |

**Held items belong in the file too.** An item that waits is not left out. There are two kinds,
and they end differently (section 3):

- **A restorable row that waits** (`dealRunning`, `holidayHold`, `waitForSchedule`): a normal
  row with `status: held`, `prePromoValue`, `valueBeforeRun` and `expectedCurrentValue` as for
  any row, and `steps` empty - they are decided when the hold ends. `waitForSchedule` is only
  for a direct group setting (say the group total budget) that the user wants left alone while
  a schedule still runs: the **setting row** is held, the schedule itself is not restored.
- **A schedule still in effect, or a group whose bid audit waits** (`scheduleRunning`): a reminder row, never written -
  `objectType: schedule`, `field: scheduleWindow`, the schedule id and window, no
  `writeRoute`, no `steps`, `prePromoValue` and `valueBeforeRun` empty. The schedule ends on its
  own; the row only makes the next run check that it did. Its `bidAudit` (table above) is
  filled before the row is set to `ended`.

**Update the file after every write and read-back, and hand the updated file back to the
user.** MCP keeps no state between conversations: the next day's "继续复位" works
only from this file (or, in the same conversation, the latest version of it). If the user
cannot provide it, say the run cannot be resumed reliably and rebuild a fresh restore list
instead.

## 2. Stale check - before every write, including resumed steps and undo

Two conditions, both required:

- **The value matches.** The current value equals `expectedCurrentValue`, compared as numbers
  at the field's precision (`"50"`, `"50.0"` and `"50.00"` are equal; money to the currency's
  minor unit, placements to whole percent on SB, `targetType` as an integer).
- **Nobody else wrote since.** Query the log for this object and field from `writtenAt` (or
  `staleCheckFrom`, for a row never written) to now.
  - Both times carry an offset, so convert them to the clock of the rows you compare against:
    store-local for ad-entity rows on a single-profile query, **UTC for SP/SB managed-group
    rows**; SD group rows have no known clock - compare them by order and value, not by an
    exact time.
  - The log's `dateStart` takes a date only - query from that day and drop earlier rows by
    timestamp.
  - Remove the rows this run produced - same field, `newValue` equal to a step this run wrote
    (for an undo, `valueBeforeRun`), at its `writtenAt`. Every write made through MCP is logged with `operationSource` = `MCP` -
    advertising entities and managed groups alike, including schedule saves and group deletes -
    so match on `operationSource` = `MCP` + object + field + `newValue` + `writtenAt`. Older
    managed-group delete and schedule rows may still carry `PAGE`; for those, match on object,
    field, value and time alone.
  - **A group-total write rescales its campaigns**: the campaign `dailyBudget` rows logged at
    the time of a group-total write this run made (or undid) are this run's own too, for the
    rows that carry that group write's time in `rebasedAt` (`restore-list.md` section 4).
  - **Any other row on that field, from any source, -> stop**: set `stoppedChangedByOthers` and
    ask, even if the value has since been set back to the expected one - a change made and
    undone is still someone else's decision about that object.

For a row that has not been written yet, also: if the current value differs from the log's
last value, something changed it outside what the log shows - move it to "you decide"
(`status: customerDecides`, section 3).

### Run it per write batch, not per object

A restore can touch hundreds of budgets or bids. Checking them one by one means hundreds of
calls, rate limits and a long run. Check each **write batch** - the batch you are about to send
(one `campaignType`, within the write skill's cap) - as a whole, right before sending it:

1. **Current values: one `get_entity_metadata` read per write type in the batch**, filtered with
   `in` on that entity's identity field (table below), `pageSize` large enough for the batch,
   paging while `hasNextPage`. Match each returned row to its plan row by "Match by".
2. **The log: one `get_operation_log` query per write type**, with `dateStart` = the earliest
   `writtenAt` / `staleCheckFrom` among the batch's rows. Match each log row to its object by
   the row's `entityId` (the **internal** id) - plus `changeField` where the table says so -
   then compare it with that object's own `writtenAt` / `staleCheckFrom`, dropping rows that are
   earlier for that object. Page while `hasNextPage`; a limit-only response must not be
   `truncated` (step 3).
3. **If a query cannot cover the batch** - the response is `truncated`, or the tool rejects the
   number of ids - split the batch into smaller fixed slices (for example 50 objects) and check
   each slice, or split the time range ("Reading a window completely" below); never fall back
   to one call per object, never move the start date later, and never treat a truncated result
   as "nobody wrote". Under `rate_limited`, wait the `retryAfterSeconds` it returns.
4. **Failures stay local.** An object that fails either condition is taken out of the batch and
   marked (`stoppedChangedByOthers`, or `customerDecides` for a row never written); the rest of the
   batch is written. Say which objects were taken out and why.

A batch is written right after its check. If the user's confirmation or anything else delays
the write noticeably (minutes, not seconds), check the batch again.

### Reading a window completely

A limit-only response that comes back `truncated: true` is missing rows - and they can be from
any part of the window. **Never move the start later or the end earlier**: that drops changes at
the edge and the write would then overwrite them. Instead:

1. Split the whole window into **consecutive, non-overlapping sub-windows that together cover
   every day of it** - the log takes dates only, so whole days (for example halve it, or one
   query per day).
2. Query each sub-window with the same filters; split any sub-window that is still `truncated`
   again, down to a single day.
3. Merge all the rows, then match them to the batch's objects by `entityId` and each object's own
   `writtenAt` / `staleCheckFrom`.
4. **A single day that is still `truncated`** cannot be read completely: stop the batch and say
   so - do not write it. (With `resourceIds` available, slicing the batch's objects is the other
   way to get under the limit - step 3 above.)

This is the operation-log skill's rule for limit-only queries ("Split the date range into
non-overlapping sub-windows and recurse"), applied to the stale check.

### Query shapes per write type

Tried live, read-only, on two production stores (2026-11-16). Every current-value filter below
returned exactly the requested rows.

| Write type | Current values (`get_entity_metadata`) | Match by | Log query (`get_operation_log`) | Match log rows by |
|---|---|---|---|---|
| Campaign budget | `entity: campaign`, `{"campaignId": {"in": [...]}}` | `campaignId` | `entities: ["campaign"]`, `changeField: dailyBudget`, `resourceIds: [{"idEntity": "campaign", "ids": [<Amazon campaign ids>]}]` | `entityId` = `campaignId` |
| Keyword bid | `entity: keyword`, `{"keywordId": {"in": [...]}}` | `keywordId` | `entities: ["target"]`, `changeField: bid`, `resourceIds` `idEntity: campaign` with the campaigns' **Amazon** ids | `entityId` = `keywordId` (rows carry `entity: KEYWORD`) |
| Target bid | `entity: target`, `{"targetId": {"in": [...]}}` | `targetId` | As keyword bids | `entityId` = `targetId` (`entity: AUTOMATICTARGET` and the other target kinds) |
| Ad group default bid | `entity: adGroup`, `{"adGroupId": {"in": [...]}}` | `adGroupId` | `entities: ["adGroup"]`, `resourceIds` `idEntity: campaign` with the campaigns' Amazon ids, `changeField` = the field the window rows reported (not tried live) | `entityId` = `adGroupId` |
| Placement | `entity: placement`, `{"campaignId": {"in": [...]}}`. A placement has **no id of its own**: one row per campaign x placement comes back | `campaignId` + `placement` | `entities: ["placement"]`, `resourceIds` `idEntity: campaign` with the campaigns' Amazon ids, **no `changeField`** - a batch writes several placements, and each is its own field (`topAdjustment`, `restOfSearchAdjustment`, ...) | `entityId` = `campaignId` + `changeField` = the placement's field |
| Portfolio cap | `entity: portfolio`, `{"portfolioId": {"in": [...]}}` - on `portfolio` this is the **internal** id (on `campaign` the same name holds the Amazon id) | `portfolioId` | `entities: ["portfolio"]`, `changeField: amount`, **no `resourceIds`** - `idEntity: portfolio` returned 0 rows with both internal and Amazon ids while the same rows came back without it | `entityId` = `portfolioId` |
| Managed-group setting | `entity: aiGroup`, `{"aiGroupId": {"in": [...]}}` | `aiGroupId` | `entities: ["aiGroup"]` only, `resourceIds` `idEntity: aiGroup` with the **internal** group ids, **no `changeField`** - the tool rejects `changeField` with `aiGroup` (`changeField requires explicit entities excluding aiGroup`). Limit-only: check `truncated` | `entityId` = `aiGroupId` + `changeField` = the field written; rows are UTC (SP/SB) or an unknown clock (SD), section 2 |

**A wrong id space fails silently.** `idEntity: campaign` with **internal** campaign ids returned
0 rows and no error - which reads exactly like "nobody wrote". So prove the filter once per
write type in a run, on the first batch, against rows you already know exist. Which rows depends
on the batch's `targetSource`:

| The batch holds | Proof |
|---|---|
| Rows with `targetSource: log` (alone or mixed with file rows) | Run the batch's log query once from the **window start**, using only the `log` rows' objects: it must return the window rows those targets were built from - same object, field and `previousValue` / `newValue`. Any missing -> the filter is wrong: stop, fix it, do not write the batch |
| Only `targetSource: file` rows | There may be no log row to find - the file can hold changes the log never saw (`from-file.md` section 3) - so an empty result proves nothing either way. **If an earlier `log` batch of the same write type already proved the query shape in this run**, reuse that shape: it covers this batch. **Otherwise drop `resourceIds`** and run the stale query unfiltered for this write type - same `entities` and `changeField` as the table (none for managed groups and placements) - from the batch's earliest `writtenAt` / `staleCheckFrom` to now. Read it to the end: page while `hasNextPage`; on a limit-only response that comes back `truncated`, split the window as in "Reading a window completely" below. Then match rows to the batch's objects client-side by `entityId` (the internal id). If the window cannot be read completely, **stop the batch** - do not write it |

A batch whose proof failed, or whose unfiltered check could not be read completely, is not
written; the other write types go ahead. When a batch was checked unfiltered, the report says
"the id filter was not cross-checked against a known row, so the check ran without it" - not
that the stale check itself was skipped.

**Current-value filters were verified live** (table above). If one is rejected now:

- keyword, target, ad group: these rows carry `campaignId`; `campaignId` filtering was verified
  on `target` and `adGroup` and is documented for `keyword` (every keyword field is filterable) -
  filter on `campaignId` (`in`) instead and
  match client-side by "Match by", still one read per batch;
- campaign, portfolio, managed group, placement: there is no other id to fall back on (placement
  already uses `campaignId`) - stop that batch and report that the tool's filter contract has
  changed. Never read the entity unfiltered and guess.

## 3. Row states and what the next run does with each

| `status` | Next action |
|---|---|
| `planned` | Not written yet (e.g. the first run stopped part-way). Stale check, show it again, write step 1 once confirmed |
| `inProgress` | Stale check, then write step `lastCompletedStep + 1` |
| `needsReadBack` | The last write came back `ambiguous`. Read back first: the value equals the step written -> count that step as done (`inProgress` or `done`); equals `expectedCurrentValue` -> it did not apply, back to the previous state; anything else -> `stoppedChangedByOthers` |
| `failed` | Read back, show the user what happened, write again only after they confirm |
| `held` (`dealRunning`, `holidayHold`, `waitForSchedule`) | Until `holdUntil` has passed: nothing. After it: stale check, then judge the item on the days after the hold ended (`pacing-rules.md` section 5; thin data until 3 such days exist), show the suggestion, fill `steps` and set `planned` once the user confirms |
| `held` (`scheduleRunning`) | Until `holdUntil` has passed: nothing. After it: re-read the group's schedules (`restore-list.md` section 3). Ended or gone -> run the section 5 bid audit, record its result, then set `ended`, nothing written - unless another schedule of the group is in effect: record `scheduleStillRunning` and keep it `held` with the `holdUntil` section 5 gives; still in effect with a later end date (someone extended it) -> move `holdUntil` and tell the user; cannot be read -> show it under "you decide". Never build schedule-restore steps for it |
| `ended` | A schedule that ended by itself. Final for the schedule settings; its report row retains the section 5 bid-audit result. No bid write is implied |
| `done` | Last step confirmed by read-back. Nothing to do |
| `undoPending` | The user asked to undo; the undo write is not confirmed yet (section 4). Stale check, then write `valueBeforeRun` - never a restore step |
| `undone` | Undone by the user (section 4). Never written again in this run - not by "continue the reset", not by a later step. Restoring it again takes a new run (section 4, step 6) |
| `customerDecides` | A row never written that a stale check or a mismatch moved to "you decide" (section 2). Not written; shown under "You decide"; becomes `planned` only when the user picks it |
| `skipped` | The user dropped it from the preview, or a prep row whose day passed. Nothing to do unless the user asks for that item specifically |
| `stoppedChangedByOthers` | Someone else changed it after this run's last write. Nothing to do unless the user asks for that item specifically |

**Read-back updates the row**: `writeResult`, `readBackValue`, `writtenAt`; when the read-back
shows the step's value, advance `lastCompletedStep`, set `expectedCurrentValue` to that value,
and set `status` to `inProgress` (or `done` after the last step). An `ambiguous` result sets
`needsReadBack`, never a completed step.

**Continuing on a later day**: drive the work from the plan file, not from a fresh restore list.
Handle every row by its `status` (table above), running the stale check before each write. Do
not write a step twice on the same store day.

**Coming back after a schedule or a hold ends** is "继续复位" with the **same** plan
file, not a new run: the file's `runId` and `writtenAt` values are what let the stale check and
the restore list recognise this reset's earlier writes. If the user starts a new run anyway, ask
for the previous plan file and treat the writes of its `done`, `inProgress`, `undoPending` and
`undone` rows (restore and undo writes alike) as this reset's own - without it, the earlier
restores look like "changed again after the window" and every one of them would go to
"需要你决定".

## 4. Undo

"撤回刚才的复位" means writing `valueBeforeRun` back, through the same stale check, preview and
confirmation - an undo must not overwrite a change made after this run either:

1. **Settle `needsReadBack` rows first** by reading them back now (they belong to this run, so a
   read-back is valid): a step that applied counts like `lastCompletedStep > 0`.
2. **Mark what will be undone**: every row with `lastCompletedStep > 0` (and every
   `needsReadBack` row whose step applied) becomes `undoPending`. From here on no restore step
   is ever written for it - "continue the reset" only finishes the undo (step 6). Rows still `planned`
   or `held` need no write: set them to `undone` - except `scheduleRunning` reminder rows, which
   stay `held` so the post-schedule bid audit still runs. `ended` schedule rows stay `ended` - this run
   never wrote them.
3. **Write order**: group totals first (writing a total back rescales its campaigns), then
   re-read those campaigns and re-base their `expectedCurrentValue` and `rebasedAt` (as for the
   restore), then the campaign budgets back to their own `valueBeforeRun` - which the rebase
   never changed - then bids and placements.
4. After each undo write and its read-back: read back `valueBeforeRun` -> `status: undone`,
   `expectedCurrentValue` = `valueBeforeRun`, `writtenAt` = the undo write's time. In later
   stale checks the undo write is one of this run's own rows (`newValue` = `valueBeforeRun`).
   An `ambiguous` result keeps `undoPending` with `writeResult: ambiguous`: the next run reads
   it back - `valueBeforeRun` -> `undone`; the pre-undo value -> write the undo again (with the
   stale check); anything else -> `stoppedChangedByOthers`. A `failed` undo keeps
   `undoPending`; show it and write the undo again only on the user's yes.
5. `undone` is final: resuming never writes those rows again.
6. **"继续复位" after an undo**: say the reset was undone, and that this run only finishes
   pending undo writes, the bid audit and the schedule reminder rows - nothing is restored. To
   reset again, the user starts a new run with this plan file: it builds a fresh restore list,
   and the earlier restore and undo writes are recognised from the file (section 3, "Coming
   back"), not treated as "changed again after the window".
