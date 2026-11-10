# Adding ad groups to an existing SB campaign

`create_sb_ad_group`. Registered only when SB is enabled on this server. Each ad group has
**exactly one ad** - its creative and landing page - plus keyword **or** product targeting.

## Before anything else

- **`campaignId` is the INTERNAL id** from `get_entity_metadata(entity='campaign')`, not
  `amazonCampaignId`. This is the single most common failure.
- Only `sponsoredBrands` campaigns are accepted. Another type, a campaign that does not belong
  to `profileId`, or an archived campaign is rejected.
- At most **10 ad groups per call**, all under one `profileId`. At most 1000 items in any one
  child list and 5000 child items across the call.

## Not atomic - plan the recovery before you call

Ad groups are created **one at a time in request order**. If one fails, the ones already
created stay. The result lists every item with `success` / `adGroupId` / `message`, and the
call reports `partial_success`.

- **Retry only the failed items**, and before retrying call
  `get_entity_metadata(entity='adGroup')` for that campaign to check whether the ad group
  already exists.
- **If the response says the outcome is unconfirmed** (timeout or downstream error), do not
  retry blindly - check the ad group list first.
- **Fail Closed**: if the campaign or the existing ad group names cannot be verified, the
  **whole** batch is rejected and nothing is created. That is a clean state to retry from.
- A concurrent request creating the same ad group name in the same campaign is rejected until
  the first one finishes, and that rejected request creates nothing.

Creation needs no confirmation token.

## Names

`name` is required (max 256 after trimming) and is **never auto-generated**; the one `ads`
entry also needs its own `name` (max 255), likewise never auto-generated. Neither may contain
control characters (NUL, tab, CR, LF, U+007F-U+009F) or the separators U+2028 / U+2029. The ad
group name must additionally avoid Arabic characters, `❤ ★ ♥ ☆ ™ © €`
(Amazon rejects them asynchronously) and 4-byte characters such as most emoji (the database
cannot store them).

**The ad group name must be unique within the campaign, case-sensitively. Archived ad groups do
not count here** - which is the opposite of the SD tool, so do not carry the rule across.
Repeating a name inside one request for the same campaign is also rejected.

## `creativeType`: four values, not five

Required, no default: `manualCollection`, `storeSpotlight`, `video`, `brandVideo`.
**`autoCollection` and `productCollection` are not supported by this tool** - if the user wants
`autoCollection`, it is available when creating a new campaign with `create_sp_sb_campaign`,
not here.

| creativeType | Required creative fields | Landing page |
|---|---|---|
| `manualCollection` | `asins` (3-10), `brandName` (max 30); `title` optional (max 32, `headline` accepted as an alias) | `PRODUCT_LIST`, or `STORE` with `url` |
| `storeSpotlight` | `brandName` (max 30), `headline` (max 50), `brandLogoAssetID`, `subpages` (exactly 3) | `STORE` with `url` |
| `video` | exactly 1 `asin`, `videoAssetIds` (exactly 1) | none; no brandName / logo / headline |
| `brandVideo` | `asins` (1-3), `brandName` (max 30), `headline` (max 50), `brandLogoAssetID`, `videoAssetIds` (exactly 1) | `STORE` with `url` |

**`storeSpotlight` subpages are verified against the real store pages.** Each of the three needs
`asin`, `pageTitle` and `url`; `asin` and `pageTitle` must each be unique across the three; and
**each asin is checked against the products of its own subpage url**. If an asin is not on that
page, or that page's products cannot be read, **the whole batch is rejected**. So read the
ASINs with `get_entity_metadata(entity='pageAsins', filters.pageUrl=<that page's url>)` - one
call per subpage - rather than reusing a list from elsewhere.

`asinExclusions` is rejected here (it belongs to `autoCollection`).

**Where the values come from** (each needs a single authorized `profileId`):

| Field | Source |
|---|---|
| `brandLogoAssetID`, `videoAssetIds` | `entity='asset'` -> `amazonAssetId`; `IMAGE` for the logo, `VIDEO` for videos. Rows without `amazonAssetId` are unusable |
| landing page `url`, subpage `url` / `pageTitle` | `entity='store'` -> `storePageUrl` / `storePageName` |
| `subpages[].asin` | `entity='pageAsins'` with `filters.pageUrl` |

Format rules the tool enforces: text fields (`brandName`, `title`, `headline`,
`brandLogoAssetID`) must be strings; `asins` entries must be valid and distinct; asset ids must
look like `amzn1.assetlibrary.asset1.<32 hex>` with an optional `:version_vN` (one without `:`
gets `:version_v1` appended); store urls must look like
`https://www.amazon.com/stores/page/<id>`.

**Landing page input**: pass it as `ads[0].landingPage` with `pageType` and `url`, the same
shape as `create_sp_sb_campaign`. Do not also put a `landingPage` inside `creative`; the server
copies it in when it builds the downstream request.

## Targeting: pick one mode

- `targetingType: 'keyword'` -> `keywords`, `negativeKeywords` allowed, **no `targets`**.
- `targetingType: 'target'` -> `targets`, `negativeTargets` allowed, **no `keywords`**.

Omitting `targetingType` infers it: only keywords -> `keyword`, only targets -> `target`.
Sending both, or neither, is rejected.

- `keywords[].matchType`: `exact` / `phrase` / `broad` / `theme`. **`group` is not supported
  here and `keywordGroupText` is rejected.** For `theme` the `keywordText` must be one of the
  fixed theme texts. `keywordText` is trimmed, and a `(keywordText, matchType)` pair must not
  repeat. Duplicates in any list are rejected, never silently dropped.
- `negativeKeywords[].state`: **SB negative keywords cannot be paused** - omit `state` or send
  `enabled`.
- `negativeTargets`: a brand entry needs **both** `brand` (the id) and `name` (the display
  name), each at most 255 characters.
- **Product targets are only available on US, CA, DE, ES, FR, IT, UK, IN and JP profiles.**
  Elsewhere use keyword targeting and tell the user why.
- Each target specifies exactly **one** of `expression` (with `resolvedExpression`) or `asin`.
  An `asin` target defaults to `asinSameAs` and only `asinSameAs` is accepted
  (`asinExpandedFrom` is SP-only). The refinement `asinIsPrimeShippingEligible` is likewise
  SP-only and rejected. **`categoryName` is not supported**: use `expression` with
  `resolvedExpression`, each type at most once per target, and `resolvedExpression` listing the
  same types in the same order. Category ids come from
  `get_entity_metadata(entity='sdCategory', filters.keyword=<name>, filters.targetableOnly=true)`.

## Bids and state

Every bid (keywords and targets) must be **greater than 0 and not exceed the campaign budget**;
the marketplace minimum is enforced downstream. On JP marketplace profiles all bids must be
integers.

Ad group `state` and `ads[0].state` default to `enabled`; `paused` is allowed, `archived` is
rejected. Use `paused` when testing to avoid real spend.

**Optional means omitted or null.** An empty or blank string is **not** treated as omitted for
enum and id fields (`state`, `targetingType`, `type`, `asin`, `brand`, ...) and is rejected.

## What success means

A successful item means the ad group was created **locally** and its local `adGroupId`
returned. The Amazon sync runs afterwards and its outcome is not returned here. Say the ad
groups were created and the sync result is unconfirmed; do not say they are live or delivering.
