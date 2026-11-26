# AI Group Schedule Query (`entity: aiGroup_schedule`)

Reads all schedules ("flights") of **one** AI managed group. This entity has a special contract: one profile, one `aiGroupId`, no pagination.

## Step 1 — find the group

```json
{
  "userContext": "Find the managed group named Summer Push",
  "entity": "aiGroup",
  "profileIds": [2618208845223116],
  "filters": {"aiGroupName": {"like": "%Summer Push%"}},
  "select": ["aiGroupId", "aiGroupName", "campaignType", "aiStatus", "targetType", "targetAcos", "aiPersonality"]
}
```

Keep `targetType` / `targetAcos` / `aiPersonality` from this row — weekly schedules inherit them from the group (see below).

## Step 2 — read its schedules

```json
{
  "userContext": "Show the schedule for managed group 29123",
  "entity": "aiGroup_schedule",
  "profileIds": [2618208845223116],
  "filters": {"aiGroupId": 29123}
}
```

## Contract — what makes this entity different

| Rule | Detail |
|---|---|
| `profileIds` | **Exactly one**, authorized. Otherwise: `aiGroup_schedule query requires exactly one authorized profileId` |
| `filters` | **`aiGroupId` only.** Missing → `aiGroup_schedule query requires filters.aiGroupId`. Any extra key → `aiGroup_schedule query only supports filters.aiGroupId` |
| `aiGroupId` form | Single positive integer. `29123`, `[29123]`, `{"in": [29123]}` all work; two IDs do not |
| Pagination | Ignored — every schedule comes back in one call. Response has no `page` / `pageSize` / `hasNextPage` |
| `orderBy` | Ignored |

Things this rules out:
- **No cross-group query.** One `aiGroupId` per call — loop serially for several groups.
- **No cross-store query.** One `profileId` per call — loop stores serially.
- **No filtering by date, status, or type.** Pull all schedules and filter client-side.
- **Don't loop pages to count.** `rowCount` here is the complete total for the group.

## Reading the rows

Each schedule is a time-boxed override of the group's settings.

| `timeType` | Meaning | Which fields are meaningful |
|---|---|---|
| `1` | Fixed date window | Carries its own `startDate`/`endDate` plus `optimizeType`, `acos`, `aiPersonality` |
| `2` | Weekly repeat | Carries `weekDays` (1=Monday … 7=Sunday); `optimizeType`, `acos`, `aiPersonality` are **inherited from the parent group** |

So when describing a weekly schedule, read the target/ACOS/personality from the group row in Step 1 — reporting them from the schedule row is wrong or empty. When describing a fixed-window schedule, use the schedule's own values.

**⚠️ `weekDays` read vs write encodings differ.** The `1`=Monday … `7`=Sunday values above are what the **read** side returns here. The **write** tool `save_sp_sb_ai_group_schedule` expects a **different** encoding — `0`=Sunday … `6`=Saturday. Do **not** echo a `weekDays` value read here straight into a save-schedule call; translate between the two encodings first.

Schedules can also carry per-schedule action-space settings (`aiActionSettings`) and automation rules (`aiAutomation`), read the same way as on the group itself — including the "currently effective" projection rules in the main SKILL.md.

## Writing schedules is a different tool

Creating, updating, or deleting schedules goes through `save_sp_sb_ai_group_schedule` (SP/SB only) — see the managed-group edit skill. This read skill never writes.
