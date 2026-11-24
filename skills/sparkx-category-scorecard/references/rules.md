# Rules (every rule the scripts apply, in plain text)

## 1. Axis 1 - do shoppers buy from you as often as from the market? (`market_by_category.py`)

- Source: `get_market_search_perf`, `factEntity: marketAsinQuery`, weekly rows. Own counts (`myBrandClickCount`,
  `myBrandPurchaseCount`) are summed over the category's ASIN rows. Market counts (`totalClickCount`,
  `totalPurchaseCount`) repeat on every ASIN row, so they are taken **once per search x week** - never summed across ASINs.
- Measure: your purchases per click / the market's purchases per click, from summed counts. Row-level rates and
  `*LowSample` flags are never used to judge.
- Relevant searches: your clicks >= 0.5% of the market's clicks, or any own purchase, over the window.
- Generic searches (relevant, no brand name from `--brand-terms` / `--competitor-terms`) are used first: own-brand
  searches convert for you and competitor-brand searches for them. Fall back to all relevant searches when generic has
  < 50 own clicks; under 50 own clicks on all relevant searches the value is not computed ("too few own clicks").
- Bands: ahead >= 0.95x, close 0.80-0.95x, behind < 0.80x. Play line = 0.80x.
- Coverage: market rows for < 40% of the category's ad spend -> "not measured", not used for the play, products listed
  under Fix the data first (when the category has >= 3x the minimum spend); 40-60% -> used, noted.
- A row with null own or market counts is skipped (never 0). Missing weeks (`missingWeekEnds`) are named, never filled.
  `meta.truncated` -> counts are lower bounds: the market axis is **not used** for the play (the category is placed on
  peers and ACOS, the row says why, no orders at stake) until a re-pull in smaller ASIN batches succeeds.
- One read per category (all brands in it together).

## 2. Axis 2 - do your ads cost less than similar brands? (`category_scorecard.py`)

- Source: `get_peer_benchmark` rows as returned: `adProduct` (`sponsoredProducts` / `sponsoredBrands` /
  `sponsoredDisplay`), `goal` (`CONVERSION` / `CONSIDERATION` / `AWARENESS`), `<metric>`, `<metric>_p25/_p50/_p75`,
  `<metric>_status`, `isDefaultNode`, `periodStart`, `categoryMetadata.parentCategoryId` / `pathIds`.
- Goal decides the metric: CONVERSION -> ROAS (higher is better); CONSIDERATION -> cost per click (lower is better; SB
  CPC campaigns are CONSIDERATION); AWARENESS -> CPM (lower is better). Any other `goal` value -> the row is not used and
  the report says so; it is never read as conversion.
- Node: walking the category's path from leaf to root, the first level where the brand's own key metric and the peers'
  P50 both exist. The level is always named (changing level often flips better / worse).
- Period: the latest `periodStart` per brand x category x ad product x goal. Periods, goals, levels and brands are never
  combined.
- Lead row: the ad product with the most of your spend that has a usable row; within it SP -> CONVERSION, SB ->
  CONSIDERATION first, SD -> CONVERSION first.
- Position: top 25% (>= P75), above median, below median, bottom 25% (< P25); cost metrics flipped (cheaper = better).
- No usable row (`_status` `NO_PEER_BENCHMARK`, unknown goal, brand without rows): category ACOS / account ACOS, <= 1.10 =
  fine; the row says which. Never "too few peers".
- ACOS columns come from the tool (already derived from reversed ROAS percentiles); never invert them again.

## 3. Plays

| Shoppers buy | Ads vs peers | Play | Hand-off (search level) | Owner first |
|---|---|---|---|---|
| >= 0.80x | at or better than median | Scale | sparkx-sqp-insight plan mode: Grow | Ad manager |
| >= 0.80x | worse than median | Fix ad cost | sparkx-sqp-insight plan mode: Improve efficiency | Ad manager |
| < 0.80x | at or better than median | Fix listing | sparkx-sqp-insight plan mode: Both (listing first) | Category manager |
| < 0.80x | worse than median | Fix first | sparkx-sqp-insight plan mode: Improve efficiency + page / price | Category manager, Sales |

Without SQP (Vendor or no market data) the hand-off for non-Scale plays is sparkx-search-term-diagnosis.

Modifiers (written in the row note, never silent):
- **Hold (stock)**: Scale with < 30 days of stock on either of the two top products.
- **Keep**: Scale with the category's ACOS above the confirmed ACOS goal - no raise until it is back under.
- **SB only / SD only**: the lead row is not SP and conversion is unusable or category ACOS > 1.2x the account.
- **Check the page as you scale**: converts 0.80-0.95x.
- **Low ROAS on a consideration row**: ROAS in peers' bottom 25% -> check before adding budget.

"Ads only" drops listing / price rows from the action table.

## 4. Fair peer goals

- The goal is the peers' **P25-P75 range** for the same brand, category level, ad product, goal and period, with the
  ACOS equivalent from the tool's `acos_p25` / `acos_p75` (P25 is the good, low-ACOS end).
- The median is shown beside it only when the spread is narrow; when P75 >= 2x P25 the report gives the range only.
- Consideration rows: cost-per-click range (CTR range beside it); awareness rows: CPM range.
- SP without a usable row: own 14-day ACOS, said so.

## 5. Timing (calendar)

- From 7 days before an event's start through its last day (in progress included): plan only. No budget lowering, no
  writes from this skill; every change-list row is `ready = no`. Promotion budgets: sparkx-promo-prep before,
  sparkx-promo-monitor during. Fix listing and stock refills can start now (they are not ad writes).
- Budget moves resume the day after the event ends; judge on settled days after that.
- Outside that window: moves go to the user for confirmation now.

## 6. Sizing

- Orders at stake (Fix listing / Fix first / close): own purchases on the searches used x (1 / conversion - 1) over the
  market weeks. Upper bound. A category shared by brands splits it by ad spend.
- Checks: a raised campaign is re-read after 7 settled days; back to the old budget if its ACOS is above the goal. Peer
  positions are re-read at the next peer refresh (weekly rows are refreshed every 2 weeks; peer data has no daily grain).

## 7. Budget plan (`budget_room.py`)

| Move | Test | New daily budget | Size |
|---|---|---|---|
| Raise | ACOS <= goal - 3 and capped | +20% (capped 3-6 h a day), +35% (6-12 h), +50% (>= 12 h); with daily spend at least the de-spiked peak day (2nd highest of 30) x 1.1; never above +50%; rounded up to a whole unit; never below 10 | extra a week = weekly spend x lift; sales = extra x ROAS x 0.8 |
| Lower | ACOS > goal + 5 (or spend with no sales), >= 2,000 spend in 14 days, usage checked, not capped | 80% of the average daily spend, at least 50% of the old budget and 10; no move if that does not bind | saving = (average daily spend - new) x 7 |
| Flag | ACOS > goal + 5 and capped | unchanged; "lower bids at keyword level - see sparkx-sqp-insight plan mode" | - |
| SB banner | SB between goal + 5 and goal x 2.0 (x 1.4 for the efficiency goal) | unchanged; creative and landing check | - |
| Not placed | room left after the raises that fit | - | reported, never forced |

- **Capped** = out of budget on average >= 3 hours a day over the usage window, from `budgetUsage.outOfBudgetMinutes`
  (>= 2,520 minutes in 14 days). `outOfBudgetPercentage` is never used (its denominator is the whole window). Null
  `budgetUsage` or null minutes = "not checked": no move, counted in the report.
- **Room**: same budget = savings from ready lowers; +x% = x% of weekly spend plus savings; -x% = savings minus the cut
  (a shortfall is reported). Raises fit best ROAS first; a raise that does not fit is held.
- **TACOS** = (ad spend + DSP) / all store sales, now and after the ready moves; with a TACOS goal the weekly extra is
  capped to stay at or under it.
- **Not in the change list**: campaigns in an AI managed group whose `aiStatus` is 1 (AI on) or whose group status was not
  read - listed apart: adjust the group with sparkx-edit-ai-group (a group budget change rescales all its campaigns).
- **Held (in the CSV, `ready = no`)**: < 30 days of stock (raises); a daily-budget change in the last 7 days
  (`get_operation_log`); lifetime budget (`campaign.updateBudget` is daily only); no internal `campaignId` / `profileId`;
  event window; does not fit the budget.

## 8. Words

- "Shoppers buy vs market", "ads vs peers' median", "top 25%", "cost per click". Never "CVR index", "percentile rank".
- Owners: Ad manager / Category manager / Sales. Never name the reader's role.
- Every number with unit and period: "$36.2K ad spend, 14 days"; "ROAS 3.31 vs peers' median 1.72 (October, Herbal
  Supplements, SP conversion)".
