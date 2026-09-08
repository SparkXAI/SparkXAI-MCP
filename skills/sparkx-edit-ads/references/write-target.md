# Target and negative-target writes

Five routes. `target` covers product / category / expression / automatic targeting;
`negativeTarget` covers negative ASIN and negative brand.

---

## `target` + `create` - no confirmation

**SP / SB.** Ad-group level. Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `adGroupId` | number | yes | positive. **Do not send `campaignId`** - foreign field, rejects the batch |
| `profileId` | string | yes | |
| `campaignType` | string | yes | `sponsoredProducts` or `sponsoredBrands` |
| `targets[]` | array | yes | each entry picks **exactly one** targeting mode |
| `targets[].bid` | number | yes | must be **> 0** |

### Exactly one targeting mode per entry

| Mode | Fields | Notes |
|---|---|---|
| product (ASIN) | `asin` (+ optional `type`) | `type` in `asinSameAs` / `asinExpandedFrom` |
| category | `categoryId` **and** `categoryName` | both or neither - one alone is rejected |
| expression | `resolvedExpression[]` | this is the field that counts as a mode |

- Providing more than one mode is rejected.
- **`expression` alone is not a mode.** Only `resolvedExpression` satisfies the
  requirement. `expression` may be sent alongside, but an entry with `expression` and no
  `resolvedExpression` fails with "requires one of asin, categoryId+categoryName, or
  resolvedExpression". Older doc wording implied the two were interchangeable; they are not.
- **`type` is only legal when `asin` is present.** Sending `type` on a category or
  expression entry - even `type: ""` - is rejected. Do not emit it unconditionally.
- **`type: "asinExpandedFrom"` is Sponsored Products only**, despite the route accepting SB.
- Expression entries (`expression[]` and `resolvedExpression[]`) each need non-blank `type`
  and `value`. Their `type` is **not** enum-checked on this route.
- No ASIN format validation - a typo is forwarded downstream.

### The 200 cap counts targets, not items

`targets[]` lengths are summed across all items in `request.data`.

Creation is not idempotent; re-submitting duplicates targets.

---

## `target` + `updateStatus` - confirms only for `archived`

Payload: `request.data[]` **plus top-level `request.targetType`**.

| Field | Type | Required | Notes |
|---|---|---|---|
| `request.targetType` | string | yes | `product` or `auto` - selects the endpoint, then removed from the payload. **How to decide: see below** |
| `data[].id` | number | yes | `targetId` from metadata |
| `data[].profileId` | string | yes | |
| `data[].campaignType` | string | yes | see the matrix below |
| `data[].state` | string | yes | `enabled` / `paused` / `archived` |

### Deciding `targetType` from metadata

The `target` entity carries no "auto vs manual" flag - the only signal is `targetMatchType`
(`campaign.targetingType` is a *campaign* field, not available on the target row). Decide in
this order:

1. **`campaignType = sponsoredDisplay` -> `product`.** `auto` only accepts
   `sponsoredProducts`, so SD rows can never be `auto`.
2. **`targetMatchType` is one of `queryHighRelMatches`, `queryBroadRelMatches`,
   `asinAccessoryRelated`, `asinSubstituteRelated` -> `auto`.** These four are the automatic
   targeting groups.
3. **`asinSameAs`, `asinExpandedFrom`, `asinCategorySameAs` -> `product`.**
4. **`similarProduct` (also `exactProduct`, `relatedProduct`, `audienceSameAs`) ->
   `product`.** Its display label reads *"Auto-Similar Product" / "自动-相似商品"*, which is
   misleading: the data layer classifies these as **audience** expressions, not automatic
   targeting, and they are Sponsored Display. Rule 1 already forces `product` for SD - this
   entry just spares you the round-trip. Sending `auto` for one of these fails, because
   `auto` accepts Sponsored Products only.
5. **Anything else - including a value you do not recognise - ask.** Do not guess: picking
   the wrong `targetType` sends the write to the wrong endpoint.

Keywords never appear here at all - they are the `keyword` entity and have their own routes.

| `targetType` | Allowed `campaignType` |
|---|---|
| `product` | `sponsoredProducts` / `sponsoredBrands` / `sponsoredDisplay` |
| `auto` | **`sponsoredProducts` only** |

`matchType` is **not** in this route's whitelist and is silently dropped - unlike the
keyword routes, which keep it. Send `campaignType` for row resolution.

Max 200 items.

---

## `target` + `updateBid` - always confirms

Same shape as `updateStatus`, with `bid` instead of `state`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `request.targetType` | string | yes | `product` or `auto`; same campaignType matrix |
| `data[].id` | number | yes | `targetId` |
| `data[].profileId` | string | yes | |
| `data[].campaignType` | string | yes | |
| `data[].bid.type` | string | yes | `set to` / `increase amount` / `decrease amount` / `increase percent` / `decrease percent` |
| `data[].bid.previousBid` | number | yes | `>= 0`, read from metadata just before |
| `data[].bid.amount` | number | yes | **> 0** for every type, `set to` included |

- `increase percent` <= 10000, `decrease percent` <= 99.
- **`set to` with `amount: 0` is rejected** (older docs said otherwise). Pause the target
  instead of bidding it to zero.
- `previousBid` is forwarded raw and never verified - a stale value goes through unnoticed.
- The preview for this route also carries `campaignType`.

---

## `negativeTarget` + `create` and `negativeTarget` + `copy` - no confirmation

**These two routes are the same operation.** Same implementation, same endpoint
(`create`), byte-identical request body; `action` changes nothing. Both add new rows at the
destination, so both are **non-idempotent**.

**SP / SB only.** Payload: `request.businessType` (**top-level**) + `request.target[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `request.businessType` | string | yes | only `adgroup` is accepted |
| `target[].id` | number | yes | destination ad group id |
| `target[].profileId` | string | yes | |
| `target[].campaignType` | string | yes | `sponsoredProducts` or `sponsoredBrands` |
| `target[].expression[]` | array | **yes** | exactly one entry |
| `target[].resolvedExpression[]` | array | **yes** | exactly one entry |
| ...`[].type` | string | yes | `asinSameAs` (negative ASIN) or `asinBrandSameAs` (negative brand) |
| ...`[].value` | string | yes | the ASIN, or the brand id |

- **Both `expression` and `resolvedExpression` are required**, each with exactly one entry.
  This is not a choice: the route validates the two fields separately, and a missing or empty
  one fails with "is required and cannot be empty". Send both, with the same `type`/`value`.
- **This is the opposite of the internal `target + create` route**, where only
  `resolvedExpression` counts as a targeting mode and `expression` is optional. Do not carry
  the rule from one route to the other.
- More than one entry in either array is rejected; zero is rejected.
- Each entry is trimmed to `type` + `value`; anything else is dropped.
- `target[]` max 200 entries.
- Note the type set here is **`asinSameAs` / `asinBrandSameAs`** - `asinExpandedFrom` is a
  positive-targeting value and is not valid for negative targets.

---

## `negativeTarget` + `updateStatus` - confirms only for `archived`

Payload: `request.data[]` (**not** `target`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | `negativeTargetId` from metadata |
| `profileId` | string | yes | |
| `campaignType` | string | yes | **`sponsoredProducts` / `sponsoredBrands` only** - `sponsoredDisplay` is rejected on this route |
| `state` | string | yes | `enabled` / `paused` / `archived` |

A top-level `request.businessType` is silently dropped on this route.

SD negative targets exist in a separate physical table, but **no `negativeTarget` write route
accepts `sponsoredDisplay`** - create, copy and updateStatus all whitelist SP/SB only. This is
**by design (confirmed with the platform team), not a defect or a temporary gap**. If a
metadata row comes back with `campaignType = sponsoredDisplay`, tell the user negative
targets on Sponsored Display are not editable through this tool - do not call it a bug and do
not promise it later.
