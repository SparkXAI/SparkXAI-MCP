---
name: sparkx-ads-structure-analysis
description: >-
  Analyze how ad spend and efficiency break down across a structural dimension — campaign type
  (SP/SB/SD), marketplace/site, portfolio, weekday-vs-weekend, or hour-of-day — and diagnose where spend share
  and efficiency don't match (over-invested underperformers, under-invested strong performers).
  Optional sub-scenarios: SP deep-dive (manual vs auto targeting), SB new-to-brand focus. Use when
  the user asks "我 SP/SB/SD 结构合理吗", "各站点谁强", "SB 新客到底行不行", "工作日和周末哪个好",
  "structure analysis", "campaign type breakdown". Not for a single-entity trend/anomaly check (use
  sparkx-weekly-ads-report / sparkx-monthly-ads-report / a lighter ad-hoc analysis skill), product-level diagnosis
  (use sparkx-product-diagnosis), or keyword-level diagnosis (a dedicated skill, not yet built).
metadata:
  version: 1.0.3
---

# Ads Structure Analysis

## Scope: This Is an Orchestration Skill, Not a New MCP Tool

This skill does **not** map to a single MCP tool of its own — it orchestrates two existing read tools, each already covered by its own skill:

- `get_ads_perf` → [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md)
- `get_entity_metadata` → [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md)

> **Dependency — install these two base skills alongside this one:** `sparkx-query-ads-performance`, `sparkx-query-entity-metadata`. Skills install as sibling directories under your current agent's skills root (`.claude/skills/<name>/` for Claude Code; the equivalent root for other agents — see the [supported-agents table](../../README.md)), which is exactly what the `../query-.../…` links above (and elsewhere in this doc) resolve against — if a base skill isn't installed there, those links won't resolve and this skill can't run. Install both first.

**Read those two SKILL.md files first** (parameter formats, field-naming rules, the Ratio Metric Display Rule) plus [`references/platform-notes.md`](references/platform-notes.md) (auth flow, error handling, pagination, date-range limits, currency rules). This document only covers logic specific to structural analysis; it doesn't repeat what the base skills already document.

Rewritten against the new tool's conventions from the start — carries forward the same discipline established across `sparkx-weekly-ads-report`/`sparkx-monthly-ads-report`: full `profileIds` resolution rules, currency-aware thresholds, output-language adaptivity, disclosed sampling fallback, and zero-denominator handling.

## Output Language: Always Match the User, Never Hard-Code Chinese or English

**The worked examples and output templates below are written in Chinese** (matching this product's primary customer base), but they are **structural illustrations, not literal text to copy verbatim**. Generate the actual report in whatever language the user asked in. When calling `get_ads_perf`, also set the `language` parameter (`zh`/`en`/`ja`) to match the customer's language. **`get_entity_metadata` has no `language` parameter** — it's not in that tool's documented parameter list. Localize its enum values using the returned `{field}Text` companion fields, or `sparkx-query-entity-metadata`'s own [`enum-i18n.md`](../sparkx-query-entity-metadata/references/enum-i18n.md) if a given enum has no `Text` companion — don't pass `language` to `get_entity_metadata` expecting it to have the same effect as on `get_ads_perf`.

## When to Use

**Trigger phrases**: 结构分析, 结构合理吗, 类型对比, 站点对比, SP/SB/SD 结构, SB 新客, 工作日 周末, structure analysis, campaign type breakdown

**User roles**: ads managers, account managers, ads ops doing a deep-dive (not a periodic report)

**Core question**: how is spend distributed across this dimension, is that distribution matched by efficiency, and where's the structural imbalance

**Not for**:
- Periodic recaps (WoW/MoM cadence) → `sparkx-weekly-ads-report` / `sparkx-monthly-ads-report`
- Single-campaign root-cause investigation → [ACOS root-cause investigation example](../sparkx-query-ads-performance/references/example-acos-root-cause-investigation.md)
- Product-level diagnosis → `sparkx-product-diagnosis`; keyword-level diagnosis → a dedicated skill (not yet built)

## Input Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `profileIds` | array[long] | No | — | See "Resolving `profileIds`" below |
| `breakdownBy` | enum | No | `campaignType` | `campaignType` \| `marketplace` \| `portfolio` \| `dayOfWeek` \| `hourOfDay`. See "Breakdown Dimensions" for how each is actually queried — some require client-side derivation, not a native `groupBy` |
| `dateStart` / `dateEnd` | string (`YYYY-MM-DD`) | No | Trailing 30 days ending yesterday | The analysis window. Must satisfy `get_ads_perf`'s 90-day span / 15-month lookback caps like any other call |
| `focusMetrics` | array[string] | No | `["Spend", "Sales", "ACOS", "ROAS", "CPA"]` | Which metrics drive the share/efficiency comparison. `CPA` is included by default alongside `ACOS` — the product's own canonical "Campaign Type Analysis" board treats them as equally core, not `ACOS` alone. Must be valid for the entities involved — check `sparkx-query-ads-performance`'s Metrics × Entity Support Matrix |
| `includeTrend` | bool | No | `true` | Whether to include a per-segment trend view (Step 3) alongside the single-period snapshot — on by default, matching how the product's own dashboards present this analysis (trend lines, not just a static table). Set `false` for a lighter, snapshot-only response |
| `subScenario` | enum | No | — | `spDeepDive` \| `sbNtb` \| `weekdayWeekend`. See "Sub-Scenarios" below. **`sbvCreative` (creative-type breakdown) is not offered — see Data Boundaries for why** |

### Resolving `profileIds`

Always call `get_user_authorized_context` first to get the authorized `profiles` list, then apply exactly one of these cases:

1. **The user named specific store(s)** → resolve the name(s) against the authorized list and query only the matching profile(s).
2. **The user explicitly said "all stores" / "全账号" / equivalent** → query all authorized `profileIds`.
3. **The user didn't name a store, and there's only one authorized profile** → use it directly — there's nothing to ask.
4. **The user didn't name a store, and there are multiple authorized profiles**:
   - **5 or fewer** → you may default to using all of them.
   - **More than 5** → do not silently roll everyone up. Hand the user the `profiles` list and ask them to pick one, several, or explicitly confirm "all stores" first.

Case 4's threshold exists because a silent multi-store aggregate can hide a single store's structural pattern behind a blended number, and forces an unannounced USD conversion (see "Multi-Store and Currency" below).

## Breakdown Dimensions

**`campaignType`** (default) — `campaign.campaignType_` (`sponsoredProducts`/`sponsoredBrands`/`sponsoredDisplay`). A native dimension field; group directly via `select`.

**`marketplace`** — `profile.countryCode_`. Only meaningful when `profileIds` spans multiple countries; if it's a single-country selection, say so and suggest `campaignType` or `portfolio` instead of producing a one-row "breakdown."

**`portfolio`** — `portfolio.portfolioId_`, displayed via `portfolio.portfolioName_`. Rows with no portfolio must be grouped as an explicit "no portfolio" bucket, not silently dropped from the total.

**`dayOfWeek`** — **not a native `groupBy` expression.** `get_ads_perf`'s time-aggregation options are calendar day/week/month/quarter/year (see `sparkx-query-ads-performance`'s Time Aggregation table) — there is no "bucket every Monday together regardless of week" expression. To do this breakdown: pull daily-granularity data (`select: ["date"]`, one row per day across the window), then **client-side** map each row's `date` to a weekday name and aggregate the 4-5 occurrences of each weekday within the window yourself. Don't attempt to express this as a single server-side `groupBy`.

**`hourOfDay`** — available via hourly (AMS) data, with tighter limits than every other breakdown here. Query `factEntity: "campaign"` with `timeGranularity: "hourly"` and explicitly include both `date` and `hour` in `select`; hourly mode changes the source table but does not inject `hour` into the selected grouping. Aggregate the returned rows by hour **client-side** (same shape as `dayOfWeek`).

Constraints you must respect and disclose:
- **Campaign level only.** There is no hourly adGroup / target / placement / ASIN data — `timeGranularity: hourly` on any other entity is a hard error. So an hourly breakdown cannot be crossed with `portfolio` or `marketplace` beyond what campaign-level `select` fields give you.
- **7-day window per call, not 30 or 90.** This breaks the skill's default trailing-30-day window: either narrow to ≤7 days, or split the requested window into contiguous ≤7-day calls and aggregate hour-of-day across all chunks. Call it a **sample** only when you deliberately cover a subset (for example, the latest 14 of 30 days), and disclose that subset. If every day is covered by non-overlapping chunks, describe it as a split full-window query, not sampling.
- **Averaging**: divide each hour's totals by the number of *days* covered, not the number of rows.
- **T+2 delay** hits hardest here: the most recent hours are incomplete, so drop or label the trailing partial day rather than reporting a fake evening collapse.
- **Timezone is not stated** for hourly buckets, so avoid strong claims like "spend peaks at 8pm local"; describe the shape ("a clear evening peak") and note the hour labels' zone is unconfirmed.

A keyword × placement structural view is also possible (`factEntity: "keywordPlacement"`, SP only, hourly, ≤7 days) — see `sparkx-query-ads-performance`'s hourly/AMS example. Note its AI metrics are placeholders (`AISpend`/`AISales` = 0, `AIACOS`/`AIROAS` = null), so don't put AI columns in that table.

## Sub-Scenarios

**`spDeepDive`**: narrow to `campaign.campaignType_ = sponsoredProducts`, then further break down by `campaign.targetingType_` (`manual`/`auto`) — compare manual vs auto targeting's spend share and efficiency within SP specifically. **Don't confuse this with `target.targetingType_`**, a different field with different values (`keyword`/`target`/`auto`/`audience` — categorizing the target's own type, not the campaign's manual/auto setting).

**`sbNtb`**: narrow to `campaign.campaignType_ = sponsoredBrands`, and add the NTB metrics (`NTBOrders`, `NTBSales`, `NTBUnits`, `NTBOrdersRate`, `NTBUnitsRate`, `NTBSalesRate`) to the metrics pulled — these are confirmed available for `campaign`/`adGroup`/`target`/`searchTerm`/`productAd` (not `placement`/`asin`), so request them at whichever entity level the rest of the breakdown is using. Report NTB share alongside the regular spend/efficiency breakdown, since "is SB driving new customers" is specifically what NTB answers.

**`weekdayWeekend`**: use the `dayOfWeek` breakdown above, then bucket further into two groups (Mon-Fri vs Sat-Sun) rather than 7 separate days, if that's what the user actually asked ("workday vs weekend" is coarser than "which specific day of the week").

**Companion breakdowns customers often ask for alongside `campaignType`**: the product's own "Campaign Type Analysis" dashboard template pairs the campaign-type view with a **targeting-type breakdown** (manual vs auto — covered here via `spDeepDive`) and a **search-term match-type breakdown** (broad/phrase/exact, etc.). The second one is **not covered by this skill** — it belongs to a future search-term-analysis skill (not yet built). If a customer's ask naturally extends into match-type territory (e.g. "结构分析完了，再看看搜索词匹配类型"), say plainly that this skill's scope stops at campaign/targeting-type structure and point them to that future capability instead of trying to fold match-type analysis into this skill's output.

## Workflow

### Step 1 · Define the Analysis Window

Default: trailing 30 days ending yesterday (T+2 delay — see below). If the user gives an explicit range, use it, but confirm it satisfies `get_ads_perf`'s 90-day max span and 15-month lookback before issuing the call — if it doesn't, split into multiple ≤90-day calls per the standard procedure (see `sparkx-query-ads-performance`'s aggregation-over-time example) rather than sending an oversized request.

**T+2 data-delay check**: if the window's end date is within 2 days of today, note that the most recent day(s) may not have finished processing yet.

### Step 2 · Pull Data

**a. Breakdown-level performance**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "{window start}",
  "dateEnd": "{window end}",
  "select": ["campaign.campaignType_"],
  "metrics": ["Impressions", "Clicks", "Spend", "Sales", "Conversions"],
  "pageSize": 500,
  "userContext": "Structure analysis - breakdown by campaign type"
}
```
`select` changes per `breakdownBy`: `["campaign.campaignType_"]` for `campaignType`, `["profile.countryCode_"]` for `marketplace`, `["portfolio.portfolioId_", "portfolio.portfolioName_"]` for `portfolio`, `["date"]` for `dayOfWeek` (aggregate to weekday buckets client-side per "Breakdown Dimensions" above), and `["date", "hour"]` plus `timeGranularity: "hourly"` for `hourOfDay` (aggregate the same hour across dates client-side). **Recompute ACOS/ROAS/CTR/CVR from the summed base metrics per segment** rather than requesting them directly alongside a `select` that spans the whole window in one row per segment — request the base metrics (`Impressions`/`Clicks`/`Spend`/`Sales`/`Conversions`) and derive the ratios, so there's no ambiguity about which period/grouping a pre-computed ratio belongs to.

**If `subScenario` is set, this call changes further — don't run the plain breakdown call above and expect Step 5 to somehow retrofit it:**
- **`spDeepDive`**: add `{"campaign.campaignType_": "sponsoredProducts"}` to `filters`, and add `campaign.targetingType_` to `select` alongside (or instead of, if not also doing the base `campaignType` breakdown) the `breakdownBy` dimension.
- **`sbNtb`**: add `{"campaign.campaignType_": "sponsoredBrands"}` to `filters`, and add `NTBOrders`/`NTBSales`/`NTBUnits`/`NTBOrdersRate`/`NTBUnitsRate`/`NTBSalesRate` to `metrics`.
- **`weekdayWeekend`**: same as the `dayOfWeek` breakdown's call shape (`select: ["date"]`) — the Mon-Fri/Sat-Sun bucketing happens client-side afterward, no additional field needed here.

**b. Segment-level entity config** (only if the diagnosis needs config context, e.g. explaining *why* a segment underperforms): `get_entity_metadata` for the relevant entity (`campaign`, `portfolio`, etc.) to pull status/settings for the segments identified as imbalanced in Step 4.

**c. Segment-level weekly trend** (only when `includeTrend=true`, the default): same shape as (a), but `select` adds a weekly time-aggregation expression alongside the breakdown dimension — e.g. `["campaign.campaignType_", "toMonday(parseDateTime32BestEffort(date)) as week"]` — so each segment gets one row per week across the window instead of one row for the whole period. **Use weekly, not daily, granularity for the trend view**: a 30-day default window is ~4-5 weekly points per segment, which reads cleanly in a text report; daily granularity (30 points × N segments) is what the product's own web dashboard can render as a line chart but is too dense for a markdown table. Recompute `ACOS`/`CPA` per segment per week from that week's own summed base metrics — never average pre-computed weekly ratios across weeks, and never derive a week's ratio from another week's base metrics.

**Exception for `breakdownBy=hourOfDay`: do not issue this separate weekly-trend call.** The 24-point intraday curve derived from Step 2a's `date` + `hour` rows is already this mode's trend output, and its ≤7-day source window does not produce a meaningful 4-5-point weekly series. Treat `includeTrend` as satisfied by the intraday curve; only add a day-by-day comparison when the user explicitly asks, using the same rows client-side rather than a weekly aggregation expression.

**⚠️ `breakdownBy=dayOfWeek` or `subScenario=weekdayWeekend` need a different shape here — the breakdown "dimension" isn't a native field to add alongside `week` the way `campaign.campaignType_`/`profile.countryCode_`/`portfolio.portfolioId_` are.** There's no server-side field for "which weekday" to combine with a week aggregation. Instead: `select: ["date"]` only (same as the base breakdown call), pull daily rows across the whole window, then **client-side** derive two labels per row — the weekday/weekend segment (per "Breakdown Dimensions" above) and the week bucket it falls in — and organize the trend as segment × week from those two derived labels together. Don't expect the server to return a "Monday" or "weekday" row directly at any granularity.

**Fully paginate before analyzing** — loop `page` while `hasNextPage` is `true`. **If full pagination would be impractical at scale** (e.g. very many portfolios or campaigns), you may fall back to a spend-ranked sample instead of the full population — this fallback **must be disclosed explicitly**, stating what was actually covered, and **a degraded section must not fail the whole analysis** — produce whatever's complete and mark only the affected part as partial.

### Step 3 · Compute Share and Efficiency Per Segment

For each segment in the breakdown: **share of total** (`segment Spend / account total Spend`, and separately `segment Sales / account total Sales` — report both, they can diverge) plus the segment's own `ACOS`/`ROAS`/`CTR`/`CVR`/`CPA` recomputed from its summed base metrics (`CPA = Spend/Conversions`).

**Zero-denominator handling**: a segment with `Sales = 0` has undefined `ACOS` — don't compute it, don't treat it as infinite; report the segment's `Spend` and note "no sales this period" instead of a fabricated ratio. Likewise, a segment with `Conversions = 0` has undefined `CPA`.

**Trend view (when `includeTrend=true`)**: using Step 2c's weekly-grouped data, show each segment's `ACOS`/`CPA` across the weeks in the window — the product's own canonical dashboard treats this trend, not just the period snapshot, as the primary way to read structural efficiency. Call out any segment whose trend moved meaningfully within the window (e.g. "SB's ACOS was stable at ~24% for three weeks, then jumped to 31% in the last week") — a snapshot alone would average that shift away and miss it.

**Ratio-metric display rule**: `ACOS`/`CTR`/`CVR` are confirmed pre-scaled ×100 — append `%`, don't re-scale. `ROAS`/`CPA` are plain ratios/unit-costs, not percentages — no `%`. `TACOS`/NTB `*Rate` fields are the confirmed-scale exception among NTB metrics — see the base skill's Ratio Metric Display Rule for which NTB fields are Tier 1 vs Tier 2 before appending `%` to any of them.

### Step 4 · Diagnose Structural Imbalance

Compare each segment's **spend share** against its **efficiency** (ACOS/ROAS) and **sales share** relative to the account average:

- **Over-invested, underperforming**: spend share meaningfully higher than sales share, and/or ACOS meaningfully worse than the account average — flag as a candidate for reallocating budget away from.
- **Under-invested, strong performer**: spend share meaningfully lower than sales share, and/or ACOS meaningfully better than the account average — flag as a candidate for scaling up.
- **Currency-aware thresholds**: define "meaningfully" using percentage-point gaps (share) and relative ACOS deviation (e.g. ">20% worse than account average"), not a hardcoded absolute dollar gap — a fixed dollar threshold breaks for non-USD single-store analyses the same way it would in the weekly/monthly report skills.
- Don't diagnose a segment with negligible spend share (e.g. <2% of total) as a meaningful imbalance either way — flag it as "too small to be structurally significant" instead, to avoid noise from long-tail segments.

### Step 5 · Sub-Scenario Section (if `subScenario` was requested)

Add the relevant specialized section per "Sub-Scenarios" above — this supplements, not replaces, the base breakdown from Steps 3-4.

### Step 6 · Structural Recommendations

Derive 3-5 recommendations from Step 4's findings, each with: action + target segment + evidence (share %, efficiency numbers). Same discipline as the report skills — **correlation, not causation**: a structural finding ("SD share grew while overall ACOS worsened") is not proof SD caused the ACOS change unless you've actually isolated SD's own ACOS as the driver; say what the data shows, not more.

## Multi-Store and Currency

When `profileIds` spans multiple stores:
- All monetary metrics from `get_ads_perf` auto-aggregate to **USD** — label dollar amounts "(USD)" explicitly.
- Add `profile.profileId_`/`profile.profileName_` to Step 2a's `select` if you need to know which store each row belongs to (e.g. combining `marketplace` breakdown with multi-store detail) — but don't add it when the point is one blended breakdown across all selected stores, since that would fragment each segment's row by store instead of aggregating it.

## Output Format

### markdown mode

```markdown
# 广告结构分析 · {profile_name}
**维度**：{campaignType / marketplace / portfolio / dayOfWeek}
**周期**：{dateStart} ~ {dateEnd}
{If data may be incomplete due to T+2 delay, or a section is based on a partial sample, note it here}

## 一、结构占比

| 分段 | 花费占比 | 销售额占比 | ACOS | ROAS | CPA |
|---|---|---|---|---|---|
| SP | {pct} | {pct} | {acos}% | {roas} | {cpa} |
| SB | ... | ... | ... | ... | ... |
| SD | ... | ... | ... | ... | ... |

{仅当 includeTrend=true 时展示——按周展示每个分段的 ACOS/CPA 走势，不只是期末快照}

### 分段周度趋势（ACOS / CPA）

| 分段 | 第1周 | 第2周 | 第3周 | 第4周 | ... |
|---|---|---|---|---|---|
| SP · ACOS | {pct}% | ... | ... | ... | ... |
| SP · CPA | {value} | ... | ... | ... | ... |
| SB · ACOS | ... | ... | ... | ... | ... |
| SB · CPA | ... | ... | ... | ... | ... |

{如果某个分段的趋势中途有明显变化，单独点出来，不要让期末快照把这个变化平均掉}

## 二、结构失衡诊断

- **过度投入/表现不佳**：{segment} — 花费占比 {pct}，销售额占比仅 {pct}，ACOS 比账户均值差 {pct}
- **投入不足/表现优秀**：{segment} — ...

{Segments below the 2% spend-share floor: mention briefly as "too small to be structurally significant," don't over-analyze}

## 三、{子场景标题，若有 subScenario}

{spDeepDive: manual vs auto targeting 对比表；sbNtb: NTB 指标专区；weekdayWeekend: 工作日 vs 周末对比表}

## 四、结构调整建议

1. **{action}** {target}
   - 依据：{data}
2. ...

---
_生成时间：{timestamp} · 数据源：SparkX AI MCP · Skill: sparkx-ads-structure-analysis v{version}_
```

### structured_report mode

```json
{
  "dimension": "campaignType",
  "period": {"start": "...", "end": "..."},
  "dataFreshnessWarning": null,
  "segments": [{"segment": "...", "spendShare": ..., "salesShare": ..., "acos": ..., "roas": ..., "cpa": ..., "tooSmallToAnalyze": false}],
  "trend": null,
  "imbalances": [{"segment": "...", "type": "overinvested|underinvested", "evidence": "..."}],
  "subScenario": null,
  "recommendations": [{"priority": 1, "action": "...", "target": "...", "evidence": "..."}]
}
```
`"trend"` is `null` when `includeTrend=false`; otherwise it's `[{"segment": "...", "weekly": [{"weekStart": "...", "acos": ..., "cpa": ...}]}]` — one entry per segment, each with its own array of weekly points.

## Data Boundaries

- **`sbvCreative` (creative-type breakdown) is not offered by this skill.** `get_ads_perf`/`get_entity_metadata`'s documented fields don't include a "creative type" dimension anywhere in the campaign/adGroup/target/productAd entity tables — this isn't a documented capability of either tool. Don't invent a field name for it; if a customer asks for creative-level SBV analysis, say plainly this data isn't currently queryable via these tools rather than guessing at an undocumented field.
- **`dayOfWeek` is a client-side derivation, not a server aggregation** — see "Breakdown Dimensions." Accuracy depends on correctly mapping each `date` to a weekday; don't get this wrong for reports spanning a daylight-saving or year boundary (unlikely at a 30-day default window, but worth checking for longer custom windows).
- **No historical structural snapshot** — `get_entity_metadata` has no point-in-time capability, so "how has the structure changed since 6 months ago" can only be approximated by re-running this analysis over a past window with `get_ads_perf`, not by querying `get_entity_metadata` for a past config state.
- **Structural findings are correlational**, not causal — see Step 6.

## Example Call

**User input**:
> 看下 Demo US 最近 30 天 SP/SB/SD 结构合不合理

**Skill flow**:
1. Resolve the profile: `get_user_authorized_context` → find Demo US's `profileId`
2. `breakdownBy = campaignType`, window = trailing 30 days ending yesterday
3. Run Steps 2-6
4. Output the markdown report — in Chinese, since the user asked in Chinese

## Error Handling

Follows the shared error envelope used by both underlying tools (`isError`/`errorType`, see [`references/platform-notes.md`](references/platform-notes.md)).

| Situation | Handling |
|---|---|
| `profileIds` is empty | Follow "Resolving `profileIds`" above — ask only when those rules require it |
| Any call returns `isError: true` | Handle per `errorType` — `invalid_params` usually means a construction bug in this skill's own call; `rate_limited` → wait `retryAfterSeconds` |
| `effectiveProfileIds` doesn't match requested `profileIds` | Explain the scope mismatch before concluding "no data" |
| A segment has `Sales = 0` | Report Spend and "no sales," don't compute ACOS against a zero denominator |
| A degraded/sampled section | Disclose what was covered; don't fail the whole analysis over one segment's pagination trouble |

## Not Covered by This Skill

- Periodic WoW/MoM cadence recaps → `sparkx-weekly-ads-report` / `sparkx-monthly-ads-report`
- Creative-type (SBV) breakdown → not currently a queryable capability, see Data Boundaries
- Product-level diagnosis → `sparkx-product-diagnosis`
- Keyword/search-term-level diagnosis → a dedicated skill (not yet built)
- Single-campaign root-cause investigation → [ACOS root-cause investigation example](../sparkx-query-ads-performance/references/example-acos-root-cause-investigation.md)

## Version History

- **v0.1.0** (2026-07-24) · Initial build, written directly against the new tool's conventions from the start (camelCase params, `factEntity`/`dateStart`/`dateEnd`/`select`/`metrics`/`userContext`). Based on the original `ads_structure_analysis` concept sketch in `skill-design-draft.md` (Group 2 · 专项深度分析, old-tool naming, never built into an actual SKILL.md). Carries forward the fixes `sparkx-weekly-ads-report`/`sparkx-monthly-ads-report` needed multiple review rounds to reach: full 4-case `profileIds` resolution, currency-aware imbalance thresholds instead of a hardcoded dollar gap, zero-`Sales`-means-undefined-ACOS handling, disclosed sampling fallback with non-blocking degradation, output-language adaptivity, and multi-store USD/attribution rules. Explicitly declined to implement the `sbvCreative` sub-scenario from the original sketch — no creative-type field is documented in either underlying tool, so building it would mean inventing an unconfirmed field name.
- **v0.1.1** (2026-07-24) · Self-review pass (simulated end-to-end walkthrough + cross-reference sweep) found four issues. (1) This skill's own `references/platform-notes.md` was never actually present — the copy command run at creation time silently failed (the base skill folders were temporarily missing from `skills-v2` at that moment) and was never retried after they came back; copied it in now. (2) `spDeepDive` specified breaking down by `target.targetingType_` (values `keyword`/`target`/`auto`/`audience`) when the actual manual-vs-auto SP distinction is `campaign.targetingType_` (values `manual`/`auto`) — a different field entirely; corrected and added a note distinguishing the two. (3) Step 2's data-pull call never explicitly said how it changes when `subScenario` is set (extra `filters`/`metrics` for `spDeepDive`/`sbNtb`) — the connection was only implied by the separate "Sub-Scenarios" section, which an agent executing Step 2 in isolation could easily miss; added explicit per-`subScenario` call adjustments directly into Step 2. (4) Three places (frontmatter description, "Not for," "Not Covered by This Skill") still said product-level diagnosis needed "a dedicated skill, not yet built" — `sparkx-product-diagnosis` was built after this skill and these references were never updated; repointed to it, keeping only keyword/search-term diagnosis as still not-yet-built.
- **v0.2.0** (2026-07-24) · Compared this skill against the product's own live "Campaign Type Analysis" custom-board template and made three changes based on it. (1) Added `CPA` to the default `focusMetrics` — the real dashboard treats CPA and ACOS as equally core comparison metrics, not ACOS alone. (2) Added an `includeTrend` parameter (default `true`) and a new Step 2c: a weekly-grouped data pull per segment, plus a Step 3 trend view and a markdown/`structured_report` section for it — the real dashboard's primary presentation is a per-segment ACOS/CPA trend line over the window, not just a single-period snapshot, and a snapshot alone can average away a mid-window shift (e.g. a segment whose ACOS was stable for weeks and then spiked in the last one). (3) Added a note under Sub-Scenarios: the live template pairs the campaign-type view with a search-term match-type breakdown as a companion chart — out of scope for this skill (belongs to the not-yet-built search-term-analysis skill), but worth saying so explicitly when a customer's ask naturally extends there, instead of silently ignoring the adjacency.
- **v0.2.1** (2026-07-24) · Two more review issues, both confirmed against the file. (1) Step 1's `language` guidance still told the agent to pass `language` to `get_entity_metadata` as well as `get_ads_perf` — but `get_entity_metadata` has no `language` parameter in its documented parameter list (same class of bug already fixed in `sparkx-product-diagnosis`); corrected to scope `language` to `get_ads_perf` only, with `get_entity_metadata` enum values localized via the returned `{field}Text` companion fields or `sparkx-query-entity-metadata`'s own `enum-i18n.md`. (2) Step 2c's weekly-trend data pull only illustrated the case where the breakdown dimension is a native field (e.g. `campaign.campaignType_`) added alongside a `week` aggregation expression — but `breakdownBy=dayOfWeek`/`subScenario=weekdayWeekend` have no native field to add that way, since "which weekday" isn't a server-side dimension; added an explicit note that for those cases the trend pull is still `select: ["date"]` only, with both the weekday/weekend label and the week bucket derived client-side per date, then organized as segment × week from those two derived labels together.
- **v0.2.2** (2026-07-28) · Renamed the cross-reference "weekly-aggregation example" → "aggregation-over-time example" (Step 2's split-window guidance and `references/platform-notes.md`) so it matches the base `sparkx-query-ads-performance` skill's actual file, `example-aggregation-over-time.md` — the old name predated the file's rename and no longer resolved. Doc-only; no behavioral change.
- **v0.2.3** (2026-07-28) · Added an explicit dependency declaration to the Scope section (needs `sparkx-query-ads-performance`/`sparkx-query-entity-metadata` installed as sibling skills for the `../query-.../…` cross-references to resolve). Links unchanged — they're correct for the standard flat `.claude/skills/<name>/` layout; the note just makes the install dependency explicit.
- **v1.0.0** (2026-08-18) - First stable release; moved from `skills/optional/` to the top-level `skills/` folder alongside the required skills.
- **v1.0.1** (2026-08-25) - Added an `hourOfDay` breakdown backed by hourly (AMS) data, with its campaign-only / 7-day / sampling-disclosure constraints spelled out. Platform-behavior sync: all-or-nothing `profileIds`, strict `pageSize`/`page` validation, `language` default `en`. Removed a reference to a design draft that doesn't ship with the skill.
