---
name: sparkx-monthly-ads-report
description: >-
  Generate a monthly ad performance recap for ads managers / account managers at month-end.
  Includes full-month KPIs (MoM + YoY), goal attainment, structural breakdown (campaign type /
  site / portfolio share), product analysis (Top ASIN changes, new products, long-tail), keyword
  analysis (Top keywords, new keyword opportunities, negative-keyword candidates), an issues list
  with attribution, and next-month structural recommendations. Use when the user says "出个月报",
  "月度复盘", "这个月表现如何", "monthly report". Not for weekly recaps (use sparkx-weekly-ads-report) or
  quarterly/QBR-level strategic review (use quarterly-ads-report, not yet built).
metadata:
  version: 1.0.3
---

# Monthly Ads Report

## Scope: This Is an Orchestration Skill, Not a New MCP Tool

This skill does **not** map to a single MCP tool of its own — it orchestrates three existing read tools, each already covered by its own skill:

- `get_ads_perf` → [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md)
- `get_operation_log` → [sparkx-query-operation-log](../sparkx-query-operation-log/SKILL.md)
- `get_entity_metadata` → [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md)

> **Dependency — install these three base skills alongside this one:** `sparkx-query-ads-performance`, `sparkx-query-entity-metadata`, `sparkx-query-operation-log`. Skills install as sibling directories under your current agent's skills root (`.claude/skills/<name>/` for Claude Code; the equivalent root for other agents — see the [supported-agents table](../../README.md)), which is exactly what the `../query-.../…` links above (and elsewhere in this doc) resolve against — if a base skill isn't installed there, those links won't resolve and this skill can't run. Install all three first.

**Read those three SKILL.md files first** (parameter formats, field-naming rules, the Ratio Metric Display Rule) plus [`references/platform-notes.md`](references/platform-notes.md) (auth flow, error handling, pagination, date-range limits, currency rules — shared by all three underlying tools). This document only covers logic specific to the monthly-report use case; it doesn't repeat what the three base skills already document.

This skill shares its overall shape with [sparkx-weekly-ads-report](../sparkx-weekly-ads-report/SKILL.md) (same underlying tools, same output-language and multi-store discipline) but goes deeper: AdGroup-level granularity, structural share analysis, product and keyword analysis, and a MoM+YoY baseline instead of WoW.

## Output Language: Always Match the User, Never Hard-Code Chinese or English

**The worked examples and output templates below are written in Chinese** (matching this product's primary customer base), but they are **structural illustrations, not literal text to copy verbatim**. Generate the actual report in whatever language the user asked in — section headers, KPI labels, everything. Do not assume the audience is Chinese-speaking just because this skill's own documentation and templates are.

When calling `get_ads_perf`, also set the `language` parameter (`zh`/`en`/`ja`) to match the customer's language, so returned enum companion text (e.g. `campaignTypeText`) is localized consistently with the rest of the report. **`get_entity_metadata` has no `language` parameter** — it's not in that tool's documented parameter list. Localize its enum values using the returned `{field}Text` companion fields, or `sparkx-query-entity-metadata`'s own [`enum-i18n.md`](../sparkx-query-entity-metadata/references/enum-i18n.md) if a given enum has no `Text` companion — don't pass `language` to `get_entity_metadata` expecting it to have the same effect as on `get_ads_perf`.

## When to Use

**Trigger phrases**: 月报, 月度复盘, 这个月表现如何, monthly report, recap this month

**User roles**: ads managers, account managers (client-facing)

**Core question**: how did this month perform, did we hit target, where are the problems, what's the plan for next month

**Not for**:
- Weekly recap → `sparkx-weekly-ads-report`
- Quarterly/QBR strategic review → `quarterly-ads-report` (not yet built)
- A specific question the user brings ("why did this one campaign's ACOS spike") → a dedicated analysis skill (not yet built), or the [ACOS root-cause investigation example](../sparkx-query-ads-performance/references/example-acos-root-cause-investigation.md)

## Input Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `profileIds` | array[long] | No | — | Target profile IDs. See "Resolving `profileIds`" below for the exact selection rules — don't default to "all stores" without checking those rules first |
| `month` | string (`YYYY-MM`) | No | Last full calendar month | The month this report covers. Always a **completed** month, not the current in-progress one |
| `monthlyTarget` | object | No | — | Optional KPI target for this month (a single metric+target+direction), e.g. `{"metric": "ACOS", "target": 25, "direction": "at_most"}` or `{"metric": "Spend", "target": 50000, "direction": "at_least"}`. `direction` is `at_least` (hit or exceed the target) or `at_most` (stay at or under it). Supplied by the user/account team — not retrievable from any tool |
| `compareBaseline` | enum | No | `mom+yoy` | `mom` \| `yoy` \| `mom+yoy`. **Controls only the KPI section (Step 3) baseline columns.** Structural analysis (Step 5) and product MoM changes (Step 6) are always month-over-month regardless of this setting — they always pull last-month data (2e/2g) |
| `outputFormat` | enum | No | `markdown` | `markdown` \| `structured_report` |

### Resolving `profileIds`

Always call `get_user_authorized_context` first to get the authorized `profiles` list, then apply exactly one of these cases:

1. **The user named specific store(s)** → resolve the name(s) against the authorized list and query only the matching profile(s).
2. **The user explicitly said "all stores" / "全账号" / equivalent** → query all authorized `profileIds`.
3. **The user didn't name a store, and there's only one authorized profile** → use it directly — there's nothing to ask.
4. **The user didn't name a store, and there are multiple authorized profiles**:
   - **5 or fewer** → you may default to using all of them.
   - **More than 5** → do not silently roll everyone up into one report. Hand the user the `profiles` list and ask them to pick one, several, or explicitly confirm "all stores" first.

Case 4's threshold exists because this is a customer-facing report: a silent multi-store aggregate can hide a single store's problem behind a healthy blended number, and it forces an unannounced USD conversion (see "Multi-Store and Currency" below) the customer didn't ask for.

**Determining whether to include an AI-managed section**: call `get_entity_metadata` (`entity: aiGroup`, filtered to the relevant `profileIds`; **add `filters: {"aiStatus": 1}`, or fully paginate — default page size is 100, so a running AI group sitting past page 1 would otherwise be missed and the section wrongly skipped**) — if any returned row has `aiStatus: 1`, include an AI-managed performance callout in the KPI section; otherwise omit it. **This check only decides whether to show the callout — it doesn't supply the callout's actual data.** For the content itself, add `AISales`/`AIACOS`/`AIROAS` to Steps 2a/2b/2c's existing `metrics` list (these are campaign-level-only metrics per the platform notes, which is already `factEntity: campaign` for these calls, so no separate call is needed) whenever the callout applies, and report those alongside the regular KPI table — don't include the callout with only a "yes, AI management is on" statement and no actual performance figures.

## Workflow

### Step 1 · Define Time Windows

- **This month**: the full calendar month named by `month` (default: last full calendar month) — `dateStart` = 1st of that month, `dateEnd` = last day of that month.
- **Last month (MoM baseline)**: the calendar month immediately before "this month".
- **Same month last year (YoY baseline)**: the same calendar month, 12 months earlier.

All three windows are single calendar months (28-31 days) — comfortably within the 90-day single-call cap, no window-splitting needed for any of them individually.

**⚠️ Full calendar months are not equal length — do not force them to be.** Per the shared platform rule: compare the two full calendar months as-is (don't truncate the longer one or pad the shorter one), and **explicitly note the day-count difference** to the user when it exists (e.g. "July has 31 days, June has 30"). If the user cares about rate/efficiency rather than raw totals, additionally compute each month's **daily average** (`total ÷ day count`) alongside the raw totals.

**⚠️ Check the YoY lookback against the 15-month cap.** Same-month-last-year reaches back up to 13 months from "this month" (1 month for MoM + 12 more for YoY) when `month` defaults to last month — comfortably within the 15-month lookback. But if the user explicitly requests a `month` further in the past, recompute the actual YoY lookback distance and confirm it's still ≤15 months before issuing the call; if it isn't, say so explicitly rather than silently returning an error or omitting the YoY column without explanation.

**T+2 data-delay check**: if `month` is very recently completed (e.g. the report is generated on the 1st-2nd of the following month), the last day or two of that month's data may not have finished processing. Check how many days have elapsed since the month ended; if fewer than 2, add an explicit note that the month's final days' figures may still shift slightly.

### Step 2 · Pull Data

The calls below are independent and can be issued in parallel. Every call needs `userContext` (non-empty string, ≤100 chars). Structure/product/keyword calls deliberately **don't** filter by `campaignState`/`asinIsDelete` etc unless noted — MoM/YoY comparisons need to see entities that existed in one period but not the other (see Step 6's new/disappeared bucketing, which applies the same way to Steps 5 and 7).

**a. This month, account-level KPIs**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "{this month start}",
  "dateEnd": "{this month end}",
  "metrics": ["Impressions", "Clicks", "Spend", "Sales", "Conversions", "ACOS", "ROAS", "CTR", "CVR"],
  "pageSize": 500,
  "userContext": "Monthly report - this month's account-level KPIs"
}
```
No dimension in `select` — global aggregate across all campaigns. **If the AI-managed callout applies** (per the check under "Input Parameters"), add `AISales`/`AIACOS`/`AIROAS` to this call's `metrics` (and the same-shape calls b/c) — don't request them unconditionally on every report, since they're only meaningful when AI management is actually active.

**b. Last month** (only when `compareBaseline` is `mom` or `mom+yoy` — skip entirely when `compareBaseline=yoy`) and **c. same month last year** (only when `compareBaseline` is `yoy` or `mom+yoy` — skip entirely when `compareBaseline=mom`) — identical shape to (a), `dateStart`/`dateEnd` shifted to each baseline window. Don't issue a call whose baseline the report doesn't need.

**d. This month, AdGroup-level (feeds structure + attribution)**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "adGroup",
  "dateStart": "{this month start}",
  "dateEnd": "{this month end}",
  "select": ["adGroup.adGroupId_", "adGroup.adGroupName_", "campaign.campaignId_", "campaign.campaignName_", "campaign.campaignType_", "portfolio.portfolioId_", "portfolio.portfolioName_", "profile.countryCode_"],
  "metrics": ["Impressions", "Clicks", "Spend", "Sales", "Conversions"],
  "pageSize": 500,
  "userContext": "Monthly report - this month's adGroup-level data for structure analysis"
}
```
**e. Last month, AdGroup-level** — same shape as (d), shifted back one month. `select` must match (d) exactly for a valid comparison.

**f. This month, Top ASINs**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "asin",
  "dateStart": "{this month start}",
  "dateEnd": "{this month end}",
  "select": ["asin.asin_", "asin.asinTitle_"],
  "metrics": ["TotalSalesAmount", "OrderCount", "TACOS"],
  "orderBy": [{"field": "TotalSalesAmount", "direction": "DESC"}],
  "pageSize": 500,
  "userContext": "Monthly report - this month's ASIN-level sales for product analysis"
}
```
**g. Last month, Top ASINs** — same shape as (f), shifted back one month, for MoM product comparison (Step 6).

**h. New-product identification**: `get_entity_metadata` (`entity: asin`). **`asinOpenDate` is NOT a filterable field** — asin's filterable fields are `asin`/`parentAsin`/`sku`/`asinBrand`/`asinTitle`/`asinBsr`/`asinPrice`/`asinInventoryStatus`/the eligibility flags/`asinIsDelete`/`productLine*` — so you can't filter the call by open date. Instead, pull the asin metadata (**fully paginate — loop `page` while `hasNextPage` is `true`; default page size is 100, so a catalog past one page silently truncates otherwise**), then read the returned `asinOpenDate` field and filter to this month's window **client-side**. `asinOpenDate` is a datetime-with-timezone string, e.g. `"2026-06-01 00:00:00 PST"` — not `YYYYMMDD`, and not the `YYYY-MM-DD` used by `dateStart`/`dateEnd` — so parse it and mind the **PST timezone** when judging whether an ASIN opened inside the month, to avoid month-boundary misclassification. (`YYYYMMDD` is `campaignStartDate`/`EndDate`'s format, not this field's.)

**i. Keyword-level performance**: `get_ads_perf` with `factEntity: target`, `queryType: keyword`, this month's window, `select` including `target.targetId_`/`target.targetText_`/`target.targetMatchType_`, metrics `Impressions/Clicks/Spend/Sales/Conversions/ACOS`.

**j. Search-term data (feeds new-keyword and negative-keyword candidates)**: `get_ads_perf` with `factEntity: searchTerm`, this month's window, `select` including `query_`/`matchType_`/`targetId_`/`adGroupId_`/`campaignId_`, metrics `Impressions/Clicks/Spend/Sales/Conversions/ACOS`.

**k. This month's operation log** (feeds Step 8's attribution): `get_operation_log`, this month's window, no `changeBy` filter (capture manual + AI + automation), `pageSize: 200`. **Check `truncated`** — if `true`, follow `sparkx-query-operation-log`'s "Getting a Complete Count" procedure (split into non-overlapping sub-windows) rather than treating one page as the full month.

**Step 2k as a whole is best-effort, not a hard dependency for the rest of the report.** If splitting into sub-windows still times out or keeps erroring, don't let it block the rest of the report from completing — produce Steps 3-7/9 normally and mark Step 8's attribution as "operation log data incomplete this month" (or similar, in the report's own language) rather than failing the entire report over one section.

**Fully paginate (d)/(e)/(f)/(g)/(i)/(j) before analyzing** — loop `page` while `hasNextPage` is `true`. **If full pagination across many profiles/entities would be impractical at scale**, you may fall back to a spend-ranked sample (top N by `Spend`/`TotalSalesAmount` via `orderBy` + a capped `pageSize`) instead of the full population — but this fallback **must be disclosed explicitly** in the relevant section (e.g. "structure breakdown based on top-spend sample, not full population"), stating concretely what was actually covered (how many profiles/entities, how many pages, whether `hasNextPage` was still `true` when you stopped), never silently presented as complete. **A degraded or failed section (structure, product, or keyword analysis) must not fail the whole report** — produce whatever sections do have complete data normally, and present only the affected section as partial/unavailable rather than aborting report generation entirely.

### Step 3 · Full-Month KPIs (MoM + YoY)

**Core KPIs**: Spend, Sales, ACOS, ROAS, Impressions, Clicks, CTR, CVR.

For each: this-month value, last-month value (if `compareBaseline` includes `mom`), same-month-last-year value (if includes `yoy`), and the % change against each baseline — computed independently per Step 3's zero-denominator rules below, never averaged across baselines.

**Zero-denominator handling** (same discipline as any period comparison): if the baseline period's value is `0` and this month's is nonzero, there's no valid percentage — report "N/A (no prior baseline)," never a fabricated large number or "+∞%". If both are `0`, report "flat / no activity."

**Ratio-metric display rule**: `ACOS`/`CTR`/`CVR` are confirmed pre-scaled ×100 — append `%` directly, don't re-scale. `ROAS`/`CPC`/`CPA` are plain ratios, no `%`. `TACOS`/other `*Rate` fields are unconfirmed scale — relay raw, no `%`, no assumed scale.

### Step 4 · Goal Attainment (if `monthlyTarget` supplied)

Compare the relevant KPI's actual this-month value against `monthlyTarget.target` — **the attainment formula depends on `monthlyTarget.direction`,** don't infer direction from the metric name alone:

- **`direction: "at_least"`** (hit-or-exceed a floor — typically `Sales`, `Conversions`, `ROAS`, or a *spend goal* meaning "make sure we deploy at least this much budget"): attainment `= actual / target × 100`; "exceeded" means `actual > target`.
- **`direction: "at_most"`** (stay at-or-under a ceiling — typically `ACOS`, `CPC`, `CPA`, or a *spend cap* meaning "don't blow past this budget"): attainment `= target / actual × 100`, or state it plainly as "under target" / "over target by X" rather than forcing a percentage that reads backwards — a lower `actual` than `target` is the good outcome here.

**`Spend` is genuinely ambiguous without `direction`** — it can mean either a budget cap (`at_most`: don't overspend) or a deployment goal (`at_least`: make sure the budget actually gets spent). Don't default it to either interpretation silently. If `monthlyTarget.direction` is missing for a `Spend` target specifically, ask the user which they meant, or state explicitly which assumption you're using and why, rather than guessing. `ACOS`/`CPC`/`CPA` and `Sales`/`Conversions`/`ROAS` are unambiguous enough that a missing `direction` can default to `at_most` and `at_least` respectively, but `Spend` should not get a silent default.

Report a plain-language verdict either way ("hit," "missed by X," "exceeded by X") consistent with the direction above. If `monthlyTarget` wasn't supplied, omit this section entirely rather than inventing a target or comparing against an arbitrary baseline.

### Step 5 · Structural Analysis

Using Step 2's (d)/(e) AdGroup-level data, compute **share of total Spend/Sales** (not just raw totals) for three breakdowns, each month independently, then compare the share shift MoM:

- **By campaign type** (`campaign.campaignType_`): SP / SB / SD share of total Spend and Sales.
- **By site** (`profile.countryCode_`): only meaningful when `profileIds` spans multiple stores/countries.
- **By portfolio** (`portfolio.portfolioId_`, displayed using `portfolio.portfolioName_`): rows with no portfolio should be grouped as "no portfolio," not silently dropped.

Report both months' share percentages and the point-change (e.g. "SP share: 62% → 58%, -4pp"), not just one month's snapshot — a structural shift is only visible in the comparison, not a single period's numbers.

### Step 6 · Product Analysis

**Top ASIN MoM changes**: follow the same rigorous join procedure as [sparkx-query-ads-performance's Period-over-Period and Top Movers example](../sparkx-query-ads-performance/references/example-period-comparison-top-movers.md) — join Step 2's (f)/(g) by `asin.asin_` (not by title), bucket into new/disappeared/present-in-both, floor the "% change" ranking on the **prior month's** (denominator) value, and show both months' raw values plus the absolute delta alongside any percentage.

**New-product performance**: for ASINs identified in Step 2h (opened this month), report their this-month `TotalSalesAmount`/`OrderCount`/`TACOS` from Step 2f (the actual metrics that call requests — not `Sales`/`Conversions`, which aren't part of it) — there is no "last month" baseline for these by definition, so don't compute a MoM % for them; present as "new this month" with their standalone numbers. **Don't assume every new ASIN is present in Step 2f**: if 2f was reduced to a disclosed spend/sales-ranked sample (per Step 2's pagination fallback), newly-opened products — which usually have low sales — likely fall outside the top sample. In that case, issue a separate `get_ads_perf` (`factEntity: asin`) call scoped to the Step 2h ASIN list (`filters` on `asin.asin_`) to fetch their performance, rather than reporting them as "no data" just because they weren't in the Top-ASIN sample. **If Step 2h's new-ASIN list is large, batch this supplemental call** — split the ASIN list into chunks of a reasonable size for the `in` filter rather than one unbounded `asin.asin_: {"in": [...hundreds...]}` call, fully paginate each batch (`hasNextPage`), and merge/dedupe the batches' results by `asin.asin_` before reporting — don't silently drop ASINs because a single oversized call or an unpaginated batch left some out.

**Long-tail situation**: from Step 2f's full (paginated) ASIN list, compute what share of total Sales comes from the top N ASINs vs the rest (a simple Pareto-style cut, e.g. "top 20% of ASINs account for X% of Sales") — this characterizes concentration, not a specific product recommendation.

### Step 7 · Keyword Analysis

**Top keyword performance**: from Step 2i, rank by Spend or Sales, report Impressions/Clicks/Spend/Sales/ACOS per keyword. If a MoM comparison is wanted, pull the same-shape data for last month and join by `target.targetId_` the same way as Step 6.

**New keyword opportunities**: from Step 2j's search-term data, find search terms with strong performance (e.g. meaningful Conversions and non-zero-Sales ACOS at or below account average — see the zero-Sales handling below) that **do not already exist as an explicit keyword target in the same adGroup**. Cross-reference against `get_entity_metadata` (`entity: target`, `filters: {"targetMatchType": {"in": ["exact", "phrase", "broad"]}, "adGroupId": {"in": [...]}}`) — **narrow by the specific `adGroupId`(s) the search term actually appeared under** (Step 2j's own `adGroupId_` field on that row), not a bare account-wide `targetMatchType` filter. The same search-term text can legitimately be a promoted keyword in one adGroup and not yet promoted in another; without narrowing by adGroup, a term already targeted elsewhere in the account would be wrongly excluded here, or a genuinely-new-to-this-adGroup term could be wrongly treated as already covered. **Narrowing by adGroup alone isn't sufficient** — that call returns the adGroup's existing keyword targets, but you still need to check whether *this specific search term* is among them: normalize both sides (case-fold, trim whitespace) and compare each search term's `query_` against the returned targets' `target.targetText_` for an exact match. Only a search term with no exact-text match among that adGroup's existing keyword targets counts as genuinely new; only flag those.

**Zero-Sales ACOS handling** (applies to both Step 2i and Step 2j wherever `ACOS` is used to rank or filter): a row with `Sales = 0` has an undefined `ACOS` (division by zero) — never treat it as "infinite" or sort it to the extreme end of an ACOS-based ranking. Exclude zero-Sales rows from any ACOS-based comparison (like the "new keyword opportunities" filter above); they belong in the negative-keyword-candidate check below instead, which is keyed on Spend + near-zero Conversions, not ACOS.

**Negative-keyword candidates**: from Step 2j, search terms with meaningful Spend and zero (or near-zero) Conversions over the full month — same underlying logic as a high-spend/zero-order anomaly, applied at the search-term level. **Currency-aware, same caveat as the weekly skill**: don't hardcode a bare dollar figure as the "meaningful spend" floor if the store is in a non-USD currency — use a floor that's actually meaningful in that store's local currency (or the account's typical spend distribution), and for a multi-profile USD-aggregated report, a USD floor is reasonable.

### Step 8 · Issues List + Attribution

Compile the notable findings from Steps 3/5/6/7 (e.g. "ACOS worsened driven by a mix shift toward SD," "ASIN X's sales collapsed," "Portfolio Y's share shrank") and cross-reference Step 2k's operation log for changes in the same window that might explain them.

**Correlation, not causation** — same discipline as the weekly skill: say "ACOS rose in the same window a bid change was recorded on this campaign" rather than "the bid change caused the ACOS rise," unless the operation log pinpoints the exact change and the timing lines up precisely enough to say so with confidence.

### Step 9 · Next-Month Plan

Derive 3-6 structural-adjustment recommendations from Steps 5-8, e.g.:
- Structural share shift toward an underperforming type → recommend rebalancing budget back toward the higher-ROAS type
- A long-tail concentration finding → recommend consolidating spend toward top performers or testing budget on emerging mid-tier ASINs
- New keyword opportunities found → recommend promoting them to explicit keyword targets
- Negative-keyword candidates found → recommend adding them as negatives

**Every recommendation must have**: action + target (specific campaign/ASIN/keyword) + evidence (data) — same requirement as the weekly skill.

## Multi-Store and Currency

When `profileIds` spans multiple stores:
- All monetary metrics from `get_ads_perf` auto-aggregate to **USD** — label dollar amounts "(USD)" explicitly.
- **Steps 2a/2b/2c (account-level KPIs) deliberately do NOT get `profile.profileId_` added.** They're single blended totals for the whole month (no dimension in `select` at all) — adding a `profile` field would change the grouping from "one row for the month" to "one row per profile per month," which is a different question (per-store KPIs, not the one blended KPI overview Step 3 expects). If the customer wants each store's KPIs broken out separately, that's a distinct call with `profile.profileId_`/`profile.profileName_` added to `select` alongside whatever else is there — issue it separately rather than trying to derive one shape from the other.
- **Steps 2d/2e (AdGroup-level) need `profile.profileId_`/`profile.profileName_` added to `select`** — they already carry `profile.countryCode_` for the Step 5 "by site" breakdown, but `countryCode_` alone doesn't disambiguate two profiles sharing a country, and Step 8's attribution needs to know which store a given adGroup/campaign belongs to.
- **Step 2f/2g (Top ASINs) — decide which question you're answering, same as `sparkx-weekly-ads-report`'s equivalent call:** for one cross-store blended Top-N, don't add `profile.profileId_` (the call as written already aggregates `TotalSalesAmount` per ASIN across every profile in `profileIds`). For each store's own Top-N, add `profile.profileId_`/`profile.profileName_` — but note that once you do, `orderBy`+`pageSize` returns the top rows by *global* rank across every store's ASINs mixed together, not N rows per store; a genuine per-store Top-N needs one call per `profileId`, or the full set pulled and grouped client-side.
- `asin.asinPrice_` (if ever added to this report) stays local currency, unaffected by the USD-aggregation rule above.
- The "site" breakdown in Step 5 is only meaningful for a multi-country `profileIds` selection — for a single-store report, omit it or note it's not applicable.

## Output Format

Remember: **the section headers and labels below are structural placeholders (shown in English here) — always regenerate them in the user's own language**, not copy the English (or any other) wording verbatim (see "Output Language" above).

**Plain-text fallback**: any severity markers or direction arrows used below are for rendering contexts that support them (chat UIs, rendered markdown). In a plain-text-only output context, replace them with words instead ("High"/"Medium" for severity, "up"/"down"/"flat" for direction).

### markdown mode (default)

```markdown
# Monthly Ads Report · {profile_name}
**Month**: {month} ({day_count} days)
**Baseline**: {MoM / YoY / both}
{If data may be incomplete due to T+2 delay, or day-count differs from the baseline month, note it here}

## 1. Monthly KPI Overview

{Show only the column(s) that match `compareBaseline`: `mom` → drop the "MoM Change" column entirely; `yoy` → drop the "YoY Change" column entirely; `mom+yoy` → show both, as below. Don't display a comparison column the report didn't actually request/compute. Each cell shows the baseline's own raw value alongside the % change — not the % alone — so the reader isn't left guessing whether "+8.4%" is $100 or $100,000: e.g. "$12,300 / +8.4%".}

| Metric | This Month | MoM Change | YoY Change |
|---|---|---|---|
| Spend | ${spend} | ${last_month_spend} / {mom%} | ${last_year_spend} / {yoy%} |
| Sales | ${sales} | ${last_month_sales} / {mom%} | ${last_year_sales} / {yoy%} |
| ACOS | {acos}% | {last_month_acos}% / {mom%} | {last_year_acos}% / {yoy%} |
| ROAS | {roas} | {last_month_roas} / {mom%} | {last_year_roas} / {yoy%} |
| Impressions / Clicks / CTR / CVR | ... | ... | ... |

## 2. Goal Attainment
{Only if monthlyTarget was supplied — actual vs target, % attainment, verdict}

## 3. Structural Analysis

{Step 5 computes share of both Spend and Sales — show both as separate columns per breakdown below, since a category's spend-share and sales-share can move in different directions (e.g. shrinking spend-share with growing sales-share signals improving efficiency, not decline).}

### By Campaign Type
| Type | This Month Spend Share | Last Month Spend Share | Spend Share Change | This Month Sales Share | Last Month Sales Share | Sales Share Change |
|---|---|---|---|---|---|---|
| SP | {pct} | {pct} | {pp change} | {pct} | {pct} | {pp change} |
| SB | ... | ... | ... | ... | ... | ... |
| SD | ... | ... | ... | ... | ... | ... |

### By Site (if multi-country)
{same format}

### By Portfolio
{same format}

## 4. Product Analysis

### Top ASIN Changes (MoM)
| ASIN | This Month Sales | Last Month Sales | Change |
|---|---|---|---|
| ... | ... | ... | ... |

### New Products This Month
{table — standalone figures, no MoM %}

### Long-Tail Concentration
{one or two sentences + a simple share breakdown}

## 5. Keyword Analysis

### Top Keywords
{table}

### New Keyword Opportunities
{list — search terms not yet promoted to explicit targets}

### Negative-Keyword Candidates
{list — high spend, ~zero conversions}

## 6. Issues List

- **{issue}**: {evidence} — {correlated change from operation log, if any, framed as correlation}

## 7. Next Month's Plan

1. **{action}** {target}
   - Evidence: {data}
2. ...

---
_Generated: {timestamp} · Data source: SparkX AI MCP · Skill: sparkx-monthly-ads-report v{version}_
```

### structured_report mode

Output JSON schema:
```json
{
  "period": {"month": "...", "dayCount": ...},
  "dataFreshnessWarning": null,
  "kpiCards": [{"metric": "spend", "current": ..., "momValue": null, "momPct": null, "yoyValue": null, "yoyPct": null}],
  "goalAttainment": [{"metric": "...", "target": ..., "actual": ..., "direction": "at_least|at_most", "attainmentPct": ...}],
  "structure": {
    "byCampaignType": [{"type": "...", "thisMonthSpendShare": ..., "lastMonthSpendShare": ..., "spendShareChangePp": ..., "thisMonthSalesShare": ..., "lastMonthSalesShare": ..., "salesShareChangePp": ...}],
    "bySite": [...],
    "byPortfolio": [...]
  },
  "productAnalysis": {
    "topAsinChanges": [...],
    "newProducts": [...],
    "longTail": {"topSharePct": ..., "topNCount": ...}
  },
  "keywordAnalysis": {
    "topKeywords": [...],
    "newOpportunities": [...],
    "negativeCandidates": [...]
  },
  "issues": [{"issue": "...", "evidence": "...", "correlatedChange": "..."}],
  "nextMonthPlan": [{"priority": 1, "action": "...", "target": "...", "evidence": "..."}]
}
```
`kpiCards[].momValue`/`momPct` and `yoyValue`/`yoyPct` should be `null` for whichever baseline `compareBaseline` didn't request (e.g. all four stay populated for `mom+yoy`, but both `yoyValue` and `yoyPct` are `null` throughout when `compareBaseline=mom`) — never fabricate a value for a baseline that wasn't computed. `momValue`/`yoyValue` carry the baseline period's own raw figure (not just the % change), matching the markdown template's "raw value / % change" cell format.

## Data Boundaries

- **Paid Sponsored Ads data only** — no DSP, no AMC
- **`monthlyTarget` is user-supplied, not tool-derived** — this skill has no way to independently know what a customer's KPI goal should be
- **No structural analysis below the AdGroup/portfolio/campaign-type level** — SKU-level margin/profitability analysis is out of scope
- **Cannot reliably compute "real-time remaining budget"** — same caveat as sparkx-weekly-ads-report; `dailyBudget`/`currentBudget` are configuration values, not a live spend ledger
- **`get_entity_metadata` has no historical-snapshot capability** — "this month's config vs last month's config" can only be inferred from `get_operation_log`'s change records, not from querying current config as if it were historical
- **New-keyword and negative-keyword candidates are heuristic suggestions**, not a guarantee of correctness — always show the underlying data (spend, conversions) so the customer can judge, don't present them as an automated decision

## Example Call

**User input**:
> 给 Demo US 出个上个月的月报，ACOS 目标是 25%

**Skill flow**:
1. Resolve the profile: `get_user_authorized_context` → find Demo US's `profileId`
2. `month` = last full calendar month; `monthlyTarget` = `{"metric": "ACOS", "target": 25, "direction": "at_most"}`
3. Run Steps 2-9
4. Output the markdown report — in Chinese, since the user asked in Chinese

## Error Handling

Follows the shared error envelope used by all three underlying tools (`isError`/`errorType`, see [`references/platform-notes.md`](references/platform-notes.md)).

| Situation | Handling |
|---|---|
| `profileIds` is empty | Follow "Resolving `profileIds`" above — call `get_user_authorized_context` first, then apply those rules; ask the user to pick only when those rules actually require it |
| Any call returns `isError: true` | Handle per `errorType` — `invalid_params` usually means a construction bug in this skill's own call (check field names/date ranges first); `rate_limited` → wait `retryAfterSeconds`, don't retry immediately |
| `effectiveProfileIds` doesn't match requested `profileIds` | Explain the scope mismatch before concluding "no data" |
| YoY window would exceed the 15-month lookback | Say so explicitly and omit the YoY column rather than sending an invalid request or silently dropping it without explanation |
| `get_operation_log` returns `truncated: true` | Split into sub-windows per its "Getting a Complete Count" procedure; note in the report if the operation count ends up as a partial/lower-bound figure |
| A time window is genuinely missing data (not an error) | State clearly which days/range is missing, and still produce the report with what's available |

## Not Covered by This Skill

- Weekly-cadence recap → `sparkx-weekly-ads-report`
- Quarterly/QBR strategic review → `quarterly-ads-report` (not yet built)
- Deep root-cause attribution on a single campaign → [ACOS root-cause investigation example](../sparkx-query-ads-performance/references/example-acos-root-cause-investigation.md)
- SKU-level margin/profitability analysis (needs the customer's own cost data, not just ad data)

## Version History

- **v0.1.0** (2026-07-23) · Initial build, written directly against the new tool's conventions (camelCase params, `factEntity`/`dateStart`/`dateEnd`/`select`/`metrics`/`userContext`, `get_operation_log`). Based on the original monthly-report concept sketch in `skill-design-draft.md` (which used old-tool naming and was never built into an actual SKILL.md) — no prior working version existed to port from. Carries forward the fixes already applied to `sparkx-weekly-ads-report` v0.4.0 from the start: a confirm-first gate for customer-facing multi-store defaults (>5 profiles), currency-aware spend thresholds instead of a hardcoded USD figure, a disclosed sampling fallback for pagination at scale, output-language-adaptive templates, and a plain-text fallback for severity/direction markers.
- **v0.2.0** (2026-07-23) · Retroactively applied the fixes `sparkx-weekly-ads-report` picked up in its v0.5.0-v0.9.1 review cycle (this skill was written before those rounds happened, so it started with the same gaps): replaced the simplified `profileIds` default rule with the full "Resolving `profileIds`" 4-case procedure (named store / explicit "all stores" / single authorized profile / many authorized profiles split at 5). Fixed the same blended-vs-per-store attribution bug weekly had: the account-level KPI calls (2a/2b/2c) were listed as needing `profile.profileId_` added, which would have fragmented their single blended monthly total into one row per profile — removed them from that list and added an explicit note on issuing a separate per-store call if that's what's wanted instead. Added `profile.profileId_`/`profile.profileName_` to the AdGroup-level calls (2d/2e), which support Step 8's attribution but weren't previously called out for multi-store use. Extended the Top ASIN calls (2f/2g) with the same two-case treatment (blended cross-store Top-N vs. genuine per-store Top-N, including the global-rank-not-per-store `pageSize` caveat) that `sparkx-weekly-ads-report` needed for its analogous call. Marked Step 2k (operation log) as best-effort so its failure doesn't block the rest of the report, and extended the pagination-fallback note to require stating what was actually covered and to require that a degraded section not fail the whole report. Updated the Error Handling table's `profileIds is empty` row to point back to the "Resolving `profileIds`" procedure instead of restating a simplified version of it.
- **v0.3.0** (2026-07-23) · Fixed a wrong field name: Step 2h's new-product filter used `asinOpenDate_` (the `get_ads_perf` dimension-field convention), but `get_entity_metadata` fields are plain camelCase with no prefix/suffix — corrected to `asinOpenDate`. Fixed a metric-name mismatch: Step 6's new-product paragraph said to report "Sales/Conversions/TACOS" from Step 2f, but that call actually requests `TotalSalesAmount`/`OrderCount`/`TACOS` — corrected to match. Fixed Step 4's goal-attainment formula, which applied `actual/target×100` uniformly regardless of metric direction — split into higher-is-better (`Spend`/`Sales`/`Conversions`/`ROAS`: `actual/target`) and lower-is-better (`ACOS`/`CPC`/`CPA`: `target/actual`, since a lower actual is the good outcome there). Made `compareBaseline` actually gate Step 2's data pulls: calls (b) and (c) were previously issued unconditionally regardless of `compareBaseline`, with only Step 3 checking "if includes mom/yoy" after the fact — now (b) is skipped when `compareBaseline=yoy` and (c) is skipped when `compareBaseline=mom`. Narrowed the new-keyword-opportunity dedup check to the specific `adGroupId`(s) a search term actually appeared under, instead of a bare account-wide `targetMatchType` filter — the same term can be a promoted keyword in one adGroup and genuinely new in another, so an unscoped check could wrongly include or exclude candidates. Added the same zero-`Sales`-means-undefined-ACOS handling used elsewhere to the new-keyword-opportunity filter (exclude, don't treat as infinite). Added `portfolio.portfolioName_` to the AdGroup-level `select` and Step 5's portfolio breakdown — it only had the ID before, which isn't reader-friendly in a customer-facing report.
- **v0.4.0** (2026-07-23) · Fixed four correctness gaps found in review. (1) Step 2h (new-product identification via `get_entity_metadata`) was missing from the "fully paginate" instruction — added an explicit `page`/`hasNextPage` pagination note so new ASINs beyond the first page aren't silently dropped. (2) Step 6's new-product performance read straight from Step 2f (Top ASINs), but 2f can be a disclosed spend/sales-ranked sample and newly-opened low-sales ASINs typically fall outside it — added a fallback to pull a separate ASIN-performance call scoped to the Step 2h list instead of assuming they're in the sample. (3) `compareBaseline` gated the KPI-section baseline (2b/2c) but not the structural/product-MoM pulls (2e/2g), which stayed MoM even under `yoy` — clarified in the param table that `compareBaseline` controls only the Step 3 KPI columns and that Steps 5/6 are always MoM (2e/2g always pulled), removing the ambiguity. (4) `monthlyTarget` was typed as a single-target object but described as "target(s)" — reworded to "a single metric+target" to match the type and Step 4's single-target handling.
- **v0.5.0** (2026-07-23) · Fixed six gaps found in review. (1) `monthlyTarget` gained an explicit `direction` field (`at_least`/`at_most`) instead of inferring attainment direction from the metric name — `Spend` specifically is genuinely ambiguous (budget cap vs. deployment goal) and must not default silently; ask or state the assumption if `direction` is missing for a `Spend` target. (2) The Step 6 fallback call for new-product ASINs (added in v0.4.0) now specifies batching the `asin.asin_` filter list, fully paginating each batch, and merging/deduping by ASIN, instead of one unbounded `in` filter that could silently drop entries for a large new-product list. (3) The new-keyword-opportunity check now spells out the actual text-match step (normalize + exact-match `query_` against the adGroup's existing `target.targetText_` values) — narrowing by `adGroupId` alone doesn't tell you whether a specific search term is already targeted. (4) The markdown KPI table and `structured_report`'s `kpiCards` now explicitly omit/null the MoM or YoY column/field that `compareBaseline` didn't request, instead of always showing both. (5) Step 5's structural breakdown tables now show separate Spend-Share and Sales-Share columns (both were being computed but the template only had one generic "Share" column) — a category's spend-share and sales-share can move in different directions, which a single merged column would hide. (6) The AI-managed-callout check only ever decided *whether* to show the callout, not what data fills it — added `AISales`/`AIACOS`/`AIROAS` to Steps 2a/2b/2c's `metrics` (conditionally, only when the callout applies) so there's actually AI-specific performance data to report instead of just a yes/no AI-status statement.
- **v0.5.1** (2026-07-23) · The KPI table's MoM/YoY columns showed only the % change, not the baseline period's own raw value — "+8.4%" alone doesn't tell the reader whether that's $10 or $10,000. Renamed the columns "MoM Change"/"YoY Change" and changed each cell to show the raw baseline value alongside the %, matching the "both raw values plus the delta" discipline already used elsewhere in this skill (Step 5's structural shares, Step 6's Top ASIN changes). Added `momValue`/`yoyValue` to `structured_report`'s `kpiCards` alongside the existing `momPct`/`yoyPct`. Updated the Example Call's `monthlyTarget` to include `direction` (`{"metric": "ACOS", "target": 25, "direction": "at_most"}`), matching the field v0.5.0 introduced — the old example predated it.
- **v0.5.2** (2026-07-23) · Three small documentation-consistency fixes. Fixed a wrong cross-reference in Step 2's intro: it pointed to "Step 4" (Goal Attainment) for the new/disappeared-entity handling, but that logic actually lives in Step 6's join procedure — repointed to Step 6 and noted it applies the same way to Steps 5 and 7. Fixed Step 5's campaign-type bullet, which only mentioned "share of total Spend" despite the section's own intro (and the output template) covering both Spend and Sales share — reworded to match. Added `spendShareChangePp`/`salesShareChangePp` to `structured_report`'s `byCampaignType` schema — it had this-month/last-month share but no explicit change field, while the markdown template shows a "Change" column; the JSON was quietly less informative than the markdown output for the same data.
- **v0.5.3** (2026-07-24) · Same cross-skill zh/en audit that caught two issues in `sparkx-weekly-ads-report` v0.9.2 found the identical pair here, since this skill's language-handling text was originally copied from weekly's pre-fix version. (1) "Output Language" told the agent to pass `language` to `get_entity_metadata` as well as `get_ads_perf` — `get_entity_metadata` has no such parameter; corrected to scope `language` to `get_ads_perf` only, with `get_entity_metadata` enum localization via `{field}Text` companion fields or `enum-i18n.md`. (2) The Output Format lead-in claimed the template was "written in Chinese as this product's default illustration," but the shipped template (`# Monthly Ads Report`, `## 1. Monthly KPI Overview`, etc.) is English — reworded to describe it as a language-neutral placeholder instead of asserting the wrong source language.
- **v0.5.4** (2026-07-28) · Corrected Step 2h's new-product identification against the authoritative tool spec: `asinOpenDate` is **not** a filterable `get_entity_metadata` field, and v0.3.0/v0.4.0 wrongly assumed it was filterable in `YYYYMMDD` format. Rewrote to pull asin metadata (no `asinOpenDate` filter) with full pagination, then filter to the month window **client-side** on the returned `asinOpenDate`, which is a datetime-with-timezone string (e.g. `"2026-06-01 00:00:00 PST"`) — not `YYYYMMDD` — so it must be parsed with PST-timezone awareness to avoid month-boundary misclassification (`YYYYMMDD` is `campaignStartDate`'s format, not this field's). Also renamed the cross-reference "weekly-aggregation example" → "aggregation-over-time example" to match the base skill's actual `example-aggregation-over-time.md` (references only).
- **v0.5.5** (2026-07-28) · Synced the AI-managed-section detection call with the fix `sparkx-weekly-ads-report` v0.9.3 got: the `get_entity_metadata` (`entity: aiGroup`) check now instructs adding `filters: {"aiStatus": 1}` or fully paginating — with a default page size of 100, an account whose only running AI group sat past page 1 would previously have been misjudged as "no AI management" and the whole callout wrongly skipped.
- **v0.5.6** (2026-07-28) · Added an explicit dependency declaration to the Scope section (needs `sparkx-query-ads-performance`/`sparkx-query-entity-metadata`/`sparkx-query-operation-log` installed as sibling skills for the `../query-.../…` cross-references to resolve). Links unchanged — they're correct for the standard flat `.claude/skills/<name>/` layout; the note just makes the install dependency explicit.
- **v1.0.0** (2026-08-18) - First stable release; moved from `skills/optional/` to the top-level `skills/` folder alongside the required skills.
- **v1.0.1** (2026-08-25) - Same platform-behavior sync as the weekly report: all-or-nothing `profileIds`, strict `pageSize`/`page` validation, `language` default `en`, and the entity/profile-count-dependent `createdDate` timezone on `get_operation_log`.
