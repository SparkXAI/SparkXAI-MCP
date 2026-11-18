# Pacing rules: how fast to restore each item

Two kinds of numbers drive the suggestions, and the reasons must show both:

- **Ranges and targets come from the store's own data** - each item's normal ACOS / CVR range,
  the store's range, the target ACOS (sections 2-3).
- **A few cut-offs are default rules of thumb**, set from two backtests (2026-10). They are
  not derived from the store; state them when they decide an item, and let the customer
  change them:

| Default | Value | Used in |
|---|---|---|
| Smallest raise counted as a promo change | 10% (budgets and bids; smaller raises go to "you decide") | [`restore-list.md`](restore-list.md) section 3, both restore modes |
| Orders needed for an own range | 5 | normal range (2) |
| Clicks needed for "restore now" | 20, and at least 2x the store's clicks per order | 5 |
| "Barely spent" spend ceiling | 10 x the store's average CPC over the normal period | 5 |
| Step-down cut-offs | raised < 1.5x -> at once; >= 2x with high CVR -> 3 days | 5 |
| Low stock | promoted ASINs' days of cover under about 2 weeks | 5 |
| Binding budget | out of budget on 2 of 3 post-promo days (every day when only 1-2 exist) | 7 |
| Attribution lag | 7 days Seller SP; 14 days SB, SD and any Vendor | 4 |

The spend ceiling is expressed in CPC so it works in any currency without an exchange rate.

## 1. Data to pull

`get_ads_perf`, one store, daily (`select` includes `date`):

| Period | Range | Used for |
|---|---|---|
| Normal | the 14 days before the window starts (one summed pull per item, plus the store by day) | normal range per item, and for the store |
| Post-promo | the latest 3 full days after the window that end no later than **today - 2** (so their sales have mostly come in). Never today, never yesterday. If fewer than 3 such days exist, use the ones there are and apply the thin-data rule below | the item's post-promo performance |

- Budgets and placements are judged on the **campaign** (`factEntity: campaign`, select
  `campaign.campaignId_` + `campaign.campaignName_`); bids on the **keyword / target**
  (`factEntity: target`). A **managed-group total budget** is judged like a campaign budget on
  the group's campaigns summed (map them by `aiGroupId`); the group's goal, target and other
  settings are not paced - they go back at once with the group settings (SKILL.md Step 2c). The perf ids are Amazon ids - join them to the log's
  `amazonCampaignId` / Amazon entity id, not to internal ids.
- Metrics: `Spend`, `Sales`, `Clicks`, `Conversions` (compute ACOS and CVR yourself from the
  sums - never average daily ratios).
- Store totals for the same days (`select: ["date"]`): the store normal range and the
  one-line store context.
- **Search terms worth keeping** (SKILL.md Step 4 item 6): one pull over the promo window,
  `factEntity: searchTerm`, `select: ["query_", "matchType_", "campaign.campaignId_",
  "campaign.campaignName_"]` (`query_` has no entity prefix), no `queryType` (manual and auto
  terms both), metrics `Clicks, Conversions, Spend, Sales`, `filters: {"Conversions": {">=": 3},
  "Clicks": {">=": 10}}`, ordered by sales. Drop rows whose `matchType_` is `SUBSTITUTES` or
  `COMPLEMENTS` (`query_` is an ASIN there), rows whose ROAS is under the target (section 3,
  as ROAS = 100 / target ACOS), and terms that are already an exact keyword in that campaign
  (`get_entity_metadata(entity='keyword')`, `matchType` exact). Suggested exact bid = the term's
  promo CPC, capped at its value per click (sales / clicks) x target ACOS / 100.
- Thin data: fewer than 3 post-promo days up to today - 2 (0, 1 or 2) -> section 5 is not
  used: restore at once if raised < 1.5x, otherwise step down over 2 days, and say the data
  was too thin to judge. The overrides in section 5 (stock, deal, holiday hold, "you decide")
  still apply; the binding check in section 7 has its own rule for 1-2 days. Attribution lag:
  section 4.
- **Run long after the promo** (window ended more than ~14 days ago): SKILL.md Step 1 has
  already asked whether the values were kept on purpose; pace only what the customer wants
  restored, on the latest 3 full post-promo days ending no later than today - 2.
- **"All at once"** (Step 1): no per-item performance pull (the store-level recap pulls in SKILL.md
  Step 4 still run) and sections 2-6 and 8 are not used (the recap still follows section 4's
  attribution lag) - every
  raised item is restored at once - **except two overrides of section 5 that need no
  performance data and still apply**: a deal still running holds its items, and the "you
  decide" buckets stay. Low stock and the holiday hold are not used (they need the pull or a
  performance judgement). **Section 7 still applies**: the "is the lower budget
  binding" note comes from the operation log's out-of-budget events, not from performance data,
  so count the post-promo days by date the same way.

## 2. Normal range

From the item's 14 normal days, summed (no day-by-day pull):

- **Normal ACOS** = the item's 14-day ACOS +/- noise, noise = ACOS x 1 / sqrt(orders). **Normal
  CVR** the same way: CVR +/- CVR x 1 / sqrt(orders).
- **Width floor**: W = the store's 90th minus 10th percentile of daily ACOS over the same 14
  days. The item's range is ACOS - max(noise, W / 2) to ACOS + max(noise, W / 2). CVR the same
  way with the store's daily CVR.
- **Fewer than 5 orders**: no own range (neither ACOS nor CVR) - rule 2 compares with the
  target only (ACOS above target, same click minimum); rules 3 and 4 do not apply; the reason
  says "too few orders for its own range".
- **Store range** (context, the width floor, and target fallback 3): the 10th-90th percentile of
  the store's daily ACOS over the 14 days.

This replaces day-by-day 3-day windows: a backtest of that method left most items on the store
range, which is only a point or two wide on a brand-heavy store.

## 3. Target ACOS

First that exists:

0. When the user's post-promo goal is "stay profitable at a target ACOS" (SKILL.md Step 1):
   that target, for every item.
1. The item's managed group's **pre-promo** target ACOS - the `previousValue` of the group's
   first `acos` change in the window, or the current value if the group's target was not
   changed.
2. A target the user gave.
3. The upper end of the store's normal ACOS range.

The store range can be very narrow when branded campaigns dominate spend (29-32% in one
production store) - too tight to judge a category-keyword campaign by. That is why the
group's own target comes first.

## 4. Post-promo values

Over the post-promo days (section 1): spend, sales, clicks, conversions. Section 5 judges only
items with all 3 days; with 1-2 days the item follows the thin-data rule (section 1), and the
values are shown as context with the number of days - only section 7 (binding budgets) and
section 8 (money both ways) use them. ACOS = spend / sales (spend
with no sales counts as worse than any range); CVR = conversions / clicks. Ratio = current
value / pre-promo value (for a placement whose pre-promo value is `0` there is no ratio - use
the uplift in percentage points instead: under 50 points counts as "< 1.5x", 100 or more as
">= 2x").

**Attribution lag - the one rule.** Sales keep being attributed after the day they belong to:
up to 7 days for Seller SP, 14 days for SB, SD and any Vendor profile
(`sparkx-query-ads-performance` field reference). Recent days miss sales and their ACOS reads high.

| When | Then |
|---|---|
| Any recap window (SKILL.md Step 4) or the post-promo days end less than 7 days ago (Seller SP) or 14 days ago (SB, SD, any Vendor) | The recap and the pacing reasons say sales are still being attributed, and until when |
| An item on SB, SD or a Vendor profile would be "restore now" on ACOS (section 5 rule 2, including the holiday-hold exception) and its post-promo days end less than 14 days ago | Rule 5's pace instead: restore at once if raised < 1.5x, otherwise over 2 days; the reason says ACOS may still fall as late sales come in |

## 5. Decision, in this order

| # | Condition | Suggestion | Reason should say |
|---|---|---|---|
| 1 | Spend below 10 x the store's average CPC (normal period), whatever the clicks - on cheap-click ads (Sponsored Display) 10+ clicks can cost a dollar or two | Restore at once | "大促后 3 天只花了 $2.1，影响很小" |
| 2 | ACOS above its normal range **and** above target, on at least 20 clicks and at least 2x the store's clicks per order over the 3 days (fewer clicks: rule 5) | Restore now (SB / SD / Vendor: rule 5's pace instead - section 4) | ACOS, the range, the target, the clicks |
| 3 | ACOS above target, but **not** above its own normal range (own range, not store fallback) | Normal pace (rule 5) + note | "高于目标，但和它平时差不多——不是大促造成的" |
| 4 | CVR above its normal range | Step down: 3 days if ratio >= 2, else 2 days | CVR, the range, the ratio |
| 5 | Otherwise | Restore at once if ratio < 1.5, else 2 days | ACOS / CVR within range, the ratio |

Then overrides:

- **Product low on stock** (the promoted ASINs' `asinDayAvailability` under ~2 weeks, Seller
  profiles with SP-API only) -> restore now: "库存只够 9 天，不要把剩余库存花在高价流量上".
- **A deal still running** (from Step 1) -> hold until it ends - only the items whose campaigns
  advertise a deal ASIN (at least half of their advertised products; the prep change log's
  `dealAsins` when it is there, else the ASINs the user names). Other items are paced as usual.
- **Holiday hold** (Black Friday / Cyber Monday, only when the user said yes in Step 1) -> every
  item is held until the user's date **except** items that are clearly worse (rule 2: they are
  restored now, subject to the attribution lag of section 4). This is the one rule; SKILL.md Step 3 says the same. With thin data (section 1)
  rule 2 cannot be applied, so every raised item is held.
- **Order when several apply to one item**: low stock (restore now) > a deal still running
  (hold) > holiday hold > the decision table. "You decide" buckets are settled before any of
  them.
- **After a hold ends**, judge the item on the days **after** the hold's end date (the same
  post-promo rules of section 1, counted from the day after the hold ended), not on deal or
  holiday days; until 3 such days exist, the thin-data rule applies.
- **Changed again after the window**, **created in the window**, **paused or enabled in the
  window**, **lowered** -> you decide
  (see [`restore-list.md`](restore-list.md)).

## 6. Step values

For `n` days from current value `c` to pre-promo value `b`, day `k` writes
`c - (c - b) * k / n`; the last day writes exactly `b`. Round to the currency's precision
(whole units for JPY), placements to whole percent on SB.

Example: 100 -> 35 over 3 days: 78.33 -> 56.67 -> 35 (shown as $78 -> $57 -> $35).

## 7. Lowered budgets: is the cut binding?

Count the **distinct days** with a `Campaign Out of Budget` event per campaign in the
post-promo days (section 1; several events can land on one day), counting only `newValue`
`CAMPAIGN_OUT_OF_BUDGET` - `PORTFOLIO_OUT_OF_BUDGET` means the portfolio cap stopped it, which
a campaign budget cannot fix: say so and point to the portfolio cap. With `n` post-promo days:

| `n` | Binding when |
|---|---|
| 3 | out of budget on 2 or more of them |
| 1-2 | out of budget on every one of them - say the read rests on `n` day(s) |
| 0 (the window ended less than 3 days ago) | cannot tell yet - say "还看不出是否卡预算，从{日期}起可以看", where {日期} is the window end + 3 days (the first post-promo day is usable from then) |

- **Binding** -> "大促后每天都花光 $100，大促前是 $250，可以考虑加回".
- **Not binding** -> adding budget back changes nothing. If the campaign's sales also
  fell sharply, say budget is not the cause and suggest checking stock, buy box and listing
  status.

## Backtest notes (2026-10, two production stores, read-only)

- A manual-bidding store, 88 campaigns with promo budget changes: 16 restore now (3-day
  post-promo spend of 1,533), 13 step down, 7 at once, 4 changed again later, 45 lowered,
  3 unchanged.
- A managed-group store: all 43 groups still on 活动冲量 five days after the promo; of 41
  campaign budgets, 7 restore now, 5 step down, 6 at once, 12 lowered (4 binding), 11
  unchanged. Switching the target from the store range to each group's pre-promo target did
  not change any "restore now" verdict. (Those counts used a fixed 20 USD "barely spent"
  ceiling; with the CPC-based ceiling one campaign - 3 clicks, 26 spent - moves from "restore
  now" to "at once". Both write the pre-promo value in one step. The first store's verdicts
  are unchanged.)
- Still to validate on more promos: the 1.5x / 2x step-down cut-offs, and whether the store
  fallback range is too strict for small campaigns.

## 8. Money both ways

Per item, per day, from its post-promo days:

| Item | Saved per day | Sales given up per day |
|---|---|---|
| Budget | post-promo daily spend above the pre-promo budget (0 if it does not reach it) | saved x the item's post-promo ROAS x 0.8 |
| Bid | post-promo daily spend x (1 - pre / now) x 0.8 | same |
| Placement | post-promo daily spend x (now - pre) / (100 + now) | same |

Show both totals. When the ROAS of what is given up is above the target, say so plainly: the
restore returns to settings known to work - it is not a saving. The 0.8 factors are rules of
thumb.
