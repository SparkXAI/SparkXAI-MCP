# Adding ad groups to an existing SD campaign

`create_sd_ad_group`. Registered only when SD is enabled on this server. Each ad group carries
its product ads, its manual targets and an optional creative.

## Before anything else

- **`campaignId` is the INTERNAL id** from `get_entity_metadata(entity='campaign')`, not
  `amazonCampaignId`.
- Only `sponsoredDisplay` campaigns are accepted. Another type, a campaign that does not belong
  to `profileId`, or an archived campaign is rejected.
- At most **10 ad groups per call**, all under one `profileId`.

## Three things this tool does that the others do not

**1. SD ad groups cannot be created paused.** The downstream always creates them `enabled`.
There is no way to stage one safely here - so **do not create SD ad groups for testing against
a real account**, and tell the user that the ad group will be live under its campaign as soon
as it syncs. If the campaign itself is paused, nothing delivers; that is the only brake.

**2. No ad group id comes back.** A successful item has `adGroupId: null`, because sd-api does
not return one. Look it up by name with
`get_entity_metadata(entity='adGroup', filters.campaignId=<campaignId>)`. Report the ad group
by **name**; do not claim an id you did not receive.

**3. Archived ad groups count for the name check.** The name must be unique within the campaign
including archived ones, case-sensitively - the opposite of `create_sb_ad_group`. Repeating a
name inside one request for the same campaign is also rejected. The check relies on the ad
group list, with the downstream rejecting a duplicate as a last resort.

## Not atomic across ad groups, atomic within one

Ad groups are created one at a time in request order and the ones already created are **not**
rolled back. But each single ad group - with its product ads, targets and creative - is written
in **one downstream transaction**, so a *rejected* item leaves nothing behind. An
**unconfirmed** item (timeout or downstream error) may still have been created.

- On `partial_success`, retry only the failed items, after checking that campaign's ad group
  list.
- On an unconfirmed outcome, never retry blindly - check the list first and retry only what is
  genuinely missing.
- **Fail Closed**: if the campaign or the existing ad group names cannot be verified, the whole
  batch is rejected and nothing is created.
- A concurrent request creating the same name in the same campaign is rejected until the first
  one finishes, and creates nothing.

Creation needs no confirmation token.

## What is an input and what is inherited

Required: `campaignId`, `adGroupName`, a non-empty `productAds`, a non-empty `targets`.

**Inherited from the campaign, not inputs**: `tactic`, `state`, `defaultBid`, `costType`. The
tactic in particular decides the shape of every target expression below, and you cannot change
it here - read it off the campaign first.

`bidOptimization` is optional and defaults from the campaign `costType` (`vcpm` -> `reach`,
otherwise `clicks`). If given it must agree: `cpc` campaigns accept `clicks` or `conversions`;
`vcpm` campaigns accept `reach`.

`adGroupName` is at most 255 characters after trimming, with no control characters (NUL, tab,
CR, LF), no `!` `%` `#` `<` `>`, no Arabic characters and none of
`❤ ★ ♥ ☆ ™ © €` (Amazon rejects those asynchronously), and no 4-byte
characters such as most emoji (the database cannot store them).

**Optional means omitted or null.** An empty or blank string is **not** treated as omitted for
enum and id fields (`bidOptimization`, `state`, `expressionType`, asset ids and versions) and is
rejected.

## Product ads

`asin` plus `sku`. Every `asin` must be a real ASIN and is stored upper-cased. `state` may be
omitted or `enabled` - the only value sd-api supports.

- **Seller** profiles: `sku` is required on every product, each `(asin, sku)` is verified
  against the shop's catalog, and a product that is `INELIGIBLE` for Sponsored Display is
  rejected.
- **Vendor** profiles: ASIN only.
- Duplicate products (same `asin` and `sku`) within one ad group are rejected.

## Targets

Manual only: `expressionType` may be omitted or `manual`; `state` may be omitted or `enabled`.
Both `expression` and `resolvedExpression` are **required JSON array strings** - for example
`'[{"type":"asinSameAs","value":"B09YYYYYYY"}]'` - with `resolvedExpression` carrying the
display values.

The structure must match the **campaign's** tactic and is validated before anything is created:

- **`T00020`**: bare clauses (`asinSameAs` / `asinCategorySameAs` / `similarProduct`). No
  `views` / `purchases` / `audience` wrappers, no top-level `lookback`.
- **`T00030`**: every element must be a `views` / `purchases` / `audience` wrapper whose `value`
  holds the clauses. Bare clauses such as `asinSameAs` are rejected. `relatedProduct` is only
  allowed inside `purchases` and `similarProduct` only inside `views`, as in the console.

Category ids come from `get_entity_metadata(entity='sdCategory', filters.keyword=<name>,
filters.targetableOnly=true)`; never invent them. Audience ids for `T00030` come from
either `entity='sdAudience'` (Amazon's SD catalog) or
`entity='amcAudience'` with `filters.campaignType='sponsoredDisplay'` (AMC audiences) - two
separate pools, both valid here, **never mixed or inferred from one another**. **The pool is
not validated on this path**, so an id from the wrong pool passes and fails at Amazon sync
instead; copy it from the query result and check the sync status afterwards.

**Every target needs a `bid`**, within the marketplace bid range for the campaign's `costType`
and **strictly less than half** the campaign daily budget. On JP marketplace profiles all bids
must be integers. Duplicate targets (same expression) within one ad group are rejected.

## The optional creative

Field `creative`, at most one per ad group. **Omit it entirely to send none - an empty object is
rejected.** Three independent modules, at least one required:

- **headline**: max 50 characters, no punctuation or special characters, only the first letter
  of each word uppercase.
- **brand logo**: `brandLogoAssetId` + `brandLogoCroppingCoordinates`.
- **custom image**: `rectCustomImageAssetId` + `rectCustomImageCroppingCoordinates` +
  `squareCustomImageCroppingCoordinates`; the square asset defaults to the rect asset.

Asset ids are the `amazonAssetId` from `get_entity_metadata(entity='asset')` (single
`profileId`), **not** the local id, and must look like `amzn1.assetlibrary.asset1.<32 hex>`.
Put the row's `version` (such as `version_v1`) into the matching `*AssetVersion` field,
otherwise `version_v1` is used. **An `*AssetVersion` without its asset id is rejected** - for
instance `squareCustomImageAssetVersion` needs `squareCustomImageAssetId`. Cropping coordinates
are JSON strings.

**Image size, file size and format cannot be verified by this tool.** For reference, the console
requires a logo of at least 600x100 and under 1MB (PNG/JPEG), and a custom image of at least
1200x628 and under 5MB (PNG/JPEG/GIF), cropped to 1200x628 and 628x628. A file that violates
these passes here and fails at Amazon.

The creative is submitted **in the same request** as the ad group and stored in the same
transaction, so an ad group is never created locally without its creative. It then syncs to
Amazon asynchronously and is **moderated, which can take about 72 hours**. A successful result
means it was submitted - do not tell the user the creative is live.

## Common errors

| Error | Meaning |
|---|---|
| Duplicate name | An ad group with that name already exists in the campaign, **archived ones included** |
| Campaign not found or does not belong to profile | Check `campaignId` and `profileId` via `get_entity_metadata(entity='campaign')` |
