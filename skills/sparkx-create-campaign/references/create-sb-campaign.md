# Creating a Sponsored Brands campaign

Same tool as SP - `create_sp_sb_campaign` with `campaignType: "sponsoredBrands"` - and the same
atomic, 20-campaign batch. Everything below is what differs from the SP path in
[`sp-fields.md`](sp-fields.md).

**Fields of the other type are silently ignored downstream, not rejected.** Send only the
fields of the type you are creating; an SP-only field on an SB campaign disappears without an
error, and you will not find out until the campaign behaves differently than you described it.

## Collect these before you build anything

| What | Where |
|---|---|
| `brandEntityId` (**required on Seller profiles**) | `get_entity_metadata(entity='brandEntity')` |
| store page url and page name | `get_entity_metadata(entity='store')` -> `storePageUrl` / `storePageName` |
| `subpages[].asin` for `storeSpotlight` | `get_entity_metadata(entity='pageAsins', filters.pageUrl=<storePageUrl>)`, one page per call |
| `brandLogoAssetID`, `videoAssetIds` | `get_entity_metadata(entity='asset')` -> `amazonAssetId` + `version` |

A brand entity belonging to another shop is rejected. Never invent any of these.

## Campaign-level differences

- **`biddingStrategy` is required and SB accepts only `maximizeImmediateSales`.** There is no
  default; omitting it would store an empty strategy.
- **Targeting**: manual keywords or manual product targets. **Auto targeting does not exist on
  SB.**
- **`targetingType` must be sent explicitly.** On SB it defaults to `target`, which is the
  opposite of the web console's SB page (that preselects keyword). **SB keywords without
  `targetingType` are rejected**, so always send it.
- **`budgetType`** is `daily` or `lifetime`; `lifetime` additionally requires `endDate`.
- **`productLocation`**, if sent at all, must be `soldOnAmazon` - prefer omitting it.
- **`newToBrandPurchase` is not supported.** Omit it or send `0`.
- **Placement adjustments** are a different set from SP: `topAdjustment`, `homeAdjustment`,
  `detailPageAdjustment`, `otherAdjustment`, each an integer percentage 0-900. When
  `bidOptimization` is `true` they do not take effect and are reset to 0, so omit them in that
  case. `bidOptimization` defaults to `true`, or to `false` when any non-zero adjustment is
  sent.
- **SP-only, never send on SB**: `siteRestrictions`, `siteAmazonBusinessAdjustment`,
  `offAmazonBudgetControlStrategy`, and the SP placement field names.
- **Name characters.** SB campaign names must not contain `!` `%` `#` `<` `>` or Arabic
  characters; SB ad group names must not contain Arabic characters (the five symbols are
  allowed there). Neither may contain `❤ ★ ♥ ☆ ™ © €`, and no name of any
  type may contain 4-byte characters such as most emoji - the database cannot store them.
  CJK, full-width and accented Latin characters are fine. Amazon rejects the forbidden ones
  **asynchronously**, so a name that passes here can still kill the campaign later.
- Campaign name max 128 characters, ad group name max 255.

## Ad group: `ads`, not `productAds`

An SB ad group carries a non-empty **`ads`** list; `productAds` is SP-only and is **rejected**
on SB. Every ad needs a `name` (max 255) and a `creative` object. `ads[].state` is `enabled`
(default) or `paused`; `archived` is rejected, and it sets only that ad's state.

Keyword and negative rules that differ from SP:

- `matchType` **`theme` is SB-only** (and `group` is SP-only); a mismatch is rejected. For
  `theme` the `keywordText` must be exactly `KEYWORDS_RELATED_TO_YOUR_LANDING_PAGES` or
  `KEYWORDS_RELATED_TO_YOUR_BRAND`.
- Product targets: an `asin` target accepts only `asinSameAs` (`asinExpandedFrom` is SP-only
  and rejected here) and may omit `type`. The expression refinement
  `asinIsPrimeShippingEligible` is SP-only and rejected. `categoryName` is accepted on SB as an
  alternative form, unlike SP where it is rejected.
- **SB product targeting is only available on US, CA, DE, ES, FR, IT, UK, IN and JP.** On any
  other marketplace the console greys the option out; use keyword targeting there and say why.
- Under manual targeting the ad group's dimension constrains the negatives too: a `keyword` ad
  group must not send `negativeTargets`, a `target` ad group must not send `negativeKeywords`.

## `creativeType` decides which creative fields are required

Required, no default. One of `manualCollection`, `autoCollection`, `storeSpotlight`, `video`,
`brandVideo`.

| creativeType | Required creative fields | Landing page |
|---|---|---|
| `manualCollection` | `asins` (3-10), `brandName` (max 30); `title` optional (max 32, omit for an Amazon-generated one) | `PRODUCT_LIST`, or `STORE` **with `url`** |
| `autoCollection` | `brandName` (max 30), `brandLogoAssetID` | - |
| `storeSpotlight` | `brandName`, `headline` (max 50), `brandLogoAssetID`, `subpages` (**exactly 3**, each with a unique `asin`, a unique `pageTitle` and the page `url`) | `STORE` with `url` |
| `brandVideo` | `asins` (1-3), `brandName`, `headline` (max 50), `brandLogoAssetID`, `videoAssetIds` (**exactly 1**) | `STORE` with `url` |
| `video` | exactly 1 `asin`, `videoAssetIds` (exactly 1) | none |

`headline` is also accepted as an alias for `title` on `manualCollection` and is sent as
`title`.

**The landing page goes at `ads[].landingPage`, never inside `ads[].creative`** - putting it in
the creative is rejected. The server copies `name` / `pageType` / `url` into the downstream
creative for you (`asins` there are ignored). A `manualCollection` landing page with
`pageType='STORE'` **must** include `url`; without it Amazon rejects the ad and its keywords
asynchronously.

**`ads[].creative` accepts only these keys**: `brandName`, `brandLogoAssetID`, `brandLogoCrop`,
`asins`, `asinExclusions`, `title`, `headline`, `subpages`, `videoAssetIds`. Anything else is
rejected, because the downstream would silently drop it. **The downstream does not validate
creative content at all** - this server's checks are the only guard, and Amazon can still
reject the ad asynchronously afterwards.

`brandLogoCrop`, when given, is an object with four required integers: `top`, `left`, `width`,
`height`. Amazon decides the valid ranges; this server does not check them.

**Asset ids** should be `<amazonAssetId>:<version>`. A value with no `:` gets `:version_v1`
appended; a value that already contains `:` is sent unchanged.

## What success means

The same as SP: the campaign exists **locally**, with local ids. The push of ads, keywords,
targets and the creative to Amazon is asynchronous and its result is not returned here. Say the
campaigns were created and that the Amazon sync result is unconfirmed. Do not say they are live
or delivering.
