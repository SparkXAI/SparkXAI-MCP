# Ad group state

`adGroup + updateStatus` changes SP/SB/SD ad groups and executes directly, including
`state: "archived"`. The platform does not issue a confirm token for this route, so obtain
the user's approval before an irreversible archive.

Use `request.data` with 1-200 items. Every item requires:

| Field | Rule |
|---|---|
| `id` | internal `adGroupId` from metadata, not `amazonAdGroupId` |
| `profileId` | authorized profile owning the row |
| `campaignType` | exact metadata value: `sponsoredProducts` / `sponsoredBrands` / `sponsoredDisplay` |
| `state` | exact lowercase `enabled` / `paused` / `archived` |

Before writing, the server verifies the ad group and parent campaign, rejects configured
`archived` rows and `processStatus: Archived/Ended`, and refreshes `adGroupName` and
`defaultBid` because the downstream status endpoint requires them. A real zero bid is valid;
a missing or unparsable bid is not replaced with zero. An empty `processStatus` may be valid,
but a failed or incomplete metadata lookup rejects the whole batch.

Several states can be mixed in one call. If any target is already archived, the whole batch is
rejected before writing. The read and write are not one transaction; read the ad groups back
and report actual resulting states.

---

## Ad group name - `adGroup` + `updateName`

`adGroup + updateName` renames SP, SB and SD ad groups and **executes directly** - no
confirmation token, no preview. Renaming does not change delivery, but it does change what
every report and every later lookup calls that ad group, so state the old and new names back
to the user.

`request.data`, 1-200 items, same identity fields as the state route:

| Field | Rule |
|---|---|
| `id` | internal `adGroupId` from metadata, **not** `amazonAdGroupId`; must be a positive integer |
| `profileId` | authorized profile owning the row, a positive-integer **string** |
| `campaignType` | `sponsoredProducts` / `sponsoredBrands` / `sponsoredDisplay` |
| `name` | 1-255 characters **after trimming**; leading and trailing whitespace is stripped before the length check and before the write |

**One `campaignType` per batch.** Mixing types in one call is rejected with `Ad group
name/bid edits require one campaignType per batch; submit each campaignType separately`.
Group the user's ad groups by type and send one call per type.

**No duplicate rows.** Two items with the same `profileId` + `campaignType` + `id` fail with
`request.data[N] duplicates an ad group`, before anything is written.

Only the field this action owns is sent downstream - a rename writes the name and nothing
else, so it cannot silently carry a stale bid along with it.

---

## Ad group default bid - `adGroup` + `updateBid`

`adGroup + updateBid` sets the ad group's default bid. **SP and SD only** - an SB item is
rejected with `Only SP/SD ad groups support default bid editing`, and SB has no equivalent
route, so tell the user rather than substituting a target-level bid change.

**This route always confirms.** Phase 1 returns a preview titled `Set ad group default bids:
N item(s)` and a `confirmToken` valid for 5 minutes; Phase 2 repeats the call with the token
added and everything else unchanged.

> The preview carries **the new values only**. It does not read the current bid, so a preview
> that looks right is not evidence the baseline is what you think it is. Read `defaultBid`
> through `get_entity_metadata(entity='adGroup')` before building the request whenever the
> user asked for a relative change ("raise by 10%") - the tool takes absolute amounts.

`request.data`, same identity fields as above, plus `defaultBid`. The same **one
campaignType per batch** and **no duplicates** rules apply.

### What the server checks before issuing the token

Every item is verified against the live ad group and its parent campaign. Any failure rejects
the whole batch - there is no partial write.

- **Editable state.** Archived or ended ad groups, and ad groups whose `processStatus` is
  missing, blank or unverifiable, are refused: `Archived, ended or unverifiable ad groups
  cannot be edited`. An unverifiable row is refused on purpose - the server will not write a
  bid it could not check.
- **Decimal shape.** Positive, at most two decimal places. **JP must be a whole number** -
  `JP defaultBid must be an integer`.
- **Marketplace range.** Bounds come from the marketplace, and for SD also from the campaign's
  `costType`. The error names both bounds, so read it rather than guessing:
  `SP defaultBid must be between <min> and <max>`, or for SD `defaultBid must be between
  <min> and <max> for <country> <costType>`.
- **Against the campaign's daily budget.** SP: the bid must not exceed the budget. SD: the bid
  must be **strictly less than half** the budget - `SD defaultBid must be strictly less than
  half the campaign daily budget`. A bid exactly at half fails. If the user wants a bid the
  budget cannot support, raising the budget is a separate `campaign + updateBudget` call with
  its own confirmation; do not do it silently.
- **Verifiability of the inputs themselves.** If the campaign budget, the marketplace or (for
  SD) the `costType` cannot be read, the batch is rejected rather than written on a guess:
  `Unable to verify SP campaign daily budget`, `Unable to verify SP marketplace bid limits`,
  `Unable to verify SD marketplace, costType or daily budget`.

**The bid ranges here are the ad-group-page ranges, not the campaign-creation ranges.** They
differ by marketplace - AU, for one, allows a lower minimum on edit than on create. Do not
carry a limit over from `sparkx-create-campaign`; let the error tell you the bound.
