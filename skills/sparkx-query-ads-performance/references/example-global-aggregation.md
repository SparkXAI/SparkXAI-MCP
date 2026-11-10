# Global (Store-Level) Aggregation

Overall spend/sales/ROAS with no grouping — omit `select` entirely for a single summary row.

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "select": [],
  "metrics": ["Spend", "Sales", "ROAS"],
  "userContext": "Overall store spend and ROAS for June"
}
```

Notes:
- `select: []` (or omitting `select` altogether) returns one aggregate row across the whole date range/profile scope — no `groupBy` needed for this case, since there's nothing to group by.
- `factEntity` still has to be set (it determines which underlying table the aggregate is computed over) even though no dimension fields are selected.
