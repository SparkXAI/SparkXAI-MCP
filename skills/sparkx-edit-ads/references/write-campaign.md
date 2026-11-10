# Campaign writes

Seven routes: daily budget, state, bidding strategy, audience bid adjustment, placement bid
adjustment, name, end date. (Moving a campaign in or out of a portfolio lives in
[`write-portfolio.md`](write-portfolio.md).)

## `campaign` + `updateAudienceBid` - always confirms

Send `request.profileIds` and `request.data[]` with `id` (internal campaign ID),
`profileId`, `campaignType`, `audienceId`, `audienceSegmentType`, and
`audienceBidPercentage`. Each batch supports SP/SB only, one profile and campaignType,
at most 200 items, and an absolute integer percentage from 0 to 900. 0 retains the
audience binding with no uplift. This does not edit placements.

Only when the user explicitly requests disabling audience bid adjustment, set
`data[].audienceBidAdjustmentEnabled=false` and omit the audience fields. Skip audience
selection, but still show the preview and obtain confirmation: the server sends empty
`audienceId` and `audienceSegmentType`, and `audienceBidPercentage=0`, clearing the binding.
Non-empty audience fields or a non-zero percentage conflict with disabling and are rejected.
With the flag true or omitted, all existing audience fields remain required. Missing fields
or 0% alone never disable adjustment. Re-enabling requires specifying the audience and
percentage again. SP/SB, same-profile/type and campaign-state constraints still apply.

### `audienceSegmentType` - the field the read side will not give you

Two values, matching the two radio buttons under 选择受众类型 / Select audience type:

| Value | Console (EN) | Console (ZH) |
|---|---|---|
| `SPONSORED_ADS_AMC` | Increase bids on a custom audience created in AMC | 提高针对自定义 AMC 人群的竞价 |
| `BEHAVIOR_DYNAMIC` | Increase bids for audiences built by Amazon | 提高针对亚马逊人群的竞价 |

It is **required and has no default here**, and this is the hard part: **you cannot count on
reading which one an already-bound campaign is using.** `entity: campaign` does return
`audienceSegmentType` next to `audienceId` and `audienceBidPercentage`, but it may be empty - a
live check against a bound campaign returned it empty. Treat empty or any other value as unknown
and confirm the pool as described below.

**Sending the wrong one fails silently.** The two values address separate audience pools. An
`audienceId` from one pool submitted with the other is accepted by this tool, accepted
downstream, stored, and reported back as success - and then **never applies on Amazon**. There
is no error to react to and nothing in the response to notice, so there is no room to guess
now and correct later.

**Asking the user is the reliable answer.** The console shows the two options as radio
buttons, so it is a question they can answer at a glance, and no read path is known to settle
it authoritatively:

- On `get_ads_perf(factEntity='campaignAudience')` the same-named filter is **a name prefix
  downstream** (`segment_name LIKE 'AMC%'`), so it classifies by naming convention and
  misreads any audience whose name does not follow it. Do not use it to decide the type.
- `get_entity_metadata(entity='amcAudience')` lists each pool separately, so finding the
  `audienceId` under one value is **evidence**, and the pools do not overlap. Use it to form
  an expectation - but it lists what is bindable now, so an audience that is bound yet no
  longer offered simply will not appear, which is not proof of the other type.

So: check `amcAudience` for each of the two values if you want a starting point, and **confirm
with the user before writing** whenever it did not appear under exactly one of them. Do not
fall back to `SPONSORED_ADS_AMC` because it is the metadata filter's default - that default
belongs to the query, not to this campaign, and a wrong value here fails silently.

**A resolved `audienceName` proves nothing about the type.** Amazon-built audiences resolve
their names too. Do not infer the segment type from the presence of any enriched field.

Query campaign metadata for current binding and amcAudience for selectable IDs/types.
Never guess an ID or audience pool. The server checks the exact audience ID against the requested profile, campaign type and pool before preview and again before submission. Missing matches or unavailable lookups block the whole batch; explicitly disabling adjustment skips the lookup. The first call returns a preview, not a write result.
Review the target campaigns, audience IDs/types and new percentages with the user;
then resend identical parameters with the returned `request.confirmToken`.
The preview contains requested target values, not queried current values or audience names.
The existing five-minute, one-time confirmation protocol applies even if approval
was already given in conversation; see [confirmation.md](confirmation.md).

`campaignType` values everywhere: `sponsoredProducts` / `sponsoredBrands` /
`sponsoredDisplay`.

---

## `campaign` + `updatePlacementBid` - always confirms

Send `request.profileIds` and `request.data[]` with `id` (internal campaign ID),
`profileId`, `campaignType`, and **at least one** placement adjustment. An item carrying no
adjustment at all is rejected. SP / SB only; the `request.data` 200-item cap applies.

**The placement fields are different for SP and SB, and they do not cross over.** Field
names, and the labels the customer sees for them in the web console:

| campaignType | Field | Console label (EN) | Console label (ZH) | Decimals |
|---|---|---|---|---|
| `sponsoredProducts` | `topAdjustment` | Top of search (first page) | 搜索结果顶部(首页) | allowed |
| | `productPageAdjustment` | Product pages | 商品页面 | allowed |
| | `restOfSearchAdjustment` | Rest of search | 搜索结果的其余位置 | allowed |
| `sponsoredBrands` | `topOfSearchAdjustment` | Top of search | 搜索结果顶部 | **integers only** |
| | `homeAdjustment` | Home | 首页 | **integers only** |
| | `detailPageAdjustment` | Product page | 商品页面 | **integers only** |
| | `otherAdjustment` | Rest of search | 搜索结果的其余位置 | **integers only** |

Talk to the user in the console labels, not the field names - "搜索结果顶部" is what they see
on screen. Two of these are easy to get wrong:

- **SP's top-of-search field is `topAdjustment`; SB's is `topOfSearchAdjustment`.** Similar
  names, different campaign types, not interchangeable.
- **SB's "Rest of search" is `otherAdjustment`**, not `restOfSearchAdjustment` (which is
  SP-only). The name reads like a catch-all; the console does not offer any other SB
  placement, so it is the rest-of-search slot.

A field that is **present** but belongs to the other campaign type is rejected with
`... is not supported for this campaignType`. A field left **absent** is fine - see below.

**Omitting a field keeps its current value; it does not zero it.** Absent fields are not sent
downstream at all, which is exactly what the console means by "提交将维持修改前的值" /
"Submission without bid adjustment will maintain the value before modification". So send only
the placements you mean to change, and say so when you report back - "改了搜索结果顶部,其余
广告位保持原值", not "把广告位竞价设成了 X".

Every value is an absolute percentage from **0 to 900**. It replaces that placement's current
adjustment rather than adding to it, so re-running the same request is harmless - unlike the
budget and bid routes. `0` means "no uplift for this placement"; there is no way to remove a
placement, only to stop boosting it.

**SP keeps its bidding strategy; SB does not.** The route never forwards a `biddingStrategy`
of its own, so it cannot overwrite one. On SP that is the whole story. On **Sponsored Brands
the downstream also sets `bidOptimization=false`**, switching that campaign to custom bidding
as a side effect of the placement write - so this call does write a bidding-related field on
SB, and a concurrent change to `bidOptimization` can still be lost.

⚠️ **Say this to the user before writing an SB placement adjustment.** They asked to change
one number and they are also changing the campaign's bidding mode; that is not something to
discover afterwards. On SP there is no such effect - state the difference rather than
applying one warning to both.

To change a strategy deliberately, use `campaign + updateBiddingStrategy` as a separate call.

⚠️ **AI placement bid optimization.** The console shows a per-campaign "AI 广告位竞价优化" /
"AI ad placement bid optimization" toggle beside these fields. Where that automation is
running it manages placement adjustments itself, so a manual value set here may not be what
ends up live. This tool neither reads nor reports that toggle - if the user is surprised that
an adjustment "did not stick", point them at it rather than re-sending the write.

**One campaign per batch.** Listing the same `id` twice is rejected with
`duplicates campaign ... ; combine its placement adjustments into one item` - put every
placement for one campaign into a single item, not one item per placement.

**One campaignType and one marketplace per batch.** The marketplace is verified before the
write by reading the profiles; if a profile's country cannot be resolved, or the lookup
itself fails, the batch is refused (`Unable to verify marketplaces before updatePlacementBid`)
rather than submitted partially. Split by marketplace and resubmit.

The first call returns a preview, not a write result. The preview echoes the percentages you
asked for - it does **not** query and show the current adjustments, so if the user wants a
before/after comparison, read campaign placement metadata yourself first. The usual
five-minute single-use token rules apply; see [confirmation.md](confirmation.md).

---

## `campaign` + `updateBudget` - always confirms

Payload: `request.data[]`, each item:

| Field | Type | Required | Notes |
|---|---|---|---|
| `campaignId` | number | yes | internal id, must be positive |
| `profileId` | string | yes | must be one of `request.profileIds` |
| `campaignType` | string | yes | SP / SB / SD |
| `budget.type` | string | yes | one of the nine values below |
| `budget.amount` | number | yes | see rules |
| `budget.suggestBudget` | number | for `Suggest` modes | must be > 0 |

**Do not include** `adGroupId`, `state`, `keywords`, `targets` or `negativeKeywords` - a
foreign field rejects the whole batch.

### The nine `budget.type` values

```
setTo
increaseAmount        decreaseAmount
increasePercent       decreasePercent
increaseSuggestAmount    decreaseSuggestAmount
increaseSuggestPercent   decreaseSuggestPercent
```

Use the exact camelCase values above, with no spaces. Any type containing `Suggest` additionally requires
`budget.suggestBudget > 0`.

### Amount rules

**Units first, before the bounds below:**

- **Percent modes take `10` for 10%, not `0.1`.**
- **Amounts are in the profile's local currency** - never cents, never USD-converted. Budget
  (`dailyBudget` / `currentBudget`) read back from metadata is a JSON number; other amounts
  such as `targetBid` / `portfolioBudget` may still be **decimal strings** (`"100.00"`) - parse
  those before doing arithmetic.
- **Adjustment amounts are always non-negative.** To decrease, use a `decreaseAmount`, `decreasePercent`,
  `decreaseSuggestAmount` or `decreaseSuggestPercent` mode with
  a positive amount - **never pass a negative number**.


- `setTo`: `amount` must be **> 0**. Zero is rejected.
- Other types: `amount >= 0` (0 is accepted and means "leave unchanged").
- `increasePercent` / `increaseSuggestPercent`: `amount <= 10000`.
- `decreasePercent` / `decreaseSuggestPercent`: `amount <= 99`. **You cannot cut a budget
  by 100%** - use `setTo` with a floor, or pause the campaign instead.

### One campaignType and one marketplace per batch

The batch is rejected unless **all items share the same `campaignType`**. If the batch spans
more than one `profileId`, all those profiles must be in the **same country**; if the
marketplace cannot be resolved for any of them, the batch is rejected rather than
attempted.

So "raise every campaign's budget by 10%" across a mixed account is **several calls**: one
per campaignType per site. Say so rather than silently doing only part of it, and confirm
each batch separately.

The marketplace comes straight from `get_user_authorized_context` - each profile carries
`countryCode` (plus `currencyCode` and `timezone`). No extra lookup needed.

**The marketplace check only runs when the batch spans more than one profile.** A
single-profile batch skips it entirely, so the "marketplace could not be resolved" rejection
cannot happen there. The single-`campaignType` rule applies to every batch.

**Sponsored Brands lifetime budgets are not covered here.** All nine `budget.type` values are
daily-budget operations, and the only budget fields on the campaign entity are `dailyBudget`
and `currentBudget`. If an SB campaign is on a lifetime/total budget, do not assume this route
handles it - tell the user that is outside what you can verify.

### Read the current budget one profile at a time

Before a relative change (or any change you want to state as "from X to Y"), read
`dailyBudget` with a **single-`profileId`** metadata call. Multi-profile rows do carry their
own `currency`, so this is not about the currency being unknowable - it is about not taking an
amount from the wrong store's row, and about the fact that amounts across stores are not
comparable without converting. One profile per read keeps the base of a percentage or delta
unambiguous.

### Not idempotent

`increaseAmount 10` twice adds 20. If a call times out or returns
`ambiguous_write`, **read the budget back before retrying**.

### Reconciling the preview

The Phase 1 preview reports `currentBudget` / `projectedBudget`, and `currentBudget` is the
campaign's **`dailyBudget`** - not the `currentBudget` field on a metadata row, which is a
different number. Compare against `dailyBudget`. See
[`confirmation.md`](confirmation.md).

---

## `campaign` + `updateStatus` - confirms only for `archived`

Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `campaignId` | number | yes | positive |
| `profileId` | string | yes | |
| `campaignType` | string | yes | SP / SB / SD |
| `state` | string | yes | `enabled` / `paused` / `archived` |

`archived` is **irreversible** and triggers confirmation. Tell the user it cannot be undone
before you preview, not after.

Status changes are idempotent - re-sending `paused` is harmless.

The preview for this route shows `currentState: "unknown"` by design; the underlying query
does not return state. Do not report it as fact.

---

## `campaign` + `updateBiddingStrategy` - no confirmation

**SP only.** Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | the campaign's internal id (note: `id`, not `campaignId`) |
| `profileId` | string | yes | |
| `campaignType` | string | yes | must be `sponsoredProducts` |
| `biddingStrategy` | string | yes | one of the three below |

### The three strategies

| Value | Meaning |
|---|---|
| `legacyForSales` | Dynamic bids - **down only** / 动态竞价-仅降低 |
| `autoForSales` | Dynamic bids - **up and down** / 动态竞价-提高和降低 |
| `manual` | **Fixed** bids / 固定竞价 |

Older versions of the product spec labelled both `legacyForSales` and `manual` as
"固定竞价". **The table above is the correct mapping** - picking by the old labels silently
sets the wrong strategy and the call still succeeds.

⚠️ **`ruleBased` is rejected on this route.** It is a legitimate value to *read* back from
`get_entity_metadata` and `get_ads_perf` - campaigns really do run on it - but this batch route
will not set it, because it does not create the rule conditions that make rule-based bidding
mean anything. A campaign already on `ruleBased` can be switched to one of the three above;
moving *to* `ruleBased` has to happen in the console. Say that rather than picking a
substitute.

### What this route now refuses instead of ignoring

- **Any field that is not `id` / `profileId` / `campaignType` / `biddingStrategy`** -
  `name`, `state`, `startDate`, `endDate`, `portfolioBudget`, `amazonPortfolioId`,
  `defaultBid`: `only accepts id, profileId, campaignType and biddingStrategy`. These used to
  be dropped silently, so a request that "worked" before can now fail - send one action per
  call rather than bundling.
- **The same campaign twice** in one batch: the whole batch is rejected.
- **Ended or archived campaigns.** The shared guard only looked at `campaignState`, so a
  campaign with `campaignState: enabled` and `processStatus: Ended` used to go through. It is
  now re-checked and refused, as are campaigns whose state cannot be verified. A no-op request
  (sending the strategy a campaign already has) does not bypass this.

`businessType` is injected server-side; do not set it.

---

## Campaign name and end date - no confirmation

Two routes, both on `request.data`, both **executing immediately** - no preview, no
`confirmToken`, no undo. Get the user's agreement before calling either; a rename changes what
every report and every later lookup calls that campaign.

**One `campaignType` per batch** (`Campaign name/date edits require one campaignType per
batch`), SP, SB and SD all supported. Every item carries `id` (the internal campaign id),
`profileId` and `campaignType`, plus exactly one of `name` or `endDate`.

**Neither route accepts anything else.** `budget`, `portfolio`, `defaultBid` and `state` are
refused outright (`Campaign name/date edits do not accept budget, portfolio, bid or state`),
and so is `startDate` - **`startDate` is read-only here**
(`Campaign startDate is read-only; updateDates accepts endDate only`). Archived, ended or
unverifiable campaigns are refused before anything is written.

### `campaign` + `updateName`

`name` is required and non-blank; `endDate` must not be sent. The checks, all applied to the
**raw** value before trimming unless stated:

| Rule | Error |
|---|---|
| at most **128 UTF-16 code units** after trimming | `Campaign name must contain at most 128 characters after trimming` |
| no ISO control characters - leading/trailing tabs, newlines, U+0007, DEL, C1 | `Campaign name must not contain control characters` |
| no **U+200B ZERO WIDTH SPACE**, anywhere | `Campaign name must not contain U+200B ZERO WIDTH SPACE` |
| no HTML or script tags, comments included | `Campaign name must not contain HTML or script tags` |

The limit is measured with Java's `String.length()`, i.e. **UTF-16 code units, not visible
characters**. Anything outside the Basic Multilingual Plane - most emoji, and the rarer CJK
extension characters - costs **two** units each, so a name of 70 emoji is already over the
limit while 128 Latin letters is exactly at it. Count conservatively rather than trusting a
character count from elsewhere.

U+200B is singled out because Amazon rejects such names with `FORBIDDEN_CHARS` /
`campaign name has invalid characters`, and it is invisible: it survives `strip()`, is not an
ISO control character, and makes two names that look identical compare as different. **The
batch is rejected rather than the character silently removed** - so the name you sent is the
name you get or an error, never a quietly altered third thing. Other zero-width characters
(U+200C, U+200D) are *not* blocked; they have legitimate uses in some scripts and emoji
sequences. If a name you did not compose comes back refused, show the user the offending name
rather than cleaning it up for them.

⚠️ **Renaming is not atomic on any ad type, and the failure mode is different from
everything else here.** The SP/SB page has only a **single-campaign** rename endpoint, so items
are submitted **one at a time, in request order** - and SD goes through the same loop, one item
per downstream call, even though its endpoint takes a list. Do not read "SD uses a list API" as
"SD is atomic". If one fails after earlier ones succeeded, the call stops and
returns an ambiguous-write error naming the ids already accepted:
`Campaign rename stopped at id=...; previously accepted IDs=[...]; later items were not
submitted.` **Never replay the batch.** Read the current names back with
`get_entity_metadata(entity='campaign')` and resend only the campaigns that still have the old
name. Each response also needs reading item by item - acceptance is not Amazon
synchronization.

### `campaign` + `updateDates`

`endDate` is required - **omitting it or sending `null` is rejected**, which is the opposite of
most optional fields here. `name` must not be sent.

- Format `yyyyMMdd`.
- **An empty string clears the end date** on SP and SB.
- **Clearing is blocked on SD**: `Clearing SD campaign endDate is temporarily unsupported until
  the downstream synchronization is fixed`. This is a real downstream defect - the empty string
  reaches Amazon verbatim and comes back `End date has invalid date format, must be yyyyMMdd`,
  so the sync fails after the local write appears to succeed. Setting a non-empty SD end date
  is fine; only clearing is blocked. Tell the user to clear it in the console.
- **`endDate` must not be earlier than the campaign's current `startDate`** - the server reads
  the current value to check it (`endDate must not be before current startDate`).
- **It is not compared with today.** A past end date is accepted here; that is deliberate, not
  an oversight, so do not assume the platform will stop you from ending a campaign in the past.

Unlike renaming, `updateDates` goes downstream as **one batch call**.
