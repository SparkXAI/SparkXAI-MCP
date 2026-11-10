# Resolving a Name to an ID Before Querying Logs

`get_operation_log` only accepts IDs (via `resourceIds`), never names. When the user describes something by name — a campaign, a keyword, an ASIN — resolve it first via `get_entity_metadata`.

**Campaign name → campaignId:**
```json
{"profileIds": [4404871489220462], "entity": "campaign", "filters": {"campaignName": {"like": "%holiday-sale%"}}, "userContext": "Resolve campaign name to ID"}
```

**Keyword text + match type → targetId:**
```json
{"profileIds": [4404871489220462], "entity": "target", "filters": {"targetText": {"like": "%wireless earbuds%"}, "targetMatchType": "exact"}, "userContext": "Resolve keyword to target ID"}
```

**ASIN → amazonAdId / campaignId:**
```json
{"profileIds": [4404871489220462], "entity": "productAd", "filters": {"asin": "B0DPG55T3C"}, "userContext": "Resolve ASIN to ad/campaign ID"}
```

Then pass the resolved ID(s) into `get_operation_log`'s `resourceIds`. For example, if the campaign lookup above returned `campaignId: 298539385213868`:
```json
{"idEntity": "campaign", "ids": [298539385213868]}
```

If the name match returns more than one row (e.g. several campaigns contain "holiday-sale"), either narrow the `like` pattern or ask the user which one they meant — don't silently pick the first match.
