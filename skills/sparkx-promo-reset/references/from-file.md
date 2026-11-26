# Restoring from the customer's own file

The customer may hand over their own record of what things were before the promo - a sheet they
kept, a bulk export taken before the event, a screenshot of a table. Then the **restore target
comes from the file**, not from the operation log.

**The promo change log from `sparkx-promo-prep` / `sparkx-promo-monitor` is not such a file.**
It covers only what those skills wrote, so it never replaces the operation log: the log stays
the source of the list and of the targets, and the change log is the cross-check of SKILL.md
Step 1 (a mismatch goes to "you decide"). The section "If the file is the prep / monitor change
log" below only says how to read its pre-promo values for that cross-check; the rest of this
file (file as target, "Default: the file", items in the log but not in the file) does not apply
to it. Everything else in SKILL.md still applies: the restore mode
(all at once or by performance), the "you decide" buckets, the plan / undo file, the stale check
before every write, read-back.

The file is the customer's statement of what they want back. This skill checks that each row
points at a real object and that nobody changed the object after the promo - it does not
second-guess the customer's numbers, but it shows them where the log disagrees.

## 1. Read the file, then confirm what was read

Any format the conversation can read: Excel, CSV, a spreadsheet export, PDF, a screenshot.
Columns vary and can be in any language; match them by meaning:

| What | Common headers |
|---|---|
| Campaign | Campaign name, Campaign ID, 广告活动, 广告活动名称, 广告活动 ID |
| Ad group | Ad group name / ID, 广告组 |
| Keyword / target | Keyword text, Match type, Targeting, ASIN target, 关键词, 匹配方式, 投放 |
| Managed group | Group name, 托管组 |
| Portfolio | Portfolio, 广告组合 |
| Field | Budget, Daily budget, Bid, Default bid, Top of search %, Target ACOS, Objective, Personality, 预算, 竞价, 出价, 默认竞价, 搜索结果顶部, 目标 ACOS, 投放目的 |
| Value to restore | Before, Original, Pre-promo, Old value, 原值, 大促前, 改前 |
| Value now (optional) | After, Promo, New value, 现在, 大促中 |

A bulk export from Amazon Ads or the platform has one row per entity with a `Record Type` /
`Entity` column; read the value column for that entity (e.g. `Daily Budget`, `Bid`,
`Percentage` for placements).

Before going further, show the customer one short table and ask them to confirm:

- the columns used and how each was understood (which column is the restore value);
- how many rows were read, per field (e.g. "62 campaign budgets, 140 keyword bids");
- rows that could not be read (blank value, unreadable screenshot cell, unknown field) - listed,
  not guessed;
- **units, when they are ambiguous**: target ACOS `0.35` vs `35`; a placement `50` (percent) vs
  `0.5`; budgets in the store's currency. Ask once rather than infer per row.

If the file is the prep / monitor change log, its columns are known (see that skill's
`references/change-log.md`): its pre-promo value - **for the cross-check only** - is the
**first `valueBefore` per object and field among confirmed writes**, and no column question is
needed. Filter first:

- keep rows with `status = written`; keep a `needsReadBack` row only once the operation log
  shows the write applied (`restore-list.md` section 2, "Matching a log row to the change log")
  - reading the object now proves nothing, others have changed it since; with no matching log row,
  drop it as unconfirmed;
- drop `planned`, `fulfilled`, `failed`, `skipped` and `changedByOthers` rows - they are not
  writes (a `fulfilled` row's write is the later row that carries it; or not writes through this
  plan), so their `valueBefore` is not a pre-promo value. Drop `schedule`, `scheduleTarget` and
  `scheduleDelete` rows as well - schedules end by themselves and a deleted ended schedule has
  nothing to restore. List the dropped rows by status in the confirmation table;
- among the rows kept, "first" is the **earliest `writtenAt`**, not the order in the file;
- an object with no confirmed write has no restore target from the file. It goes to the "could
  not match" list with the reason "no confirmed write in the log".

## 2. Match each row to a live object

Resolve every row with `get_entity_metadata` for the store, preferring ids:

| Row carries | Match on | Notes |
|---|---|---|
| Amazon id (campaign, ad group, keyword, target) | the Amazon id | Most reliable |
| Internal id (platform export) | the internal id | Only if the file is from this platform |
| Name only | exact name, case and spaces normalised | Two objects with the same name -> ambiguous, not written |
| Keyword without match type | keyword text in that campaign / ad group | Several match types -> ambiguous |
| Managed group by name | `aiGroupName` | |

Rows that match nothing, match more than one object, or match an archived object go to a
**"could not match"** list with the reason. They are never written.

## 3. Compare with the account and the log

Ask for the promo dates if the customer has not given them. If they do not know them, ask when the
file was recorded and use that day as the window start. With neither, say plainly that changes made
after the promo cannot be told apart from promo changes, so nothing is written without the
customer confirming the full list. Then for each matched row:

1. **Read the current value** (same fields as [`restore-list.md`](restore-list.md) section 3).
2. **Pull the operation log for the window through today** exactly as in
   [`restore-list.md`](restore-list.md), so that the log's own pre-promo value and any later
   change are known for the same objects.

| Situation | Bucket |
|---|---|
| Current = file value | Skip (count it) |
| Changed again **after** the window by any source except this run's own writes (log) | You decide - a newer decision |
| AI changed it after the last human change (bids in a running managed group) | You decide - the AI is managing it and may move it again (same as [`restore-list.md`](restore-list.md)) |
| File value and the log's pre-promo value differ | Show both ("你的文件：$50，日志里大促前：$40"); ask once for all such rows which to use. Default: the file - it is the customer's record |
| The log has no promo change for it | Still restorable from the file - the change may predate the window or not be logged; say so in the reason |
| File value **below** current (the usual case: raised for the promo) | Restore candidate - Step 3 paces it |
| File value **above** current (it was lowered) | You decide - restoring raises spend; needs its own yes, with the "is it binding" note when it is a budget |
| Field with no write route (SB ad group default bid, the Amazon Business placement, anything the write skills do not cover) | Listed with the file value for the customer to change in the platform |
| On / off state in the file | You decide - re-enable / pause only the items the customer names |

**Changes in the log that are not in the file** (human promo changes the restore list would
normally find): do not add them. Report the count and offer to include them ("日志里还有 12 个大促期间的预算改动，你的文件里没有——要一起复位吗？").

Managed groups: the same rules as SKILL.md Step 2c apply to group rows - restore group settings
before budgets; a dated schedule's settings need no restore once its end date has passed (check
it against the store's date, as in `restore-list.md` section 3), but its group still gets the
bid audit of `restore-list.md` section 5; and a total budget changed directly on the
group is restored separately. A campaign budget in the file
for a campaign inside a running managed group is restored as a campaign budget, never by editing
the group total; say that the group's AI keeps adjusting that campaign's spend within it.

## 4. Pace, preview, write

Unchanged from SKILL.md Steps 3-5, with two differences:

- **"In batches by performance" needs the promo dates** (for the normal range and the
  post-promo days). Without dates, only "all at once" is available and the store-level recap
  (SKILL.md Step 4) is skipped - say both.
- **The plan / undo file** records `prePromoValue` = the value restored to, and a `targetSource`
  column: `file` or `log` (when the customer chose the log value for a mismatch). The stale
  check uses `staleCheckFrom` as usual.

In the list header, say that the restore targets come from the customer's file, name the file,
and give the counts: matched, could not match, skipped, you decide.
