# Golden tests

Run before every release of this skill. Two layers:

1. **Executable** - `python -I scripts/test_sqp_insight.py -v` (synthetic data, any working
   directory). 25 tests; all must pass. `sqp_calc` / report tests skip if pandas is missing -
   a skip is not a pass for a release.
2. **Answer review** - the conversations below, run in the user's language and in English.
   Pass bar: numbers match the script outputs 100%; verdicts match the reviewed answer on 85%+;
   red lines 0 failures. Shares and rates use last-digit tolerance.

Numbering: D = Diagnose (D1-D44), PG = Plan (PG1-PG20), RL = red lines (RL1-RL10), T = triggers.
Rules are M1-M8 (`rules.md`) and PL1-PL14 (`plan-mode.md`); scenarios S1-S7, playbooks P1-P6.

## 1. Executable tests (`scripts/test_sqp_insight.py`)

| Test | Checks |
|---|---|
| TestRows (4) | tool JSON (both factEntity variants, real field names) -> canonical rows; `*LowSample` kept; market-only row stays empty (not 0); `missingWeekEnds` and `meta.truncated` become notes; weeks are added, not maxed; market counted once per search and week across ASINs; Windows paths and `@date` labels |
| TestCalcEndToEnd (1) | `sqp_calc.py` on tool JSON with `--split-at`, run as `python -I` from outside the skill |
| TestPlanRules (18) | category figures from its own ASIN rows only; unmatched category or no own-ASIN rows -> no SQP-driven moves; truncated SQP -> SQP-driven rows not executable; end to end with route-ready payloads (internal ids, `setTo` with `previousBid`); grow never lowers; efficiency never raises; -20% / -15% cut steps; own brand never cut; conversion 0.70x -> no raise + owner task; AI group -> no write + group suggestion with the rescale warning; changed in 14 days -> held; typo bid -> -20% default with the set-to-CPC alternative; budget raise reads `outOfBudgetMinutes`, null -> not checked; budget cut; test campaign uses `budget`, `state: paused`, ASIN + SKU; promotion window -> nothing executable; Grow + same budget funds no raises; Vendor -> ads-only; UTF-8 output |
| TestReportAndCategory (2) | report renders with `{store}` and `--brand sparkx` / `none`, plan block from `plan.json`, no real store name; default category from the top-spend parent |

## 2. Diagnose

### Scenario chains

| # | Question | Pass when |
|---|---|---|
| D1 | "Audit my SQP for the last 4 weeks." | S1; planning line; leads with share + conversion index + top 3 leaks; names one gap |
| D2 | "Why did sales drop in my vitamin category?" | S2 at category level; splits sessions vs conversion vs price; market vs share verdict |
| D3 | "Why did spend decline after <date>?" when it did not | Corrects the premise with numbers, then explains the real change |
| D4 | "ROAS fell this month - what do I tell the client?" | S3; exec version; 3 numbers; fixed basket; peer direction only at brand level |
| D5 | "What should I fix this week?" | S4; conversion vs market + own-median CTR; grouped by parent; orders, not money |
| D6 | "Where can I grow?" | S5; efficiency and room both required; no bid values; offers Plan mode for one category |
| D7 | "Did last week's bid increase on <campaign> work?" | S6; aligned weeks; volume vs share verdict |
| D8 | "Is my new <product line> gaining ground?" | S7; weekly share curve; notes the 14-day ad-spend rule |
| D9 | "What happened to B0XXXXXXXX?" | Routes to `sparkx-asin-deep-dive` |

### Calculation traps

| # | Question | Pass when |
|---|---|---|
| D10 | Share of 3 ASINs on one search | Market counted once per search and week (M3) |
| D11 | "What's my CTR vs the market?" | Explains the three CTRs; no "x% of the market" CTR claim |
| D12 | 4-week CVR on a search | Sums then divides; never averages weekly CVR (M2) |
| D13 | "Which search converts best?" | Low-sample rows flagged (tool flag) and sorted last |
| D14 | "Why no data for <search>?" | No demand / no advertised ASIN / unsupported / missing week |
| D15 | "Cut or fix these 12 searches?" | Four classes; insufficient sample listed separately |
| D16 | "Why is CVR below market on <search>?" | Delivery gate, price coverage, Buy Box first |
| D17 | Peer ACOS for the brand | Tool percentiles used as given (no inversion); `NO_PEER_BENCHMARK` -> "no peer benchmark"; range over P50 when wide |
| D18 | Tool response with `missingWeekEnds` | Names the weeks; missing is not zero |
| D19 | Tool response with `meta.truncated: true` | Narrows and pulls again; never quotes truncated totals as complete |
| D20 | marketSearchQuery rows only, product question | Says per-product splits need `marketAsinQuery`; no crash, no guessed product |

### Role playbooks and reports

| # | Question | Pass when |
|---|---|---|
| D21 | "Which keywords should I bid up?" | Relative CTR rule; relevant, non-branded first; ROAS joined; numbers only via Plan mode |
| D22 | "Which search terms belong in my title?" | `title_audit.py`; competitor names and health claims excluded; word-order finding stated |
| D23 | "Where is my category growing that I'm not capturing?" | Coverage gaps scoped to the store's categories; theme groups |
| D24 | Agency: "Triage these 3 stores" | One action per store from the triage ladder |
| D25 | "Which keywords for my new launch?" | Keyword tiers; ABA top-3 for concentration, own ASINs excluded |
| D26 | "How many High Cart, Low Purchase searches?" on an export without ATC | "Not available in this export", not 0 |
| D27 | Report row on a below-market search | Names the product carrying it and its price vs market, with the pack-size caveat |
| D28 | Coverage-gap list with 100K+ searches | Labelled head terms; never "cheapest to test" |
| D29 | Protect list contains another brand's name | Listed apart as conquest |
| D30 | "What is the opportunity worth?" | Orders x ad sales per ad order, labelled a ceiling |
| D31 | Every action in a report | Has where, when and a 2-week measure tied to a number on the page |
| D32 | Quadrant counts shown | Top searches per group plus the CSV download |
| D33 | "Why does brand awareness matter?" | Three search types with click vs buy price, share, conversion and ad CPC / ROAS per type |
| D34 | Export where own-brand ad clicks far exceed own-brand searches | Says the export undercounts branded demand |
| D35 | Any SQP brand figure in a headline | No "your own searches" in any language |
| D36 | Low-share, below-market group | Labelled "fix before more spend", never "cut" |
| D37 | Single-period report | Notes say no trend without the prior weeks |
| D38 | Report with `--brand none` | Store name in the header, no SparkX wordmark; `{store}` filled, never a fixed store name |
| D39 | Product with a very low conversion index | Shows its main searches, or says own-ASIN rows are needed |
| D40 | "Apply the actions" during Diagnose | Switches to Plan mode for one category; writes nothing from Diagnose |
| D41 | Spend with no orders found | Points to `sparkx-search-term-diagnosis`; no negatives proposed |

### Missing data

| # | Situation | Pass when |
|---|---|---|
| D42 | Export, no weeks given, change question | Asks for the weeks and the prior period; still answers Q2 / Q4 / Q5 |
| D43 | Search Term export of exactly 10,000 rows | Totals are a lower bound |
| D44 | Vendor profile | SQP unavailable (coverage gap); offers ads-only skills |

## 3. Plan

| # | Input | Pass when |
|---|---|---|
| PG1 | "Plan for Magnesium" with nothing else | Round 1 asks goal, budget (with $), ACOS goal - at most 4 questions; brands pre-filled for confirmation |
| PG2 | No category preference | Defaults to the top-spend parent's BSR category and says so once |
| PG3 | Goal Grow | No bid or budget decrease anywhere in the numbered rows (PL1) |
| PG4 | Goal Improve efficiency | No raise, new keyword, top of search or test; owner tasks listed first (PL1) |
| PG5 | Goal Both, budget +10% | Cuts and raises; budget fit shows room, savings, net change, unused room (PL13) |
| PG6 | Grow with "keep the same" | Says nothing pays for raises; offers Both or an increase |
| PG7 | Search converts 1.3x market, 5% share, exact keyword ACOS 14% vs goal 20%, 40 clicks | +10% raise with internal keywordId, previousBid, matchType (PL2) |
| PG8 | Grow, search converts 0.7x market | No raise; owner task (page and price, or brand reach); "grow" is answered with the listing path (PL3) |
| PG9 | Keyword ACOS 50% vs goal 25%, 50 clicks | -20%; 33% -> -15% (PL4) |
| PG10 | Broad keyword serving many terms, one term at 90% ACOS | Decided on the keyword's own ACOS, not the term's (PL4) |
| PG11 | Own-brand keyword at 60% ACOS | Never cut (PL5) |
| PG12 | Campaign in an AI group with AI on | No keyword, placement or budget row; suggests the group's target ACOS via `sparkx-edit-ai-group` with the rescale warning (PL10) |
| PG13 | Keyword changed 5 days ago | Held (PL6) |
| PG14 | Bid $10 vs CPC $1 | Anomaly, default -20%, set-to-CPC only as a separate confirmation; not in "run all" (PL7) |
| PG15 | Capped campaign under goal; another with `outOfBudgetMinutes` null | +20% budget on the first; the second "not checked" (PL8) |
| PG16 | Converting broad source, no exact keyword | `keyword.create` with `adGroupId`, exact, start bid capped at value per click; stated as applying on submit (PL11) |
| PG17 | Head term passing the market test with few ad clicks | Paused test campaign with `budget`, ASIN and SKU (PL14) |
| PG18 | Black Friday in 4 days | Plan shown, nothing written; points to `sparkx-promo-prep` / `sparkx-promo-monitor` |
| PG19 | User confirms rows 1 and 3 | Executes exactly those via the owning skills; pre-read, preview where available, read-back, per-row report |
| PG20 | Vendor profile | Ads-only plan, labelled; no raises, keywords, top of search or tests |

## 4. Red lines (refuse and redirect)

| # | Ask | Required |
|---|---|---|
| RL1 | "SQP purchases minus ad orders = organic?" | Refuse; direction-only checks |
| RL2 | "SQP doesn't match Seller Central - which is right?" | Explain both; no winner |
| RL3 | "Estimate monthly searches from the ABA rank." | Refuse; order of magnitude only |
| RL4 | "3 clicks, 0 orders - is conversion broken?" | Insufficient sample |
| RL5 | "What bid should I set on <search>?" in Diagnose | Direction only; offer Plan mode |
| RL6 | "How does this search perform in its category?" | No category on searches; behaviour class |
| RL7 | "Rank my searches by SQP Score." | Declines Score as a ranking |
| RL8 | "Which competitor took my share?" | No identity in SQP; ABA top-3, own ASINs excluded |
| RL9 | "Just apply everything" without a waiver in the user's own words | Ask; waiver follows `sparkx-edit-ads` |
| RL10 | "Archive the losers" | No archive from this skill; pause is the reversible choice, through `sparkx-edit-ads` on its own request |

## 5. Triggers

- **Should use this skill:** "audit my SQP", "why did sales drop in this category", "explain the
  ROAS drop to my client", "where should extra budget go in Magnesium", "lower ACOS in this
  category", "branded vs generic searches".
- **Should not:** "my purchase share on 'fish oil' last week" (`sparkx-query-market-data`);
  "what happened to B0XXXXXXXX" (`sparkx-asin-deep-dive`); "negative keyword candidates"
  (`sparkx-search-term-diagnosis`); "which ASINs have problems" (`sparkx-product-diagnosis`);
  "weekly report" (`sparkx-weekly-ads-report`); "where should next month's budget go across
  categories" (`sparkx-category-scorecard`); "get my ads ready for Black Friday"
  (`sparkx-promo-prep`).
