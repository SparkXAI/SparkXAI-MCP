# AI Bid Adjustment Records (Last 7 Days)

`changeBy: {"values": ["ai"]}` alone returns **every** kind of AI operation (budget changes, pauses, bid changes, etc) — to get only bid changes, add `actionType` as well.

```json
{
  "profileIds": [4404871489220462],
  "dateStart": "2026-07-13",
  "dateEnd": "2026-07-19",
  "changeBy": {"operator": "IN", "values": ["ai"]},
  "actionType": {"operator": "IN", "values": ["Bid Increased", "Bid Decreased"]},
  "pageSize": 200,
  "userContext": "AI bid adjustment records for the last 7 days"
}
```

**If you actually want all AI operations, not just bids** — drop `actionType` and keep only `changeBy`:

```json
{
  "profileIds": [4404871489220462],
  "dateStart": "2026-07-13",
  "dateEnd": "2026-07-19",
  "changeBy": {"operator": "IN", "values": ["ai"]},
  "pageSize": 200,
  "userContext": "All AI auto-adjustment records for the last 7 days"
}
```

Note: `changeBy`/`actionType` are always objects with `operator`/`values`, not bare arrays — `{"operator": "IN", "values": ["ai"]}`, not `["ai"]`.

**Always check `truncated` before presenting either result as complete.** If `truncated=true` (more than 200 matching entries in the 7-day window), split the date range into non-overlapping sub-windows and repeat — don't present a truncated response as the full picture.
