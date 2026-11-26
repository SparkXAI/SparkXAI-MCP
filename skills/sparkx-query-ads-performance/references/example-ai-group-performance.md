# AI-Managed Campaign Performance (Labeled by AI Group)

**Grain note**: `select` includes both `campaign.campaignName_` and `aiGroup.aiGroupName_`, so this returns **one row per campaign**, each labeled with its AI managed group — not a rolled-up total per AI group. If you want genuine per-AI-group totals (one row per group, campaigns summed together), drop `campaign.campaignName_` from `select` and keep only `aiGroup.aiGroupName_`.

**Per-campaign rows, labeled by AI group:**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS", "AISpend", "AISales", "AIACOS"],
  "select": ["campaign.campaignName_", "aiGroup.aiGroupName_"],
  "filters": {"aiGroup.aiStatus_": 1},
  "userContext": "AI-managed campaign performance, each campaign labeled with its AI group"
}
```

**True per-AI-group rollup (campaigns summed together):**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS", "AISpend", "AISales", "AIACOS"],
  "select": ["aiGroup.aiGroupName_"],
  "filters": {"aiGroup.aiStatus_": 1},
  "userContext": "Total performance per AI managed group"
}
```

Notes:
- `aiGroup.aiStatus_: 1` means the AI managed group is currently running (`0` = not started, `2` = paused).
- `AISpend`/`AISales`/`AIACOS` are AI-attributed variants of the base metrics, only meaningful on `campaign`.
