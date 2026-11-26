# Filtered Campaign List

Enabled SP campaigns, sorted by daily budget descending.

```json
{
  "profileIds": [4404871489220462],
  "entity": "campaign",
  "filters": {
    "campaignState": {"in": ["enabled"]},
    "campaignType": {"in": ["sponsoredProducts"]}
  },
  "orderBy": [{"field": "dailyBudget", "direction": "DESC"}],
  "page": 1,
  "pageSize": 20,
  "userContext": "Enabled SP campaigns sorted by budget"
}
```

Note: `campaignState`/`campaignType` are plain camelCase, no `campaign.` prefix and no `_` suffix — this is `get_entity_metadata`'s own field convention, different from `get_ads_perf`'s `campaign.campaignState_`.
