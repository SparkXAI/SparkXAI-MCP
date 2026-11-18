# Promo Reset - error handling

| Situation | Handling |
|---|---|
| Log `hasNextPage: true` | Page - only when the response itself carries `page` / `hasNextPage` |
| Log `truncated: true`, or "page 2" returns the same rows | Limit-only mode, even with one entity: narrow by `changeField`, `actionType` / `operationType` or `resourceIds`, or split the date range into consecutive non-overlapping slices that cover all of it, until it no longer truncates (`references/restore-list.md` section 1). Never build the list from a partial log |
| No human change found in the window | Say so, show which sources and dates were searched, offer to widen the window or the sources. Empty managed-group history while groups are still on 活动冲量, with no dated schedule in effect that carries goal `3`, = the query failed, not "nothing changed" |
| An item's current value differs from the log's last value | Move it to "you decide" (Step 5.2) |
| A write is refused or `ambiguous_write` | Follow the owning write skill: do not retry blindly, read back, report |
| Fewer than 5 orders in the 14 normal days | No own range: compare with the target only, and say "too few orders for its own range" ([`pacing-rules.md`](pacing-rules.md) section 2) |
