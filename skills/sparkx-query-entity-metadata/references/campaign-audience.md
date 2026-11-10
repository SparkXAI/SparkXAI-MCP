<!-- Split out of SKILL.md; the entry point keeps a one-line pointer plus the guards that fail silently. Content has been edited since the split - do not assume it still matches any older copy of SKILL.md. -->

# `entity: campaign` - audience configuration arrives on its own

What the campaign list itself knows about an audience is just two fields - `audienceId` and
`audienceBidPercentage`. When `audienceId` is non-empty, the server looks that audience up and
merges its configuration into the same row: **you do not query it separately, and there is no
audience-detail entity**. The lookup is batched across profiles, so many stores cost one extra
call, not one per row.

**`audienceId` is always present.** An unbound campaign carries `""`, not a missing key - so
`audienceId != ""` is the test for "is an audience bound", and `audienceBidPercentage: 0` is
**not** (0 legitimately means "bound, no uplift").

Fields merged in: `audienceName`, `audienceType`, `proximityLevel`, `autoUpdate`,
`updateFrequence`, `audienceCount`.

**`audienceSegmentType` is NOT one of them - it is a plain campaign row field, but it may be
empty.** It names which of the two audience pools a campaign is bound to - a custom AMC audience
(`SPONSORED_ADS_AMC` / 提高针对自定义 AMC 人群的竞价) or an Amazon-built one
(`BEHAVIOR_DYNAMIC` / 提高针对亚马逊人群的竞价). A live check against a bound campaign returned
that field empty, so **do not rely on it alone**: when it is empty or any other value, treat the
pool as unknown and keep the confirmation flow below. It is also a filter on
`entity: amcAudience`, echoed back on that entity's own rows.

**And you cannot infer it from a name.** `get_ads_perf(factEntity='campaignAudience')`
resolves audience names for **both** pools - it reads them from the report table, not from AMC
- so seeing a name there says nothing about the type. A live campaign bound to the
Amazon-built audience "High interest based on shopping history" showed its name there
normally. The enrichment on *this* row is a different matter: it resolves only audiences
created and synced here, so its absence is ambiguous and its presence is not something to
build a write on either. When a write needs the type, see `edit-ads`, which has the procedure for establishing
it.

**Read them carefully - `meta.hint` says as much:**

- **The enums are raw, not display text** - the product has official labels for all of them,
  and those are what a user should see:

| Field | Raw value | English | 中文 | 日本語 |
|---|---|---|---|---|
| `audienceType` | `target` | Rule-based Audience | 基于规则的受众 | ルールベースのオーディエンス |
| | `lookalike` | Lookalike Audience | 相似受众 | 類似オーディエンス |
| `proximityLevel` | `MOST_SIMILAR` | Most Similar | 最相似 | 最も類似 |
| | `SIMILAR` | Similar | 相似 | 類似 |
| | `BALANCED` | Balanced | 平衡 | バランス |
| | `BROAD` | Broad | 广泛 | 広範 |
| | `MOST_BROAD` | Most Broad | 最广泛 | 最も広範 |
| `updateFrequence` | `daily` | Daily | 每日 | 毎日 |
| | `weekly` | Weekly | 每周 | 毎週 |
| | `biweekly` | Biweekly | 每两周 | 隔週 |

  The field itself is **Audience type / 受众类型**, **Proximity Level / 邻近度级别** and
  **Auto update frequency / 自动更新频率**; the group is **Audience Configuration /
  受众配置**. Note `proximityLevel` is upper snake case while `updateFrequence` is lower case -
  match on the raw value, don't normalize case and hope.

- **`proximityLevel` only means anything when `audienceType` is `lookalike`.** Rule-based
  audiences return an empty string for it, which is then dropped from the row entirely.
- **Auto-update is `autoUpdate` (`0`/`1`), not the presence of `updateFrequence`.** A disabled
  audience can still carry a stale frequency value, so reading the frequency as "it updates"
  is wrong.
- **The targeting rule itself (`expression`) is not included here.**
- `audienceCount` is the audience size - the number worth checking before paying an uplift.

**A row with an audience but no configuration is "unknown", not "broken".** Only AMC audiences
created and synced on this platform carry configuration: Amazon behavioural audiences,
audiences created outside the platform, and audiences whose sync has not finished have none,
and a lookup call can also simply fail. All of those produce a `meta.hint` counting the
affected rows. **Do not report those campaigns as having no audience, or as having an invalid
one** - the binding is real; only its description is missing.

**SD campaigns never get this - but not because SD has no audiences.** What SD lacks is the
**campaign-level audience binding**: the `audienceId` + `audienceSegmentType` +
`audienceBidPercentage` trio that applies a bid uplift on SP and SB. SD does its audience work
one level down, as a **target** inside an ad group (tactic `T00030`), which this field cannot
represent. So an SD campaign's `audienceId` is always blank and no lookup is attempted, and a
blank value here says nothing about whether the campaign targets an audience - read its
targets for that.

## "Which campaigns have no audience bound?"

Both conditions filter **server-side**. One query answers it:

```json
{
  "entity": "campaign",
  "profileIds": [4404871489220462],
  "userContext": "Find SP/SB campaigns without an audience bound",
  "filters": {
    "audienceId": "",
    "campaignType": {"in": ["sponsoredProducts", "sponsoredBrands"]}
  }
}
```

- **`{"audienceId": ""}` is a real condition**, not an empty one - the empty string is what an
  unbound campaign actually stores, and the downstream matches on it.
- **The `campaignType` half is not optional.** Sponsored Display has no audience
  targeting of either kind, so every SD campaign carries `audienceId: ""` forever. Filtering on the audience
  alone reports the entire SD estate as "missing an audience".
- **`meta.total` is the answer to "how many"** here, because both conditions were applied
  server-side - it is the count of unbound SP/SB campaigns. You only need to page if the user
  wants the *list*: raise `pageSize` (max 500) and continue while `meta.hasNextPage` is
  `true`.

To go the other way - which campaigns use a *particular* audience - filter
`{"audienceId": "<id>"}` with the same `campaignType` pairing.

The reverse question - *which* campaigns do have one, with performance attached - is
`get_ads_perf(factEntity='campaignAudience')`. **Do not derive the unbound set from it by
subtraction.** Whether a campaign appears there is decided by an inner join onto the audience
report table, and `campaign.audienceId` plays no part in it - so a campaign that is genuinely
bound can be missing entirely (observed: 273 bound campaigns on one profile, `total: 0`).
Subtracting would report all of them as unbound. `audienceId != ""` on this entity is the
only answer to "is an audience bound".
