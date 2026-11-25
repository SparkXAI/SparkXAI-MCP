---
name: sparkx-sqp-insight
description: 'Amazon SQP read against the market, two modes. Diagnose (default, read-only): SQP audit, why store / category / brand sales or share dropped, KPI story for a client, fix-first, did a change work, launch traction, branded vs generic searches, role playbooks, one-page HTML report. Plan (one category): asks goal, budget and ACOS goal, sizes bid raises and cuts, new exact keywords, top of search, budgets and paused tests plus listing tasks; writes only confirmed rows via the edit skills. Use for "SQP", "market share", "why did sales drop", "explain to my client". Not for one SQP / ABA / peer number (sparkx-query-market-data), one ASIN (sparkx-asin-deep-dive), negatives or harvesting (sparkx-search-term-diagnosis), ASIN tiers (sparkx-product-diagnosis), recaps (weekly / monthly report), all-category budgets (sparkx-category-scorecard), promotions (sparkx-promo-prep).'
metadata:
  version: 1.0.1
---

# SQP Insight

## Scope: one SQP skill, two modes

SQP (Search Query Performance) is the only data that reads every other number **against the
market**: impressions, clicks, add-to-carts and purchases for the store's advertised ASINs and
for all of Amazon on the same search, by Sunday-Saturday week. This skill joins it with the
store's ads, metadata and change log.

| Mode | When | Writes |
|---|---|---|
| **Diagnose** (default) | audit, sales or share drop at store / category / brand level, KPI story, fix-first, verify a change, launch traction, brand vs generic searches, role playbooks, one-page report | never |
| **Plan** | the user wants a plan for one category: grow, improve efficiency, or both, sized to a budget | only rows the user confirms, through the owning write skill |

Pick the mode from the ask. "Where should the money go in <category>", "lower ACOS in
<category>", "build me a plan", "apply it" -> Plan. Everything else -> Diagnose; a diagnosis may
end by offering Plan mode for one category.

### Boundaries

| The ask | Goes to |
|---|---|
| One number or table from SQP / ABA / peer ("my purchase share on X last week", "search volume for these terms", "peer ROAS median") | `sparkx-query-market-data` |
| One named ASIN ("what happened to B0XXX", "why did this product drop") | `sparkx-asin-deep-dive` |
| Negatives for spend with no orders, harvesting search terms into exact | `sparkx-search-term-diagnosis` |
| Which ASINs have problems, product tiers | `sparkx-product-diagnosis` |
| Weekly / monthly recap | `sparkx-weekly-ads-report` / `sparkx-monthly-ads-report` |
| Budget direction across all categories, peer targets per category | `sparkx-category-scorecard` |
| From 7 days before a retail event to its end | `sparkx-promo-prep` / `sparkx-promo-monitor` (Plan mode still plans, never writes) |

### Tools and dependencies

| What | Tool | Owning skill - read its rules there |
|---|---|---|
| SQP + ABA rows | `get_market_search_perf` | [sparkx-query-market-data](../sparkx-query-market-data/SKILL.md) (`references/sqp-aba.md`) |
| ABA market demand: rank band, direction, top-3 concentration | `get_market_search_perf`, a SECOND pull with `factEntity: marketSearchQuery` and `aggregate: false` - `marketAsinQuery` carries no ABA | same (`references/data-sources.md` section 1b) |
| Brand peer benchmark | `get_peer_benchmark` | [sparkx-query-market-data](../sparkx-query-market-data/SKILL.md) (`references/peer-benchmark.md`) |
| Sales, sessions, ad results by campaign / keyword / target / search term / placement | `get_ads_perf` | [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md) |
| Internal ids, bids, states, categories, budgets and budget usage, AI groups, placements | `get_entity_metadata` | [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md) |
| What changed | `get_operation_log` | [sparkx-query-operation-log](../sparkx-query-operation-log/SKILL.md) |
| Plan mode: bids, keywords, budgets, top of search | `batch_update_ads` | [sparkx-edit-ads](../sparkx-edit-ads/SKILL.md) |
| Plan mode: paused single-keyword test campaigns | `create_sp_sb_campaign` | [sparkx-create-campaign](../sparkx-create-campaign/SKILL.md) |
| Plan mode: suggestions for campaigns in AI managed groups | `save_sp_sb_ai_managed_group` / `edit_sd_ai_managed_group` | [sparkx-edit-ai-group](../sparkx-edit-ai-group/SKILL.md) |

> **Dependency - install these 7 skills next to this one** (sibling directories under your
> skills root): the 4 read skills above (`sparkx-query-market-data`, `sparkx-query-ads-performance`,
> `sparkx-query-entity-metadata`, `sparkx-query-operation-log`) for both modes, plus the 3 write
> skills (`sparkx-edit-ads`, `sparkx-create-campaign`, `sparkx-edit-ai-group`) for Plan.
> Auth, paging, date limits and currency rules are in the read skills'
> `references/platform-notes.md`. Write rules (payloads, confirmation, read-back) live in the
> write skills and are not repeated here.

| Reference | Read it when |
|---|---|
| [`references/rules.md`](references/rules.md) | **Always**, before quoting any SQP number: metric rules M1-M8, sample gates, red lines |
| [`references/data-sources.md`](references/data-sources.md) | Pulling SQP rows (which factEntity, scope, weeks) and joining ads / metadata |
| [`references/scenarios.md`](references/scenarios.md) | Diagnose: scenarios S1-S7, role playbooks P1-P6, specific questions Q1-Q9 |
| [`references/output.md`](references/output.md) | Writing a Diagnose answer: exec vs operator, wording, confidence |
| [`references/reports.md`](references/reports.md) | The user wants something to present or share: the one-page HTML report |
| [`references/plan-mode.md`](references/plan-mode.md) | Plan mode: questions, plan rules PL1-PL14, write routes, confirmation, report |
| [`references/golden-tests.md`](references/golden-tests.md) | Changing this skill: the regression set |

| Script | Does |
|---|---|
| [`scripts/sqp_rows.py`](scripts/sqp_rows.py) | Loads tool JSON or exports into one row schema. The only place SQP columns are named |
| [`scripts/sqp_calc.py`](scripts/sqp_calc.py) | Every Diagnose calculation -> `sqp_summary.json` |
| [`scripts/title_audit.py`](scripts/title_audit.py) | Titles vs the searches each product gets (P2) |
| [`scripts/sqp_report.py`](scripts/sqp_report.py) | One-page HTML report from the summary and a short narrative |
| [`scripts/pick_category.py`](scripts/pick_category.py) | Plan Step 1 default category when the user has no preference |
| [`scripts/sqp_plan.py`](scripts/sqp_plan.py) | Plan mode: applies PL1-PL14 in code, emits route-ready rows (never writes) |
| [`scripts/test_sqp_insight.py`](scripts/test_sqp_insight.py) | Executable tests (synthetic data) |

### Requirements

Python 3. `sqp_rows.py`, `sqp_plan.py`, `title_audit.py`, `pick_category.py` and the tests use
the standard library only; `sqp_calc.py` and the HTML report need **pandas**; reading `.xlsx`
exports needs **openpyxl**. In a client that cannot run code, answer from the tool output with
the same rules (rates from summed counts, market counted once per search and week, the gates and
plan rules as written), label the answer "computed by hand, not by sqp_calc / sqp_plan", keep
it to a few searches, and give the script path so it can be rerun.

## Output Language: Always Match the User, Never Hard-Code Chinese or English

**The worked examples and output templates below are written in English, but they are structural
illustrations, not literal text to copy verbatim.** Generate the actual report in the user's
language, including section headers and KPI labels.

When calling `get_ads_perf`, also set the `language` parameter (`zh`/`en`/`ja`) to match the
customer's language. **`get_entity_metadata` has no `language` parameter** - localize its enum
values using the returned `{field}Text` companion fields, or `sparkx-query-entity-metadata`'s
[`enum-i18n.md`](../sparkx-query-entity-metadata/references/enum-i18n.md) where an enum has no
`Text` companion.

This skill has a renderer, which the other report Skills do not, so one extra rule applies:
**the markdown report is yours to write, the HTML one-pager is the script's.** Write the markdown
in the user's language, copying every figure from the JSON the scripts produced - never recompute
one, never round one again. When the user wants something to share, run the renderer with
`--lang en|zh|ja` to match; it localizes its own headings, table headers, legend, chart labels,
plays, peer positions and the reason behind each row, and it prints amounts in the store's
currency (`--currency` overrides what it reads from the peer rows). Accept a confirmation in any
language.

For the HTML, the narrative's top level stays English and `i18n` carries `zh` / `ja`
(`references/reports.md`); a language with no `i18n` block renders as English prose under
translated labels, so fill it or do not offer that language. `--lang` also decides which language
the page opens in.

## Principles

1. **Market first, then me.** Every SQP finding is relative: my share, my rate vs the market
   rate, my growth vs market growth. A number with no market comparison is not an SQP finding.
2. **Computation, not judgement.** Ratios, losses, quadrants, verdicts and plan rows come from
   the scripts. Quote their output files.
3. **Rates from counts, never averaged** (M1-M3). Tool rates are percentages (3.2 = 3.2%); the
   scripts recompute every rate from counts anyway.
4. **Sample before verdict.** Use the tool's `*LowSample` flags; a cut / fix / scale verdict on
   one search needs 20+ store clicks. Below that a search is "insufficient sample", never dropped.
5. **Say what SQP cannot see**, once per answer: no campaigns, spend, revenue, placements,
   competitor names or serving status.
6. **SQP brand numbers are organic + paid.** Never call them "your keywords" or ad results.
7. **Three CTRs.** Market CTR, advertised-ASIN CTR and ad CTR have different denominators.
   Compare CVR with the market; compare CTR with the store's own usual CTR index.
8. **Market data is a planning decision.** Every Diagnose run states "Market data: use /
   conditional / not used - reason" before pulling.
9. **Diagnose never writes. Plan writes only confirmed rows**, each through its owning write
   skill with that skill's pre-read, confirmation and read-back.

## Workflow - Diagnose

### Step 0 - Store, weeks, events

- `get_user_authorized_context`. SQP covers **Seller** profiles in US, CA, UK, DE, FR, IT, ES
  and JP only. A Vendor profile or another marketplace: say SQP is not available there (a
  coverage gap, not a finding) and offer the ads-only skills (`sparkx-weekly-ads-report`,
  `sparkx-search-term-diagnosis`, `sparkx-product-diagnosis`). One store per run.
- Weeks are Sunday-Saturday. Default window: the last 4 complete weeks; for "what changed",
  those 4 vs the 4 before (one 8-week pull split with `--split-at`).
- Check the window for retail events: a one- or two-day spike in daily `TotalSalesAmount`.
  Label the week, keep it out of the baseline, and ask the user to confirm.

### Step 1 - Get SQP rows (`data-sources.md`)

1. Write the planning line (`scenarios.md`). Find the searches, products and campaigns in the
   account first; pull SQP only for those (always pass `searchQueries` or `asins`).
2. `get_market_search_perf`, weekly rows, saved as JSON. Relay `missingWeekEnds`,
   `meta.truncated` and the response notes.
3. Exports only when the user supplies files or the tool is unavailable: ask which weeks each
   file covers.

### Step 2 - Route the question (`scenarios.md`)

| User says | Scenario |
|---|---|
| audit, SQP audit, "how am I doing in the market" | **S1 Audit** |
| why did store / category / brand sales, orders or share drop | **S2 Sales-drop root cause** |
| ROAS / ACOS / TACOS got worse, explain to client or boss | **S3 KPI narrative** |
| what to fix first, where am I losing orders | **S4 Fix-first** |
| where can I grow, which searches deserve more | **S5 Grow** (offer Plan mode for the category) |
| did my change work | **S6 Verify** |
| new product / launch traction | **S7 Launch** |
| names a role or a role task (bid up / protect, title audit, category white space, agency triage, launch keywords) | **Role playbooks P1-P5** |
| branded vs generic vs other brands' names, "why brand awareness matters" | **P6 Brand owner** |
| a single specific question | Q1-Q9 |

Ambiguous ("look at my SQP") -> S1, then offer S2 / S4. At most one clarifying question before
a first answer.

### Step 3 - Compute and join

- `python scripts/sqp_calc.py --current <files> [--prior <files> | --split-at <date>] --out <dir>`;
  read `sqp_summary.json`, including `notes` and `coverage`.
- Pull the MCP signals the scenario names. Rebuild ads data from **daily** rows into the same
  Sunday-Saturday weeks before comparing.
- Map ASINs through `get_entity_metadata(entity='asin')` before joining SQP to ads data.

### Step 4 - Answer (`output.md`), report on request (`reports.md`)

Conclusion first with its number, then evidence, actions with owners, and the one-line "what
SQP cannot tell here". For something to present or share, build the one-page report.

## Workflow - Plan (`plan-mode.md`)

1. **Ask** (at most 4 questions in round 1): category, goal (grow / improve efficiency /
   both), budget (same / +x / -x with the dollar value), ACOS goal. Brand names to protect are
   pre-filled and confirmed in the same card or in round 2. Defaults stated once.
2. **Pull** for that category: SQP (`marketAsinQuery` for its ASINs), keyword / target and
   campaign results, metadata with budget usage, AI groups, placements, search terms, and the
   operation log for the last 14 days (one entity per call).
3. **Compute**: `scripts/sqp_plan.py` -> `plan.json` + `plan_<lang>.md`. Never build rows by hand.
4. **Show** the plan; ask which numbered rows to run. Anomalies, tests and AI-group suggestions
   need their own yes.
5. **Execute** confirmed rows only, through the owning write skill: pre-read, platform preview
   where the route has one, read-back; report applied / not applied / unknown per row and the
   check date. Inside a promotion window nothing is written.

## Data boundaries

- Only ASINs with ad spend in the last 14 days are in SQP; at most 100 searches per ASIN per
  week. An empty brand column is "no advertised ASIN appeared", not 0.
- SQP purchases are counted within 24 hours of the click; ads use 7 days (SP on a Seller
  profile) or 14 days (SP Vendor, SB, SD) - see `sparkx-query-ads-performance`
  `references/field-reference.md`. Never subtract one from the other.
- No brand revenue in SQP: money comes only from `get_ads_perf`.
- Row caps: the tool returns up to 100,000 rows per call and sets `meta.truncated`; the Search
  Term main-page export caps at 10,000 rows.
- `asinBsrCategoryName` / `parentAsinBsrCategoryName` is the BSR category, not a full browse
  tree; Plan mode groups by it.

## Error handling

| Situation | Handling |
|---|---|
| `missingWeekEnds` not empty | Name the weeks; missing is not zero; never average across them |
| `meta.truncated: true` | Narrow searches, ASINs or weeks and pull again; never quote truncated totals as complete |
| `get_market_search_perf` refused (missing `sqp:read` scope or `MCP_tool_SQP_ABA` permission) | Access gap, not "no SQP data": name the permission and how to get it (admin / re-authorize); do not retry. Diagnose and Plan can run only on exports the user supplies; otherwise stop the SQP part and offer the ads-only skills |
| `get_peer_benchmark` refused (missing `benchmark:read` scope or `MCP_tool_benchmark` permission) | Access gap, not missing data: name the permission, continue without peers (`sparkx-query-market-data`) |
| Export without week labels | Ask for the weeks; do not guess from file names |
| Only one period, change question | Answer the cross-sectional part; pull the prior 4 weeks |
| Brand CTR above market on nearly every search | Expected (different denominators): use the own-median CTR index |
| User says SQP does not match Seller Central | `rules.md` section 6: independent reports, 14-day spend rule |
| Question about one day | The Sunday-Saturday week containing it, as background |
| `get_ads_perf` `unknown field` | Check that skill's `field-reference.md`; the parent field is `asin.parent_asin_` |
| Vendor profile / unsupported marketplace | Diagnose: SQP unavailable, offer ads-only skills. Plan: ads-only plan, labelled (no raises, keywords, top of search or tests) |
| A write returns `ambiguous_write` | Read back first; never retry blind (owning skill's rules) |

## Not covered

See "Boundaries" above. Also: writing the listing itself (this skill names the fix and the
evidence), Sponsored Display search analysis (no search terms), competitor identity (SQP has
none; ABA top-3 via `sparkx-query-market-data`).
