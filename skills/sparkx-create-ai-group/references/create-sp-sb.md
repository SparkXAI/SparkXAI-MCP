# Create SP/SB managed group - `save_sp_sb_ai_managed_group` (create mode)

Creates a **Sponsored Products** or **Sponsored Brands** AI managed group. All
arguments go inside a single `request` object. **Create mode is triggered by leaving
`aiGroupId` empty (omit it or set `0`)** - a positive `aiGroupId` means edit, which
belongs to the `sparkx-edit-ai-group` skill.

Create mode is **AI mode only**. Use `aiActionSettings.xxxStatus` for the action-space
on/off switch. When that action space has a corresponding `aiAutomation` mode field,
set it to `0` (AI); never set it to `1` (Rule/RBA). Rule condition/action configs cannot be
written through this tool (they *can* be read - see `sparkx-query-entity-metadata`).

**Template-based creation is supported**: pass `templateId` (>0) and the template's config
becomes the baseline, with any field you send explicitly overriding it. Read templates first
with `get_ai_group_template`. One hard restriction: a template whose rule 4 / rule 5 is
bound to specific campaigns and ad groups (`isSelf=2`, rule enabled) is rejected. See the
main SKILL.md section "Creating from a template".

**If you send no `aiActionSettings` at all, the server fills in ad-type-appropriate
defaults** (an SB-specific default set for `sponsoredBrands`, otherwise the SP set). That's
usually what you want for a basic create - don't hand-build a full object just to look
thorough. It also means "I didn't send it" is not the same as "it's off": read the group back
if the user needs to know what's active.

## Required for create

| Field | Type | Notes |
|---|---|---|
| `profileId` | long | Shop ID |
| `aiGroupName` | string | Unique per profile |
| `acos` | number | Target ACOS on the **x100 scale** - the user's `25%` is sent as **`25`** (not `0.25`). Must be `> 0` |
| `targetType` | int | `1`=drive growth, `2`=maintain stability, `3`=volume, `4`=legacy growth |
| `campaignType` | string | `"sponsoredProducts"` or `"sponsoredBrands"` |

## Common optional fields

| Field | Type | Notes |
|---|---|---|
| `aiStatus` | int | `0`=off, `1`=on. **Omit it** - the server fills in `1` and the group starts optimizing. Send `0` only when the user asked for it not to start |
| `campaignIds` | int[] | Campaigns to include (auto-increment IDs). Omit to create an empty group |
| `campaignNameSign` | int | Campaign-name label: `0`=off, `1`=on |
| `aiPersonality` | int | `1`-`5`; **must be >=3 when `targetType=3` (volume/冲量)** (front-end rule - MCP won't enforce it) |
| `preAddCampaignNums` | int | Pre-add campaign count |
| `aiAutomation` | object | AI/Rule mode fields: create may use only `0`=AI; never `1`=Rule/RBA. See field-reference |
| `aiActionSettings` | object | Supported action-space config (bid / struct / budget / target optimization). See field-reference |

Only send `aiAutomation` / `aiActionSettings` fields the user wants to change from
platform defaults - both are large flattened objects and you rarely need most of it
for a basic create. Exact field names are in `field-reference.md`.

## Action-space coupling rules

Enabling an action-space switch usually requires sending its companion fields (dynamic
budget -> numType+num; ranges -> min/max with min <= max). Word-list settings are not
supported and must not be sent. The supported coupling rules are in the shared
[`coupling-rules.md`](coupling-rules.md) - read it before enabling any `aiActionSettings`
switch.

## SP vs SB differences (SB is not SP)

Some capabilities exist only for SP. On an SB group these are now **rejected outright**, not
silently ignored - the call fails with `X is not supported for sponsoredBrands; remove it or
set to 0` (or `set to null` for numeric range fields), and **every** offending field is
listed at once. Nothing is applied.

SP-only `aiActionSettings` fields (complete list as enforced):

| Group | Fields |
|---|---|
| B2B bidding | `bidAmazonBusinessStatus`, `btbRangeStatus`, `btbMin`, `btbMax` |
| Bid dayparting | `bidDaypartStatus` |
| Strict ACOS | `bidPerformanceStrictAcosStatus` |
| Placement bidding | `bidAdPlaceStatus`, `bidAdPlaceRangeStatus`, `tosMin`, `tosMax`, `pdpMin`, `pdpMax`, `rosMin`, `rosMax` |
| Struct optimization | `structPauseProductStatus`, `structPauseCampaignStatus` |

Sending `0` (or `null` for the numeric ones) is accepted - only an *enabled* value trips the
check. Best practice is to omit them entirely on SB.

**Template exception**: applying an SP template to an SB group (`templateId` set, and
`aiActionSettings` **omitted**) does not fail - the server zeroes those SP-only fields for
you. Send `aiActionSettings` yourself and you lose that: the template's action-space config
is skipped and your values go through the check above.

When the user is on SB and asks for one of these, tell them it isn't available for
Sponsored Brands rather than sending it and letting the whole call fail. The full "which capability is
supported (AI / Rule / none) per SP / SB / SD" matrix is in
[`action-space-matrix.md`](action-space-matrix.md) - check it before enabling any
action-space switch (notably: **SB's BidDaypart has no AI mode**, and
`budgetRedistribute` / `bidAmazonBusiness` are `noRule` - never attach Rule configs).

## Example - create a basic SP group

`aiStatus` is omitted, so the group is created with AI on and starts optimizing
immediately. Say that in the preview before calling this.

```json
{
  "request": {
    "profileId": 3721212165742,
    "aiGroupName": "SP-Core-Keywords-US",
    "campaignType": "sponsoredProducts",
    "acos": 25,
    "targetType": 1,
    "campaignIds": [45444534]
  }
}
```

**Same group, but the user asked not to start it yet** - add `aiStatus: 0`:

```json
{
  "request": {
    "profileId": 3721212165742,
    "aiGroupName": "SP-Core-Keywords-US",
    "campaignType": "sponsoredProducts",
    "acos": 25,
    "targetType": 1,
    "aiStatus": 0,
    "campaignIds": [45444534]
  }
}
```

`campaignIds` uses each campaign's internal `campaignId` (int) - **not**
`amazonCampaignId` (the long Amazon string).

Success returns `data.result.aiGroupId`. Then verify with the full-signature read
`get_entity_metadata(profileIds=[3721212165742], entity='aiGroup',
filters={"aiGroupName": {"like": "%SP-Core-Keywords-US%"}}, userContext='verify created group')`
and exact-match the name in the results (the filter is a substring `like`).

> Reminder: a group created with `aiStatus=0` reads back as `aiStatus=2`
> ("AI Turned Off") - that's expected, it is off.
