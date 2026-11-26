# Promo Prep - error handling

| Situation | Handling |
|---|---|
| The user gives no event budget | Run the health check and preview the schedules, but write nothing - no schedule, no raise - until the user picks an amount or says to push with today's budgets only. A Promotion-sales-boost goal and a looser target spend more even though a schedule has no budget field |
| A new schedule overlaps an existing one | Name the existing schedule and its dates; offer to shorten the new phase so it no longer overlaps. Without a yes, skip that phase (and the group when the event phase cannot fit) - push-plan section 6 "Before writing". Never shorten, overwrite or delete the existing schedule |
| `startDate` would be today or earlier | A schedule cannot start today. Offer a direct goal / ACOS change for today (restored later by the reset skill) and a schedule from tomorrow |
| A write is refused or `ambiguous_write` | Follow the owning write skill: do not retry blindly, read back, report |
| Stock data missing for the store | Say so; ask the stock question; never treat missing as "enough" |
| No baseline (new store, fewer than 14 days of data) | Say so; size from the user's budget alone and keep the tier conservative |
