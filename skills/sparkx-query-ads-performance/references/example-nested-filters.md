# AND/OR Nested Filters

Enabled campaigns AND (spend > 100 OR sales > 1000):

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS"],
  "select": ["campaign.campaignName_"],
  "filters": {
    "AND": [
      {"campaign.campaignState_": "enabled"},
      {"OR": [
        {"Spend": {">": 100}},
        {"Sales": {">": 1000}}
      ]}
    ]
  },
  "orderBy": [{"field": "Spend", "direction": "DESC"}],
  "userContext": "Enabled campaigns with spend over 100 or sales over 1000"
}
```

Notes:
- Nesting is arbitrary depth — `AND`/`OR` blocks can contain further `AND`/`OR` blocks.
- Dimension-field conditions (`campaign.campaignState_`) and metric-field conditions (`Spend`, `Sales`) can be mixed freely inside the same `AND`/`OR` tree.
