---
name: sparkx-edit-ads
description: >-
  Edit live Amazon Sponsored ad entities in bulk through the single tool
  `batch_update_ads` - campaign daily budget / state / bidding strategy, keyword and target
  status and bids, promoted products (product ads), negative keywords and negative product
  targets. 18 entity+action routes; 9 of them require an explicit two-phase user
  confirmation. Use when the user wants to change / pause / enable / archive / raise / lower
  / add / copy something on the ads themselves - 改预算 / 暂停广告 / 调价 / 加词 / 加否定词 /
  投放商品 / 复制否定词. Not for AI managed groups (托管组) - creating, editing or deleting
  those uses sparkx-create-ai-group / sparkx-edit-ai-group / sparkx-delete-ai-group. Not for
  reading data (use sparkx-query-ads-performance / sparkx-query-entity-metadata).
metadata:
  version: 1.0.0
---

# Edit Ads

One tool, `batch_update_ads(entity, action, request, userContext)`, covers every write.
`entity` + `action` select one of **18 registered routes**; an unregistered pair is refused.

Read [`references/platform-notes.md`](references/platform-notes.md) once first - scope,
the response envelope, the full `errorType` list, rate limits, and how to tell
"it failed" from **"we do not know whether it applied"**.

## These writes touch live spend

Every route here changes a real campaign that is spending real money right now.

**Treat every `state = archived` write as irreversible.** Once an object is archived the
archived-state guard refuses any further write to it through this tool, so there is no
un-archive path here - that applies to keywords, targets, negative keywords and negative
targets just as much as to campaigns.

Do not confuse "irreversible" with "always confirms" - they are different sets:

- **Always confirms, on every call** (4 routes): `campaign + updateBudget`,
  `keyword + updateBid`, `target + updateBid`, `productAd + archive`.
- **Confirms only when the payload contains `archived`** (5 routes): the `updateStatus`
  routes of `campaign`, `keyword`, `target`, `negativeKeyword`, `negativeTarget`.

So `productAd + archive` is the only archive path that is *always* gated;
`campaign + updateStatus` with `archived` is gated **conditionally**, by the value you send.
An archive you build without `archived` in the payload gets no preview at all.

A confirmation preview only tells the user *what* you are about to do - **you** are
responsible for it being the right thing.

## Before you write anything

1. `get_user_authorized_context` -> each profile carries `profileId`, `profileName`,
   `countryCode`, `currencyCode`, `timezone` and **`storeType`** (`seller` / `vendor`).
   That one call answers the marketplace and seller-vs-vendor questions - do not go looking
   elsewhere for them. **If the profile-metadata lookup fails the server degrades to
   `profileId` only**, so when `storeType` (or `countryCode`) is missing, blank, or not one
   of the expected values, ask the user instead of guessing. **`profileIds` is all-or-nothing**: one
   unauthorized id rejects the entire batch. Never widen the set "just in case".
   Note the server **de-duplicates** `profileIds`, so `meta.effectiveProfileIds` can be
   shorter than what you sent.
2. `get_entity_metadata` -> the **internal** ids AND their discriminator fields. See
   [`references/id-and-identity.md`](references/id-and-identity.md). This step is not
   optional and its output cannot be guessed.

**The ids from `get_ads_perf` and `get_operation_log` are Amazon ids (15-19 digits) and
are useless here.** Passing one either fails a positive-long check or resolves nothing.

## The five rules that will bite you

**1. Always send the discriminator fields, exactly as metadata returned them.**
`keywordId` alone does not identify a row. Keyword writes are routed to one of three
different physical tables by `matchType` (`theme` -> theme table, `group` -> target table,
`exact`/`phrase`/`broad` -> keyword table) and those tables have **independent id spaces**.
Negative keywords are split by `businessType`, negative targets by `campaignType`, the
same way.

- Send `matchType` + `campaignType` for keyword, `businessType` + `campaignType` for
  negativeKeyword, `campaignType` for target / productAd / negativeTarget.
- **Echo the value metadata gave you. Never infer it, never omit it, never normalise its
  case.** A wrong value surfaces as the confusing `unable to resolve owning campaign`;
  omitting it silently drops a safety filter.
- This is about the *value*, not the JSON type: internal ids go into write payloads as
  **numbers** even where a read table shows them as strings, and only `profileId` and
  text/enum values are strings. Converting `"991201"` to `991201` is required, not
  normalising.
- The spec's per-route field tables mark some of these "透传" (pass-through). Treat them
  as **required** regardless.

**2. Send enums byte-exact.** Every enum is matched case-sensitively with no trimming and
no aliases. `"ENABLED"`, `"Exact"`, `" archived"` all fail. Only `profileId` is trimmed.

**3. Nested `profileId` is a string; top-level `profileIds` is an array of numbers.**
`request.profileIds: [4404871489220462]` but `data[].profileId: "4404871489220462"`.
Quote every nested one - unquoted large ints risk precision loss. Send every **other** id
(`campaignId`, `adGroupId`, `id`) as a number. (Page routes do parse numeric strings too,
but do not rely on it.)

**4. There is no partial success on validation.** Both internal and page routes reject the
**whole batch** before calling anything downstream if any item is invalid. Do not design a
"submit everything and let the server drop the bad rows" flow. Note the difference when
fixing: **internal routes list every bad item** in one message; **page routes name only the
first**, so fixing a page-route batch costs one round-trip per bad item.

**5. Any object being touched must not be archived.** Before validation, before
confirmation, every route queries the current state of the targets, the destination
campaign/ad group, and the owning campaign. Archived -> whole batch refused. **State
missing, unknown, or unqueryable -> also refused** (fail-closed). Details and the five
distinct rejection messages: [`references/archived-guard.md`](references/archived-guard.md).

## Pick the route

| User intent | entity + action | Confirm |
|---|---|---|
| change campaign daily budget | `campaign` + `updateBudget` | always |
| enable / pause / archive a campaign | `campaign` + `updateStatus` | if `archived` |
| change SP bidding strategy | `campaign` + `updateBiddingStrategy` | - |
| add negative keywords to a campaign | `negativeKeyword` + `create` | - |
| enable / pause / archive negative keywords | `negativeKeyword` + `updateStatus` | if `archived` |
| copy negative keywords elsewhere | `negativeKeyword` + `copy` | - |
| add keywords / keyword groups / themes to an ad group | `keyword` + `create` | - |
| enable / pause / archive keywords | `keyword` + `updateStatus` | if `archived` |
| change keyword bids | `keyword` + `updateBid` | always |
| add product / category / expression targets | `target` + `create` | - |
| enable / pause / archive targets | `target` + `updateStatus` | if `archived` |
| change target bids | `target` + `updateBid` | always |
| promote products (ASIN/SKU) into a campaign | `productAd` + `create` | - |
| enable / pause a promoted product | `productAd` + `updateStatus` | - |
| archive a promoted product (**irreversible**) | `productAd` + `archive` | always |
| add negative ASIN / brand targets | `negativeTarget` + `create` | - |
| enable / pause / archive negative targets | `negativeTarget` + `updateStatus` | if `archived` |
| copy negative targets | `negativeTarget` + `copy` | - |

Per-route payloads, enums and limits live in the four write references:
[campaign](references/write-campaign.md) - [keyword & negative keyword](references/write-keyword.md) -
[target & negative target](references/write-target.md) - [product ad](references/write-product-ad.md).
The payload **array name differs per route** (`data` / `updates` / `campaigns`+`asins` /
`businessType`+`target`) and a wrong name is silently dropped, then reported as
"required array missing" - check [`references/route-matrix.md`](references/route-matrix.md)
before building the request.

## Workflow

```
1. get_user_authorized_context            -> profileIds
2. get_entity_metadata                    -> internal ids + discriminator fields
                                             (+ current bid, for updateBid)
3. Resolve the user's words to ONE entity+action. Ambiguous -> ASK, do not pick.
4. Build request. userContext is **required and must be non-blank**, <= 100 characters
   (counted as characters, so CJK is 1 each - not bytes). It is the user's own request
   plus why.
5. Call batch_update_ads.
6. data.status == "PENDING_CONFIRMATION" -> show the preview, get a real yes,
   then call again with request.confirmToken added and everything else unchanged.
7. Read the result as three-state (see platform-notes.md), then
8. get_entity_metadata again and confirm the fields actually moved.
```

Step 8 is not optional for anything irreversible or bid/budget related.

## Two-phase confirmation

Nine routes return a preview instead of writing. Full protocol, preview field meanings and
failure modes: [`references/confirmation.md`](references/confirmation.md). The parts you
cannot get wrong:

- **Phase 2 must be byte-identical** except for the added `request.confirmToken`. The
  fingerprint covers `entity` + `action` + `request`; changing any value invalidates the
  token. (`userContext` is not fingerprinted, but keep it consistent anyway.)
- The token is an **opaque UUID with no prefix**, valid **5 minutes**, single use, bound to
  the user who previewed.
- **A conditional-confirmation batch previews only the `archived` items, but Phase 2
  executes the whole batch.** If you sent 1 archive plus 20 pause changes, the preview
  headline counts 1. `details.batchItemCount` and `details.otherStatusChanges` carry the
  rest - **but only on `updateStatus` routes**; they are absent on budget, bid and archive
  previews. **Always state the full scope yourself**; do not let the user confirm a number
  that describes part of the batch.
- **Never auto-confirm.** Do not call Phase 2 without the user actually saying yes in
  response to the preview. If they decline, do not call again.
- A null field in the preview means the lookup failed or matched nothing - **not** "the
  value is empty". Never present it as fact. `campaign + updateStatus` previews always show
  `currentState: "unknown"` by design.

## Resolving what the user pointed at

Users say "这个广告活动", "这些关键词", or paste names - not internal ids. You cannot guess
the id, and the lookup is fuzzier than it looks:

- **Name matching is contains-only.** `get_entity_metadata`'s `like` strips your `%` and
  always matches "contains". There is no exact-name match, so a pasted name can hit rows
  the user did not mean.
- **One name can be several rows.** The same keyword text commonly exists as both `exact`
  and `phrase`, in more than one ad group, or in more than one campaign. Four pasted
  keywords can resolve to seven rows.
- **So: resolve first, then show the resolved rows and get agreement before writing** -
  ids, names, ad type, current state. Never write on a name match you have not shown.
- If the user is pointing at something on screen that you cannot see, say so and ask for
  the name or id. Do not pick the first match.
- Filter the read on that entity's own state field so you find out up front that something
  is archived, instead of eating a whole-batch rejection later. **There is no generic `state`
  field** - it is `campaignState`, `adGroupState`, `keywordState`, `targetState`,
  `productAdState`, `negativeKeywordState` or `negativeTargetState`, and an unknown filter
  field is a hard error. Say which rows you excluded and why.
- If a row is already in the state the user is asking for, say so rather than silently
  including or dropping it. Re-sending `enabled` or `paused` is idempotent and harmless -
  but the user should know it was already paused. **This does not extend to `archived`**: an
  already-archived object is refused by the archived-state guard, not quietly accepted.

## Confirm it yourself when the platform does not

Nine entity+action pairs **can** require a preview - four always, five only when the
payload contains `archived`. The other nine write **immediately**, with no preview and
no undo:

`campaign + updateBiddingStrategy` - `keyword + create` - `target + create` -
`negativeKeyword + create` - `negativeKeyword + copy` - `negativeTarget + create` -
`negativeTarget + copy` - `productAd + create` - `productAd + updateStatus`.

**Do not add the `updateStatus` routes of `keyword` / `negativeKeyword` / `target` /
`negativeTarget` to that list.** Those write immediately **only for `enabled` / `paused`**;
the moment the payload contains `archived` they return a preview and require confirmation.
Never treat one of them as immediate without checking what `state` you are sending.

So before an immediate-write call, **show the user what you are about to do and get a yes**
whenever the change is bulk (more than a couple of rows), changes bidding behaviour, or
creates something that would have to be cleaned up by hand. Say plainly that it applies as
soon as you send it. A route having no platform confirmation is not permission to skip
asking.

## Do not guess - ask

These words map to different routes, and choosing wrong changes live spend:

- **"暂停" / "stop it"** - the campaign, or just some keywords/targets/products? Different
  entities.
- **"删除" / "下架"** - almost always means **archive**, and archiving is
  **irreversible for every entity here** - campaigns, keywords, targets, promoted products,
  negative keywords and negative targets alike. Confirm that is what they mean, say it cannot
  be undone, and offer `paused` as the reversible alternative.
- **"调价"** - keyword bid, target bid, budget, or bidding strategy? "竞价"/"出价" is a
  keyword/target bid; "预算" needs one more question - see the next bullet.
- **"预算"** - this tool changes a **campaign's daily budget**. But if the campaign sits in
  an AI managed group (`campaign.aiGroupId` is set), the user may mean the **group's total
  budget** instead, which is a different setting on a different tool
  (`sparkx-edit-ai-group`). Two reasons this matters:
  - Editing the group total **proportionally rescales every enabled campaign's daily
    budget** in that group - so it is not the same operation with a different name.
  - Conversely, a daily budget you set here on an AI-managed campaign can be rescaled away
    the next time the group's total budget is edited or the AI re-optimises.

  So when the campaign is under a managed group, **ask which budget they mean** before
  writing, and say which tool will be used.
- **"加词"** - a positive keyword (`keyword + create`) or a negative one
  (`negativeKeyword + create`)? Opposite effects.
- **"+10"** - +10 currency units or +10 percent? Budget and bid both support both, and
  **neither is idempotent** - running "increase amount 10" twice adds 20.

If a request could mean more than one of these, **stop and ask**.

## What these files do not tell you

When one of these comes up, **say you do not know and ask** - do not reason from general
Amazon Ads knowledge, because the platform's behaviour here is what matters:

- **Sponsored Brands lifetime/total budgets.** The nine `budget.type` values are daily-budget
  operations. Whether `campaign + updateBudget` handles an SB campaign on a lifetime budget,
  errors, or moves a different number is not documented.
- **AI-managed campaigns.** If a campaign has an `aiGroupId`, whether a manual bid or
  bidding-strategy change sticks or gets re-optimised at the next AI evaluation is not
  documented here. Tell the user the campaign is under AI management and let them decide;
  managed-group settings themselves belong to the managed-group skills. One mechanism *is*
  documented: editing a group's **total** budget rescales its campaigns' daily budgets
  proportionally, so a daily budget set here can be overwritten that way.
- **Switching away from `ruleBased`** bidding strategy.
- **`profileType`** for `productAd + create` when `profiles[].storeType` came back empty
  (server-side degradation) - there is no other source, so ask.
- **A platform minimum daily budget.** `set to` requires an amount above 0, but the real
  floor (and whether it varies by marketplace) is not documented.

## Composition limits

- **200 write operations per call.** For the internal `create` routes this counts the
  **expanded sub-items summed across the batch**, not the number of `data` entries: 3 items
  x 100 keywords = 300 -> rejected.
- **A budget batch must be one `campaignType`, and one marketplace when it spans several
  profiles.** All items must share `campaignType` always. The marketplace check only runs
  for a multi-profile batch: those profiles must share a `countryCode` (which
  `get_user_authorized_context` already gave you), and if it cannot be resolved the batch
  is refused. Split SP/SB/SD, and split by site when crossing profiles.
- **When one request becomes several calls, say so before you start**, and confirm each
  batch separately - each one needs its own preview and its own yes. If the user approves
  some batches and declines others, their original intent ends up **partly applied**: state
  exactly which parts went through and which did not, and do not treat the approved part as
  finishing the request.
- Only send the fields a route uses. Internal routes **reject foreign write fields
  outright** - a `campaignId` added "for context" to `keyword + create`, or a `state`
  alongside `budget`, fails the whole batch.
- Write rate limit is **20 calls/min** per tenant+tool and per user+tool. A serial
  write/read-back loop over many entities will hit it; pace it and honour
  `retryAfterSeconds`.

## After the write

The envelope is not proof. Read [`references/platform-notes.md`](references/platform-notes.md)
for the three-state result rules, then re-read the entities with `get_entity_metadata`.

**`ambiguous_write` means the state is unknown, not that it failed.** Downstream returned
success but the row count or ids did not line up, or the call timed out. **Do not retry** -
read the entities back first and tell the user what you found.

## Reference files

| File | Read it when |
|---|---|
| [`references/platform-notes.md`](references/platform-notes.md) | Always, first. Scope, envelope, `errorType`, rate limits, three-state results |
| [`references/route-matrix.md`](references/route-matrix.md) | Building any request - which array name, which ad types, which routes confirm |
| [`references/id-and-identity.md`](references/id-and-identity.md) | Always, before the first write. Internal ids, discriminator fields, metadata gotchas |
| [`references/confirmation.md`](references/confirmation.md) | Any of the 9 confirmation routes |
| [`references/archived-guard.md`](references/archived-guard.md) | A batch was refused and you need to know why |
| [`references/write-campaign.md`](references/write-campaign.md) | Budget, state, bidding strategy |
| [`references/write-keyword.md`](references/write-keyword.md) | Keywords and negative keywords |
| [`references/write-target.md`](references/write-target.md) | Targets and negative targets |
| [`references/write-product-ad.md`](references/write-product-ad.md) | Promoted products |
