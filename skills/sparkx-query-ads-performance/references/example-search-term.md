# Search Term Query

`searchTerm` is the one entity whose dimension fields drop the `entity.` prefix but keep the `_` suffix — a common source of mistakes.

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "searchTerm",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "Conversions", "CTR"],
  "select": ["query_", "matchType_", "campaign.campaignName_"],
  "queryType": "keyword",
  "filters": {"campaign.campaignId_": 298539385213868},
  "orderBy": [{"field": "Spend", "direction": "DESC"}],
  "userContext": "Search term report for a specific campaign, sorted by spend"
}
```

Notes:
- `query_`/`matchType_` (searchTerm's own fields) have **no entity prefix** — not `searchTerm.query_`.
- `campaign.campaignName_`/`campaign.campaignId_` (joined dimension) **do** keep the normal `entity.field_` form, since they belong to the `campaign` entity, not `searchTerm`.
- `queryType` on `searchTerm` is **optional**, unlike on `target`. Passing `keyword` or `product` filters to that source; passing `auto` is rejected outright (`queryType=auto is not supported for factEntity=searchTerm`); **omitting it returns the full unfiltered set — manual keyword/product terms mixed with Auto-matched terms in the same result.**
- `CTR` in the response is pre-scaled ×100 — append `%` when presenting it.

## Auto-targeting search terms (no dedicated `queryType` — omit it and filter on `matchType_`)

There is no `queryType: "auto"` for this entity. To see the search terms Amazon's Auto targeting matched against, omit `queryType` and filter `matchType_` to the four Auto categories:

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "searchTerm",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Impressions", "Clicks", "Spend", "Sales"],
  "select": ["query_", "matchType_", "campaign.campaignName_"],
  "filters": {"matchType_": {"in": ["CLOSE-MATCH", "LOOSE-MATCH", "SUBSTITUTES", "COMPLEMENTS"]}},
  "orderBy": [{"field": "Spend", "direction": "DESC"}],
  "userContext": "Auto-targeting search terms only, sorted by spend"
}
```

Notes:
- **Use these exact upper-case values**: `CLOSE-MATCH`, `LOOSE-MATCH`, `SUBSTITUTES`, `COMPLEMENTS`. Only the two-word ones are hyphenated — `SUBSTITUTES`/`COMPLEMENTS` have no hyphen. See field-reference.md's `matchType_` entry.
- `CLOSE-MATCH`/`LOOSE-MATCH` are keyword-side — `query_` holds real shopper search text, same as for manual keyword targeting.
- `SUBSTITUTES`/`COMPLEMENTS` are product-side (the ad showed on another product's detail page, not in response to a search) — **`query_` holds an ASIN, not search text**, for these two match types. Don't assume every row in this entity is a text query.
- Do not add `matchTypeText` to `select` on this entity — it fails the call (`business_error`). `matchType_` itself is fine.
- Without a `matchType_` filter, the result is a genuine mix of manual and Auto rows in one list — filter or group by `matchType_` before presenting "top search terms" to the user, so manual-keyword and Auto-matched rows aren't silently blended together.
