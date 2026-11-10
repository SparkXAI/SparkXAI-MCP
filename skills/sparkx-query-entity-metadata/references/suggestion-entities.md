<!-- Split out of SKILL.md; the entry point keeps a one-line pointer plus the guards that fail silently. Content has been edited since the split - do not assume it still matches any older copy of SKILL.md. -->

# Suggestion entities - a different contract from the ordinary entities

Five entities exist to feed **campaign creation** rather than reporting: `amcAudience`,
`keywordGroup`, `suggestedKeyword`, `suggestedTarget`, `suggestedBid`. They come from their
own providers and share a contract that breaks most of the habits the other entities teach:

- **Exactly one `profileId`.** Not "one or more" - a list of two is rejected. Recommendations
  are scoped to a single store.
- **`filters` is mandatory**, and what it must contain differs per entity (below). These are
  not optional narrowing filters; the query cannot run without them, and **none of them has a
  list-all form**.
- **No pagination at all.** `page` / `pageSize` / `hasNextPage` / `total` are absent from
  `meta`: the downstream pages internally and the tool returns every row it got. Do not try
  to page, and do not treat a large result as truncated.
- **No sorting, and no comparison operators.** There is no `>=` / `like` vocabulary here.
  A **list-valued** filter - `asin`, and `keyword` on `suggestedBid` - accepts three
  interchangeable shapes: a bare string, an array, or `{"in": [...]}`. **Single-valued
  filters do not**: `matchType`, `targetingType`, `campaignType` and `audienceSegmentType`
  must resolve to exactly one value. `campaignType` and `audienceSegmentType` will accept a
  one-element array or `{"in": [...]}` and reject anything longer (`accepts a single value
  only, got N`), so just send a plain string and avoid the question.
- **Unknown filter keys are rejected.** Each entity accepts only the filters listed in its
  section below (`suggestedBid`: `asin`, `keyword`, `matchType`, `targetingType`,
  `biddingStrategy`). Anything else - `ids` or `adGroupId` on `keywordGroup`, for instance -
  fails with `invalid_params` naming the supported keys, instead of being silently ignored.
- **They are recommendations, not account state.** Nothing here describes what you already
  run - `suggestedKeyword` does not tell you which keywords exist on a campaign. Use the
  ordinary `keyword` / `target` entities for that.

## `amcAudience` - targetable audiences you may bind to a campaign

Required `filters.campaignType`: `sponsoredProducts`, `sponsoredBrands` or
**`sponsoredDisplay`**. SD is accepted here now - the same endpoint also serves the AMC
audience tab of the SD targeting page. Do not confuse the result with `sdAudience`, which is
Amazon's own SD audience catalog and a different pool entirely; an id from one is not valid
in the other. An SD AMC audience is used as an audience target on `create_sd_campaign`
(tactic `T00030`), not as a bid uplift the way SP/SB audiences are.

Optional `filters.audienceSegmentType`: `SPONSORED_ADS_AMC` (the default) or
`BEHAVIOR_DYNAMIC`; either filter accepts a single value only.

Also optional: **`filters.keyword`** narrows by audience **name** - use it when the user names
an audience instead of making them pick from a long list.

Returns `audienceId`, `audienceName`, and `audienceSegmentType` echoed back on every row.

⚠️ **Send that echoed `audienceSegmentType` back on every write that uses this
`audienceId`** - when you create a campaign, and when you change the audience bid on an
existing one. The two segment types are separate pools, and **both write paths verify that the
id belongs to the pool you name**: create checks before creating anything, and
`updateAudienceBid` checks before the preview and again before submission. A mismatched pair
is **rejected, and it takes the whole batch with it** - so carry the pair together from this
row to the write rather than reconstructing the type later.

This entity is where an id and its type arrive together, already paired and known-good - which
is what you need when **choosing** an audience to bind. The campaign row does carry
`audienceSegmentType` as well, but **it can come back empty**, so it cannot be relied on alone
(see [`campaign-audience.md`](campaign-audience.md)). For a campaign
that is already bound and whose `audienceSegmentType` is empty, find which pool its
`audienceId` sits in by querying this entity once per pool, or ask the user.

## `keywordGroup` - keyword-group suggestions for an ad group

Required `filters.asin` (one or more) - the suggestions are derived from the advertised
products, so there is nothing to compute without them.

Returns `keywordText`, `keywordGroupText`, `suggestedBid`, and where the downstream supplies
a range, `suggestedBidRangeStart` / `suggestedBidRangeEnd`.

⚠️ **A missing `suggestedBid` means no suggestion was obtained.** The downstream swallows its
error and reports 0; the tool drops such values (the bid fields are omitted, never `0`) and
`meta.hint` says how many rows lack one. Never carry a `0` into a create request - fall back to
the ad group's default bid, or ask.

## `suggestedKeyword` - keyword suggestions

Required `filters.asin`. Returns `keywordText`, `matchType`, `suggestedBid`,
`suggestedBidRangeStart` / `suggestedBidRangeEnd`, `keywordTranslation` and
`recommendationRank`. Rank is the downstream's ordering - respect it rather than re-sorting
by bid. Rows without a suggestion omit the bid fields (same rule as `keywordGroup`).

**The rows drop straight into a campaign.** `matchType` comes back lower-case
(`exact` / `phrase` / `broad`), which is exactly what `create_sp_sb_campaign` takes in
`keywords[].matchType`, and `suggestedBid` is the bid for that keyword **at that match type** -
the same keyword is priced differently per match type, so carry the pair together and never
reuse one match type's bid for another.

**Suggesting keywords for a new campaign, end to end:**

1. `get_entity_metadata(entity='suggestedKeyword', filters={"asin": "<the ASIN(s) to advertise>"})`
   - one `profileId` only, not paginated, returns every row at once.
2. Show the user a shortlist in `recommendationRank` order with the bid for each match type, and
   let them choose. Do not silently take the top N.
3. Put the chosen rows into `keywords[]` of `create_sp_sb_campaign`. **The field names are
   not the same on both sides** - map them one by one:

   | Row from `suggestedKeyword` | Field in `keywords[]` |
   |---|---|
   | `keywordText` | `keywordText` |
   | `matchType` | `matchType` |
   | **`suggestedBid`** | **`bid`** |

   There is no `suggestedBid` field on `keywords[]`; sending the row unchanged drops the bid.

`suggestedBid` on its own entity prices **your** keywords instead
(`filters.keyword` + `filters.matchType`); use that when the user brings their own list.

## `suggestedTarget` - product **and** category suggestions

Required `filters.asin`. **Two kinds of row come back in one list**, told apart by
`targetType`:

| `targetType` | Fields |
|---|---|
| `product` | `asin` |
| `category` | `categoryId`, `categoryName`, `categoryParentId`, `categoryPath`, `canBeTargeted` |

`rowCount` is the two kinds summed. **Keep both by default** - the product rows are
recommended ASINs to target, and silently dropping them answers a narrower question than the
user asked. Filter to one kind only when they asked for one kind ("给我推荐的品类"), and say
which kind you kept.

⚠️ **`canBeTargeted: false` rows come back too.** They are context for the category tree, not
usable targets - filter them out before offering anything to the user or putting it in a
create request.

## `suggestedBid` - a bid for a keyword, or for auto targeting

Required `filters.asin`, plus **one of two mutually exclusive modes**:

- **Keyword bids**: `filters.keyword` **and** `filters.matchType`. Supplying `keyword`
  without `matchType` is rejected.
- **Auto-targeting bids**: `filters.targetingType: "auto"`. Optional
  **`filters.biddingStrategy`** is passed through to the suggestion request - send the
  strategy the campaign will actually use, since the suggested bid depends on it. When
  omitted it defaults to `autoForSales`; send the strategy of the campaign the ad group goes
  into (from `entity='campaign'`).

Neither mode given is an error naming both. Returns `suggestedBid` plus
`suggestedBidRangeStart` / `suggestedBidRangeEnd`, with `keywordText` + `matchType` in
keyword mode and `targetGroup` in auto mode. A row without a suggestion omits the bid fields.

⚠️ **An empty auto-mode result is not proof the products can't be advertised** - the
downstream also returns an empty list when the Amazon call fails (`meta.hint` says so); set the
`targetBid` bids to at least the marketplace minimum (e.g. the ad group's default bid) or ask,
never `0`.
