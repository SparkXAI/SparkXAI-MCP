# Pause Operations on Campaigns and Ad Groups

```json
{
  "profileIds": [4404871489220462],
  "dateStart": "2026-06-01",
  "dateEnd": "2026-07-19",
  "actionType": {"operator": "IN", "values": ["Paused"]},
  "entities": ["campaign", "adGroup"],
  "pageSize": 200,
  "userContext": "Pause operations on campaigns and ad groups"
}
```

Note: `entities: ["campaign", "adGroup"]` restricts to pause events on those two entity types directly — a pause event on a `target` (keyword) would not be included. Omit `entities` to catch pause events across all entity types instead.

**Check `truncated` before presenting this as complete** — if `true`, split the date range into non-overlapping sub-windows and repeat.
