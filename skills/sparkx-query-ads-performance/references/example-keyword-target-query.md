# Keyword Target Query

Find enabled keyword targets with the lowest ACOS (spend above a floor, to avoid noisy near-zero-spend keywords):

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "target",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS", "Clicks"],
  "select": ["target.targetText_", "target.targetMatchType_"],
  "queryType": "keyword",
  "filters": {"target.targetState_": "enabled", "Spend": {">": 5}},
  "orderBy": [{"field": "ACOS", "direction": "ASC"}],
  "userContext": "Keywords with the lowest ACOS"
}
```

Notes:
- For `factEntity: target`, exactly one `queryType` value is required: `keyword`, `product`, or `auto`. On `searchTerm` it's **optional** — `keyword`/`product` filter to that source, `auto` is rejected, and **omitting it returns everything (manual + Auto-matched terms mixed)** — see the search-term example for retrieving Auto-matched terms via `matchType_` instead.
- `target.targetMatchType_` for a keyword-type query returns `broad`/`phrase`/`exact`.
- `Spend": {">": 5}` is a metric-field filter (evaluated in HAVING), separate from the dimension-field filter `target.targetState_` (evaluated in WHERE) — both can appear in the same flat `filters` object.
