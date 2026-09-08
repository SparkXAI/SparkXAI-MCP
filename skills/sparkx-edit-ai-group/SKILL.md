---
name: sparkx-edit-ai-group
description: >-
  Modify an EXISTING AI managed group (托管组) for Amazon Sponsored ads - change target
  ACOS/ROAS, budget, turn its AI on/off, personality, adjust SP/SB campaign membership, and
  the AI action space (bid / budget / target / structure optimization) - for one group or
  many at once (bulk). Use when the user wants to modify / adjust / 修改 / 调整 / 批量改 an
  existing group's settings or automations. SD uses edit_sd_ai_managed_group; SP/SB uses
  save_sp_sb_ai_managed_group (edit mode). Not for creating a group (use sparkx-create-ai-group)
  or deleting one (use sparkx-delete-ai-group).
metadata:
  version: 1.1.2
---

# Edit AI Managed Group

Change the configuration of one or more existing managed groups. Read
[`references/platform-notes.md`](references/platform-notes.md) once first - it covers
auth, the response envelope, generic errors, and the crucial fact that **MCP bypasses
the platform UI's validation, so you must enforce the front-end-only rules yourself.**

## Route by ad type

| Ad type | Tool | Reference |
|---|---|---|
| **SD** | `edit_sd_ai_managed_group` (takes an `ids` array - inherently batch, max 20) | [`references/edit-sd.md`](references/edit-sd.md) |
| **SP / SB** | `save_sp_sb_ai_managed_group`: `aiGroupId > 0` for one group; `operation + ids` for batch | [`references/edit-sp-sb.md`](references/edit-sp-sb.md) |

Outside batch mode, `aiGroupId = 0`/empty means create (that's sparkx-create-ai-group) and a
positive id edits. In SP/SB batch mode, `operation` selects batch behavior, `ids` are
the targets, and `aiGroupId` is ignored. Determine ad type from each group's
`campaignType` before choosing a mode.

## Editing a running group can be silently skipped

If a group's AI is on (`aiStatus=1`), the backend **may silently drop some of your
changes** - the call returns `success` but the setting didn't move. This is the single
biggest trap here.

- **Never turn AI off on your own to force an edit through.** Turning off AI stops live
  optimization; that's the user's decision, not yours.
- If an edit doesn't stick because AI is running, **tell the user** what didn't apply
  and let them decide (e.g. pause AI themselves, or accept it).
- Always **verify after** (below) - don't trust the `success` envelope.

## Disambiguate before writing (when in doubt, ASK - don't guess)

Everyday words - in English OR Chinese - map to DIFFERENT things in a managed group, and
the **exact field depends on the ad type (SD vs SP/SB) and the write path (flat/batch vs
action-space)**. So this section lists **business meanings only** - do NOT hard-code a
field name from it. Resolve the meaning first, then determine ad type + tool path, then
look up the exact field/param in [`references/field-reference.md`](references/field-reference.md)
and [`references/action-space-matrix.md`](references/action-space-matrix.md).

**If a request could map to more than one meaning, STOP and ask - don't pick one.**
Guessing wrong changes live spend.

**"budget" / "预算"** (e.g. "把预算调到 100" / "set the budget to 100") - be precise which
one, and whether it's a **target value** or an **increase**:
- **托管组总预算 / group total budget** = the sum of the group's **enabled** campaigns'
  daily budgets. Editing it **proportionally rescales every enabled campaign's daily
  budget** to the new total (`totalBudget` / `totalDailyBudget` on read reflect this sum).
- **单个 campaign 的日预算 / a campaign's daily budget** - campaign-level, and
  **cannot be modified through the managed-group tools**. It *can* be changed with the
  `sparkx-edit-ads` skill (`batch_update_ads`, `entity=campaign` +
  `action=updateBudget`); route the user there rather than telling them to use the platform
  UI. Warn them that editing this group's **total** budget afterwards rescales every enabled
  campaign's daily budget proportionally, which would overwrite that change.
- **按表现调预算 / performance (dynamic) budget** (`DYNAMIC_BUDGET`) - the value is an
  **increase cap on top of the current budget, NOT a target** (fixed `+$num` or `+num%`;
  e.g. $100 with 20 -> up to $120). **Its scope depends on 预算重新分配**: OFF = per enabled
  campaign; ON = whole group (see [`references/coupling-rules.md`](references/coupling-rules.md)).
- **预算重新分配 / budget reallocation** (`BUDGET_REDISTRIBUTE`) - a switch that also changes
  the *scope* of 按表现调预算 (above).

> **Target vs increase:** "把预算调到 X" is a **target value**; "按表现最多加 X" is an
> **increase**. Never map one onto the other. When the user says "调预算" / "预算预期",
> confirm which they mean - **托管组总预算 / a campaign's budget (targets)** vs **按表现调预算
> 的增量上限 (an increase)** - before writing. The exact write field still depends on ad type
> + path (`budgetType`/`budgetRatio` are edit/batch only); look it up in field-reference
> once the meaning is fixed.

**"bid / adjust bid" / "调价 / 出价 / 竞价"** - candidate meanings (field differs by ad
type/path, look it up after): 按表现调竞价 · 广告位调价 (SP only) · 竞价范围 (min/max) ·
分时调价 (on SB this is Rule/RBA-only; MCP can **read and explain** the retained Rule
configuration through `get_entity_metadata`, but cannot edit it - if that's the intent on
an SB group, show the current setup when useful, point the user to the platform for changes,
and do **not** build write params). Also **ACOS 优先模式 / strict ACOS / ACOS priority**
(`bidPerformanceStrictAcosStatus`) is a sub-switch of 按表现调价 - **SP only, with strict
preconditions** (`targetType=2` + `bidPerformanceStatus=1` + `aiPersonality>=3`) and a
real tradeoff; see [`references/coupling-rules.md`](references/coupling-rules.md). Ask which one.

**"off / pause / stop" / "关掉 / 关闭 / 暂停 / 停"** - three very different things:
- **关闭托管组 AI** (stop the group's AI optimization) - a status change. **Never do this
  on your own; confirm first.**
- **允许 AI 暂停广告活动 / 暂停商品** (`structPauseCampaign*` / `structPauseProduct*`) - this
  is an **action-space switch that *enables the AI* to pause**; turning it on does **not**
  immediately pause anything. SP only.
- **立即暂停某个广告活动** (pause a specific campaign right now) - campaign-level, **not a
  managed-group operation** and not settable through these tools.
> "暂停广告活动" is ambiguous between "let AI pause campaigns" (action space) and "pause
> this campaign now" (campaign-level, not here). **Never map it straight to a field and
> execute - ask which is meant.**

**"target / goal" / "目标"**: 推广目标 `targetType` (1 growth / 2 stability / 3 volume /
4 legacy) vs 目标 ACOS/ROAS. Also "ACOS 调到 25" (a value) vs "ACOS 降 20%" (a ratio) are
different inputs - confirm which. **And note: "ACOS 优先模式 / ACOS priority" is the
strict-ACOS switch (`bidPerformanceStrictAcosStatus`, see the bid item above), NOT setting
a target ACOS value - don't confuse the two.**

**Clarification is NOT authorization.** Even after the user answers the ambiguity, only
produce a **change preview** (business meaning + resolved field + old -> new). Do **not**
call any write tool until the user explicitly confirms the object, the meaning, and the
new value.

## Workflow

1. **Resolve the group(s) and read current config.** Look them up with the full
   signature `get_entity_metadata(profileIds=[...], entity='aiGroup',
   filters={"aiGroupName": {"like": "%<name>%"}}, userContext='...')` (the name filter is a
   substring `like` - exact-match in the results). Read each group's `aiGroupId`,
   `campaignType` (routing), `aiStatus`, and the current values of whatever you're
   about to change - SP/SB edit **merges** onto current config, and you want a before
   value to verify against. **If the request touches 按表现调预算 (dynamic budget), you MUST
   also read the current 预算重新分配 status** - it decides whether the increase applies
   per-campaign or to the whole group, so you can't correctly interpret the request without
   it. Only ask the user about scope if you can't read that state or their intent is still
   unclear - don't ask mechanically when it's already determinable.
   - **To compute a budget cap for the preview, get the *enabled* campaigns properly:**
     query `entity='campaign'` **filtered by this group's `aiGroupId` and
     `campaignState='enabled'`** (both are server-side filterable for campaigns),
     **fully paginate**, then use the returned campaigns' `dailyBudget`
     + their actual count. Do **not** use `numCampaign` - it may not equal the enabled count.
     If you can't read the full campaign set, **don't state a definite cap** - explain the
     calculation rule instead.
2. **Disambiguate into a single, concrete mapping** (see "Disambiguate before writing"
   above). Determine the object level, the business meaning, the value type, and the unit.
   **If more than one mapping is plausible, STOP and ask the user - do not build any params
   yet.**
3. **Build a partial update - only the fields you're changing** (only once the mapping is
   unique). Both tools take partial input (SP/SB fills the rest from current config; SD
   applies the non-null fields to the `ids`). Don't resend unchanged fields.
4. **Self-validate the front-end-only rules MCP bypasses** (see references):
   - **ACOS / ROAS / Budget type are mutually exclusive** - the `*Type` decides which
     value field to send; sending the wrong companion (or both) fails. See
     [`references/edit-sd.md`](references/edit-sd.md).
   - **Action-space support** - only enable a capability that supports AI for this ad
     type ([`references/action-space-matrix.md`](references/action-space-matrix.md)).
     If the user asks for one that isn't supported for their ad type / mode, tell them
     and skip it - don't send a silently-ignored field.
   - **Budget** - enforce only rules you can determine reliably (positive, JP
     integer-only, and the known multi-campaign minimum relationship). Site/account
     ranges are incomplete; do not invent or silently clamp an unknown limit. See
     [`references/budget-limits.md`](references/budget-limits.md).
   - **`aiPersonality` 1-5, and >=3 when `targetType=3` (volume/冲量)**; name not blank;
     any range min <= max; coupled switches carry their companion fields.
   - **The backend now rejects invalid values - pre-validate anyway** for a clear error
     instead of a downstream one (prod-confirmed 2026-08-13): `acos`/`roas` out of range
     (incl. `0`, negative, over-limit), `aiPersonality` outside `1`-`5`, `remark` over
     **200** chars, a `*Type` sent without its value (or with the wrong companion), `ids`
     empty or over **20**, and `tosMin > tosMax` are all rejected. Also enforce these
     value bounds yourself (backend may not catch them yet, per the 2026-08-14 spec):
     `budget > 0`, `budgetRatio <= 10000`, dynamic-budget `num > 0` (`numType=1` <= 1000,
     `numType=2` <= 100000), and action-space ranges (placement/B2B `0`-`900`, bid-range
     percentage `0.01`-`100`). Don't lean on the backend for these.
   - **Word-list settings are not supported.** Do not send branded, non-branded,
     competitor, harvest-blacklist, or negative-target-blacklist fields, even if the
     routed schema exposes them. Tell the user to configure word lists in the platform.
5. **Confirm before applying - especially for bulk and for running groups.** Show a change
   preview per group: **business meaning + resolved field + old -> new**, and how many
   groups are affected. **For a budget change, spell out the inputs and the effect**: current
   group total & number of enabled campaigns, the 预算重新分配 state, the mode (fixed/percent),
   and the resulting budget cap. Editing the group total proportionally rescales each enabled
   campaign's daily budget; a 按表现调预算 value is an *increase cap* (per-campaign or
   whole-group per 预算重新分配), not a target. For a
   running group, note that some changes may not apply while AI is on. Get an explicit
   go-ahead. **Clarification is not authorization** - a prior answer
   to an ambiguity question is not itself permission to write; you still need an explicit
   confirm of the actual change here before calling any write tool.
6. **Verify - read back and compare.** Re-read the group(s) and confirm each changed
   field actually took the new value. For bulk, check **every** group, not just one -
   partial success is possible. Report any field that didn't move (often because AI was
   running) instead of implying it did. For `campaignNameSign`, also re-read the
   affected campaigns and verify their actual names gained/lost `[AI]` according to
   `campaignNameRecoveryType`; the group setting alone is not enough - also cross-check
   the `campaignNameSign` entry in `get_operation_log` (prod shows it logged with
   `changedBy=manual`).
7. **Verify the audit trail when available.** If the token also has operation-log read
   access, query `get_operation_log` for the affected group(s) and time window and
   confirm the action, object, time, and identifiable operator. `changedBy` is derived
   server-side from the authenticated token - never send or fabricate it. If log access
   is unavailable, say the business state was verified but the audit entry was not.

## Scheduling - use `save_sp_sb_ai_group_schedule`

Schedules are **not** fields on the edit tools (there is still no `scheduleType` /
`scheduleDate` / `scheduleStartDate` / `scheduleEndDate` - don't invent them). They are a
separate tool: **`save_sp_sb_ai_group_schedule`**, with reads via
`get_entity_metadata(entity='aiGroup_schedule')`.

**SP/SB only** - there is no SD schedule tool. If the user asks to schedule an SD group, say
it's not available for Sponsored Display.

### Parameters

```json
{
  "request": {
    "profileId": 2618208845223116,
    "aiGroupId": 29123,
    "schedules": [ { "...": "one object per schedule" } ]
  }
}
```

The call takes a single top-level `request` object (same wrapping as the SP/SB
`save_sp_sb_ai_managed_group` calls in [`references/batch.md`](references/batch.md));
inside it, `profileId`, `aiGroupId`, and a non-empty `schedules` array are all required.
Each item:

| Field | Type | Notes |
|---|---|---|
| `id` | long | **Omit/null = create**, `>0` = update that schedule |
| `isActive` | boolean | `false` **with a valid `id` = delete** that schedule |
| `timeType` | int | `1` = fixed date window, `2` = weekly repeat |
| `startDate` / `endDate` | string | `YYYY-MM-DD`, `timeType=1` only |
| `weekDays` | int[] | `timeType=2` only. **`0` = Sunday, 1-6 = Mon-Sat** |
| `optimizeType` | int | `1`=drive growth, `2`=control cost, `3`=volume. **`timeType=1` only - required there, rejected on `timeType=2`** |
| `acos` | number | Target ACOS, x100 scale. Same `timeType` rule as above |
| `aiPersonality` | int | `1`-`5`. Same `timeType` rule as above |
| `aiActionSettings` | object | Per-schedule action space, same shape as the group |
| `aiAutomation` | object | Per-schedule rules, **keyed by rule number** (`"2"`,`"4"`,`"5"`,`"13"`,`"17"`,`"19"`,`"20"`,`"181"`,`"182"`), each at least `{"status": 0}` |

### The three rules that will bite you

1. **Weekly schedules must NOT carry `optimizeType` / `acos` / `aiPersonality`.** Passing any
   of them on a `timeType=2` item is a **hard error** - even though the downstream API
   requires those three on every schedule. The tool reads the parent group and fills them in
   for you, which is why you must leave them out. (If the parent group's detail can't be
   read, the call fails - so make sure the group exists and is readable first.) For a
   fixed-window schedule, these three are required from you.
2. **Word-list settings are stripped silently.** `aiActionSettings.targetOptimization` and
   `brandOptimization` are removed server-side on schedules. Don't offer them, and don't
   claim they were applied.
3. **Overlaps are rejected downstream**, surfacing as `Schedule_Date_Overlap`. Before
   writing, read the existing schedules (`entity='aiGroup_schedule'`) and check your new
   window/weekdays against them, so you can tell the user *which* schedule conflicts instead
   of relaying an opaque error.

### Validate these yourself - the backend does not

The platform UI enforces these; the API does not, so a "successful" write can still be
nonsense. Check before sending:

| # | Rule | Why it matters |
|---|---|---|
| 1 | `startDate` ≥ **tomorrow** | The backend accepts past dates; such a schedule is simply already expired and never runs |
| 2 | `endDate - startDate` ≤ **365 days** | The backend accepts longer ranges; the UI caps at one year |
| 3 | `acos` ∈ **(0, 1000]** | The backend does not range-check schedule ACOS |
| 4 | No overlap between schedules (dates **and** weekdays) | The backend does reject this, but with an opaque `Schedule_Date_Overlap` - pre-checking lets you name the conflicting schedule |
| 5 | `weekDays` ⊆ `[0..6]`, no duplicates | No backend guard |

One more interaction to surface to the user: if the group runs **bid dayparting or budget
dayparting**, changing a weekly schedule's `weekDays` can change when those rules execute.
The UI warns about this; say it out loud rather than letting the user discover it.

Deleting is `isActive: false` + the existing `id` - state clearly to the user that you're
removing a schedule, and read back afterwards to confirm it's gone.

## Templates - readable, and applicable via `templateId`

- **Read** with `get_ai_group_template`: no args = list (`searchName` fuzzy match,
  `createdBy`, `page`, `pageLimit` default 50, `applyFlag=1` to include system presets);
  `templateId` = full detail of one. This is a read behind the **write** scope.
- **Apply** by passing `templateId` (>0) to `edit_sd_ai_managed_group` or
  `save_sp_sb_ai_managed_group`. It supplies `acos`, `optimizeType`, `status`,
  `budgetDynamicStatus`, `numType`, `num`, `campaignNameSign`, `targetHarvestStatus`,
  `budgetRedistributeStatus`, `aiPersonality` plus action-space/automation config.
- **Explicit params beat template values**; omitted fields fall back to the template.
- **Priority: `templateId` > `operation` > plain field edit.** If you pass both `templateId`
  and a batch `operation`, the template path wins and the operation is ignored - never send
  both expecting both to apply.
- **Cross-type apply is supported and sanitized for you.** A template isn't bound to an ad
  type; applying an SP template to an SB group zeroes the template's SP-only fields
  (`bidAmazonBusinessStatus`, `btb*`, `bidDaypartStatus`,
  `bidPerformanceStrictAcosStatus`, `bidAdPlace*`, `tos`/`pdp`/`ros` bounds,
  `structPause*`) rather than failing. **This applies only when you omit
  `aiActionSettings`.** Send `aiActionSettings` yourself and the template's action-space
  config is skipped entirely (yours wins, no merge) and the SB compatibility check applies
  as usual - an SP-only field with a non-zero value then fails the whole call. Don't
  hand-build `aiActionSettings` on a cross-type template apply, and tell the user which
  parts of the template won't carry over.
- **Hard error**: a template whose target-harvest (rule 4) or negative-target (rule 5) config
  is bound to specific campaigns/ad groups (`isSelf=2`, rule enabled) is rejected, because
  this tool can't carry the bindings. Tell the user to apply that template in the UI or pick
  one using "current object" scope.
- **No template writes.** You cannot create, edit, delete, or "save as" a template through
  MCP. Read + apply only.

Because a template can flip AI on and rewrite several settings at once, read its detail and
show the user what will change **before** applying it to an existing group.

## RBA mode restriction

- The tool may switch an existing group from **RBA (Rule mode) to AI mode**.
- It must **not** switch a group from **AI mode to RBA**.
- **RBA configuration is readable, but not writable.** A rule-mode group's actual conditions,
  actions, condition items, time periods and hour matrices come back from
  `get_entity_metadata(entity='aiGroup')` under `aiAutomation.{ruleType}` - so you *can* show
  the user their current rule setup and explain it accurately. What you cannot do is change
  it: there is no MCP tool that writes rule conditions or actions. For any RBA config change,
  point the user to the platform.
- When reporting a rule setup, relay unlabeled leaves verbatim (only confirmed fields carry a
  `...Text` companion) and never reuse a label across rule types - the same raw value means
  different things under different rules.

## Bulk / batch edits

Bulk uses an **operation-based** protocol (`operation` + `ids` + operation-specific
parameters) - **not** a bare array of ids. Read
[`references/batch.md`](references/batch.md) before any bulk edit; the essentials:

> **Server-version guard.** This batch protocol is newer than some deployed MCP
> servers. Check the routed tool separately: SD is upgraded when
> `edit_sd_ai_managed_group` exposes `operation`; SP/SB is upgraded when
> `save_sp_sb_ai_managed_group.request` exposes `operation`, `ids`, and `batchParams`.
> If the relevant check fails, do not send new-protocol parameters; tell the user batch
> is unavailable on that server and edit groups one at a time instead.

- **`operation` + `ids` + params.** One `operation` per request. SD parameters are
  top-level. SP/SB Flat parameters go in `batchParams`; SP/SB action-space parameters
  go in `aiActionSettings`/`aiAutomation`. Don't mix unrelated fields.
- **`operation` values are UPPER_SNAKE_CASE** (`STATUS`, `BUDGET`, `BUDGET_REDISTRIBUTE`,
  ...) - prod-confirmed 2026-08-13; verify the exact enum in the tool schema. For a
  single SD flat change (e.g. AI on/off), **use the batch form `{operation:"STATUS",
  status:1}` rather than a Legacy full edit** - omitting `operation` took the Legacy path
  and returned a misleading `only supports SD groups` error in pre. See
  [`references/batch.md`](references/batch.md).
- **Validate ids vs profile.** The backend enforces profile authorization and **rejects
  cross-profile batches** (prod-confirmed 2026-08-13: a cross-profile edit is denied with
  `profileId ... is not authorized for the current user`). Still read each group first
  and confirm they're all under this profile and in the token's scope, and keep every
  batch single-profile - don't send one you expect to be rejected.
- **`ids` max is 20 - for every tool.** Both `edit_sd_ai_managed_group` and
  `save_sp_sb_ai_managed_group` reject more than 20 ids per call (prod-confirmed). Over
  20 -> split into batches of at most 20 ids, run them **serially**, and read back after
  each.
- **Group by tool, and split by ad type first.** SD -> `edit_sd_ai_managed_group` (flat,
  top-level); SP/SB -> `save_sp_sb_ai_managed_group` (`request`-wrapped) - different
  shapes, see batch.md. **SP + SB can share one SP/SB batch**, but only for operations
  **both** support; **SP-only operations** (`structOptimization`) must
  exclude SB ids. **SD is always its own call** - never mixed with SP/SB. The backend
  rejects a wrong-tool/wrong-type call (e.g. `campaignType must be sponsoredProducts or
  sponsoredBrands`), but split by each group's `campaignType` from metadata **before**
  sending rather than relying on that error.
- **Result is three-state.** A batch can **partially** succeed with `isError:false`.
  When `failedItems` is populated, derive the succeeded set and verify it. When it is
  empty, re-read every requested id to identify what applied. Never infer specific ids
  from counts or call a partial success a full success.
- **Mixed current state** (some on, some off): the AI-running silent-skip caveat applies
  per group - verify each.

When one user request requires multiple operations, execute them **serially** for the
same groups: call one operation, read back its result, then build the next request from
fresh state. Do not run writes concurrently. After a timeout, verify before retrying.

## Name marking

`campaignNameSign` toggles the `[AI]` label on campaign names. When turning it off,
`campaignNameRecoveryType` decides the name: `1` = keep the current name, `2` = restore
the original (pre-`[AI]`) name. Confirm which one the user wants - they're different
outcomes.

## Response & errors

Success: `{ "isError": false, "data": { "status": "success", ... } }` - a `success`
envelope does **not** prove the change applied (verify), and for bulk it can be
`partial_failure` with `isError:false` (see [`references/batch.md`](references/batch.md)).
Failures are `{ "isError": true, "data": { "error", "recoveryHint" } }` - relay
`recoveryHint` when present, but it isn't always populated, so validate up front.
**Don't confuse the read enum with the write enum, and don't assume one global write
enum.** The **read-back / query** value is `0`=never enabled, `1`=running, `2`=off. The
**write** enum depends on the tool and call path - SP/SB single-group edit (`aiStatus`),
SP/SB batch (`batchParams.status`, which uses `2`=paused), and SD batch (`STATUS`
operation, seen to use `1`/`2`) each take their own values per the routed schema and
[`references/batch.md`](references/batch.md). **Never reuse the query-returned `aiStatus`
value as a write value** - look up the correct write value for the exact path you're on.

## Reference files
- [`references/edit-sd.md`](references/edit-sd.md) - `edit_sd_ai_managed_group`: fields, ACOS/ROAS/Budget `*Type` mutual exclusion, batch `ids`, name recovery
- [`references/edit-sp-sb.md`](references/edit-sp-sb.md) - `save_sp_sb_ai_managed_group` edit mode: merge semantics, action space, campaign membership
- [`references/batch.md`](references/batch.md) - SD top-level and SP/SB wrapped batch protocols, operation parameters, ID-profile validation, three-state result
- [`references/field-reference.md`](references/field-reference.md) - exact write field names + enums (incl. edit-only `*Type` fields)
- [`references/action-space-matrix.md`](references/action-space-matrix.md) - capability support (AI / Rule / none) per SP / SB / SD, and `noRule` capabilities
- [`references/coupling-rules.md`](references/coupling-rules.md) - companion-field couplings, the 按表现调预算 / 预算重新分配 scope relationship, and group-total-budget rescale behavior
- [`references/budget-limits.md`](references/budget-limits.md) - site/account-type budget ranges (front-end rules MCP bypasses)
- [`references/enum-i18n.md`](references/enum-i18n.md) - 中文 <-> English <-> code
- [`references/platform-notes.md`](references/platform-notes.md) - shared write-tool behavior (MCP-bypass principle, silent-ignore rule, envelope, errors)
