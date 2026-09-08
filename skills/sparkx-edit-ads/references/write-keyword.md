# Keyword and negative-keyword writes

Six routes. Read [`id-and-identity.md`](id-and-identity.md) first - keyword ids are only
unique **together with `matchType`**, and negative keyword ids only together with
`businessType`.

## `keywordText` rules (all routes that carry text)

- Required, non-blank.
- **Max 80 characters**, measured on the raw string, counted as characters (CJK is 1 each, not 3) - not bytes.
- **Must not contain `/`**.
- **Trim it yourself before sending, on every route.** The MCP layer never trims, and the
  two sources disagree about the downstream: the interface contract says
  `negativeKeyword + create` trims leading/trailing spaces, while the tool's own parameter
  description says whitespace is **preserved**. **Do not rely on either** - a stray space
  otherwise reaches the downstream verbatim, creating `" cheap"` as a keyword distinct from
  `"cheap"` and defeating de-duplication. The **80-character check runs before any downstream
  trim**, so padding counts against the limit regardless.
- These rules apply even when the field is not really a keyword: a `group` id or a `theme`
  enum value goes through the same check.

---

## `keyword` + `create` - no confirmation

**SP / SB.** Ad-group level. Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `adGroupId` | number | yes | internal id, positive. **Do not send `campaignId`** - it rejects the batch |
| `profileId` | string | yes | |
| `campaignType` | string | yes | `sponsoredProducts` or `sponsoredBrands` |
| `keywords[]` | array | yes | each entry below |
| `keywords[].keywordText` | string | yes | see rules above |
| `keywords[].matchType` | string | yes | `exact` / `phrase` / `broad` / `group` / `theme` |
| `keywords[].bid` | number | yes | must be **> 0**. **No default and no inherit** - see below |
| `keywords[].state` | string | no | `enabled` / `paused` only; `archived` rejected |
| `keywords[].keywordGroupText` | string | **when `matchType = "group"`** | the keyword group's display name, non-blank. **Omitting it fails the whole batch** |
| `keywords[].nativeLanguageKeyword` | string | no | forwarded unvalidated |

### `matchType` and `bid` have no defaults - ask

Both are required per keyword, and neither can be inherited: there is no "use the ad group's
default bid" option in this payload, and no default match type. **Ask the user for both**
rather than defaulting to `broad` plus the ad group's `defaultBid` - you would be choosing a
live bid on their behalf. Offering the ad group's `defaultBid` as a suggested value is fine;
picking it silently is not.

### matchType specifics

- **`theme` is Sponsored Brands only.** Sending it with `sponsoredProducts` is explicitly
  rejected, despite the route supporting SP overall.
- With `matchType = "theme"`, `keywordText` must be exactly one of:
  `KEYWORDS_RELATED_TO_YOUR_LANDING_PAGES` or `KEYWORDS_RELATED_TO_YOUR_BRAND`.
- With `matchType = "group"`, `keywordText` is the keyword-group id **and**
  `keywordGroupText` is **required** - it is the group's display name, and a blank or
  missing value rejects the entire batch. This is the one field most easily missed on
  this route.
- `state` is optional and **defaults to `enabled` downstream**. The MCP layer sets no
  default of its own - it forwards null. Send it explicitly when the user wants the keywords
  created paused.

### The 200 cap counts keywords, not items

`keywords[]` lengths are summed across every item in `request.data`. Three ad groups with
100 keywords each is 300 operations and is rejected. Split the batch.

### The downstream de-duplicates - but do not lean on it

Per the downstream contract, **keywords and keyword groups that already exist in the target
ad group are skipped automatically**, so re-submitting the same word does not create a
duplicate row.

**On a `create` route, a successful response does not tell you what was created.** The
service returns a distinct hint for creates, and `total` / `successCount` / `failCount` count
the **outer `request.data[]` entries**, not the child keywords/targets actually written. There
is no created-count, no skipped-count and no per-child detail, and success does not confirm
Amazon-side sync. **Never tell the user "created N keywords".** If the number matters, take a
baseline read before the write and diff the ids afterwards - a read after the write alone only
proves the rows exist, not that this call made them.

Two further caveats:

- De-duplication is **TEST-verified** for plain keywords, keyword groups, negative keywords
  **and both `theme` values** - re-submitting any of them adds 0 rows. What is *not* verified:
  re-creating after archiving, a duplicate submitted with a different bid or state, concurrent
  requests, and a mixed batch of new + duplicate items. Do not extrapolate to those.
- Skipped items are not errors, and the counts describe outer items, so nothing in the
  response reveals how many rows were created. Report what the ad group now contains, not a
  created-count.

`state` defaults to `enabled` downstream when you omit it.

---

## `keyword` + `updateStatus` - confirms only for `archived`

Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | `keywordId` from metadata |
| `profileId` | string | yes | |
| `campaignType` | string | **send it** | not validated by this route, but needed to resolve the row |
| `matchType` | string | **send it** | echo metadata verbatim - selects the physical table |
| `state` | string | yes | `enabled` / `paused` / `archived` |

`matchType` is **not** enum-validated on this route - any string passes MCP and is
forwarded. That is exactly why you must echo metadata rather than construct it: a plausible
wrong value fails later as `unable to resolve owning campaign`, or resolves a row you did
not mean.

No ad-type restriction on this route.

---

## `keyword` + `updateBid` - always confirms

Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | `keywordId` |
| `profileId` | string | yes | |
| `campaignType` | string | **send it** | row resolution |
| `matchType` | string | **send it** | row resolution |
| `bid.type` | string | yes | see below |
| `bid.previousBid` | number | yes | `>= 0`; read it from metadata immediately before |
| `bid.amount` | number | yes | must be **> 0** for every type, including `set to` |

### The five `bid.type` values

```
set to
increase amount        decrease amount
increase percent       decrease percent
```

- `increase percent` <= 10000, `decrease percent` <= 99.
- **`set to` with `amount: 0` is rejected.** Older docs said 0 was allowed; it is not. To
  stop spend on a keyword, pause it instead.
- `previousBid` is forwarded raw - the server does no arithmetic with it and **does not
  verify it**. A stale value is not detected. Re-read the current bid rather than reusing a
  cached one; the AI or another user may have changed it.
- Extra fields inside `bid` are silently dropped.

Bid changes are **not idempotent** for relative types.

---

## `negativeKeyword` + `create` - no confirmation

**SP only.** Campaign level. Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `campaignId` | number | yes | positive. **Do not send `adGroupId`** |
| `profileId` | string | yes | |
| `campaignType` | string | yes | must be `sponsoredProducts` |
| `negativeKeywords[]` | array | yes | |
| `negativeKeywords[].keywordText` | string | yes | see rules above |
| `negativeKeywords[].matchType` | string | yes | `negativeExact` / `negativePhrase` |

Sub-items count toward the 200 cap the same way as positive keywords.

**This route de-duplicates, and it trims.** Per the downstream contract:

- An existing negative keyword with the **same `keywordText` + `matchType` whose state is
  `enabled` or `paused`** is skipped silently - no error, no duplicate. Note the state
  condition: an **archived** duplicate does not satisfy it.
- `keywordText` gets its leading/trailing spaces trimmed downstream (this is the one route
  where that is documented). Trim it yourself anyway - the 80-character check happens first.
- **Created rows are always `state: enabled`.** There is no way to add a negative keyword in
  a paused state through this route.

---

## `negativeKeyword` + `updateStatus` - confirms only for `archived`

Payload: **`request.updates[]`** (not `data`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | `negativeKeywordId` |
| `profileId` | string | yes | |
| `campaignType` | string | yes | SP / SB / SD |
| `businessType` | string | yes | **per item** here. `campaign` or `adgroup` (lowercase g) |
| `state` | string | yes | `enabled` / `paused` / `archived` |

`businessType` selects between two tables with disjoint id spaces - echo metadata.

An older spec version claimed SB + `businessType=campaign` is rejected on this route. **It
is not** - that restriction exists only on `copy`. Do not pre-filter those items away; if
the combination is invalid the page endpoint decides.

Because this route reads `updates` (not `data`), the archived-confirmation trigger also
looks in `updates`.

---

## `negativeKeyword` + `copy` - no confirmation

Copies negative keywords to a destination campaign or ad group. **This creates new rows
downstream** (the endpoint is a create), so it is **not idempotent** - running it twice
duplicates the negatives.

Payload: `request.businessType` (**top-level**) + `request.target[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `request.businessType` | string | yes | `campaign` or `adgroup` - the destination level |
| `target[].id` | number | yes | destination id |
| `target[].profileId` | string | yes | |
| `target[].campaignType` | string | yes | SP / SB / SD |
| `target[].keywordText` | string | yes | <= 80 chars, no `/` |
| `target[].matchType` | string | yes | `negativeExact` / `negativePhrase` |

- **SB supports `adgroup` only**: `request.businessType = "campaign"` together with an item
  whose `campaignType = "sponsoredBrands"` is rejected.
- `target[]` max 200 entries.
- A per-item `businessType` or `state` is silently dropped here - the level comes from the
  top-level field only.
