# Promoted product (product ad) writes

Three routes. **SP / SD only** - `sponsoredBrands` is rejected on all three.

---

## `productAd` + `create` - no confirmation

This route is shaped differently from every other one: **two independent arrays plus a
top-level mode flag**, not a single item list.

| Field | Type | Required | Notes |
|---|---|---|---|
| `request.profileType` | string | **yes** | `seller` or `vendor`. Take it from `get_user_authorized_context`'s `profiles[].storeType` when that value is present and valid; **ask the user only if it is missing, blank, or not one of the two** (the server degrades to `profileId`-only when the profile lookup fails) |
| `request.campaigns[]` | array | yes | destinations, max 200 |
| `request.asins[]` | array | yes | products, max 100 |

`campaigns[]` entries:

| Field | Type | Required | Notes |
|---|---|---|---|
| `campaignId` | number | yes | campaign internal id. **The field is `campaignId` here, not `id`** - unlike most page routes |
| `profileId` | string | yes | |
| `campaignType` | string | yes | `sponsoredProducts` or `sponsoredDisplay` |
| `adGroupId` | number | yes | **`>= 0`** - the only place 0 is legal. `0` means "the endpoint picks or creates the ad group" |

`asins[]` entries:

| Field | Type | Required | Notes |
|---|---|---|---|
| `asin` | string | yes | non-blank only - **no format validation**, a typo is forwarded |
| `profileId` | string | yes | must match at least one campaign's profileId |
| `sku` | string | when `profileType = seller` | for `vendor` a supplied `sku` is still forwarded |

### How the two arrays combine

Campaigns and ASINs are matched **by `profileId`**. The operation count is, for each ASIN,
the number of campaigns sharing its `profileId` - summed, and capped at **200**.

- Every ASIN's `profileId` must have at least one campaign in `campaigns[]`, otherwise the
  batch is rejected.
- With `profileType = "vendor"`, all `campaigns[]` entries must belong to the **same**
  `profileId`.
- 20 campaigns x 15 ASINs in one profile = 300 operations -> rejected. Split it.

Creation is not idempotent - re-submitting promotes the same products again.

---

## `productAd` + `updateStatus` - no confirmation

Payload: **`request.updates[]`**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | `productAdId` from metadata - **not** `amazonAdId` |
| `profileId` | string | yes | |
| `campaignType` | string | yes | `sponsoredProducts` / `sponsoredDisplay` |
| `state` | string | yes | **`enabled` / `paused` only** - `archived` is not accepted here |

Because `archived` is impossible on this route, it never needs confirmation. To archive a
promoted product use the `archive` route below.

A `businessType` on an item is silently dropped.

---

## `productAd` + `archive` - always confirms, IRREVERSIBLE

Payload: **`request.updates[]`**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | `productAdId` |
| `profileId` | string | yes | |
| `campaignType` | string | yes | `sponsoredProducts` / `sponsoredDisplay` |
| `state` | - | **omit it** | the server sets `archived` |

- `state` is optional on this route. If you do send one it is **silently overwritten** with
  `archived` - sending `state: "enabled"` still archives the product. Omit it.
- The whole action is the irreversible one. Say so plainly before previewing: the product ad
  cannot be un-archived.
- The Phase 1 preview for this route is built from your request only (no lookup), so its
  `targetState` is always `archived`. It carries an `irreversible` notice, and it does **not**
  include `batchItemCount` / `otherStatusChanges` - those exist only on `updateStatus`
  routes. State the scope yourself.
