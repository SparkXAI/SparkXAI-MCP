# Ad Structure

All cut-points here come from `thresholds` and must be printed with the finding. They are analysis
cut-points for sorting a list, not rules about how an account should be built.

## Targeting mix

Count campaigns and spend by type: auto, manual-broad, manual-phrase, manual-exact, product
targeting, SB, SD, B2B. Paused campaigns go in a separate line as archive candidates, never mixed
into the active counts.

Two views, two different denominators — **never merge them into one "ASIN share" table**:

- **Channel view**: **SP only is ASIN-specific.** The promoted-product dimension exists for
  Sponsored Products alone (see `query-ads-performance`'s `ad-type-dependent-metrics.md`), so
  filter `campaignType` to `sponsoredProducts` whenever a `productAd.*` field is selected. For SB
  and SD there is no ASIN grain: report them as **"the campaigns / ad groups carrying this ASIN"**,
  with their coverage, and never as this ASIN's own performance. Writing one SP/SB/SD table with a
  single "ASIN spend" column silently promotes group-grain numbers to ASIN-grain ones
- **Targeting view**: entrances, from the `target` and `searchTerm` rows of the ad groups carrying
  this ASIN — group grain, so it covers group-mates too (see `evidence-scope.md`)

## Fragmentation and concentration

`fragmentCampaignsMax` (default 20) campaigns for one ASIN is where a structure starts being hard
to steer. Report the count and the Top3 campaigns' share of spend.

Neither is a verdict. High concentration can be a deliberate harvest on a mature product; many
campaigns can be a deliberate test matrix. Read both against the product's stage and say which
reading the evidence supports, rather than asserting that one shape is wrong.

## Duplicate bidding and self-competition

Three tiers, each a **fact**:

| Tier | Test |
|---|---|
| **红** | The same keyword in the same match type is live in two or more campaigns |
| **黄** | The same search term took spend in two or more campaigns |
| **提示** | More than `autoCampaignsMax` (default 4) auto campaigns of the same kind; or one child ASIN live in several auto campaigns |

**The detection is a fact. "Self-competition is raising our costs" is an inference.** Deliberate
layering — exact harvesting alongside broad discovery — is a normal structure, not a defect. Before
calling it a problem, check each campaign's own ACOS and whether the split looks intentional. Layers
that are clearly separated and each meeting target are not a finding. Do not assume duplication is
wrong by default.

List each tier with the campaigns, their spend and their orders, sorted by combined spend, so the
customer can judge the ones that matter.

## CPC / CVR / CPA together, never CPC alone

`CPA = CPC / CVR`. A high CPC is only expensive if conversion does not pay for it:

| Shape | Reading |
|---|---|
| CPC high, CVR high, CPA within target | **Keep, consider scaling.** Lowering the bid because the click looks expensive is the most common error here |
| CPC high, CVR not compensating, CPA poor | Contraction candidate — first check relevance, placement competition and sample maturity |
| Efficient but small spend | Scale candidate — check sellable stock and whether budget is actually the constraint before promising volume |

Mature inventory and new-product or new-keyword exploration are read separately. Averaging them
hides the increment: an exploration entrance is *supposed* to look worse than a harvest entrance.

Without a customer `targetAcos`, judge relative to this product's own baseline and label every
such judgement **盈利阈值待确认**. Never substitute an industry number.

## Waste candidates

`wasteClicksMin` (default 20) clicks and `wasteSpendMin` (default: derive from the store's own
order value) with zero orders is a **candidate for review**, not a verdict.

The reason the click floor matters: at a 2.7% conversion rate, 20 clicks with no order still has
roughly a 58% chance of happening to a perfectly good entrance. Below the floor, zero conversions
prove nothing. Derive the floor from the account's own CVR rather than carrying this example's
numbers — and print the CVR you used.

Hand the candidates to `sparkx-search-term-diagnosis` rather than deciding negatives here. That
skill holds the progressive 30 / 60 / 90-day verification and the checks that stop a negative from
killing a live keyword; duplicating them here would let the two drift apart.

## Variants (parent mode)

Compare children **within a demand layer** — same size, same count, same colour family. A 2-pack
and a 12-pack do not compete for the same demand, so comparing their ACOS is comparing nothing.

**The layer comes from the title and the pack configuration, not from a variant attribute.**
`get_entity_metadata` returns ASIN, title, brand, BSR, price, parent and inventory — there is no
size or colour field. Read the configuration off the title instead: single unit, 2-pack, 4-pack,
kit, with or without accessories. Show the grouping you used so the customer can correct it; never
present a derived layering as though the data supplied it.

**Then convert every price to per-unit before comparing anything.** This is the step that is easy
to skip and expensive to get wrong: a 4-pack at $149.99 is $37.50 a unit, so calling a $115.99
single unit "cheaper than us" has it backwards by roughly three times — and that error does not
stay in the price table. It picks the wrong competitors to target and the wrong comparison to put
in the creative.

Only same-configuration products are a head-to-head comparison. A single unit against a 4-pack is
an *upgrade* relationship: analyse it as a move up the range, not as a like-for-like. When the
category has no same-configuration comparison, say so and compare per-unit economics with the
configuration difference stated as a caveat.

Within a layer, the pause candidates are: spend over threshold with no orders; ACOS over the limit
while another child in the layer is sellable; stock cover below `lowStockDays` (default 10); zero sellable units with
the campaign, ad group and product ad all still enabled (say "still configured to spend" unless
recent daily spend proves delivery is live). A child launched under 14 days ago goes to limited observation, not
to a pause.

Every pause recommendation carries three things, and the first is not optional:

1. **Scope** — pause this child's **product ad inside campaign X**. Not a listing takedown. The
   variant stays buyable on the storefront. Write that sentence into the report; it is the one
   customers misread.
2. **Where the demand goes** — which sibling picks it up
3. **Re-entry condition** — restocked above N, price corrected, or last one sellable in its layer;
   return at a small daily budget and observe

Verify a reduction on four figures together — parent business orders, TACOS, demand-layer sales,
ad efficiency — over a stated window. Business orders moving within ±10% week-over-week is noise,
not a breach. **Never promise that a reduction will not cost sales**: cross-SKU attribution is not
available, so the gain is a hypothesis and the test must be reversible.
