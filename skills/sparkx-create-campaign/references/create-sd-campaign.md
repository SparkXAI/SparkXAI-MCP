# Creating a Sponsored Display campaign

`create_sd_campaign`. Its own tool, its own request shape, and one behaviour that no other
create tool has: **the creative is written after the campaign commits and is not rolled back
with it**.

The tool is registered only when SD is enabled on this server. If it is not in your tool list,
SD creation is unavailable here - say so and point at the console.

## Atomicity, precisely

- Campaigns, ad groups, product ads and targets of one call go into **one downstream
  transaction**. If any campaign fails - a duplicate name, including two campaigns with the
  same name inside one call - **nothing is created** and the whole call can be retried after
  fixing the cause.
- **Creatives are attached in a second step after that commit.** A creative failure does
  **not** fail the call: the campaigns and ad groups already exist, the response is still
  `success`, and it reports `creativesRequested` / `creativesCreated` plus a `creativeFailures`
  list of `campaignName`, `adGroupName`, `adGroupId`, `reason`.
- **On creative failure there is nothing to retry here.** No MCP tool attaches a creative to
  an ad group that already exists - `create_sd_ad_group` only creates a *new* ad group, with
  its creative, so using it to "fix" a failed creative would add a duplicate ad group. And
  re-running the batch would create duplicate campaigns. So:
  **report `creativeFailures` as it came back** - campaign name, ad group name, ad group id and
  reason for each - say that the campaigns and ad groups were created successfully and that
  only the creatives are missing, and tell the user to add them on the ad group's creative tab
  in the web console. Do not create anything to work around it.

Because one failing campaign rolls back the entire call, smaller batches waste less work on a
retry. Limits are the same as SP/SB: 20 campaigns, 50 ad groups per campaign, 1000 items in any
one child list, 5000 child items in total.

## Campaign fields

Required: `campaignName`, `tactic`, `budget`, `budgetType`, `startDate`, a non-empty `adGroups`.

- **`budgetType` must be `daily`.** Nothing else is accepted.
- **`tactic` is `T00020` (product / category targeting) or `T00030` (audience targeting).** It
  decides the entire shape of every target expression below, and it is inherited by ad groups
  added later - so get it right before creating, and ask the user if it is not obvious.
- **`costType`** is `cpc` or `vcpm` and must agree with the ad groups' `bidOptimization`:
  `reach` -> `vcpm`, `clicks` / `conversions` -> `cpc`. **Omit it** and the tool derives it,
  matching the web console, which has no `costType` control. It is only needed when the ad
  groups of one campaign disagree - which is itself usually a mistake worth questioning.
- `portfolioId` is optional, must be a **positive Amazon** portfolio id belonging to the
  profile (`amazonPortfolioId` from `get_entity_metadata(entity='portfolio')`), and is verified
  before anything is created. Omit it for no portfolio: `0` and negatives are rejected.
- `campaignName` max 128, `adGroupName` max 255. Neither may contain `!` `%` `#` `<` `>`,
  Arabic characters, `❤ ★ ♥ ☆ ™ © €` (Amazon rejects them asynchronously)
  or 4-byte characters such as most emoji (the database cannot store them). CJK, full-width and
  accented Latin characters are fine.
- Dates are `yyyyMMdd`. `startDate` must not be earlier than the shop's current date **in the
  shop's own timezone**; `endDate` must be on or after `startDate`.

## State: only the campaign can be paused

| Object | Allowed `state` |
|---|---|
| campaign | `enabled` (default) or `paused`; `archived` rejected |
| ad group, product ad, target | **`enabled` only**, or omit it |

So "create it paused so it does not spend" means `paused` **on the campaign**, and only there.
A paused campaign does not deliver, which is what the user asked for - but say plainly that the
ad groups underneath are enabled.

## Ad groups

Each requires `adGroupName`, `defaultBid`, `bidOptimization` (`clicks` / `conversions` /
`reach`), a non-empty `productAds` and a non-empty `targets`.

**`defaultBid` must be less than half the campaign budget, and so must every target bid.** Not
"at most half" - strictly less. Marketplace bid and budget ranges are checked per marketplace
(budget by seller/vendor, bid by `cpc`/`vcpm`); on JP profiles budget and bids must be
integers.

**Product ads.** Every `asin` must be a real ASIN (`B` + 9 alphanumerics, or 9 digits + X/digit)
- placeholders are rejected - and the same ASIN/SKU pair may appear only once per ad group.
On **Seller** profiles every product ad needs a `sku`, each `(asin, sku)` must exist in the
shop's catalog, and products whose Sponsored Display eligibility is `INELIGIBLE` are rejected
(the console hides them). Pick valid ones with `get_entity_metadata(entity='asin')`. **Vendor**
profiles identify products by ASIN alone: no `sku`, no catalog or eligibility check.

## Targets: the expression shape follows the tactic

Each target needs `expression` (a non-empty **JSON array string**) and `expressionType`, which
may only be `manual`. `resolvedExpression`, when set, must also be a non-empty JSON array
string. **Every target needs a `bid`**, less than half the campaign budget. The same
`expressionType` + `expression` may appear only once per ad group.

**`T00020` - bare clauses.** The `views` / `purchases` / `audience` wrappers are rejected, and
so is a top-level `lookback`.

```json
[{"type":"asinSameAs","value":"B0XXXXXXXX"}]
[{"type":"asinCategorySameAs","value":"<categoryId>"}]
[{"type":"similarProduct"}]
```

A category clause may be followed by `asinBrandSameAs` / `asinReviewRatingBetween` (`"3-5"`) /
`asinPriceBetween` (`"10-50"`) refinements, with no lookback. `similarProduct` takes no
lookback either - adding one is rejected by Amazon.

**`T00030` - every element must be a wrapper.** Bare clauses such as `asinSameAs` are rejected.
A wrapper's `value` must be a non-empty array of typed clauses.

```json
[{"type":"views","value":[{"type":"exactProduct"},{"type":"lookback","value":"30"}]}]
[{"type":"views","value":[{"type":"similarProduct"},{"type":"lookback","value":"30"}]}]
[{"type":"audience","value":[{"type":"audienceSameAs","value":"<audienceId>"}]}]
```

- `views` holds `exactProduct` / `similarProduct` / `asinCategorySameAs`;
  `purchases` holds `exactProduct` / `relatedProduct` / `asinCategorySameAs`. `relatedProduct`
  inside `views` and `similarProduct` inside `purchases` are rejected - this mirrors the
  console.
- **A `views` or `purchases` wrapper must contain a `lookback` clause**; a missing one is
  rejected. For `views` the value must be `7` / `14` / `30` / `60` / `90` days - `180` and
  `365` are rejected by Amazon.
- **`audienceSameAs` values have two valid sources**, and they are different pools:
  `get_entity_metadata(entity='sdAudience')` (Amazon's SD audience catalog) and
  `get_entity_metadata(entity='amcAudience', filters.campaignType='sponsoredDisplay')` (the AMC
  audience tab of the SD targeting page). Either can supply the id. **Never mix them or infer
  one from the other** - an id is valid only in the pool it came from, and the pools do not
  overlap.
- ⚠️ **Nothing here checks which pool the id belongs to.** Unlike SP/SB campaign-level audience
  binding, which is verified against the pool before anything is created, the SD path validates
  only the *shape* of the target expression. A well-formed id from the wrong pool - or a stale
  one - passes every check here and fails later, during the asynchronous Amazon sync. So
  **read the id straight from the query result and check the sync status afterwards**; a
  successful create proves nothing about the audience.

Category ids come from `get_entity_metadata(entity='sdCategory', filters.keyword=<name>,
filters.targetableOnly=true)`. Never invent ids.

## The optional creative

At most one `creative` object per ad group; all three modules are optional and may all be
omitted. Asset fields take `amazonAssetId` from `get_entity_metadata(entity='asset')`, **not**
the local id. An omitted asset version defaults to `version_v1`, which is what the console
sends; the asset row carries its own `version` if you want to be explicit.

- **Headline**: at most 50 characters, **no punctuation or symbols**, and each word may be
  capitalised only on its first letter - no all-caps, no mid-word capitals. This is checked up
  front.
- **Brand logo**: needs **both** `brandLogoAssetId` and `brandLogoCroppingCoordinates`. A logo
  without cropping is silently dropped downstream.
- **Custom image**: needs **all of** `rectCustomImageAssetId`,
  `rectCustomImageCroppingCoordinates` and `squareCustomImageCroppingCoordinates`. The square
  asset (and its version) defaults to the rect one, as in the console where both crops share
  one image.
- Any `*CroppingCoordinates` field must be a **JSON string**.

A successful creative write means it was stored locally. Pushing it to Amazon is asynchronous
and is not confirmed here.

## Common errors

| Error | Meaning |
|---|---|
| `campaign name already exists in this shop` (sd-api `124001`) | The name exists for the profile, or repeats within your call. **Nothing was created** |
| System error (`125000`) | Malformed request, e.g. missing tenant context |
