# Bid-Change Operations on a Specific Campaign

Resolve the campaign to an ID first (if the user gave a name), then query the log — see the truncation check in Step 3 below before claiming completeness.

**Step 1 — the user named a campaign rather than giving an ID, so resolve it via `get_entity_metadata`:**
```json
{
  "profileIds": [4404871489220462],
  "entity": "campaign",
  "filters": {"campaignName": {"like": "%Brand-SP-Auto%"}},
  "userContext": "Resolve campaign name to ID before querying its log"
}
```
This returns a row with `campaignId: 298539385213868` (used in Step 2 below).

**Step 2 — query bid-adjustment history for that campaign, with `pageSize` at the max:**
```json
{
  "profileIds": [4404871489220462],
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "resourceIds": [{"idEntity": "campaign", "ids": [298539385213868]}],
  "actionType": {"operator": "IN", "values": ["Bid Increased", "Bid Decreased"]},
  "pageSize": 200,
  "userContext": "Bid adjustment history for this campaign"
}
```

**Step 3 — check `truncated` before presenting this as complete.** If `truncated=false`, this is the full bid-change history for the campaign in this window — present it as such. If `truncated=true`, there were more matching records than fit in one call: split `dateStart`/`dateEnd` into non-overlapping sub-windows and repeat this query on each (per the recursive procedure in the main skill), rather than presenting a `truncated=true` response as if it were the complete history.

Note: `resourceIds` takes IDs, never names — always resolve a name-based reference through `get_entity_metadata` first.
