---
name: sparkx-category-scorecard
description: >-
  Score each ad category on shoppers-buy-vs-market and ads-vs-peers' median, give it a
  play (Scale / Fix ad cost / Fix listing / Fix first, Hold, Keep), fair peer goals (P25-P75
  with ACOS) and a campaign daily-budget plan (raise / lower / not placed) sized to the
  confirmed budget. Read-only; budget changes go to sparkx-edit-ads after confirmation. Use
  when the user asks how categories compare with market and peers, where next month's budget
  should go, or what ROAS / ACOS target is fair. Not for monthly recaps
  (sparkx-monthly-ads-report), one ASIN (sparkx-asin-deep-dive), structure
  (sparkx-ads-structure-analysis), product tiers (sparkx-product-diagnosis), negatives
  (sparkx-search-term-diagnosis), search-level or price / pack moves (sparkx-sqp-insight) or
  one number (sparkx-query-market-data).
metadata:
  version: 1.0.0
---

# Category Scorecard

One page that answers three questions, and nothing else:

1. **Where does each category stand?** Shoppers buy vs market (0.80x line) x ads vs peers' median -> one play.
2. **What goal is fair?** Peers' P25-P75 per category, ad product and goal, with the ACOS equivalent.
3. **Where does the budget go?** Campaign daily budgets to raise, to lower, and money not placed - sized to the
   confirmed budget, checked against TACOS.

## Scope: a read-only orchestration skill

No MCP tool of its own. It reads with five tools and hands execution to one skill:

| What | Tool | Owning skill - read it first |
|---|---|---|
| Spend and sales by parent ASIN and by campaign; daily spend; store sales | `get_ads_perf` | [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md) |
| Category, brand, days of stock; campaign ids, budgets, budget usage; AI managed groups | `get_entity_metadata` | [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md) |
| Budget changes in the last 7 days | `get_operation_log` | [sparkx-query-operation-log](../sparkx-query-operation-log/SKILL.md) |
| Market search data (SQP); peer benchmark | `get_market_search_perf`, `get_peer_benchmark` | [sparkx-query-market-data](../sparkx-query-market-data/SKILL.md) |
| Writing the confirmed daily budgets | `batch_update_ads` (`campaign` + `updateBudget`) | [sparkx-edit-ads](../sparkx-edit-ads/SKILL.md) |

> Install those skills alongside this one (sibling directories). Auth, paging, date limits and currency rules are in the
> query skills' `references/platform-notes.md`.

| Reference | Read it when |
|---|---|
| [`references/ask-first.md`](references/ask-first.md) | Step 1 |
| [`references/data-contract.md`](references/data-contract.md) | Step 2: every call, its parameters, the fields the scripts read, what missing means |
| [`references/rules.md`](references/rules.md) | Step 3: axes, node, plays, goals, timing, budget plan - every rule in plain text |
| [`references/calendar.md`](references/calendar.md) | Step 3: the next retail event |
| [`references/which-skill.md`](references/which-skill.md) | The question is near the edge of this skill |
| [`references/golden-tests.md`](references/golden-tests.md) | Before changing a rule |

## Requirements

Python 3, standard library only (`openpyxl` only for the optional `.xlsx` SQP export fallback). In a client that cannot
run code, follow `references/rules.md` by hand on the same pulled rows, say in the report that the numbers were computed
without the scripts, and keep every rule (sums before ratios, market counts once per search x week, null is not 0).

## Method

### Step 1 - Ask first ([`references/ask-first.md`](references/ask-first.md))

Pull 14-day spend and ACOS by category first so the options carry numbers. One card, at most 4 questions: **goal** (with
its ACOS number), **budget** (same / +x% / -x%), **actions wanted** (ads + listing + price / ads only / report only),
scope only when needed. Unattended: state the defaults and go. The report's first line restates all three.

### Step 2 - Pull the data ([`references/data-contract.md`](references/data-contract.md))

1. `get_user_authorized_context` -> one profile; note Seller / Vendor and country (SQP exists only for Sellers in
   US, CA, UK, DE, FR, IT, ES, JP).
2. `get_ads_perf`: parent ASIN spend / sales (last 14 complete days), campaign spend / sales (same window), optionally 30
   days of daily spend per campaign and store sales (`TotalSalesAmount`) for TACOS.
3. `get_entity_metadata`: `asin` (parent, brand, category, `parentAsinDayAvailability30`); `campaign` with
   `budgetUsageDateStart` / `budgetUsageDateEnd` over the same 14 days; `aiGroup` for the groups found on campaigns;
   `productAd` for the scored campaigns (internal `campaignId` -> `asin`), saved as `campaign_asins.json`. Without it a
   raise cannot be checked against stock and is held; campaigns with no product-ad rows (most SB / SD) stay held for
   stock unless the user confirms stock.
4. `get_operation_log`: `entities: ["campaign"]`, budget operation types, last 7 days, paged to the end.
5. `get_peer_benchmark`: `timeUnit: WEEK`, the last 4 complete Sun-Sat weeks, explicit `categoryIds` (leaf ids, then
   the ancestors from `pathIds`); the latest week with a row is used. Weekly is the default because weekly peer data is
   what exists (from the week of 2026-09-13, refreshed every 2 weeks); use `MONTH` only when the user asks for a
   monthly view and the tool returns monthly rows (monthly data back to January 2026 is planned for early December
   2026, then refreshed monthly). Name the week or month used. Query one authorized `profileId` as a JSON integer.
   Start the leaf and ancestor queries at `page: 1` separately. Collect every page of each query
   by incrementing only `page` while `meta.hasNextPage` is true, then score the categories.
6. `get_market_search_perf`: `marketAsinQuery`, weekly, last 4 complete Sun-Sat weeks, ASIN batches until
   `meta.truncated` is false. Skip for Vendor or uncovered marketplaces.

### Step 3 - Compute (scripts, never by hand when code can run)

```
python3 scripts/market_by_category.py --market sqp1.json [--market sqp2.json] --spend parent_spend.json \
  --category-map parent_category.json --asin-parent asin_parent.json --brand-terms "<own brand names>" --out out/
python3 scripts/category_scorecard.py --peer peer_leaf.json --peer peer_parents.json --market out/market_by_category.json \
  --spend parent_spend.json --category-map parent_category.json --parent-meta parent_meta.json --stock stock_days.json \
  --ad-type-share camp14.json --acos-goal 25 --event "<name>|<start>|<end>" --today <date> --out out/
python3 scripts/budget_room.py --campaigns camp14.json --entities campaign_meta.json --ai-groups ai_groups.json \
  --recent-changes oplog.json --stock stock_days.json --campaign-asins campaign_asins.json \
  --acos-goal 25 --budget "+10%" --window-days 14 \
  [--daily daily30.json] [--total-sales-14d N --tacos-goal T] --event "<name>|<start>|<end>" --today <date> --out out/
python3 scripts/render_scorecard.py --in out/category_scorecard.json --budget-room out/budget_room.json \
  --summary summary.json --store "<store>" --period "<windows>" --out out/
```

Vendor or no SQP: skip `market_by_category.py` and run the scorecard without `--market` (`--account vendor` for Vendor
profiles). Every category then says "no market data" and the play rests on peers and ACOS.

The play (full rules in [`references/rules.md`](references/rules.md)):

| | **Ads at or better than peers' median** | **Ads worse than peers' median** |
|---|---|---|
| **Shoppers buy >= 0.80x the market** | **Scale** | **Fix ad cost** |
| **Shoppers buy < 0.80x the market** | **Fix listing** | **Fix first** |

Modifiers: Scale with < 30 days of stock on a top product -> **Hold (stock)**; Scale with category ACOS above the goal ->
**Keep**. Search-level work in a named category (bids, new keywords, price / pack) is a hand-off to
[sparkx-sqp-insight](../sparkx-sqp-insight/SKILL.md) plan mode; this skill only moves campaign daily budgets.

Budget plan (rules.md section 7), in one breath: raise where campaign ACOS <= goal - 3 and out of budget >= 3 hours a day
on average (from `outOfBudgetMinutes`); lower where ACOS > goal + 5 and not capped; a capped campaign above goal + 5 is a
**flag** (budget unchanged; lower bids at keyword level - see sparkx-sqp-insight plan mode). At most +50% a step, floor 10,
money no campaign earns under goal is **not placed**. AI managed campaigns, campaigns changed in the last 7 days, lifetime
budgets and low stock are held or listed apart.

**Timing:** from 7 days before a retail event through its last day (in progress included), this skill plans only: no
budget lowering and no writes. Promotion budgets belong to [sparkx-promo-prep](../sparkx-promo-prep/SKILL.md) before the
event and [sparkx-promo-monitor](../sparkx-promo-monitor/SKILL.md) during it.

### Step 4 - Report

The model writes only `summary.json` (headline, at most three first actions, opportunity, challenge, action table,
not-checked line); the renderer owns layout. Order:

1. **Headline** - the answer in one sentence with its number (<= 25 words).
2. **Four tiles** - extra money placed, sales from it, capped campaigns under goal, campaigns over goal.
3. **Do this first** - at most 3 lines: owner · action · named campaigns or categories with old -> new values · number.
4. **Opportunity / Challenge** - one line each, with a number.
5. **Where the money goes** - raise / lower / flag / not placed, TACOS now and after, top 10 each; AI managed list.
6. **Where each category sits** (2x2 chart) and the **Scorecard** (play, note, timing, next skill).
7. **Actions**, **Fair peer goals**, **Fix the data first**, **Notes** (limits and the not-checked line).

Owners: **Ad manager** (budgets, bids, SB / SD), **Category manager** (listing, images, A+), **Sales** (price, promo, stock).

### Step 5 - Hand-off to execution (only after the user confirms)

`change_list.csv` is the plan. Only rows with `ready = yes` may be sent, and only after the user confirms them in any
language ("confirm", "go ahead", or the same in their language) - a confirmation must name the rows or say "all ready
rows". Then follow [sparkx-edit-ads](../sparkx-edit-ads/SKILL.md) and its confirmation flow; `campaign` + `updateBudget`
always runs the platform's two-phase confirmation. Per `references/write-campaign.md` there:

| Field | From change_list.csv |
|---|---|
| `request.profileIds` | the `profileId` values of the batch |
| `request.data[].campaignId` | `campaignId` (internal id from `get_entity_metadata`, never the Amazon id) |
| `request.data[].profileId` | `profileId` |
| `request.data[].campaignType` | `campaignType` - **one campaignType per batch**; several profiles only within one country |
| `request.data[].budget.type` | `setTo` |
| `request.data[].budget.amount` | `budget.amount` (> 0, local currency) |

Lifetime budgets are outside this route (held in the CSV). After the write, read `dailyBudget` back with
`get_entity_metadata` and report what moved.

## Output

`report.html` (one page, works at 390px), `report.md`, `market_by_category.json`, `category_scorecard.json`,
`budget_room.json`, `change_list.csv` (columns: ready, move, profileId, campaignId, amazonCampaignId, campaignName,
campaignType, budgetType, dailyBudget_old, dailyBudget_new, budget.type, budget.amount, acos_14d, spend_14d,
out_of_budget_hours_per_day, extra_spend_week, extra_sales_week, when, reason, hold).

## Acceptance

- Every number comes from the scripts (or the hand-computed rules, said so); ratios recomputed from sums.
- Headline has a number; at most 3 first actions; every budget action names old -> new, the check date and the stop rule.
- Every peer comparison names the ad product, goal, category level and period; rows are never added or averaged.
- Missing data is named with what it blocks - "not checked", "no market data", the tool's `_status` - never 0.
- Nothing is written by this skill; `ready = no` rows are never sent.

## Exceptions and known limits

- **No usable peer row** (status `NO_PEER_BENCHMARK`, unknown goal, brand without rows) -> ad cost vs the account ACOS,
  said in the row.
- **Market search call refused** (missing `sqp:read` scope or the `MCP_tool_SQP_ABA` permission) -> run
  `category_scorecard.py` with `--market-unavailable "<missing permission>"` and no `--market`: every row says market
  data is not accessible (an access gap, not "no market data"), plays rest on peers and ACOS.
- **Peer call refused** (missing `benchmark:read` scope or the `MCP_tool_benchmark` permission) -> run
  `category_scorecard.py` with `--peer-unavailable "<missing permission>"` and no `--peer`: every row says peer data
  is not accessible (an access gap, never "no peers"), ad cost is read against the account ACOS.
- **Peer values restate**: Amazon re-pulls recent periods; quote the period used. Peer data has no daily grain.
- **Own value in a peer row** is the brand's total for every campaign in that brand x category x ad product x goal and
  includes halo sales: compare it with peers, never with one campaign or the console ACOS.
- **Market purchases** use 24-hour attribution, ads 7 days (SP) / 14 days (SB, SD): compare directions, not decimals.
- **Orders at stake** is an upper bound (what the page would sell at market conversion), not a forecast.
- **Budget minutes** are reconstructed by the platform: quote them as approximate.

## Test prompts

- "How are my categories doing vs the market and peers? I need next month's budget split." -> full report, plays, budget plan.
- "What ROAS target is fair for magnesium?" -> fair peer goals for that category (range, ACOS equivalent, level, period).
- "Raise budgets for Black Friday" during the event window -> plan only; promotion budgets go to sparkx-promo-prep / sparkx-promo-monitor.
- Vendor profile -> no SQP: plays from peers and ACOS, every row marked "no market data".
- See [`references/golden-tests.md`](references/golden-tests.md).
