# Evidence Scope

One mistake produces most wrong ASIN diagnoses: quoting an ad group's or a campaign's numbers as
though they were this ASIN's. They are this ASIN's only when the row is product-ad level. Everything
else contains other products.

Fix the scope before quoting any figure, and label every figure with the scope that produced it.

## What each grain can prove

| Grain | Can answer | Cannot answer |
|---|---|---|
| `productAd` (ASIN-specific, **SP only**) | This ASIN's spend, attributed sales, orders, and which campaigns carry it | How any single keyword or search term performed **for this ASIN** — Amazon does not attribute at term × product. **And nothing at all about SB or SD**: the promoted-product dimension exists for Sponsored Products alone, so filter `campaignType` to `sponsoredProducts` whenever a `productAd.*` field is selected |
| `adGroup` / `campaign` containing it | Targeting mix, search terms, placements, audience structure around this ASIN | That those results belong to this ASIN, when the group holds other products |
| `target` / `searchTerm` | Which entrances the group bought, at what cost | The split of those entrances across the group's products |
| `asin` (business) | Total sales, sessions, TACOS, Buy Box — the denominator advertising sits inside | Why any of them moved |
| `get_entity_metadata` | **Current** configuration: budget, bid, negatives, managed-group membership | What the configuration was during the analysis window |
| `get_operation_log` | What changed, when, by whom (`changedBy`) | That the change caused what followed |

## The three sentences that must stay distinct

- **「该 ASIN 的商品广告表现」** — product-ad rows. ASIN-specific. Safe to attribute.
- **「包含该 ASIN 的广告组表现」** — group rows. Covers other products too. State the coverage:
  how many products are in the group, and this ASIN's share of its spend.
- **「当前配置快照」** — metadata. Describes today, not the window. Never back-fill it across the
  analysis period; a group's settings may have changed inside it.

Writing the second as though it were the first is how a report blames an ASIN for a group-mate's
behaviour.

## Shared ad groups

When the group carrying this ASIN also carries others, every group-grain figure needs its coverage
printed beside it — this ASIN's share of the group's spend is the honest weight to read the figure
at. Above roughly half, group-grain findings are a reasonable proxy and should still say so. Well
below that, they are background, and a conclusion drawn from them about this ASIN is unsupported.

## Attribution discipline

Mechanism before identity. An operation that coincides with a decline is a lead, not a cause. It
becomes an attribution only when:

1. **Timing** — the change precedes the deterioration
2. **Coverage** — it touched the entities that actually deteriorated
3. **Mechanism** — there is a chain from the change to the observed metric, not just correlation
4. **Convergence** — a second data source agrees
5. **Reversal** — where the change was undone, the metric recovered
6. **Alternatives excluded** — price, stock, rating, listing edits, seasonality, small samples

Grade each claim and print the grade: **A** observed directly, **B** strongly supported by several
sources, **C** inferred indirectly. Different claims in one paragraph can carry different grades;
label them individually rather than letting the strongest carry the rest.

`changedBy` decides who: only `AI` counts as an AI action. An out-of-budget event is a platform
state, not an operation by anyone. A person enabling AI is not responsible for every automatic
action that followed. When it cannot be decided, write that it cannot be, and name the missing
data — an unattributed finding is still a finding.
