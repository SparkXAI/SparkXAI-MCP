# Scenarios

Every Diagnose run starts with one planning line, even when the answer is "no SQP needed".
(A single number or table is `sparkx-query-market-data`, not this skill.)

> **Market data: use / conditional / not used - reason.**

Not using market data is allowed; not considering it is not. (In Insight Agent testing, all 9
failed answers to open-ended reviews never listed the market as a candidate cause, and a loaded
skill was often never used.)

## When SQP is needed

| Ask | Market data |
|---|---|
| Names market, share, search volume, competitors, ceiling, "is it the whole market", events | **Use** |
| Explains a change in spend, orders, traffic or conversion | **Use** on the queries that moved most |
| Judges good or bad ("ACOS too high", "CVR poor") | **Use**: market CVR on the queries; peer Benchmark for the level |
| Keyword expansion / negatives / "which terms to grow" | **Use**: volume, market CVR, ABA top-3 |
| Open review ("audit", "review last 14 days", "what's wrong") | **Conditional**: find the top queries in the account first; pull SQP when a top query's clicks or orders fell > 20% week on week, or ACOS rose > 5 pt; otherwise say "no main query moved; this is an in-account review" |
| Pure data pull, list, settings, product how-to | **Not used** |
| One day or intraday | Use only the week containing it, as background |
| User names ABA / SQP / competitors | Use, overrides "not used" |

Order inside any scenario: find the queries, campaigns and products **in the account first**,
then pull SQP for those - never a full dump.

---

## S1 SQP audit

**Ask:** "audit my account", "SQP audit", "how am I doing in the market".

1. Scope line: store, 4 Sun-Sat weeks, sources, events excluded.
2. Coverage (Q3): advertised ASINs with SQP rows vs advertised ASINs (`get_ads_perf` productAd
   with spend in last 14 days); top-100 cap; missing weeks.
3. Position: purchase share and CVR index (brand CVR / market CVR) on the query set, from
   query-level rows. Click share vs impression share (direction only).
4. Leaks (Q2): orders lost at the conversion stage vs market CVR, and below the store's own
   CTR index; top 10 queries and the ASIN carrying each.
5. Quadrants (Q4/Q6): defend / scale / fix listing / cut-or-fix counts and the top rows.
6. Concentration (Q5).
7. Delivery gate (Q8) on queries where CVR trails market and 60%+ of market purchases ship
   same/next day.
8. Join: ad spend on the scale and cut-or-fix queries (`get_ads_perf` searchTerm), inventory
   days for the ASINs in the fix list (`get_entity_metadata` asin).

**Lead:** "Across N queries you hold X% of purchases; conversion runs at Y% of market. The
three biggest leaks are A, B, C (~N orders over 4 weeks)."

## S2 Why did sales drop?

**Ask:** "why did sales drop", "orders fell", "why is this category / brand down" - store,
category or brand level. One named ASIN goes to `sparkx-asin-deep-dive`.

1. **Confirm the drop and locate it.** Store daily `TotalSalesAmount`, `OrderCount`,
   `Sessions` (`get_ads_perf` asin, `select: ["date"]`), bucket into Sun-Sat weeks; flag event
   weeks. Then by parent (`asin.parent_asin_`) - rank parents by contribution to the change.
   If the premise is wrong (sales did not fall), say so with the numbers, then explain what
   really moved.
2. **Split each top parent's change** into sessions x unit session % (conversion) x price:
   - Sessions down, conversion flat -> traffic problem -> step 3.
   - Conversion down -> step 4.
   - Price up, Buy Box down, unavailability or stockout -> step 5.
3. **Traffic: me or the market?** For the parent's top queries (by brand purchases), SQP prior
   vs current: market search volume and purchases vs advertised-ASIN impressions and purchase
   share -> Q1 verdicts. In parallel, ad spend and impressions for the same weeks.
   - Market down, share flat -> **demand** ("the category shrank").
   - Market flat/up, share down, ad spend down -> **own traffic cut** -> step 6.
   - Market flat/up, share down, ad spend flat -> **lost share** (competitor, price, listing) ->
     ABA top-3 / SOV next.
4. **Conversion:** brand CVR vs market CVR now vs before on the same queries; if the market
   CVR fell too it is seasonal / market; if only yours fell, check price, Buy Box, reviews,
   delivery gate (Q8).
5. **Availability:** `get_entity_metadata` asin inventory and days of cover; `BuyBoxPercentage`,
   `UnavailabilityRate`; price vs market median purchase price (only with coverage).
6. **What changed:** `get_operation_log` on that parent's campaigns (resolve ids through
   productAd -> adGroup), the drop window +-7 days: budgets, pauses, bids, placement, AI-group
   target or personality. Separate people, AI and Amazon-side changes.

**Lead:** one of five causes, with the number: market demand / lost share / own traffic cut /
conversion / availability-price. Then the evidence table (before, after, change), then the
fix and who owns it.

## S3 KPI got worse - explain it to the client (Q9)

**Ask:** "ROAS dropped", "ACOS is up", "what do I tell my client / boss".

1. The KPI change from ads data (same Sun-Sat weeks).
2. Demand index on a **fixed basket** of the client's top queries present in both periods:
   search volume and market purchases change.
3. Brand purchases change and purchase share change on the same basket.
4. If demand fell more than the brand: "you outran a shrinking market"; if demand rose and
   share fell: say it plainly - it is a share loss, and give the fix.
5. Peer benchmark ROAS / CPC direction for the same weeks at brand level (`rules.md` section 7):
   did the peer group move too. Skip when the row's status is `NO_PEER_BENCHMARK`.

**Lead (exec):** three numbers for the meeting - market -x%, you -y%, share from a% to b% -
and one decision.

## S4 Fix first this week (Q2)

Lost orders per query = conversion stage (`clicks x (market CVR - your CVR)`, when positive) +
click stage (`impressions x (store median CTR index x market CTR - your CTR) x your CVR`, when
positive). ATC is not added (it is inside purchase); use it to locate the leak: ATC rate near
market but CVR low -> after the cart (price, delivery, reviews); ATC rate low -> detail page.
Rank, group by parent ASIN and stage, show the top 5-10 with orders at stake. Orders, never money.

## S5 Where can I grow / add budget (Q6)

Candidates = "scale" quadrant (purchase share below the store median, CVR at or above market,
20+ clicks), sorted by market purchases. Join ad ROAS / ACOS for the same queries
(`get_ads_perf` searchTerm). Both must hold: efficiency (ROAS at or above the store's target)
and room (low share, large market). Concentration (Q5) names the next 20 queries as the pool.
No bid values here: offer Plan mode for the category (`plan-mode.md`) to size the moves.

## S6 Did my change work? (Q7)

From the change log, the change and its week. Compare 2-4 weeks before vs after: ad
impressions (aligned weeks) vs SQP impression share and market impressions. "Bought volume, not
share" when impressions rose with the market; "bought share" when share rose.

## S7 New product traction

Weekly purchase share on the product's core queries (top queries by its impressions) for the
weeks since launch; sibling ASIN on the same queries; market CVR as the bar. Verdict: gaining /
flat / stalled, with the week it changed. A new ASIN only enters SQP once it has 14 days of ad
spend.

---

## Role playbooks (from the SparkX SQP help center)

The help center has a guide per role. When the user says who they are, or the question
clearly belongs to one role, run that role's playbook. Every list below is computed by
`sqp_calc.py` (`use_cases`, `preset_counts`, `fix_first`, `quadrants`) or `title_audit.py`;
the joins name the MCP call. Read `rules.md` section 3 first: help-center signals that compare
click share with impression share are applied **relative to the store's usual ratio**.

### P1 Advertiser / ad manager - "which keywords do I bid up, cut or protect?"

| Help-center scenario | Computation | Join | Say |
|---|---|---|---|
| Bid up | `use_cases.bid_up`: CTR index >= 1.2 x store median, 500+ impressions, 5+ purchases, relevant, volume floor; non-branded first | `get_ads_perf` searchTerm: ROAS on those queries vs store | "Click share runs well above impression share compared with your usual; ROAS supports more traffic" |
| Stop spending | Excess Impression Sink preset + `fix_or_cut` quadrant | ad spend on those queries | Fix the listing first; bid cuts are sized in Plan mode; negatives for spend with no orders go to `sparkx-search-term-diagnosis` |
| Protect | `use_cases.protect`: purchase share >= 20% | `get_ads_perf` searchTerm with `matchType_`: is there exact-match coverage? | "You win 1 in 5 purchases here; keep exact match on it" |
| Coverage gaps | `use_cases.coverage_gaps`: < 1% impression share, big and relevant; "a few sales" = organic or ads already carrying | ad spend on them (0 = not covered) | Start a low-bid test (Plan mode); check share again after 2-3 SQP weeks. Price a term the store never ran with `marketOnly` (see `sparkx-query-market-data`) |
| Scale | Under-Exposed Top Performer preset + `scale` quadrant | ROAS | Highest-confidence bid increase, once ROAS agrees |
| Diagnose a drop | S2 (Q1 verdicts) | change log | Market vs share vs own traffic |
| Peak season priority | `use_cases.peak_priority`: defend/scale, test before the event, niche hold, deprioritize | event date | "Test these N before <event>" |

### P2 Content / listing manager - "what words belong in my title, where does my page lose shoppers?"

1. **Title audit** - `title_audit.py --sqp <ASIN detail export or tool rows> --titles <titles.json>`.
   For each product: its top searches by volume and whether the title has the phrase as typed,
   the words in another order, or missing words. Lead with word-order findings (a bigger search
   matched only by word order while the title uses a smaller variant).
   **Never suggest** adding a competitor brand ("<other brand> ..."), another brand's name, or a
   health claim ("parasite cleanse", "cures ...") to a title: say "not a title candidate" and
   move on. Missing words go to bullets or backend search terms first.
   Titles: `get_entity_metadata(entity='asin')`, `select: ["asin","parentAsin","asinTitle"]`,
   filtered to the ASINs in the export (`filters: {"asin": [...]}`) - the full catalog pages
   500 rows at a time and repeats per SKU.
2. **Traffic but no sales** - High Loss Converter preset by ASIN; for each, the stage: ATC rate
   below market -> page (images, first bullet, A+, price vs market median); ATC fine, CVR low ->
   after the cart (reviews, delivery, price) or a long decision (24h window).
3. **Did the update work?** - S6 with the publish week; expect CTR to move first after a title
   change, ATC rate first after images / A+.
4. **Price check** - market median purchase price vs `asinPrice` (state coverage).
5. **Which ASINs first** - High Click, Low Cart preset sorted by brand impressions (needs ATC
   columns; otherwise say the export lacks them and use High Loss Converter).

### P3 Category manager - "where is demand, and how much of it do we hold?"

1. Landscape: top relevant searches by volume, with impression and purchase share.
2. White space: `coverage_gaps` with market CVR above median (real buying intent).
3. Share trend: S3 / Q1 over 8 weeks on the top 20 searches.
4. Sub-segments: group searches by theme words the user gives (or the obvious modifiers:
   organic, kids, bulk, flavour, form) and sum volume and purchases per group; compare
   purchase share across groups. Searches have no category field - always theme groups.
5. Seasonality: weekly volume for the top 20 searches over 12 weeks; name the spike weeks.
6. Funnel vs market on the key searches (CTR relative to the store's usual, ATC and CVR vs
   market).

### P4 Agency account manager - "triage many clients fast, give each one action"

Per account, in this order, and stop at the first that fires:

| Signal | One action this week |
|---|---|
| High Loss Converter on a top-10 search | Fix the listing before adding spend |
| Under-Exposed Top Performer with good ROAS | Raise bids there |
| Excess Impression Sink | Pull back and fix conversion |
| Nothing fires | Report purchase-share trend on the top 20 searches |

Market share scorecard for the client: top 20 searches by volume -> volume, impression,
click and purchase share, change vs prior period (needs two periods). Offer the one-page
report (`reports.md`). For many stores, one row per store: purchase share, CVR index, orders
within reach, the one action.

### P5 New product launch - "which keywords, what to expect, is it working?"

1. Entry keywords (pre-launch, using searches the brand already sees in the category):
   `use_cases.keyword_tiers` - title_must (high volume, high market CVR), broad_only (high
   volume, low CVR), backend_exact (lower volume, high CVR).
2. Benchmarks: market CTR, CVR and median purchase price on those searches - "expect to be
   below these in weeks 1-4".
3. Traction: S7 milestones - week 1 appears in SQP (needs 14 days of ad spend), week 2
   impressions on target searches, week 4 CTR vs the store's usual, week 6 purchase share,
   week 8 Under-Exposed Top Performer, week 12 first 4 vs last 4 weeks.
4. Fragmented vs dominated searches: ABA top-3 conversion share on weekly rows (check each
   top ASIN is not the store's own).
5. When to scale: CTR near your usual and CVR approaching market -> scale; CVR deeply below ->
   fix first; Under-Exposed Top Performer -> scale now.

---

### P6 Brand owner - "why does brand awareness matter, and is generic traffic worth it?"

1. Run `sqp_calc.py` with `--brand-terms` (own names and misspellings) and
   `--competitor-terms @competitor_brands.txt` (a list the user confirms; owned brands removed,
   `brand_candidates_to_confirm` reviewed). Read `brand_segments`.
2. Pull the search-term ad totals by type (`rules.md` 3d): CPC, ROAS, ad sales per order.
3. Answer in this order: generic searches carry the volume but shoppers trade down (negative
   buy-vs-click price) and clicks cost the most; other brands' names show shoppers paying up
   for the name they typed and the store converting below market there; own-brand searches
   convert, are won at a high share and cost the least per click.
4. Action: brand building (Sponsored Brands / video with the brand story on top generic
   searches, own-brand ads always on), measured by own-brand ad clicks and CPC. Conquesting
   other brands' names only where the store converts at market or better.
5. Say once: SQP brand numbers are organic + paid; if the export undercounts brand-name
   searches, size branded demand from the ad report.

## Specific questions

| # | Question | Computation (`sqp_calc.py`) | Needs |
|---|---|---|---|
| Q1 | Why did my share drop? | Per query: g_brand = purchases t1/t0 - 1, g_market likewise -> verdicts: real loss (you down, market up), growing slower than market, both down you fell faster, category shrinking you outran, taking share, growing faster | 2 periods |
| Q2 | What to fix first? | S4 | 1 period |
| Q3 | Why no data on this query? | (a) market volume ~0 -> no demand; (b) market rows exist, advertised-ASIN columns empty -> no ASIN with 14-day spend appeared; (c) unsupported marketplace or Vendor profile; (d) the week is in `missingWeekEnds` | 1 period |
| Q4 | Cut or fix this query? | CVR index + market behaviour: market CVR low too -> cut (the shelf doesn't convert); only yours low -> fix listing; market ATC high, CVR low -> long consideration, change tactic not bid (24h window undercounts); market volume falling for 8 weeks -> cut and don't retest. Needs ad spend from `get_ads_perf` searchTerm | 1 period + ads |
| Q5 | Is my traffic healthy? | Top 10 queries' share of my purchases vs their share of market purchases; next 20 queries' market share and my share there | 1 period |
| Q6 | Add budget here? | S5 | 1 period + ads |
| Q7 | Did my change work? | S6 | 2 periods + change log |
| Q8 | Why is my CVR below market? | First rule out: share of market purchases that ship same/next day (>= 60% = delivery gate if you are not that fast), price vs market median (with coverage), Buy Box | detail export or tool delivery fields |
| Q9 | Explain a KPI drop | S3 | 2 periods + ads |

Market behaviour classes (from market rates only, relative to the query set's median):
high CTR + high CVR = high intent (title, exact, defend); high CTR + high ATC + low CVR = long
consideration; high CTR + low ATC + low CVR = browse (broad, keep out of title); low market CTR
= nobody on the shelf earns the click (an opening, not noise).
