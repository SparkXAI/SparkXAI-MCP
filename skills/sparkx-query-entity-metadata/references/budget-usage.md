<!-- Split out of SKILL.md; the entry point keeps a one-line pointer plus the guards that fail silently. Content has been edited since the split - do not assume it still matches any older copy of SKILL.md. -->

# `entity: campaign` - budget usage arrives only when you ask for it

Pass `budgetUsageDateStart` and `budgetUsageDateEnd` (`YYYY-MM-DD`, both or neither) and every
campaign row gets a `budgetUsage` object, sourced from Amazon Marketing Stream. Use it for "is
this campaign out of budget right now", "how much budget is left", "when did it last run out"
and "how much of the time was it in budget / out of budget". Without the two dates the key is
absent and nothing is looked up - do not pass them for ordinary campaign lookups.

- **Window**: start no earlier than 30 days ago, end no later than **tomorrow**, span at most
  30 days. The end bound is deliberately one day past today: the bounds are checked against a
  UTC+8 clock while the downstream reads the same date string in each profile's own timezone,
  so a store whose local date is ahead would otherwise lose its current day. For a "right now"
  question pass today as both dates. Other entities reject these two parameters.
- **Current fields ignore the window**: `currentBudgetUsagePercentage` (may exceed 100 - report
  Amazon's value as is), `remainingBudget`, `budgetSnapshot`, `budgetStatus`
  (`inBudget` / `outOfBudget`), `usageUpdatedTime`, `lastOutOfBudgetTime`.
  **"Current" means "not a window aggregate" - it does not mean "continuously updated".**
  Keep the two apart, because the platform's own tooltip calls this a 当前实时值 and Amazon
  documents its budget-usage pull as real-time, so flatly telling a customer "this is not
  real-time" contradicts what they are looking at. What is true:

  - It is the **latest value**, unaffected by the date window - that is the sense in which it
    is live, and it is why the date filter does not change it.
  - It **only moves when another ~5% of the budget has been consumed**. There is no fixed
    interval, so between updates the figure is stale **by design**, and "0% used" can sit
    next to real spend.

  So **always quote `usageUpdatedTime` alongside it** and let the timestamp speak, rather than
  arguing about the word. If the user needs to know whether something changed in the last few
  minutes, say that this figure cannot answer that.
- **Window fields**: `inBudgetMinutes`, `outOfBudgetMinutes`, `inBudgetPercentage`,
  `outOfBudgetPercentage`. `null` on all four means no known period in the window, which is
  different from `0`.
- **The percentages divide by the WHOLE selected window, not by the time that has data.**
  Days with no Amazon Marketing Stream record at all still count in the denominator while
  contributing nothing to the numerator, so **the two percentages do not sum to 100** - the
  shortfall is exactly the share of the window with no data. Confirmed from the platform's own
  budget-status column: across six campaigns in one query the pairs summed to 93.11% / 93.12%
  / 96.56%, and solving duration / percentage gave the **same** denominator for every row
  (~697.3 hours, a 30-day window whose current day had barely started), with each row's
  shortfall equal to a whole number of missing days.
- **The window's end is capped at the current moment**, which is why a 30-day window divides by
  ~697 hours rather than a flat 720: today contributes only the hours that have actually
  elapsed. So the same campaign's percentage **drifts upward through the day** even when
  nothing changes, and two readings taken hours apart are not directly comparable.
- ✅ **Self-check before quoting one: do the two percentages add up to ~100?** If they do, that row has data across the whole window and its percentage is trustworthy. If they fall short, the gap **is** the no-data share of the window, and the row is diluted - report the minutes instead. Measured on one account: an 8-day window gave 62.13% + 37.86% = 99.99%, while a 312-day window on the same campaigns gave 5.10% + 4.52% = 9.62%.
- **The denominator is not capped at the 30-day retention.** The dataset only keeps ~30 days, but the divisor is still the whole selected range, so a long window puts a hard ceiling on every row: over 312 days, a campaign that was in budget for its entire retained history still reads just **9.63%**, and one that never went over budget reads `0.00%` out-of-budget against it. A year-to-date view therefore makes it look like nobody is ever capped. This tool caps the window at 30 days so you cannot reach that extreme here, but the same dilution applies in miniature to any campaign whose data starts mid-window.
- **So a percentage is diluted by however little data the campaign has, and campaigns in the
  same response are not comparable on it.** A campaign created three days ago that was capped
  the whole time reads ~3% out-of-budget over a 30-day window; an old campaign capped
  occasionally reads far higher. **Never rank or threshold on `outOfBudgetPercentage`
  directly** - "which campaigns are capped most" is the most common ask here and it is exactly
  the question this field answers wrongly. Use `outOfBudgetMinutes`, or narrow the window so
  every campaign in it has data for the whole span.
- **But the minutes are a reconstruction, not a measurement.** Amazon does not report usage
  every minute; the platform rebuilds the in-budget and out-of-budget stretches from the
  records it did receive, plus fill-in rules, so **the totals carry an unquantified error**:
  - **00:00 missing** - a daily budget is filled in at `0%`; a lifetime budget carries the
    previous record's usage forward.
  - **23:59 missing** - both kinds carry the day's last recorded usage forward.
  - A real Amazon record at either point **overrides** the filled-in one.
  - Because a record has to be synthesised at each end of every day, the per-day durations
    carry roughly a **one-minute** discrepancy, while the percentages are totalled against a
    full 24 hours per day.

  So report them as approximate - "roughly 6 hours out of budget", not "6h 23m out of budget"
  - and never present them as measured delivery time. Preferring them over the percentages is
  about avoiding the denominator question, not about them being exact.
- **Times** are `YYYY-MM-DD HH:mm` in the profile's timezone, named by `budgetUsage.timezone` -
  quote it. Daily budgets reset to 0% at the profile's local midnight; lifetime budgets carry
  over.
- **`budgetSnapshot` is not `dailyBudget`, and the gap can be two orders of magnitude.**
  Measured on a live AI-managed campaign: `dailyBudget` `400.00`, while the platform's own
  budget-status panel showed that campaign at **122.83% of a `$3.11` budget** the same day.
  A $400 budget cannot be 122.83% spent at 00:17. `budgetSnapshot` is the budget Amazon
  recorded **with that usage update**, after budget rules - on a managed campaign that tracks
  the allocation in force at the time, not the configured ceiling.
- **What `remainingBudget` is "remaining" against depends on the campaign's budget type, and
  the row now tells you: `budgetType`.** For a `daily` budget it is what is left **today**; for
  a `lifetime` budget it is what is left **for the whole budget's life**. Read it rather than
  assuming - SD is always daily, but an SB campaign can be either, and quoting a lifetime
  remainder as "left today" understates the day's headroom by the whole campaign's worth.
  ⚠️ **SP rows store `budgetType` blank and the response falls back to `daily`.** That fallback
  is right for reading, but it means a `daily` you see on an SP row is a default, not a stored
  fact; and because sorting runs on the stored value, those rows do not sort with the real
  `daily` ones.
- **Never mix `budgetUsage` with `dailyBudget` or `currentBudget`.** Do not recompute a
  percentage, a spend or a remaining amount by combining them: the percentage is against the
  snapshot, and `dailyBudget` is a different number entirely. `budgetSnapshot` and
  `remainingBudget` are a self-consistent pair in the row `currency` - quote them together, and
  quote the snapshot whenever you quote the remaining amount, or the pair reads as a bug next
  to the campaign's budget.
- **The snapshot moves during the day.** The same panel showed one campaign's recorded budget
  climbing `264.98` -> `268.20` -> `272.39` -> `274.30` across a single day as a budget rule
  raised it. So two usage records from the same day can have different denominators, and
  `remainingBudget` read an hour apart is not comparable. Do not explain a gap between the
  snapshot and the configured budget unless you have checked the budget's change history -
  a later edit and a budget rule look identical from here.
- **Nothing here reflects delivery state.** Pausing is ignored by the durations *and* by
  `budgetStatus`: a paused campaign still reports `inBudget`. Never present in-budget time as
  "time the campaign was serving", and never read `inBudget` as "it is running".
- **`currentBudgetUsagePercentage: 0` with spend already today is normal, not a contradiction.**
  Usage and spend come from different pipelines; Amazon only pushes a usage update once another
  5% of the budget is consumed, so early-day spend can exist with no usage record yet.
- **`lastOutOfBudgetTime` is the START of the most recent out-of-budget period**, recorded the
  first time a usage value reached 100% in that period. Three consequences:
  - **It is not evidence the campaign is out of budget now.** Read `budgetStatus` for that.
  - **`null` means "no such record in the last 30 days", not "never".** The dataset is retained
    for 30 days; the platform shows `--` for the same reason. This is independent of the window
    you queried - a 7-day window does not narrow it to 7 days, and a `null` here does not mean
    the campaign has never run out of budget.
  - **It can disagree with the campaign's own out-of-budget state**, because the two come from
    different update channels: this is recorded when a usage value first crosses 100%, while
    the campaign status field refreshes on its own cadence. A gap between them is expected, not
    a bug to chase.
- **There is no per-record or per-day detail here.** The platform's budget-status dialog lists
  every usage update of a chosen day; this tool returns only the current values plus one
  aggregate per window. "What time did it go over budget today?" can be answered from
  `lastOutOfBudgetTime`; "how many times" and "which hours" cannot - say so rather than
  inferring it from the minute totals.
- **`budgetUsage: null` is never 0% or in budget.** It is null for archived campaigns (by
  design), campaigns with no Amazon Marketing Stream data, and failed lookups; `meta.hint`
  counts each. Report those rows as unavailable.
- **Not filterable or sortable**, by two different paths. In `filters`, `budgetUsage` and its
  sub-fields are caught by name: `Filter field '<x>' is part of the enriched budgetUsage output
  and cannot be filtered or sorted. Select budgetUsage and evaluate it on the returned rows
  instead.` In `orderBy` there is no such special case - they are simply absent from the
  campaign sortable whitelist, so you get the ordinary `Unsupported orderBy field for campaign.
  Supported fields: [...]`, whose list will not mention them. Rank and threshold on the
  returned rows instead.
- **A `select` that omits `budgetUsage` silently cancels the lookup.** The dates are still
  validated (a bad range still errors), but no downstream call is made, no `budgetUsage` key
  appears and `meta.hint` says nothing about it. If you pass `select` at all, `"budgetUsage"`
  must be in it - as one field; the sub-fields are not selectable individually.

```json
{
  "entity": "campaign",
  "profileIds": [4404871489220462],
  "userContext": "Which campaigns ran out of budget most often in the last 7 days",
  "filters": {"campaignState": {"in": ["enabled", "paused"]}},
  "budgetUsageDateStart": "2026-10-17",
  "budgetUsageDateEnd": "2026-10-23",
  "select": ["campaignName", "amazonCampaignId", "dailyBudget", "budgetUsage"]
}
```

Ranking has to happen client-side after paging through the rows - and **rank on `outOfBudgetMinutes`, not `outOfBudgetPercentage`**. The percentage divides by the whole window, so a campaign with only a few days of data is diluted and sinks below an older campaign that was capped less. Report the minutes, and give the percentage only with the window named alongside it.
