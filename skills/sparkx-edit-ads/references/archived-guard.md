# The archived-state guard

Every route runs this check **before** field validation and **before** confirmation. It
queries the platform for the current state of everything the write would touch, and
refuses the whole batch if anything is not writable. No downstream write is attempted.

## What gets checked

| Operation | Checked |
|---|---|
| `campaign` budget / state / bidding strategy | the target campaign |
| `keyword` / `target` / `productAd` / `negativeKeyword` / `negativeTarget` status, bid, archive | the entity itself **and** its owning campaign |
| `negativeKeyword` + `create` | the destination campaign |
| `keyword` / `target` + `create` | the destination ad group **and** its owning campaign |
| `productAd` + `create` | the destination campaign; plus the destination ad group when `adGroupId` is a positive integer |
| `negativeKeyword` + `copy` | destination campaign or ad group + owning campaign, per `businessType` |
| `negativeTarget` + `create` / `copy` | destination ad group + owning campaign |

`productAd + create` with `adGroupId = 0` means "the page endpoint picks or creates the ad
group", so no ad group is looked up; the destination campaign still is.

Only authorized profiles are queried - the guard never widens your permissions. Items whose
`profileId` is outside the authorized set are not checked here; they are rejected later by
the route's own authorization check, so the error you see is an authorization error, not an
archive error.

## What passes

Only `enabled` and `paused` (compared case-insensitively, whitespace trimmed) allow the
batch to continue.

**Everything else refuses the batch**, including: state is `archived`, state is missing,
state is an unrecognised value, the row was not found, the owning campaign could not be
resolved, or the lookup call failed. The guard **does not** let a write through because it
could not verify - it fails closed.

The state compared is the **current queried state**, not what you are setting. Submitting
`state=archived` for a live object is fine (it goes to confirmation); submitting anything
for an already-archived object is not.

## The five rejection messages

```
Batch rejected: archived campaigns cannot be modified; campaignIds=[1001, 1002]
Batch rejected: archived entities cannot be modified; entity=keyword; id=2001
Batch rejected: unable to verify keywordState; entity=keyword; id=2001
Batch rejected: unable to resolve owning campaign for keyword IDs [2001] in profile 4404871489220462
Batch rejected: unable to verify campaign state for campaign IDs [1001] in profile 4404871489220462
```

These are samples, **not the full set**: the campaign unknown-state message also occurs
without the `in profile <id>` suffix (the aggregated form, `... campaign IDs [1001]`), and a
guard *lookup failure* raises a different string entirely -
`Unable to verify archived campaign state before batch update`. So match on a short
substring (`archived`, `unable to verify`, `unable to resolve`), never on a whole sentence.

The two `unable to ...` forms are the most common in practice. In particular:

- **`unable to resolve owning campaign` usually means a wrong discriminator field**, not a
  wrong id. The guard filters the lookup by `campaignType`, plus `matchType` for keyword and
  `businessType` for negativeKeyword; a value that does not match returns no row. Check
  those against metadata first. See [`id-and-identity.md`](id-and-identity.md).

## The error you get is not the full picture

- The guard **stops at the first failing group** - the message does not enumerate every
  offending id in the batch. Fixing what it names may just reveal the next one.
- **"Unknown state" is raised before "archived"**, so a batch containing both may never
  mention the archived object at all.
- Do not iterate by deleting whatever id the error names and resubmitting the rest. That
  silently changes the scope of what the user approved. Re-read the entities, tell the user
  which ones cannot be modified, and let them decide the new scope.

## Error types

| Cause | `errorType` |
|---|---|
| archived / unknown state / unresolvable id / owning campaign not found | `invalid_params` |
| the state lookup itself failed | `business_error` |

There is no dedicated `archived_*` error type. `invalid_params` here does **not** mean your
JSON was malformed - read the message.

## In Phase 2

The guard re-runs on the confirmation call, because Phase 2 is a separate tool call. If a
target was archived between preview and confirmation, Phase 2 refuses - and because the
guard runs before the token is consumed, **the token is still usable**. Fix the condition
(or reduce the scope with the user's agreement, via a fresh preview) rather than assuming
you must start over.

The check and the downstream write are not one transaction. Final ownership and state
constraints are still enforced downstream.

## Batch size interaction

The guard looks up at most 1000 ids per profile per query and refuses outright if a single
query would exceed that. With the 200-operation batch cap you cannot reach it, but do not
design around it changing.
