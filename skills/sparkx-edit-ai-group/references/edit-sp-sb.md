# Edit SP/SB managed groups - `save_sp_sb_ai_managed_group` (edit mode)

All arguments go inside a single `request` object. **Edit mode = `aiGroupId` > 0**
(a positive id of an existing group owned by `profileId`). `aiGroupId = 0`/null is
*create* - that's sparkx-create-ai-group.

## Merge semantics - send only what changes

The tool **queries the group's current config internally and merges your changes onto
it**. So you only need to send the fields you're changing; everything you omit keeps
its current value. Read the current config first (so you can show old -> new and verify
after), but don't resend unchanged fields.

In **single-group edit mode**, SP/SB `acos` is a plain number (x100 scale, 25% -> `25`)
and there is no `acosType`/`budgetType` machinery. In **operation-based batch mode**,
Flat operations use the type selectors and companion values inside `batchParams`; see
[`batch.md`](batch.md).

## Action-space switch and mode restriction

- `aiActionSettings.xxxStatus` is the action-space switch: `0` = off, `1` = on.
- When the switch is on, the corresponding `aiAutomation` mode field is `0` = AI or
  `1` = Rule/RBA. Use the exact mapping in `field-reference.md`.
- Editing may set the mode field to `0` to switch **Rule/RBA -> AI**, but must not set
  it to `1` to switch **AI -> Rule/RBA** - a `1` is rejected.
- Every rule keeps its current mode unless you set it to `0`; omitted rules are untouched
  (a Rule-mode rule stays Rule).
- Turning an action-space switch on (`aiActionSettings.xxxStatus=1`, from your params or a
  template) restores that space's existing mode - if the group's rule is `status=1`, it
  resumes in Rule mode. **Exception:** turning `targetHarvestStatus` / `negativeTargetStatus` from off
  to on is rejected while rule 4 / 5 is in Rule mode on the group - set that rule to `0` in
  `aiAutomation` in the same request, or use the platform.
- **Template edit** (`templateId` > 0, `isSystemTemplate=1` for system presets): if the template's
  rule 4 (Target Harvest) or rule 5 (Negative Target) is in Rule mode (`status=1`), the call is
  rejected before anything is written, whether or not you pass `aiAutomation`; offer a template
  whose rules 4 / 5 are AI mode, or the platform UI. Other Rule-mode rules in the template (e.g.
  Budget Daypart rule 13) are written as-is when you omit `aiAutomation`; if you pass your own
  `aiAutomation`, the template's rules are ignored. Archived templates (`status=2`) are rejected;
  `aiStatus` is never taken from the template.
- **RBA configuration is readable, and writable only by inheriting a template.** For a rule in
  Rule mode, `get_entity_metadata(entity='aiGroup')` returns its real conditions, actions,
  condition items, time periods and hour matrices under `aiAutomation.{ruleType}` - you may read
  and explain that setup, but never hand-write, reconstruct or migrate it. **You cannot create or edit Rule-mode conditions and actions through MCP.** The one way Rule config reaches a group is applying a platform template with `templateId`: the template's own `aiAutomation` is carried in as-is, Rule-mode rules included, so a template *can* put an action space into Rule mode with its conditions and actions (a template whose rule 4 or 5 is in Rule mode is rejected). You inherit that config, you never author it. For any other RBA change, point the user to the platform.
- Schedules **are** writable, but through a different tool
  (`save_sp_sb_ai_group_schedule`) - not via these fields. See the Scheduling section in the
  main SKILL.md; note in particular that a read row is not a write payload.

## Editable fields

Top-level: `aiStatus` (`0`=off, `1`=on), `targetType` (`1` growth / `2` stability /
`3` volume / `4` growth with budget utilization priority), `acos`, `campaignIds`, `campaignNameSign`,
`aiPersonality` (`1`-`5`, **>=3 when `targetType=3`**), and the nested
`aiActionSettings` / `aiAutomation` objects.

⚠️ **`aiPersonality` is group-level and belongs to legacy accounts.** On an account that
sets personality per action space it is rejected before any downstream call, and the 12
`*AiPersonality` fields inside `aiActionSettings` take its place. You cannot tell which
kind of account you are on in advance - read [`ai-personality.md`](ai-personality.md) before
sending either form.

## Changing campaign membership - don't assume append

The tool describes `campaignIds` as "campaigns to include; omit to keep current". It is
**not confirmed** whether passing the array **replaces** the group's whole campaign set
or **adds** to it. So **never** pass a single ID to "add one campaign" - if the array is
a full replacement, that would drop every other campaign in the group.

To change membership safely: **read the group's current full campaign list first**
(query `entity='campaign'` filtered by the group's `aiGroupId`), construct the intended
**final** set (current +/- the change), show it to the user, and only send after they
confirm. If you just want to change settings and not membership, **omit `campaignIds`
entirely.** (Confirm the replace-vs-append semantics with the backend before relying on
either.)

Action-space field names, coupling rules, and the SP/SB support differences are in
[`field-reference.md`](field-reference.md), [`coupling-rules.md`](coupling-rules.md),
and [`action-space-matrix.md`](action-space-matrix.md). The same rules apply on edit:
enable only capabilities supported (as AI) for this ad type; `noRule` capabilities take
no Rule params; SP-only fields sent to SB should be rejected (2026-08-14 spec) but may
still be silently ignored today - either way don't send them (say so).

## Bulk (multiple SP/SB groups)

Multi-group edit uses the **operation-based batch protocol** - inside `request`:
`operation` + `ids` + `batchParams` (Flat) / `aiActionSettings` / `aiAutomation`
(action-space), one operation per request, with mandatory id<->profile validation and
three-state result handling. See [`batch.md`](batch.md).

**SP and SB can be batched together** for operations both support; **SP-only operations**
(`structOptimization`) must **exclude SB** ids. (`targetPausedAdd` is SP-only too; see the target-switch note in [`batch.md`](batch.md).) **SD**
always uses the other tool (`edit_sd_ai_managed_group`) - never in the same call.

## Example - retarget one SP group to volume with an aggressive personality

```json
{
  "request": {
    "profileId": 3721212165742,
    "aiGroupId": 826117,
    "targetType": 3,
    "aiPersonality": 4
  }
}
```

(`targetType=3` volume requires `aiPersonality >= 3` - 4 is fine.) Then verify by
reading the group back and confirming `targetType`/`aiPersonality` changed.

**This example is the legacy-account shape.** On a per-action-space account the same call
is rejected for carrying `aiPersonality`; send `bidPerformanceAiPersonality` and the other
relevant fields inside `aiActionSettings` instead - see [`ai-personality.md`](ai-personality.md).

> Reminder: if the group's AI is running (`aiStatus=1`), some changes may be silently
> skipped - verify, and don't turn AI off on your own to force them.
