# Campaign writes

Three routes: daily budget, state, bidding strategy.

`campaignType` values everywhere: `sponsoredProducts` / `sponsoredBrands` /
`sponsoredDisplay`.

---

## `campaign` + `updateBudget` - always confirms

Payload: `request.data[]`, each item:

| Field | Type | Required | Notes |
|---|---|---|---|
| `campaignId` | number | yes | internal id, must be positive |
| `profileId` | string | yes | must be one of `request.profileIds` |
| `campaignType` | string | yes | SP / SB / SD |
| `budget.type` | string | yes | one of the nine values below |
| `budget.amount` | number | yes | see rules |
| `budget.suggestBudget` | number | for `suggest` types | must be > 0 |

**Do not include** `adGroupId`, `state`, `keywords`, `targets` or `negativeKeywords` - a
foreign field rejects the whole batch.

### The nine `budget.type` values

```
set to
increase amount        decrease amount
increase percent       decrease percent
increase suggest amount    decrease suggest amount
increase suggest percent   decrease suggest percent
```

Byte-exact, lowercase, single spaces. Any type containing `suggest` additionally requires
`budget.suggestBudget > 0`.

### Amount rules

**Units first, before the bounds below:**

- **Percent modes take `10` for 10%, not `0.1`.**
- **Amounts are in the profile's local currency** - never cents, never USD-converted. Money
  read back from metadata is a **decimal string** (`"100.00"`); parse it before doing
  arithmetic.
- **Adjustment amounts are always non-negative.** To decrease, use a `decrease ...` type with
  a positive amount - **never pass a negative number**.


- `set to`: `amount` must be **> 0**. Zero is rejected.
- Other types: `amount >= 0` (0 is accepted and means "leave unchanged").
- `increase percent` / `increase suggest percent`: `amount <= 10000`.
- `decrease percent` / `decrease suggest percent`: `amount <= 99`. **You cannot cut a budget
  by 100%** - use `set to` with a floor, or pause the campaign instead.

### One campaignType and one marketplace per batch

The batch is rejected unless **all items share the same `campaignType`**. If the batch spans
more than one `profileId`, all those profiles must be in the **same country**; if the
marketplace cannot be resolved for any of them, the batch is rejected rather than
attempted.

So "raise every campaign's budget by 10%" across a mixed account is **several calls**: one
per campaignType per site. Say so rather than silently doing only part of it, and confirm
each batch separately.

The marketplace comes straight from `get_user_authorized_context` - each profile carries
`countryCode` (plus `currencyCode` and `timezone`). No extra lookup needed.

**The marketplace check only runs when the batch spans more than one profile.** A
single-profile batch skips it entirely, so the "marketplace could not be resolved" rejection
cannot happen there. The single-`campaignType` rule applies to every batch.

**Sponsored Brands lifetime budgets are not covered here.** All nine `budget.type` values are
daily-budget operations, and the only budget fields on the campaign entity are `dailyBudget`
and `currentBudget`. If an SB campaign is on a lifetime/total budget, do not assume this route
handles it - tell the user that is outside what you can verify.

### Read the current budget one profile at a time

Before a relative change (or any change you want to state as "from X to Y"), read
`dailyBudget` with a **single-`profileId`** metadata call. Multi-profile rows do carry their
own `currency`, so this is not about the currency being unknowable - it is about not taking an
amount from the wrong store's row, and about the fact that amounts across stores are not
comparable without converting. One profile per read keeps the base of a percentage or delta
unambiguous.

### Not idempotent

`increase amount 10` twice adds 20. If a call times out or returns
`ambiguous_write`, **read the budget back before retrying**.

### Reconciling the preview

The Phase 1 preview reports `currentBudget` / `projectedBudget`, and `currentBudget` is the
campaign's **`dailyBudget`** - not the `currentBudget` field on a metadata row, which is a
different number. Compare against `dailyBudget`. See
[`confirmation.md`](confirmation.md).

---

## `campaign` + `updateStatus` - confirms only for `archived`

Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `campaignId` | number | yes | positive |
| `profileId` | string | yes | |
| `campaignType` | string | yes | SP / SB / SD |
| `state` | string | yes | `enabled` / `paused` / `archived` |

`archived` is **irreversible** and triggers confirmation. Tell the user it cannot be undone
before you preview, not after.

Status changes are idempotent - re-sending `paused` is harmless.

The preview for this route shows `currentState: "unknown"` by design; the underlying query
does not return state. Do not report it as fact.

---

## `campaign` + `updateBiddingStrategy` - no confirmation

**SP only.** Payload: `request.data[]`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | the campaign's internal id (note: `id`, not `campaignId`) |
| `profileId` | string | yes | |
| `campaignType` | string | yes | must be `sponsoredProducts` |
| `biddingStrategy` | string | yes | one of the four below |

### The four strategies

| Value | Meaning |
|---|---|
| `legacyForSales` | Dynamic bids - **down only** / 动态竞价-仅降低 |
| `autoForSales` | Dynamic bids - **up and down** / 动态竞价-提高和降低 |
| `manual` | **Fixed** bids / 固定竞价 |
| `ruleBased` | Rule-based bidding; the rule itself is configured downstream, not here |

Older versions of the product spec labelled both `legacyForSales` and `manual` as
"固定竞价" and omitted `ruleBased`. **The table above is the correct mapping** - picking by
the old labels silently sets the wrong strategy and the call still succeeds.

Any other field in an item is silently dropped. `businessType` is injected server-side; do
not set it.
