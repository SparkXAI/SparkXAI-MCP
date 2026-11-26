# Promo Monitor - error handling

| Situation | Handling |
|---|---|
| Hourly data has nothing for today yet (early morning) | Say so; use budget usage and the operation log only; no ACOS judgement |
| `budgetUsage` is null for a campaign | Unavailable - never "0%" or "in budget"; judge it on hourly spend alone and say so |
| A schedule is in effect but cannot be read | Do not change the group's target; say why |
| A write is refused or `ambiguous_write` | Follow the owning write skill: do not retry blindly, read back, report |
| The user's new budget for today (or the window remaining) is below what is already spent | Say so; propose only slow-down moves |
