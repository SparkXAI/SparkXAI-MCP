# Entities that exist for SB and SD creation

Five entities feed the Sponsored Brands and Sponsored Display creation tools. They return
values you cannot construct yourself - Amazon-side ids that the create tools validate against
Amazon. None of them describes what you already run; for that use the ordinary `campaign` /
`adGroup` / `target` entities.

All five require **exactly one authorized `profileId`**. Four of them ignore pagination
entirely; `asset` is the exception and pages normally.

| Entity | Feeds | Pagination | Mandatory filter |
|---|---|---|---|
| `brandEntity` | SB campaign `brandEntityId` | none | - |
| `store` | SB creative landing page | none | - |
| `pageAsins` | SB `storeSpotlight` subpage ASINs | none | **`pageUrl`** |
| `asset` | SB / SD creative images and videos | normal | - |
| `sdAudience` | SD audience targeting (tactic `T00030`) | none | - |

## They chain, and two of them only work in sequence

```
store -> storePageUrl -> pageAsins -> subpages[].asin      (storeSpotlight)
store -> storePageUrl -> landingPage.url                   (collection / video)
brandEntity -> brandEntityId                               (SB on a Seller profile)
asset -> amazonAssetId (+ version)                         (brandLogoAssetID, videoAssetIds)
sdAudience -> audienceId -> audienceSameAs expression      (SD T00030)
```

`store` does **not** return ASINs. `pageAsins` is the only source of them, and it refuses to
run without `filters.pageUrl`, which must come from a `store` row. Query one page per call and
repeat for each subpage you need.

## `brandEntity`

Lists the brands registered to the profile. Three fields per row: `brandEntityId`,
`brandRegistryName`, `brandId`.

`brandEntityId` is required when creating an SB campaign on a Seller profile, and this is its
only source. Match the brand by `brandRegistryName` when the user names one; if several match
or none does, ask rather than picking.

## `store`

Lists the profile's brand stores and their pages, **one row per page**, not per store:
`storeId`, `storeName`, `brandEntityId`, `storePageId`, `storePageName`, `storePageUrl`.
A store with five pages is five rows that share `storeId` and `storeName`.

- `storePageUrl` is the landing-page url for an SB creative whose
  `landingPage.pageType` is `STORE`.
- The downstream asks Amazon for at most **30 stores**. That cap is fixed here and there is
  no way to page past it, so a profile with more stores than that will be missing some. Say
  so if the store the user named is not in the list, instead of concluding it does not exist.
- Every response carries the hint `subpage ASINs are not included here` - that is the normal
  response, not a warning about this particular call.

## `pageAsins`

Returns the products contained in one brand-store page: `asin`, plus the `pageUrl` echoed back
so you can tell rows apart when assembling `subpages[]` from several calls.

- **`filters.pageUrl` is required and single-valued.** Omitting it fails with a message
  pointing you at `entity='store'`; sending two fails with `query one store page per call`.
- **An empty result is ambiguous and the tool says so in `meta.hint`.** The downstream
  swallows Amazon call failures and returns an empty list, which looks exactly like a page
  with no products. Never report "that page is empty" from a bare empty result - re-check that
  the `pageUrl` came from a `store` row, and say the answer is unavailable if it still returns
  nothing.

## `asset`

Lists the creative assets uploaded for the profile. One row per **version** of an asset -
the same `amazonAssetId` appears once per version - carrying `amazonAssetId`, `version`,
`assetName`, `assetType`, `assetSubTypeList`, `status`, `width`, `height`, `fileType`,
`uploadStatus`.

- **`amazonAssetId` is the value Amazon accepts.** How you combine it with `version` depends
  on the ad type: SB creatives take `<amazonAssetId>:<version>` as one string; SD creatives
  take the asset id and the version as two separate fields.
- **A row with no `amazonAssetId` is not usable yet** - not synced to Amazon, or the upload
  failed. Such rows are returned rather than filtered out, so that "the asset exists but is
  unusable" stays distinguishable from "there is no such asset". `uploadStatus` separates the
  two: `0` / `1` / `3` registered or uploaded, `2` / `4` failed.
- `assetType` is `IMAGE` or `VIDEO`. Video creative types need a `VIDEO` asset; a brand logo
  needs an `IMAGE` asset, normally one whose `assetSubTypeList` contains `LOGO`.
- **This entity pages normally** - `page`, `pageSize`, `total` and `hasNextPage` all behave as
  they do for campaigns, because the downstream is a database query rather than a live Amazon
  call.
- Optional filters: `keyword` (asset name) and `status` (`ACTIVE` / `ARCHIVED`) take a single
  value each; `assetSubType` and `fileType` accept several.

## `sdAudience`

Lists the audiences Sponsored Display can target - **one of two sources** for the audience ids
used by `create_sd_campaign` / `create_sd_ad_group` with tactic `T00030`. Fields:
`audienceId`, `audienceName`, `category`, `adType`, `forecasts`.

**The two pools are separate but both valid for SD.** `sdAudience` serves the Amazon SD
audience catalog; `amcAudience` with `filters.campaignType='sponsoredDisplay'` serves the AMC
audience tab of the same SD targeting page. Either can supply an `audienceSameAs` value.
**An id from one is not valid in the other, and you cannot tell which pool an id came from by
looking at it** - so carry the id and its source together, and never guess the pool.

⚠️ **The SD write path does not check the pool.** SP/SB campaign-level audience binding is
verified before anything is created; the SD target path validates only the expression's shape.
A wrong-pool id therefore passes creation and fails during the asynchronous Amazon sync -
check the sync status rather than treating a successful create as confirmation.

- **`filters.keyword` and `filters.category` are EXACT matches on Amazon's side, not substring
  searches.** A partial name returns nothing rather than near misses, so a zero-row result
  after a guessed name means the guess was wrong, not that the audience does not exist.
  The SD targeting UI uses only the categories `Lifestyle`, `Interest`, `Life event` and
  `In-market`, but the value is passed through unvalidated - a typo returns zero rows.
- `filters.adType` is optional and defaults to `SD`; this entity is SD-only.
- **`total` is Amazon's match count and the call returns at most 250 rows.** When `total`
  exceeds what came back, `meta.hint` says so.
- ⚠ **Paging is not supported at all.** The downstream returns no next-page token, so there
  is nothing to continue with; `filters.nextToken` used to be accepted and has been removed,
  do not send it. Narrowing with `filters.category` is the only way to reach audiences past
  the first 250. If the user needs a complete list and `total` is larger than that, say the
  list is partial rather than implying you paged it.
- `forecasts` is Amazon's reach estimate, passed through without parsing; its shape is not
  fixed, so quote it rather than computing on it.
- **A profile that does not support audience targeting fails with an explicit error** telling
  you to use contextual (product) targeting instead. That is the real answer - relay it, do
  not retry.
