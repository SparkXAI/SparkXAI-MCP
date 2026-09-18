# Campaign writes

Four routes: daily budget, state, bidding strategy, audience bid adjustment.

## `campaign` + `updateAudienceBid` - always confirms

Send `request.profileIds` and `request.data[]` with `id` (internal campaign ID),
`profileId`, `campaignType`, `audienceId`, `audienceSegmentType`, and
`audienceBidPercentage`. Each batch supports SP/SB only, one profile and campaignType,
at most 200 items, and an absolute integer percentage from 0 to 900. 0 retains the
audience binding with no uplift. This does not unbind audiences or edit placements.

### `audienceSegmentType` - the field the read side will not give you

Two values, matching the two radio buttons under 选择受众类型 / Select audience type:

| Value | Console (EN) | Console (ZH) |
|---|---|---|
| `SPONSORED_ADS_AMC` | Increase bids on a custom audience created in AMC | 提高针对自定义 AMC 人群的竞价 |
| `BEHAVIOR_DYNAMIC` | Increase bids for audiences built by Amazon | 提高针对亚马逊人群的竞价 |

It is **required and has no default here**, and this is the hard part: **nothing you can read
tells you which one an already-bound campaign is using.** `entity: campaign` returns only
`audienceId` and `audienceBidPercentage` - the segment type is not on the row, and a live
check against a bound campaign returned it empty.

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

Never guess an ID or audience pool. The first call returns a preview, not a write result.
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
- **Amounts are in the profile's local currency** - never cents, never USD-converted. Money
  read back from metadata is a **decimal string** (`"100.00"`); parse it before doing
  arithmetic.
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
| `biddingStrategy` | string | yes | one of the four below |

### The four strategies

| Value | Meaning |
|---|---|
| `legacyForSales` | Dynamic bids - **down only** / 动态竞价-仅降低 |
| `autoForSales` | Dynamic bids - **up and down** / 动态竞价-提高和降低 |
| `manual` | **Fixed** bids / 固定竞价 |
| `ruleBased` | Rule-based bidding; the rule itself is configured downstream, not here |

Older versions of the product spec labelled both `legacyForSales` and `manual` as
"固定竞价" and omitted `ruleBased`. **The table above is the correct mapping** - picking by
the old labels silently sets the wrong strategy and the call still succeeds.

Any other field in an item is silently dropped. `businessType` is injected server-side; do
not set it.
