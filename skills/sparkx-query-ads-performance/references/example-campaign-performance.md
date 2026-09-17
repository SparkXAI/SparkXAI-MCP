# Top-N Campaign Performance

Top 10 campaigns by spend over a 30-day window, enabled campaigns only, with campaign name/type broken out.

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS", "ROAS", "Impressions", "Clicks"],
  "select": ["campaign.campaignName_", "campaign.campaignType_"],
  "filters": {"campaign.campaignState_": "enabled"},
  "orderBy": [{"field": "Spend", "direction": "DESC"}],
  "page": 1,
  "pageSize": 10,
  "userContext": "Top 10 campaigns by spend in June"
}
```

Notes:
- `pageSize: 10` directly limits to the top 10 — no need to fetch 100 rows and slice client-side.
- `campaign.campaignState_` uses the `entity.field_` convention (this tool, not `get_entity_metadata`).
- `ACOS` in the response is pre-scaled ×100 — append `%` when presenting it, e.g. "17.61%".
