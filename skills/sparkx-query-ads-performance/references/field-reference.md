# Field & Metrics Reference — `get_ads_perf`

## Supported Dimension Fields (by entity)

### Campaign

| Field | Description | Enum |
|---|---|---|
| `campaign.campaignId_` | Campaign ID | — |
| `campaign.campaignName_` | Campaign name | — |
| `campaign.campaignType_` | Campaign type | `sponsoredProducts` / `sponsoredBrands` / `sponsoredDisplay` |
| `campaign.campaignState_` | State | `enabled` / `paused` / `archived` |
| `campaign.campaignServingStatus_` | Serving status | — |
| `campaign.biddingStrategy_` | Bidding strategy | `legacyForSales` / `autoForSales` / `manual` / `ruleBased` |
| `campaign.targetingType_` | Targeting mode | `manual` / `auto` |
| `campaign.costType_` | Cost type | `cpc` / `vcpm` / `fixedprice` |
| `campaign.isAiCreate_` | Whether AI-created | `0` (no) / `1` (yes) |
| `campaign.dailyBudget_` | Daily budget | — |
| `campaign.currentBudget_` | Current budget | — |

**⚠️ "How much budget do I have left today?" cannot be reliably answered by combining these fields with today's `Spend`.** `dailyBudget`/`currentBudget` are configuration values (from `get_entity_metadata`, or these dimension fields here) that can change intraday and aren't a live spend-tracking ledger; today's `Spend` from `get_ads_perf` is also subject to the T+2 data delay, so "today's spend so far" is frequently incomplete, not a live real-time figure. Subtracting one from the other (`remaining = dailyBudget − today's Spend`) produces a number that looks precise but is not reliable. If asked this, say plainly that real-time remaining budget can't be computed reliably from this data — don't present a computed number with false confidence. You can still show the configured `dailyBudget` and the most recent *complete* day's `Spend` as background context, clearly labeled as such (not as "today's remaining budget").

| Field | Description | Enum |
|---|---|---|
| `campaign.campaignStartDate_` / `campaign.campaignEndDate_` | Start/end date | — |
| `campaign.portfolioId_` | Portfolio ID | — |
| `campaign.aiGroupId_` | AI managed group ID | — |
| `campaign.campaignAiFirstOnDate_` / `campaign.campaignAiLastOnDate_` / `campaign.campaignAiLastOffDate_` / `campaign.campaignAiStudyDate_` | AI managed lifecycle dates | — |
| `campaign.offAmazonBudgetControlStrategy_` | Off-Amazon budget strategy | `MINIMIZE_SPEND` / `MAXIMIZE_REACH` |
| `campaign.siteRestrictions_` | Site restrictions | `AMAZON_BUSINESS` / `AMAZON_HAUL` |
| `campaign.bidAdjustmentTopOfSearch_` | Top-of-search bid adjustment % | — |
| `campaign.bidAdjustmentProductPage_` | Product-page bid adjustment % | — |
| `campaign.bidAdjustmentRestOfSearch_` | Rest-of-search bid adjustment % | — |

### AdGroup

| Field | Description | Enum |
|---|---|---|
| `adGroup.adGroupId_` | Ad group ID | — |
| `adGroup.campaignId_` | Parent campaign ID | — |
| `adGroup.adGroupName_` | Ad group name | — |
| `adGroup.adGroupState_` | State | `enabled` / `paused` / `archived` |
| `adGroup.adGroupServingStatus_` | Serving status | — |
| `adGroup.defaultBid_` | Default bid | — |
| `adGroup.sdBidOptimization_` | SD bid optimization | `conversions` / `clicks` / `reach` |

### Target

| Field | Description | Enum |
|---|---|---|
| `target.targetId_` | Target ID | — |
| `target.adGroupId_` / `target.campaignId_` | Parent IDs | — |
| `target.targetText_` | Target text (keyword/ASIN/category) | — |
| `target.targetMatchType_` | Match type | `broad` / `phrase` / `exact` / `asinSameAs` / `asinCategorySameAs` / `asinAccessoryRelated` / `asinSubstituteRelated` / `asinExpandedFrom` / `keywordGroupSameAs` / `queryHighRelMatches` / `queryBroadRelMatches` |
| `target.targetState_` | State | `enabled` / `paused` / `archived` |
| `target.targetServingStatus_` | Serving status | — |
| `target.targetBid_` | Set bid | — |

**⚠️ No negative-targeting variant exists in `targetMatchType_`'s enum above.** There is no negative-target performance data in this tool. `get_operation_log` only tells you *when* a negative target was added/removed (`targetTypes`: `negativeKeyword`/`negativeAsin`/`negativeBrand`), not a queryable current snapshot. For a **current snapshot** of negatives, use `get_entity_metadata(entity='negativeKeyword')` and `get_entity_metadata(entity='negativeTarget')` - those entities exist and are filterable by `campaignId` / `adGroupId`. What does not exist is negative-target *performance*, and that is inherent: a negative blocks traffic, it never serves. So answer "what am I negating in this campaign?" from metadata, and never claim spend/clicks for a negative.
| `target.targetCurrentBid_` | Live current bid (real-time value, may differ from `target.targetBid_` if adjusted by rules/AI) | — |
| `target.targetPreCurrentBid_` | Previous day's bid | — |
| `target.targetingType_` | Targeting category | `keyword` / `target` / `auto` / `audience` |

### SearchTerm (no entity prefix on fields — see naming rules above)

| Field | Description | Enum |
|---|---|---|
| `query_` | Shopper search text or matched ASIN, depending on `matchType_` — real search text for `CLOSE-MATCH`/`LOOSE-MATCH`; an ASIN for `SUBSTITUTES`/`COMPLEMENTS`, since those are product-detail-page placements with no search query behind them | — |
| `matchType_` | Match type | `broad` / `phrase` / `exact` / `targeting` / `SUBSTITUTES` / `COMPLEMENTS` / `LOOSE-MATCH` / `CLOSE-MATCH` / `asin-expanded` / `asin` / `category` — the four Auto values are **verified upper-case** (only `LOOSE-MATCH`/`CLOSE-MATCH` are hyphenated, `SUBSTITUTES`/`COMPLEMENTS` are single words); the non-Auto values (`broad`/`phrase`/`exact`/`targeting`/`asin-expanded`/`asin`/`category`) have not been separately re-verified for casing — confirm before assuming they follow the same pattern |
| `targetId_` | Related target ID | — |
| `adGroupId_` / `campaignId_` | Parent IDs | — |

**`matchTypeText` cannot be added to `select` on this entity** — confirmed to fail with `business_error` (`invalid query parameters`). `matchType_` itself works fine in `select`/`filters`; only its `Text` companion is rejected here (unlike most enum fields elsewhere, where the `Text` companion is normally readable — see the Enum-to-Text convention in this skill's SKILL.md).

### KeywordPlacement (asymmetric naming: bare in request, `_`-suffixed in response)

Only valid when `factEntity` is `keywordPlacement`. Sourced from Amazon Marketing Stream (AMS), **SP only, hourly by nature, max 7-day span**. Do not pass `timeGranularity` with this entity (neither `hourly` nor `daily`), and do not use these bare names under any other `factEntity`.

| Write this in `select`/`filters`/`orderBy` | Read this key in the response | Description | Enum |
|---|---|---|---|
| `keywordId` | `keywordId_` | Keyword ID | — |
| `keywordText` | `keywordText_` | Keyword text | — |
| `matchType` | `matchType_` | Match type | `EXACT` / `PHRASE` / `BROAD` (upper case here, unlike `target`'s lower-case `exact`/`phrase`/`broad`) |
| `placement` | `placement` | Placement | Raw stream value, matched **verbatim** — see the full value list & filter caveat below. **Not** the `topOfSearch`/`productPage`/`restOfSearch` codes used by the `placement` entity. |
| `campaignId` | `campaignId_` | Campaign ID | — |
| `adGroupId` | `adGroupId_` | Ad group ID | — |
| — | `hour` | Hour of day, `0`-`23`, comes back automatically with hourly granularity | — |
| — | `date` | Date | — |
| — | `profileId_` | Store ID | — |

Use the left column when building a call and the right column when parsing rows. Don't feed a response key back into a request: a `keywordPlacement.<field>` reference is passed through literally, so `keywordPlacement.keywordText_` happens to resolve while `keywordPlacement.placement_` fails (the column is `placement`, no underscore). The bare form avoids the trap.

**`placement` filter — use the raw stream value (exact match).** The backend does **no** code→label mapping for `keywordPlacement`: `placement` is matched verbatim against the raw AMS value, so a short code like `topSearch` (or an `SP-…`-prefixed form) silently returns **zero rows**, not an error. Filter with one of these exact strings:

- **Legacy names** (SP daily naming, still present in the AMS stream): `Top of Search on-Amazon`, `Detail Page on-Amazon`, `Other on-Amazon`, `Off Amazon`
- **AMS newer names**: `Top of Search` (no `on-Amazon` suffix), `Product Detail Page` (= `Detail Page on-Amazon`), `Rest of Search` (search part of `Other on-Amazon`), `Rest of Browse`, `Amazon Onsite`, `Offsite` (= `Off Amazon`), `Amazon O&O`

Legacy and AMS-new forms can coexist in the stream and matching is exact/case-sensitive — if a `placement` filter returns empty, suspect a value-form mismatch: prefer reading `placement` from the returned rows instead of filtering on it, or query the candidate forms explicitly.

**`campaignType` filters are dropped on this entity** (SP-only source, so nothing is pushed down): `sponsoredProducts` changes nothing, `sponsoredBrands`/`sponsoredDisplay` yields an empty result set that means "wrong entity", not "no data".

**Restricted metric set**, with two distinct failure modes:

| Metrics | Behaviour |
|---|---|
| `Impressions`, `Clicks`, `Spend`, `Sales`, `Conversions`, `Units`, `SalesSameSKU`, `ConversionsSameSKU`, `UnitsSameSKU`, `SalesOtherSKU`, `ConversionsOtherSKU`, `UnitsOtherSKU`, `CTR`, `CVR`, `CPC`, `CPA`, `ACOS`, `ROAS` | Available |
| `AISpend`, `AISales` | Return `0` — placeholder, not a real zero |
| `AIACOS`, `AIROAS` | Return `null` — placeholder |
| NTB family, DPV / video / viewability / vCPM / impression-share, ASIN business metrics | **Query fails** (no such column in the stream table) |

Never report AI performance from this entity or divide by those values; use `factEntity: campaign`. Never include a metric from the last row — it breaks the whole call rather than returning blanks.

### Placement

| Field | Description | Enum |
|---|---|---|
| `placement.campaignId_` | Campaign ID | — |
| `placement.placement_` | Placement | `topOfSearch` / `productPage` / `restOfSearch` |
| `placement.multiplier_` | Bid adjustment % | — |

### ProductAd

| Field | Description | Enum |
|---|---|---|
| `productAd.amazonAdId_` | Amazon ad ID | — |
| `productAd.adGroupId_` | Parent ad group ID | — |
| `productAd.asin_` | ASIN | — |
| `productAd.sku_` | SKU | — |
| `productAd.productAdState_` | State | `enabled` / `paused` / `archived` |

### ASIN (child)

| Field | Description |
|---|---|
| `asin.asin_` | Child ASIN |
| `asin.parent_asin_` | Parent ASIN |
| `asin.sku_` | SKU |
| `asin.asinTitle_` | Product title |
| `asin.asinBrand_` | Brand |
| `asin.asinOpenDate_` | First-live date |
| `asin.asinCategoryInfo_` | Category info |
| `asin.asinBsr_` | Best Seller Rank |
| `asin.asinPrice_` | Price — **always local currency, even in a multi-profile USD-normalized query** |
| `asin.asinFbaQuantity_` | FBA inventory quantity |
| `asin.asinInventoryStatus_` | `Active` / `Inactive` / `Incomplete` |
| `asin.asinSpEligibilityStatus_` / `asin.asinSbEligibilityStatus_` / `asin.asinSdEligibilityStatus_` | Ad-type eligibility, `ELIGIBLE` / `INELIGIBLE` |
| `asin.asinIsDelete_` | `0` (active) / `1` (deleted) |

**⚠️ Vendor-only fields `distributorView_` and `sellingProgram_` do NOT follow the `entity.field_` convention above.** They keep the `_` suffix but have **no entity prefix** (not `asin.distributorView_`), and are recognized by dedicated server-side extraction logic rather than the general dimension-join system every other field in this table goes through. See "Vendor dimension auto-locking" below for what they mean and how to use them — don't pattern-match them onto the `asin.xxx_` style used everywhere else in this file.

### ParentAsin

| Field | Description |
|---|---|
| `parentAsin.parent_asin_` | Parent ASIN |
| `parentAsin.parentAsinTitle_` / `parentAsin.parentAsinBrand_` / `parentAsin.parentAsinOpenDate_` / `parentAsin.parentAsinCategoryInfo_` / `parentAsin.parentAsinBsr_` / `parentAsin.parentAsinPrice_` / `parentAsin.parentAsinFbaQunatity_` / `parentAsin.parentAsinInventoryStatus_` / `parentAsin.parentAsinIsDelete_` | Same semantics as ASIN, rolled up to parent |

### ProductLine

| Field | Description |
|---|---|
| `productLine.productLineParentId_` / `productLine.productLineParentName_` | Top-level product line |
| `productLine.productLineChildId_` (0 = no sub-tag) / `productLine.productLineChildName_` | Sub product line |
| `productLine.productLineCreator_` | Creator |
| `productLine.asin_` | Associated ASIN |

### Portfolio

| Field | Description | Enum |
|---|---|---|
| `portfolio.portfolioId_` | Portfolio ID | — |
| `portfolio.portfolioName_` | Portfolio name | — |
| `portfolio.portfolioState_` | State | `enabled` / `paused` / `archived` |
| `portfolio.portfolioServingStatus_` | Serving status | — |
| `portfolio.portfolioStartDate_` / `portfolio.portfolioEndDate_` | Date range | — |
| `portfolio.portfolioBudget_` | Budget amount | — |
| `portfolio.portfolioBudgetType_` | Budget type | `dateRange` / `monthlyRecurring` |
| `portfolio.portfolioCreator_` | Creator | — |

### AI Group

| Field | Description | Enum |
|---|---|---|
| `aiGroup.aiGroupId_` / `aiGroup.aiGroupName_` | AI managed group ID/name | — |
| `aiGroup.aiStatus_` | Status | `0` (not started) / `1` (running) / `2` (paused) |
| `aiGroup.targetAcos_` | Target ACOS (%) | — |
| `aiGroup.aiTargetType_` | Objective | `1` (Drive Growth) / `2` (Maintain Stable Orders) / `3` (Event Boost) |
| `aiGroup.aiPersonality_` | AI aggressiveness | `1` (very conservative) … `5` (very aggressive) |
| `aiGroup.aiGroupStatusOnDate_` / `aiGroup.aiGroupLastStatusOnDate_` / `aiGroup.aiGroupLastStatusOffDate_` | Lifecycle dates | — |
| `aiGroup.aiCreator_` / `aiGroup.aiGroupCreateTime_` | Creator / create time | — |
| `aiGroup.budgetDynamicStatus_`, `aiGroup.competitorStatus_`, `aiGroup.negativeTargetStatus_`, `aiGroup.targetPausedAddStatus_`, `aiGroup.targetHarvestStatus_`, `aiGroup.bidDaypartStatus_`, `aiGroup.bidPerformanceStatus_`, `aiGroup.bidAdPlaceStatus_`, `aiGroup.bidAmazonBusinessStatus_`, `aiGroup.btbRangeStatus_`, `aiGroup.structPauseProductStatus_`, `aiGroup.structPauseCampaignStatus_`, `aiGroup.budgetDaypartStatus_`, `aiGroup.budgetRedistributeStatus_` | Action Space feature switches (`0`/`1`; `targetPausedAddStatus_` and `targetHarvestStatus_` are `0`/`1`/`2` — see enum-i18n) | — |

### AutomationRule

| Field | Description |
|---|---|
| `automationRule.campaignId_` | Campaign ID |
| `automationRule.ruleDaypartingBid_` | Dayparting bid rule enabled (`0`/`1`) |
| `automationRule.ruleAddSearchTerm_` | Harvest search term rule |
| `automationRule.ruleAddNegativeKeyword_` | Harvest negative keyword rule |
| `automationRule.rulePauseCampaign_` / `automationRule.rulePauseCampaignV2_` | Auto-pause campaign rule |
| `automationRule.ruleDaypartingBudget_` | Dayparting budget rule |
| `automationRule.ruleTargeting_` | Auto-pause targeting rule |
| `automationRule.ruleInventory_` | Inventory rule |
| `automationRule.ruleBudget_` | Performance-based budget rule |
| `automationRule.rulePlacement_` | Placement adjustment rule |

### Profile

| Field | Description | Enum |
|---|---|---|
| `profile.profileId_` | Profile ID | — |
| `profile.profileName_` | Profile name | — |
| `profile.countryCode_` | Country | `US`/`CA`/`MX`/`JP`/`UK`/`DE`/`FR`/`IT`/`ES`/`NL`/`AU`/`SG`/`BR`/`SE`/`AE`/`PL`/`IN`/`TR`/`SA`/`BE`/`EG`/`ZA` |
| `profile.profileDailyBudgetCap_` | Account daily budget cap | — |
| `profile.profileUseBudgetCap_` | Whether budget cap enforced | — |

**Whenever `profileIds` has more than one entry, add `select: ["profile.profileId_", "profile.profileName_", ...]`** (alongside whatever other entity you're grouping by) so each row can be attributed to a specific store.

## Metrics × Entity Support Matrix

**Only request metrics valid for the chosen `factEntity`.** Requesting an unsupported combination (e.g. `NTBOrders` on `placement`, or `TACOS` on anything but `asin`) is a common source of invalid-call errors.

| Metric category | campaign | adGroup | target | searchTerm | placement | productAd | asin | keywordPlacement |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Basic (Impressions/Clicks/Spend) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sales/Conversion (Sales/Conversions/Units + Same/Other SKU) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Derived (CTR/CVR/CPC/CPA/ACOS/ROAS) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| NTB (NTBOrders/NTBSales/NTBUnits etc) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| DPV (DPV/DPVClick/DPVR) | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Attribution (OrdersClick/SalesvCPM etc) | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Viewability (ViewableImpressions/vCPM) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Video (VideoCompleteViews/VTR etc) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Impression share (TopOfSearchIS) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| AI (AISpend/AISales/AIACOS/AIROAS) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **placeholder only** |
| ASIN business (TotalSalesAmount/TACOS/Sessions etc) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |

**`keywordPlacement` caveats**: it's the only hourly-native entity (AMS-sourced, **SP only**, ≤7-day span), and its metric set is the narrowest of any entity — base + Same/Other-SKU + the six derived ratios, nothing else. AI metrics are accepted but meaningless there (`AISpend`/`AISales` come back `0`, `AIACOS`/`AIROAS` come back `null`): don't report or divide by them. See the KeywordPlacement section above for the full available / unavailable split.

**Hourly campaign queries** (`factEntity: campaign` + `timeGranularity: hourly`) cover **SP + SB + SD** over a ≤7-day span, but support only a **subset** of the daily campaign metric set: basic traffic, sales/conversion (incl. Same-SKU / Other-SKU), the derived ratios (CTR/CVR/CPC/ACOS/ROAS etc.), NTB, `ViewableImpressions`, and click/view attribution. **Not supported**: DPV, video, and impression-share (e.g. top-of-search IS) — requesting these fails with a `business_error` (`message`: `unknown field 'X'`), not a value. AI metrics are placeholders (`AISpend`/`AISales` return `0`, `AIACOS`/`AIROAS` return `null`) — real AI values are daily-only.

## Metrics Reference

### Basic metrics
`Impressions`, `Clicks`, `Spend`, `AISpend`

### Conversion metrics
`Sales`, `Conversions` (maps from user's "Orders" — there is no metric literally named `Orders`), `Units`, `SalesSameSKU`, `ConversionsSameSKU`, `UnitsSameSKU`, `SalesOtherSKU`, `ConversionsOtherSKU`, `UnitsOtherSKU`

### Derived ratio metrics
| Metric | Formula |
|---|---|
| CTR | Clicks/Impressions×100 |
| CVR | Conversions/Clicks×100 |
| CPC | Spend/Clicks |
| CPA | Spend/Conversions |
| ACOS | Spend/Sales×100 |
| ROAS | Sales/Spend |

**⚠️ `CTR`/`CVR`/`ACOS` are confirmed returned pre-scaled ×100** — a value of `17.61` means 17.61%. Don't re-scale the number, but **append `%`** when presenting it to the user: "ACOS is 17.61%". Filters stay on the raw ×100 scale with no `%` in the JSON (`{"ACOS": {"<": 20}}`). `TACOS` and other `*Rate`/`*Percentage`-named metrics are **not independently confirmed** to be on this scale — relay their raw value as-is with no `%` until backend confirms. `CPC`/`CPA`/`ROAS` are plain ratios, not percentages at all.

### NTB (New-to-Brand) metrics
`NTBOrders`, `NTBUnits`, `NTBSales`, `NTBOrdersRate`, `NTBUnitsRate`, `NTBSalesRate`

⚠️ **Not available for SP (sponsoredProducts)** — must filter `campaignType` to SB/SD. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md) for split-query rules.

### DPV (Detail Page View) metrics
`DPV`, `DPVClick`, `DPVvCPM`, `DPVR`

⚠️ **Not available for SP** — SB/SD only. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

### Attribution-window metrics
`OrdersClick`, `UnitsClick`, `SalesClick`, `OrdersvCPM`, `UnitsvCPM`, `SalesvCPM`

⚠️ **Not available for SP** — SB/SD only; not supported on placement or asin entity. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

### Viewability / vCPM metrics
`ViewableImpressions`, `ViewImpressions`, `ViewableImpressionsRate`, `vCPM`

⚠️ `ViewImpressions` is **SD vCPM only**; `ViewableImpressions`/`ViewableImpressionsRate` available for all types. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

### Video metrics
`VideoUnmutes`, `VideoFirstQuartileViews`, `VideoMidpointViews`, `VideoThirdQuartileViews`, `VideoCompleteViews`, `Video5SecondViews`, `Video5SecondViewRate`, `VTR`, `vCTR`

⚠️ **Not available for SP** — SB/SD only. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

### Impression share
`TopOfSearchIS`

⚠️ **Only supported on campaign and target `factEntity`** — not available on other entities. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

### AI metrics (campaign entity only)
`AISales`, `AIACOS`, `AIROAS`

⚠️ **Only supported on campaign `factEntity`**. See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

### ASIN business metrics (asin entity only)
`TotalSalesAmount`, `OrderCount`, `UnitCount`, `AverageOrderPrice`, `AverageProductPrice`, `TACOS`, `CPO`, `Sessions`, `UnitSessionPercentage`, `PageViews`, `GlanceViews`, `BuyBoxPercentage`, `OrderedUnits`, `OrderedRevenue`, `ShippedUnits`, `ShippedRevenue`, `ShippedCogs`, `CustomerReturns`, `NetPPM`, `UnavailabilityRate`, `AdsSalesRate`, `AdsOrdersRate`, `AdsUnitsRate`, `AdsSalesSameSKURate`, `AdsOrdersSameSKURate`, `AdsCVR`, `OrganicSales`, `OrganicOrders`, `ShippedAverageProductPrice`, `ShippedTACOS`, `OrderedAverageProductPrice`, `OrderedTACOS`

⚠️ **Only supported on asin `factEntity`** — do NOT join with Campaign/AdGroup/aiGroup dimensions (causes row duplication). See [`ad-type-dependent-metrics.md`](ad-type-dependent-metrics.md).

#### Unified metrics on Vendor rows use shipped, not ordered

**`TotalSalesAmount`, `OrderCount`, `UnitCount` mean something different depending on the row's store type** — same field name, different underlying source:

| Metric | Seller row | Vendor row |
|---|---|---|
| `TotalSalesAmount` | Consumer order sales total | **Amazon-shipped revenue** (`shippedRevenue`) |
| `OrderCount` / `UnitCount` | Consumer order count / units | **Amazon-shipped units** (`shippedUnits`) |
| `TACOS` | `Spend ÷ TotalSalesAmount`, ordered-basis denominator | `Spend ÷ TotalSalesAmount`, **shipped-basis** denominator |

Both are intended to represent "this ASIN's overall retail performance" and **can be summed directly in a mixed Seller+Vendor query** — that's the point of using shipped as the Vendor proxy (Amazon doesn't expose a consumer-order figure for Vendor, since Vendor sells to Amazon, not directly to the consumer). Don't tell the user "Vendor uses a different, incompatible metric" — the values are deliberately unified so `TotalSalesAmount`/`OrderCount`/`UnitCount`/`TACOS` can be treated the same way regardless of `storeType_`.

If the user specifically needs to distinguish ordered vs. shipped (rather than just "total sales"), use the Vendor-specific metrics instead:

| Need | Use | Availability |
|---|---|---|
| Consumer-order basis | `OrderedRevenue`, `OrderedTACOS` | **Only under `distributorView_: MANUFACTURING`** — returns `0` under `SOURCING` (Amazon doesn't provide ordered data for the self-supply view) |
| Amazon-shipped basis | `ShippedRevenue`, `ShippedTACOS` | Available under both `MANUFACTURING` and `SOURCING` |

#### Vendor dimension auto-locking (`distributorView_` / `sellingProgram_`)

**These two fields don't follow this file's normal `entity.field_` dimension convention.** They're bare — `distributorView_`, `sellingProgram_` — carrying the usual `_` suffix but **no entity prefix** (not `asin.distributorView_`). They're recognized by dedicated server-side extraction logic rather than the general dimension-join system every other field in this file goes through, and that extraction logic is what applies the auto-locking behavior below.

`storeType_` is a **different kind of field** — a normal returned dimension usable in `select`/`groupBy`/`filters` like any other, **not** subject to the auto-locking below and never appearing in `meta.appliedDefaults`. Don't group it with `distributorView_`/`sellingProgram_` when reasoning about locking behavior; it's only relevant here because it's what you group by to split a mixed Seller+Vendor query (see "Mixed Seller + Vendor queries" below).

Vendor's underlying table has up to 4 rows per `(profileId, date, ASIN)` — one per `distributorView_` (`MANUFACTURING`/`SOURCING`) × `sellingProgram_` (`RETAIL`/`BUSINESS`) combination. **These 4 rows are different observation angles on the same business fact, not additive** — summing across them inflates ad metrics (Spend/Sales/Impressions) and `GlanceViews` by up to 4×, since those fields store the full value on every row.

**Auto-locking only activates when the query includes at least one Vendor profile.** A query scoped to Seller profiles only is never locked and never returns `meta.appliedDefaults` — these dimensions have no meaning on Seller rows, so don't expect or look for `appliedDefaults` there. A mixed Seller+Vendor query is treated as a Vendor query for locking purposes (the table below applies).

To prevent accidental fan-out on Vendor rows, the server **auto-locks both dimensions when you don't otherwise pin them**:

| Your `select` | Your `filters` | `distributorView_` locked to | `sellingProgram_` locked to | `meta.appliedDefaults` |
|---|---|---|---|---|
| neither field | neither field | `MANUFACTURING` | `RETAIL` | `{"distributorView":"MANUFACTURING","sellingProgram":"RETAIL"}` |
| neither field | `distributorView_=SOURCING` | your value (`SOURCING`) | `RETAIL` | `{"sellingProgram":"RETAIL"}` |
| neither field | both filtered | your values | your values | not present |
| includes `distributorView_` | no `sellingProgram_` filter | not locked (returned per-value) | `RETAIL` | `{"sellingProgram":"RETAIL"}` |
| includes both fields | — | not locked | not locked | not present |

`meta.appliedDefaults` on the response only lists the dimensions that actually fell back to a server default — a field you set explicitly (via `select` or `filters`) never appears there. **Check this field when a Vendor `asin` query's numbers look off** — if you didn't intend the default single-slice view (e.g. the user wants direct-supply performance), re-issue with `filters: {"distributorView_": "SOURCING"}` rather than trying to sum across views yourself.

Practical guidance:
- Default behavior (no explicit dimension) gives the brand's full-retail single-slice view (`MANUFACTURING` + `RETAIL`) — this is usually what "how is this ASIN doing" means.
- For self-supply/direct performance specifically, filter `distributorView_: SOURCING` — remember only `Shipped*` metrics have data there (see table above).
- Prefer `sellingProgram_: RETAIL` (the full-program figure) over `BUSINESS` unless the user specifically wants the B2B subset — never add the two together.
- Never pass either dimension as a multi-value filter (`IN [...]`) — there is no "both views combined" business concept, and the server doesn't support it.

Source: platform fix ticket BC-9770, confirmed against the MCP server's `pre` branch.

#### Mixed Seller + Vendor queries

- The unified metrics (`TotalSalesAmount`/`TACOS`/`OrganicSales`/etc.) can be aggregated directly across a query spanning both Seller and Vendor profiles — the result is a genuine store-type-blended figure (see "Unified metrics" above for why this is valid).
- Vendor-specific metrics (`OrderedTACOS`/`ShippedTACOS`/etc.) are **not** safe to read at face value in a mixed query: the numerator (`Spend`) includes every store's ad spend, but the denominator (e.g. `ShippedRevenue`) only has a value on Vendor rows. If the user needs an accurate Vendor-specific ratio in a mixed-store query, either add `storeType_` to `select`/`groupBy` and compute it per store type, or re-query with only Vendor `profileIds`.

### Common user-to-field mapping
| User says | Standard field |
|-----------|---------------|
| Impressions | Impressions |
| Clicks | Clicks |
| Spend | Spend |
| Sales | Sales |
| Orders | Conversions |
| Units | Units |
| CTR | CTR |
| CVR | CVR |
| ACOS | ACOS |
| ROAS | ROAS |

---

**Enum i18n**: When presenting enum values to the user or translating between API values and display labels, consult [`enum-i18n.md`](enum-i18n.md) for the complete ZH/EN/JA mapping of all enum fields documented above.
