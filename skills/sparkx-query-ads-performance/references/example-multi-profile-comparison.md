# Multi-Profile (Cross-Store) SP Totals Comparison

**Grain note**: `select` here only breaks out `profile.profileId_`/`profile.profileName_` and `campaign.campaignType_` — there's no `campaign.campaignName_`/`campaignId_`. So this returns **one row per store** with all SP campaigns summed together (a store-level total), not a campaign-by-campaign comparison across stores. If you want to compare specific campaigns across stores, add `campaign.campaignName_` (or `campaignId_`) to `select` as well.

```json
{
  "profileIds": [4404871489220462, 9283746501928374],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS", "ROAS"],
  "select": ["profile.profileId_", "profile.profileName_", "campaign.campaignType_"],
  "filters": {"campaign.campaignType_": "sponsoredProducts"},
  "orderBy": [{"field": "Spend", "direction": "DESC"}],
  "userContext": "Compare total SP spend/sales across two stores"
}
```

Notes:
- `profileIds` has 2 entries, so `select` includes `profile.profileId_`/`profile.profileName_` — without this, the two stores' totals would come back merged into a single row instead of one row per store.
- Because more than one profile is in scope, all monetary metrics (`Spend`, `Sales`) come back in **USD**, not each store's local currency — say so explicitly when presenting the numbers.
- Check `effectiveProfileIds` in the response to confirm both requested profiles were actually in the token's authorized scope.
