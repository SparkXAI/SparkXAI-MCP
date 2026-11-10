# Creating a portfolio

`create_portfolio` creates **one** portfolio in one authorized shop. There is no batch form.

## Required

| Field | Rule |
|---|---|
| `profileId` | a positive integer, authorized for this user |
| `name` | 1-255 characters **after trimming**; must be unique within the shop |

## Budget policy: three mutually exclusive modes

`policy` is omitted or `""` (no cap), `dateRange`, or `monthlyRecurring`. Anything else is
rejected.

| policy | `amount` | `startDate` | `endDate` |
|---|---|---|---|
| omitted / `""` | **must be omitted** | **must be omitted** | **must be omitted** |
| `dateRange` | required, >= 1 | **required** | optional |
| `monthlyRecurring` | required, >= 1 | **must be omitted** | optional |

Sending `amount`, `startDate` or `endDate` on an uncapped portfolio is rejected
(`Omit amount, startDate and endDate for an uncapped portfolio`) rather than ignored - so
"create it with no budget cap" means sending `name` and `profileId` and nothing else.

## Budget amount

- At most **2 decimal places**, judged on the numeric value, so `100.00` and `100` are the same.
  An out-of-range precision is **rejected, not rounded or truncated**.
- Within the shop country's daily budget limits. The error names both bounds:
  `Amount outside country budget limits for <country>: <min>..<max>`.
- **JP must be an integer**: `amount must be an integer for JP profiles`.
- The country is read from shop metadata. If it is missing, the call fails rather than guessing.

The limits differ widely by marketplace - a minimum of 1 in the US and most of Europe, 100 in
JP, 50 in IN, 20 in ZA, 4 in SA and AE. Do not assume a figure; let the error tell you, or
check the shop first.

## Dates

`yyyyMMdd`. `endDate` must not precede `startDate`. **The downstream may move a past
`dateRange` start date forward to its own current date, and shift `endDate` accordingly** - so
a portfolio created with a backdated range will not have the dates you sent. Read it back and
report what actually landed rather than echoing your request.

## The returned id is not the id you want

`creationId` is the **downstream temporary portfolio id**. It is neither the internal
`portfolioId` that metadata returns, nor a verified `amazonPortfolioId`.

To attach campaigns to this portfolio you need `amazonPortfolioId`, which exists only after
synchronization. Query `get_entity_metadata(entity='portfolio')` afterwards, and do not pass
`creationId` anywhere.

## Not idempotent

Success means the portfolio was created locally and queued for synchronization with Amazon -
not that Amazon has it.

**On any failure a local record may already exist.** Query by profile and name before retrying,
or you will end up with two portfolios of the same name.
