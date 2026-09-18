---
name: sparkx-create-campaign
description: >-
  Create new Amazon Sponsored Products campaigns in bulk through `create_sp_sb_campaign` -
  campaign, ad groups, promoted products, and either auto targeting, keywords, or product
  targets, plus negatives, placement adjustments and an optional audience. Use when the
  user wants to build / launch / set up a new campaign - 新建广告活动 / 建一个自动广告 /
  开个手动词的活动 / 按这批 ASIN 建活动. Creates the campaign itself; it is NOT for editing
  existing ones (use sparkx-edit-ads), for AI managed groups (use sparkx-create-ai-group), or
  for reading data (use sparkx-query-ads-performance / sparkx-query-entity-metadata).
metadata:
  version: 1.0.1
---

# Create Sponsored Products campaigns

One tool: `create_sp_sb_campaign`. Scope `amazon_sa_campaign_create:write`, separate from the
edit scope - a token that can edit campaigns cannot necessarily create them.

## Sponsored Products only, right now

The tool is named `create_sp_sb_campaign`, but this server currently enables **SP only**.

- **Sponsored Brands is refused at the entry**, with an error naming the types that are
  enabled. **Do not retry the same type.** Tell the user SB creation is not available here
  and point them at the web console.
- **Sponsored Display has no tool at all.** `create_sd_campaign` is not registered, so it
  will not appear in your tool list. Do not go looking for it.
- The enabled set is server configuration and can widen later without a code change. **Trust
  the error over this document**: if a type is refused, it is off; if it succeeds, it is on.

Everything below describes the SP path.

## These writes create real campaigns

A created campaign is live configuration. There is no "draft" state and no undo through this
tool - a mistake has to be cleaned up in `sparkx-edit-ads` or the console, one object at a
time.

**Use `state: "paused"` while testing.** A paused campaign costs nothing and can be enabled
in one edit afterwards. Creating enabled and fixing later means paying for the gap.

**The whole batch is atomic.** If any campaign, ad group or child object fails validation or
the downstream write, **nothing is created** - not even the campaigns that were fine. So a
failure is safe, and the fix is to correct and resend the whole batch, never to "retry the
rest".

## Before you build anything

1. `get_user_authorized_context` -> the `profileId`. **One profile per call**; campaigns for
   two stores are two calls.
2. `get_entity_metadata(entity='asin')` -> the ASINs you will promote, and **their SKUs on a
   Seller profile**. Do not invent SKUs; see "Seller vs Vendor" below.
3. If the user asked for keyword or product-target suggestions, the suggestion entities live
   in `sparkx-query-entity-metadata`. All of them need exactly one `profileId`, but **their
   mandatory filters differ - they are not interchangeable**:

   | Entity | Mandatory filter |
   |---|---|
   | `suggestedKeyword`, `keywordGroup`, `suggestedTarget` | `filters.asin` |
   | `suggestedBid` | `filters.asin`, plus one of two mutually exclusive modes |
   | `amcAudience` | **`filters.campaignType`** (`sponsoredProducts` / `sponsoredBrands`; SD is rejected). It takes **no `asin`** |

4. **Picking an audience is its own step, not part of the suggestion sweep.**
   `amcAudience` also takes `filters.audienceSegmentType`, and **that filter chooses which of
   the two pools you see**. Omitting it does not widen the search - it silently narrows it to
   `SPONSORED_ADS_AMC`, so every Amazon-built audience is invisible and the user never learns
   it existed. **The filter takes one value only** - a two-value array is rejected outright
   (`accepts a single value only, got 2`), so there is no single call that returns both
   pools. When the user names the type, query that pool. When they do not, either ask, or
   **make two separate calls - one with `SPONSORED_ADS_AMC`, one with `BEHAVIOR_DYNAMIC` -
   and merge the two results into one list for them to choose from**, saying which pool each
   came from. Never let the default pick the audience.
5. Decide the targeting type **before** writing anything - the campaign's and the ad group's
   together. They decide which child lists are legal, and sending the wrong ones fails the
   batch.

## Pick the targeting type first - campaign and ad group together

The console shows one 投放类型 / Targeting radio on the campaign, but the request carries a
second `targetingType` on each ad group, and the two must agree.

A campaign is `targetingType: "auto"` or `"manual"`, and an ad group is
`targetingType: "keyword"` or `"target"` (default `"target"`). Only three combinations exist:

| What the user wants | campaign | ad group | Child lists you may send |
|---|---|---|---|
| let Amazon match automatically | `auto` | `target` (required) | `targetBid` **and** `productAds`; negatives of **both** kinds allowed |
| bid on search terms | `manual` | `keyword` | `keywords` + `productAds`; **`negativeKeywords` only** |
| target ASINs or categories | `manual` | `target` | `targets` + `productAds`; **`negativeTargets` only** |

Two things fall out of this table that are easy to get wrong:

- **An auto campaign's ad group must be `target`**, not `auto`. Sending
  `targetingType: "auto"` on the ad group is rejected.
- **Under manual targeting the ad group's dimension also constrains the negatives.** A
  `keyword` ad group must not carry `negativeTargets`, and a `target` ad group must not carry
  `negativeKeywords`. Auto campaigns accept both kinds. This mirrors the console, where the
  two panels are mutually exclusive.

The non-selected lists must be **empty**, not omitted-and-hoped-for: sending `keywords` on an
auto campaign fails the batch.

## The seven rules that will bite you

**1. `biddingStrategy` is required and has no default.** SP accepts `legacyForSales`,
`autoForSales` or `manual`. Omitting it stores an empty strategy, so pick one explicitly and
say which one you picked.

**2. An auto campaign must cover all four target groups.** `targetBid` needs `closeMatch`,
`looseMatch`, `substitutes` **and** `complements`, each at most once. **To disable one, send a
negative bid - do not omit it.** An omitted group is a validation failure, not a default.

**3. Keywords are unique per (`keywordText`, `matchType`) inside an ad group.** A repeat is
**rejected**, not silently de-duplicated - the downstream would otherwise create two rows with
different bids. Deduplicate before sending.

**4. On a Seller profile every promoted product needs `sku`, and the pair is verified.** See
"Seller vs Vendor".

**5. Bids must not exceed the campaign budget.** Every `defaultBid` / `targetBid` / keyword
bid / target bid is checked against it. A negative auto-targeting bid (rule 2) is exempt.

**6. `siteRestrictions` makes several other fields illegal.** Its only value is
`AMAZON_BUSINESS`, it exists only on US/CA/MX/UK/DE/FR/IT/ES/IN/JP, and when you set it you
must omit `siteAmazonBusinessAdjustment`, **every `audience*` field**, and
`offAmazonBudgetControlStrategy`. Amazon rejects those combinations and the downstream would
drop them silently. Note the tool does **not** fill in the usual
`offAmazonBudgetControlStrategy` default when `siteRestrictions` is set, precisely so the
request matches what actually takes effect.

**7. On JP profiles every bid and budget must be a whole number.** No decimals anywhere.

## Seller vs Vendor

| | Seller | Vendor |
|---|---|---|
| Product ad identity | **ASIN + SKU** | ASIN alone |
| `sku` on `productAds` | **required** | not needed |
| Verification | each `(asin, sku)` pair is checked against the shop's catalog | — |

On a Seller profile a pair that is not found is **rejected**. Read SKUs from
`get_entity_metadata(entity='asin')` - never construct one.

⚠️ **If the catalog lookup itself fails, the call is rejected too** (nothing is created). That
error means *retry*, not *change the ASIN*. Resending a different ASIN because a lookup
failed is how you end up advertising the wrong product.

## Audience targeting is optional, and unverified

**Three fields, one atomic group.** Configuring an audience means sending `audienceId`,
`audienceSegmentType` **and** `audienceBidPercentage` together, or none of them.
`audienceBidPercentage` is an integer 0-900 **sent as a string**; `audienceSegmentType` is
`SPONSORED_ADS_AMC` or `BEHAVIOR_DYNAMIC`.

**Only two of the three are enforced.** The tool rejects an `audienceId` without an
`audienceBidPercentage`, but **`audienceSegmentType` is optional in the validator** - leave it
out and the request passes, then the downstream applies its own default,
`SPONSORED_ADS_AMC`. Bind an Amazon-built audience without saying so and you get a success
response for targeting that never runs. (The edit path, `batch_update_ads` +
`updateAudienceBid`, does require it. Creation is the looser of the two - do not take that as
permission to omit it.)

⚠️ **Nothing validates `audienceId`** - not this tool, not the downstream. An id that is
invented, or taken from the other segment pool, is **accepted, stored locally, and never
applies on Amazon**. You will see a successful response for a campaign whose audience
targeting silently does nothing.

So copy **`audienceId` and `audienceSegmentType` from one and the same**
`get_entity_metadata(entity='amcAudience')` row - that entity echoes the type on every row
exactly so the pair travels together. **Never substitute that query's default type for the
campaign's real one**: `SPONSORED_ADS_AMC` is the default *of the lookup*, not a fact about
the audience you picked.

### ⚠️ `portfolioId` wants the **Amazon** portfolio id, and it is verified

This is the one field where the usual rule inverts. Everywhere else a write takes the
internal id; here the tool checks the value against the shop's portfolios and requires
**`amazonPortfolioId`** - the long one from `get_entity_metadata(entity='portfolio')`, not the
much shorter same-named `portfolioId` in that response.

Sending the internal id fails with `portfolioId must be an Amazon portfolio ID belonging to
profile ...`, which is a good error but an easy one to earn: the two fields differ only by
prefix. A portfolio belonging to another shop is rejected the same way.

**Convert the type as you copy it.** `amazonPortfolioId` comes back from
`get_entity_metadata` as a **string**; this request field is a **number**. Parse the digits
and send `"portfolioId": 123456789012345`, not `"123456789012345"`.

## The console can do three things this tool cannot

The user may be looking at the creation page while talking to you. These parts of it have no
equivalent here - say so and point at the console rather than approximating:

1. **从词库添加 / Add from keyword list.** The negatives panels have an "Enter list" tab and
   an "Add from keyword list" tab. Only the first has an equivalent: send the words in
   `negativeKeywords`. **Keyword lists (词库) are not supported by MCP at all** - you cannot
   reference one, and you cannot enumerate its contents to paste them in.
2. **自动定向 → 设置默认出价 / Automatic targeting → Set default bid.** The console lets an
   auto campaign run on one default bid instead of per-group bids. This tool always requires
   all four groups in `targetBid`; there is no "just use the default" mode. If the user wants
   a single bid, send the same value four times and tell them that is what you did.
3. **Adding ad groups to an existing campaign.** Creation only. Point them at the console.

Terminology for everything the tool *does* support is mapped to the console's own labels in
[`references/sp-fields.md`](references/sp-fields.md) - use those labels when you talk to the
user.

## Batch limits

| Limit | Value |
|---|---|
| campaigns per call | **20** |
| ad groups per campaign | **50** |
| items in any one child list | **1000** |
| child items across the whole call | **5000** |

Split larger workloads into several calls - but remember each call is its own atomic unit, so
report per call which ones landed.

## Workflow

```
1. get_user_authorized_context           -> profileId (one per call)
2. get_entity_metadata(entity='asin')    -> ASINs, and SKUs on a Seller profile
3. (optional) suggestion entities        -> keywords / targets / bids / audiences
4. Decide both targetingTypes (campaign + ad group). Ambiguous -> ASK, do not pick.
5. Build the batch. Check the four limits before sending.
6. Show the user what will be created and get a yes.
7. create_sp_sb_campaign
8. get_entity_metadata(entity='campaign') -> confirm it exists with the intended settings
```

Step 6 is not optional. This is a write that starts spending.

Step 8 matters more than usual here: success means the objects were created **locally**, and
the response carries no per-object detail beyond the ids.

## Confirm before creating

Show, in the user's own terms: the campaign name, budget, start date, targeting type,
bidding strategy, how many ad groups and what is in them, the ASINs, and whether it will be
enabled or paused. Then get a yes.

If the user has explicitly waived confirmation, announce the same summary and proceed without
waiting - see the waiver rules in `sparkx-edit-ads`. A waiver for editing does not authorize
creating: it has to cover creation.

## After the write

**The response gives internal ids, not Amazon ids.** Creation completes locally first and the
Amazon id appears later, after sync. So:

- Report the campaign **by name**.
- If the user asks for an id, give the internal one and say plainly that the Amazon id is not
  available until the campaign syncs. **Do not poll for it and do not invent one.**
- Do not claim the campaign is live on Amazon. It exists in the platform; delivery starts once
  it syncs and, if you created it paused, once it is enabled.

Full convention: [`references/platform-notes.md`](references/platform-notes.md) -> "Naming
things in your answer".

## Do not guess - ask

- **"建个自动广告"** - auto targeting, or a manual campaign they will manage themselves? These
  are different `targetingType`s and cannot be converted afterwards through this tool.
- **budget** - daily budget. If the user names a monthly figure, ask rather than dividing.
- **"用这些词"** - as keywords (they bid on search terms) or as product targets? Different
  child list, different ad group dimension.
- **"先别花钱"** - create `paused`. Say that you did.
- Anything the tool cannot do - SB, SD, adding ad groups to an **existing** campaign, SD
  creatives - say so and point at the console. Do not approximate it with something else.

## Reference files

| File | Read it when |
|---|---|
| [`references/sp-fields.md`](references/sp-fields.md) | Building any request - every field, its type, and what is required where |
| [`references/platform-notes.md`](references/platform-notes.md) | Auth, envelope, errors, and how to name things in your answer |

Sibling skills you will need installed: `sparkx-query-entity-metadata` (ASINs, SKUs,
portfolios, suggestions), `sparkx-edit-ads` (anything after creation).
