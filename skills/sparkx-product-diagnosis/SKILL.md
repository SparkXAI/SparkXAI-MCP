---
name: sparkx-product-diagnosis
description: >-
  Diagnose product-level (ASIN) health: rank products by spend/sales/ACOS, segment the catalog into
  a lifecycle tier (star / core / long-tail / new / declining), compare sibling variants under a
  parent ASIN, produce a diagnostic card for flagged underperformers (inventory/eligibility/buy-box
  issues, correlated operation-log changes), and give keep/optimize/cut recommendations. Use when
  the user asks "我哪些 ASIN 有问题", "变体谁在拖后腿", "新品该不该继续投", "product diagnosis",
  "ASIN health check". Not for account-wide structural share analysis (use sparkx-ads-structure-analysis)
  or periodic WoW/MoM recaps (use sparkx-weekly-ads-report / sparkx-monthly-ads-report).
metadata:
  version: 1.0.4
---

# Product Diagnosis

## Scope: This Is an Orchestration Skill, Not a New MCP Tool

This skill does **not** map to a single MCP tool of its own — it orchestrates three existing read tools, each already covered by its own skill:

- `get_ads_perf` → [sparkx-query-ads-performance](../sparkx-query-ads-performance/SKILL.md)
- `get_entity_metadata` → [sparkx-query-entity-metadata](../sparkx-query-entity-metadata/SKILL.md)
- `get_operation_log` → [sparkx-query-operation-log](../sparkx-query-operation-log/SKILL.md) (used in Step 2e for the diagnostic card's correlated-changes check)

> **Dependency — install these three base skills alongside this one:** `sparkx-query-ads-performance`, `sparkx-query-entity-metadata`, `sparkx-query-operation-log`. Skills install as sibling directories under your current agent's skills root (`.claude/skills/<name>/` for Claude Code; the equivalent root for other agents — see the [supported-agents table](../../README.md)), which is exactly what the `../query-.../…` links above (and elsewhere in this doc) resolve against — if a base skill isn't installed there, those links won't resolve and this skill can't run. Install all three first.

**Read all three SKILL.md files first** (parameter formats, field-naming rules, the Ratio Metric Display Rule, and — specific to this skill — [`references/ad-type-dependent-metrics.md`](references/ad-type-dependent-metrics.md)'s rule that ASIN business metrics must never be joined or filtered against campaign/adGroup/aiGroup-level fields) plus [`references/platform-notes.md`](references/platform-notes.md) (auth flow, error handling, pagination, date-range limits, currency rules). This document only covers logic specific to product diagnosis; it doesn't repeat what the base skills already document.

Rewritten against the new tool's conventions from the start — carries forward the discipline established across `sparkx-weekly-ads-report`/`sparkx-monthly-ads-report`/`sparkx-ads-structure-analysis`: full `profileIds` resolution rules, currency-aware thresholds, output-language adaptivity, disclosed sampling fallback, and zero-denominator handling.

## Output Language: Always Match the User, Never Hard-Code Chinese or English

**The worked examples and output templates below are written in Chinese** (matching this product's primary customer base), but they are **structural illustrations, not literal text to copy verbatim**. Generate the actual report in whatever language the user asked in. When calling `get_ads_perf`, also set the `language` parameter (`zh`/`en`/`ja`) to match the customer's language. **`get_entity_metadata` has no `language` parameter** — it's not in that tool's documented parameter list. Localize its enum values (e.g. `asinInventoryStatus`, `asinSpEligibilityStatus`) using the returned `{field}Text` companion fields, or `sparkx-query-entity-metadata`'s **own** [`enum-i18n.md`](../sparkx-query-entity-metadata/references/enum-i18n.md) if a given enum has no `Text` companion — that tool's enum-i18n file, not `sparkx-query-ads-performance`'s, since the two don't cover an identical field set. Only fall back to `sparkx-query-ads-performance`'s [`enum-i18n.md`](../sparkx-query-ads-performance/references/enum-i18n.md) for fields that are actually `get_ads_perf` fields (e.g. when this skill's Step 2a/2b calls need enum labels). Don't pass `language` to `get_entity_metadata` expecting it to have the same effect as on `get_ads_perf`.

## When to Use

**Trigger phrases**: 商品诊断, 哪些 ASIN 有问题, 变体对比, 新品该不该投, product diagnosis, ASIN health

**User roles**: ads managers, account managers doing a product-level deep-dive

**Core question**: which products are healthy, which need attention, and what specifically is wrong with the ones that don't

**Not for**:
- Account-wide spend/efficiency structure by campaign type / site / portfolio → `sparkx-ads-structure-analysis`
- Periodic WoW/MoM cadence recaps → `sparkx-weekly-ads-report` / `sparkx-monthly-ads-report`
- Keyword/search-term level diagnosis → a dedicated skill (not yet built)

## Input Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `profileIds` | array[long] | No | — | See "Resolving `profileIds`" below |
| `granularity` | enum | No | `asin` | `asin` (child ASIN) \| `parentAsin` \| `variant` (siblings under one parent — requires `parentAsin` or a specific ASIN to anchor on, see "Granularity" below) |
| `scope` | enum | No | `topN` | `topN` \| `all` \| `specifiedAsins` \| `underperformingOnly` |
| `topN` | int | No | 20 | Only used when `scope=topN` |
| `specifiedAsins` | array[string] | No | — | Only used when `scope=specifiedAsins` |
| `dateStart` / `dateEnd` | string (`YYYY-MM-DD`) | No | Trailing 30 days ending yesterday | The analysis window — must satisfy the 90-day span / 15-month lookback caps like any other `get_ads_perf` call |

### Resolving `profileIds`

Always call `get_user_authorized_context` first to get the authorized `profiles` list, then apply exactly one of these cases:

1. **The user named specific store(s)** → resolve the name(s) against the authorized list and query only the matching profile(s).
2. **The user explicitly said "all stores" / "全账号" / equivalent** → query all authorized `profileIds`.
3. **The user didn't name a store, and there's only one authorized profile** → use it directly — there's nothing to ask.
4. **The user didn't name a store, and there are multiple authorized profiles**:
   - **5 or fewer** → you may default to using all of them.
   - **More than 5** → do not silently roll everyone up. Hand the user the `profiles` list and ask them to pick one, several, or explicitly confirm "all stores" first.

### Granularity

**`asin`** (default) — child ASIN is the unit of analysis throughout.

**`parentAsin`** — roll up to the parent level. Query `get_ads_perf` (`factEntity: asin`) with `select` including `asin.parent_asin_`, and aggregate child-ASIN rows under the same parent client-side (this tool has no native `factEntity: parentAsin` for performance data — only `get_entity_metadata`'s `asin` entity nests parent-ASIN fields alongside child fields, and that's metadata, not performance metrics).

**`variant`** — compare sibling child ASINs under one parent. **Requires an anchor**: either the user names a specific parent ASIN, or names one child ASIN (resolve its `parentAsin` via `get_entity_metadata` first — plain camelCase, that tool's convention, not `get_ads_perf`'s `asin.parent_asin_` — then pull all children under that parent). Don't attempt a "variant" comparison across the whole catalog at once — it's inherently a one-parent-at-a-time comparison; if the user wants this for many parents, run it once per parent and present each as its own comparison, not a single merged table.

## Workflow

### Step 1 · Define the Analysis Window

Default: trailing 30 days ending yesterday (T+2 delay — note if the window's end is within 2 days of today, the most recent day(s) may be incomplete). If the user gives an explicit range, confirm it satisfies the 90-day span / 15-month lookback caps before issuing the call; split into multiple ≤90-day calls if it doesn't, per the standard procedure.

**Also define a comparison window** (immediately preceding period, same length) — needed for Step 3's "declining" lifecycle tier and Step 5's diagnostic correlation. Same equal-length-prior-period discipline as the report skills.

### Step 2 · Pull Data

**a. This-period ASIN performance**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "asin",
  "dateStart": "{window start}",
  "dateEnd": "{window end}",
  "select": ["asin.asin_", "asin.asinTitle_", "asin.parent_asin_"],
  "metrics": ["Spend", "Sales", "Conversions", "ACOS", "TotalSalesAmount", "OrderCount", "TACOS", "Sessions", "BuyBoxPercentage", "UnavailabilityRate", "CustomerReturns"],
  "pageSize": 500,
  "userContext": "Product diagnosis - this period's ASIN performance"
}
```
**⚠️ `Spend`/`ACOS` alongside `asin`-only business metrics in one call**: `get_ads_perf`'s ASIN business metrics (`TotalSalesAmount`, `Sessions`, `BuyBoxPercentage`, etc.) are confirmed valid only on `factEntity: asin`, and so are the regular ad metrics when queried at that same `factEntity` — this is fine as one call. What's **not** fine is joining or filtering these `asin`-only business metrics against campaign/adGroup/aiGroup-level fields (see [`ad-type-dependent-metrics.md`](references/ad-type-dependent-metrics.md)) — don't add `campaign.*`/`adGroup.*` dimension fields to this call's `select`.

**⚠️ `Sales` and `TotalSalesAmount` are two different things, both requested deliberately**: `Sales` is ad-attributed sales (the numerator context for `ACOS`, whose formula is `Spend/Sales×100`); `TotalSalesAmount` is the ASIN's total business sales including organic (the denominator for `TACOS`, whose formula is ad `Spend/TotalSalesAmount`). Don't drop either thinking the other covers it — see Step 3's zero-denominator handling, which depends on both being present.

**⚠️ `TotalSalesAmount`/`TACOS` are Seller Central metrics — they don't exist for a Vendor Central profile** (the product's "ASIN 层级" board labels these columns "(Seller)"). There's no queryable field that proves a profile's account type in advance. If `TotalSalesAmount`/`TACOS` are null/zero on every row while `Spend`/`Sales` are non-zero, treat Vendor Central as a **hypothesis, not a conclusion**: retry with `OrderedRevenue`/`OrderedTACOS` (pre-shipment) or `ShippedRevenue`/`ShippedTACOS` (post-shipment, COGS-aware). Use and relabel the Vendor fields only when that retry returns meaningful data; otherwise report the business-sales field set as unavailable rather than inferring account type from nulls alone.

Scope this call per `scope`:
- `topN` → `orderBy` on the primary ranking metric (default `Spend` descending), `pageSize` = `max(1, min(topN, 500))` — `get_ads_perf` rejects a `pageSize` of `0`, a negative number, or anything over `500` with `invalid_params` (it does **not** clamp), so both ends need guarding: a `topN` of `0` must not become `pageSize: 0`, and if `topN > 500`, keep `pageSize: 500` and loop `page` while `hasNextPage` to collect the remainder instead of requesting an oversized page
- `all` → fully paginate, no `orderBy` requirement, disclosed sampling fallback applies at scale
- `specifiedAsins` → `filters: {"asin.asin_": {"in": [...]}}`, batched per "Batching Large ASIN Lists" below if the list is long
- `underperformingOnly` → pull the full/sampled population first (Step 3-4 needs the full picture to correctly classify "underperforming" relative to the rest of the catalog), then filter to the flagged tiers when presenting — don't pre-filter the query itself on a guessed threshold before you've computed the lifecycle tiers

**`granularity=variant` overrides the above regardless of `scope`**: add `filters: {"asin.parent_asin_": "{anchored parentAsin}"}` to this call (on top of, not instead of, whatever `scope` would otherwise apply) so it returns only the anchored parent's own children — not a `topN`/`all` sweep of the whole catalog. Resolve the anchor's `parentAsin` first (per "Granularity" above) before issuing this call.

**`granularity=parentAsin` also overrides the `topN` scope rule above — don't apply `orderBy`/`pageSize` at the child-ASIN query level.** Ranking by child-level `Spend` and capping `pageSize` *before* aggregating to parents produces an incomplete/wrong parent ranking — a parent whose spend is split across several children, none individually in the child-level top N, would be undercounted or missed entirely, even though its *aggregated* total might rank highly. Instead: fully paginate the child-ASIN population first (or, if that's impractical at catalog scale, fall back to a spend-ranked **child** sample per the disclosed-sampling-fallback rule — and if you do, say explicitly that the parent ranking is therefore based on a child-level sample, not the complete population), aggregate child rows into parents by `asin.parent_asin_` client-side, **then** apply `topN` to the aggregated parent-level results.

**b. Prior-period ASIN performance** — same shape as (a), `dateStart`/`dateEnd` shifted to the comparison window, same `select`/`filters` so the two periods are comparable.

**c. New-product identification**: `get_entity_metadata` (`entity: asin`). **`asinOpenDate` is NOT a filterable field**, so don't filter the call on it. Pull the asin metadata for the current analysis set (**fully paginate — loop `page` while `hasNextPage` is `true`; default page size is 100, so a catalog past one page silently truncates otherwise**), then read the returned `asinOpenDate` and filter to the analysis window **client-side**. `asinOpenDate` is a datetime-with-timezone string, e.g. `"2026-06-01 00:00:00 PST"` (not `YYYYMMDD`, not `YYYY-MM-DD` — `YYYYMMDD` is `campaignStartDate`'s format, not this one), so parse it and mind the **PST timezone**. **Under `scope=specifiedAsins` or `granularity=variant`, scope this pull to the current analysis set** (the user's specified ASIN list, or the anchored parent's children) — don't scan the whole catalog and then tag "New" onto ASINs that aren't part of what's being analyzed.

**d. Eligibility/inventory config** (feeds Step 5's diagnostic card): `get_entity_metadata` (`entity: asin`), for the ASINs flagged in Step 3 as Declining (or explicitly in scope via `underperformingOnly`, per Step 5) — pull `asinInventoryStatus`, `asinSpEligibilityStatus`/`asinSbEligibilityStatus`/`asinSdEligibilityStatus`, `asinIsDelete`. Only pull this for flagged ASINs, not the whole catalog — it's diagnostic detail, not part of the ranking.

**e. Operation log for flagged ASINs** (feeds Step 5): `get_operation_log`, the analysis window, `resourceIds` scoped to `campaignId`/`adGroupId` (resolve each flagged ASIN → its `campaignId`/`adGroupId` via `get_entity_metadata`'s `productAd` entity first, since `get_operation_log` takes IDs, not ASINs directly). **`resourceIds.idEntity` has no `productAd` value** (see `sparkx-query-operation-log`'s field reference) — don't resolve to `amazonAdId` and try to pass it in; use `idEntity: "campaign"`/`"adGroup"` with the resolved `campaignId`/`adGroupId` instead. This returns all operations on that campaign/adGroup, not narrowed to just the one product ad — say so if the customer needs to know the result isn't ASIN-exclusive. **Check `truncated`** and follow the standard split-and-recurse procedure if so.

**⚠️ Steps 2c/2d/2e above are written for `granularity=asin`/`variant` (child-ASIN identity). Under `granularity=parentAsin`, each needs a parent-level adjustment — don't run them unchanged and silently produce child-level diagnostics under a parent-level report:**

- **New (2c)**: use the parent's own `parentAsinOpenDate`, not any individual child's `asinOpenDate`. A parent can have a mix of long-standing and newly-added children; don't infer the parent's "New" status from whichever child happens to be queried first, or from an arbitrary child. If a customer specifically wants to know "which children under this parent are new," report that as a supplementary note on the parent's diagnostic card, not as the parent's own tier.
- **Eligibility/inventory (2d)**: prefer the parent-level fields — `parentAsinInventoryStatus`, `parentAsinSpEligibilityStatus`/`parentAsinSbEligibilityStatus`/`parentAsinSdEligibilityStatus` — as the primary signal for the parent's diagnostic card. **There is no `parentAsinIsDelete` field** (`get_entity_metadata`'s documented parent-ASIN fields don't include a parent-level delete flag — only the child-level `asinIsDelete` exists) — don't invent one; if deletion status matters at the parent level, check whether *all* children are individually `asinIsDelete=1` instead. If the parent-level status looks healthy but the parent's aggregated performance is still flagged as Declining/underperforming, additionally check the individual children's `asinInventoryStatus`/eligibility (from 2d's child-level pull) to find which specific child is actually driving the problem, and list it as supporting detail under the parent's card.
- **Operation log (2e)**: expand the parent to its full child-ASIN list first (`get_entity_metadata`, `entity: asin`, `filters: {"parentAsin": "{parent}"}`), then resolve **each** child's `campaignId`/`adGroupId` via the `productAd` entity (same as the child-level procedure), and query `get_operation_log` across all of them. This is still campaign/adGroup-level, not parent/ASIN-exclusive — label it as such in the diagnostic card the same way the child-level version does, and additionally note it covers operations across all the parent's children, not just one.

**Batching Large ASIN Lists** — the filter field differs by tool, don't carry one convention into the other:
- **`get_ads_perf`** (Step 2a/2b's `specifiedAsins` scope): filter field is `asin.asin_` (that tool's `entity.field_` convention).
- **`get_entity_metadata`** (Step 2c/d's flagged-ASIN follow-ups): filter field is plain `asin` (no prefix/suffix — that tool's camelCase convention).

Either way, when the list is long: split into chunks for the `in` filter rather than one unbounded call, fully paginate each batch, and merge/dedupe results by ASIN.

**Fully paginate (a)/(b) before analyzing** — loop `page` while `hasNextPage` is `true`. **If full pagination would be impractical at scale** (very large catalogs under `scope=all`), you may fall back to a spend-ranked sample instead of the full population — this fallback **must be disclosed explicitly**, stating what was actually covered, and **a degraded section must not fail the whole diagnosis** — produce whatever's complete and mark only the affected part as partial.

### Step 3 · Rank and Segment

**Ranking table**: sort by the requested/default metric (`Spend` unless the user asked for `Sales`/`ACOS` ranking specifically), showing `Spend`/`TotalSalesAmount`/`ACOS`/`TACOS` per ASIN. **Zero-denominator handling — `ACOS` and `TACOS` have different denominators, don't conflate them**: an ASIN with `Sales = 0` (ad-attributed sales) has undefined `ACOS`; an ASIN with `TotalSalesAmount = 0` (total business sales) has undefined `TACOS` — these can differ (e.g. an ASIN can have `Sales = 0` this period while still showing organic `TotalSalesAmount`, or vice versa). Check each independently and report "no ad sales this period" / "no total sales this period" as appropriate, never a fabricated ratio for either. **Before reporting `TotalSalesAmount = 0`/`TACOS` undefined account-wide (every row, not just one ASIN), rule out the Seller/Vendor mismatch from Step 2a first** — an all-zero `TotalSalesAmount` column on a Vendor Central profile isn't a zero-denominator finding, it's the wrong field set.

**Lifecycle segmentation** — classify each analysis entity (a child ASIN under `granularity=asin`/`variant`, or a parent ASIN under `granularity=parentAsin` — don't revert to child-level classification just because the underlying rows started as child-ASIN data) into exactly one tier:
- **新品 (New)**: identified in Step 2c (opened within the analysis window). Takes priority over other tiers — a new product's low volume is expected, not "long-tail" or "declining."
- **明星 (Star)**: top spend-share band **and** efficiency at or better than the catalog average (ACOS at or below average, or TACOS trending down if available) — meaningfully contributing **and** performing well.
- **腰部 (Core)**: meaningful volume, efficiency roughly at the catalog average — the bulk of a healthy catalog, not itself a finding.
- **长尾 (Long-tail)**: low spend/sales share, has existed longer than the "new" window, performance roughly stable (not declining) — low-volume but not necessarily unhealthy.
- **濒死 (Declining)**: this-period `Sales`/`Conversions` meaningfully down vs. the prior period (Step 2b), **and** not a new product. Use the same join-by-ID, zero-denominator-aware period-comparison discipline as [sparkx-query-ads-performance's Period-over-Period and Top Movers example](../sparkx-query-ads-performance/references/example-period-comparison-top-movers.md) — an ASIN with `Sales = 0` in the prior period and `Sales = 0` now is "flat/no activity," not "declining."

**Currency-aware thresholds throughout**: define "meaningful" band cutoffs (spend share, ACOS deviation from average) proportionally, not as a hardcoded absolute dollar figure — a fixed-dollar cutoff breaks for non-USD single-store analyses the same way it would in the other skills in this family.

### Step 4 · Variant Comparison (if `granularity=variant`)

For the anchored parent's child ASINs (from Step 2a/b, filtered to that `parent_asin_`): compare each sibling's spend share within the parent, ACOS, and `BuyBoxPercentage`/`UnavailabilityRate` — variants of the same product often compete for the same demand, so a spend/efficiency imbalance here is a genuine "which variant should get the budget" finding, distinct from the catalog-wide lifecycle tiers in Step 3.

### Step 5 · Diagnostic Card (for flagged underperformers — Declining tier, or explicitly `scope=underperformingOnly`)

For each flagged entity (ASIN or parent ASIN — see the parent-mode adjustments to 2c/2d/2e above; don't drop back to child-only fields under `granularity=parentAsin`), assemble:
- **Inventory/eligibility status** (Step 2d): out-of-stock (`asinInventoryStatus`/`parentAsinInventoryStatus`), lost ad-type eligibility, or — child level only, no parent equivalent exists — deleted (`asinIsDelete`) — these can fully explain a sales collapse on their own and should be surfaced before anything else.
- **Buy Box / returns signal** (Step 2a): a `BuyBoxPercentage` drop or elevated `CustomerReturns` alongside declining sales is a strong non-advertising explanation — flag it as such rather than assuming the cause is bid/budget-related.
- **Correlated operation-log changes** (Step 2e): bid/budget/status changes on the campaigns/adGroups containing this ASIN's product ads in the same window — **not** changes on the ASIN itself (per Step 2e, `get_operation_log` can't be scoped to a single `productAd`/ASIN, only to `campaign`/`adGroup`). Label this explicitly in the diagnostic card (e.g. "非 ASIN 专属——该 campaign/adGroup 下的操作记录") so it isn't read as ASIN-specific evidence. **Correlation, not causation** — same discipline as the report skills: state what changed and when, don't claim it caused the decline unless the timing and magnitude clearly line up, and weigh that correlation more cautiously here given the change wasn't even necessarily on this specific product ad.

If none of the above turns up anything, say so plainly ("no inventory/eligibility/buy-box issue found, no correlated operation-log change found") rather than forcing a narrative onto an unexplained decline.

### Step 6 · Recommendations (Keep / Optimize / Cut)

Derive one verdict per flagged ASIN (and optionally per healthy-tier ASIN if the user wants a full-catalog verdict, not just the problems):
- **保 (Keep)**: Star or healthy Core tier — no action needed, or note it as a candidate for the *other* skill (`sparkx-ads-structure-analysis`) if there's a structural budget-reallocation angle.
- **优 (Optimize)**: Declining or underperforming Core/Long-tail with a fixable driver identified in Step 5 (e.g. restock, bid adjustment, buy-box recovery) — action + evidence.
- **撤 (Cut)**: persistent zero-conversion high-spend with no fixable driver found, or long-tail with negligible volume and no growth signal — action + evidence.

**Every recommendation must have**: action + target ASIN + evidence (data), same requirement as the other skills in this family.

## Multi-Store and Currency

When `profileIds` spans multiple stores:
- All monetary metrics from `get_ads_perf` auto-aggregate to **USD**, **except** `asin.asinPrice_` (if ever used) and ASIN-entity pricing in `get_entity_metadata`, which stay local currency per-row — label dollar amounts "(USD)" explicitly elsewhere.
- Add `profile.profileId_`/`profile.profileName_` to Step 2a/2b's `select` when `profileIds` spans multiple stores, so a ranking/lifecycle-tier call can attribute each ASIN to its store — the same ASIN can exist under multiple stores with different performance. **This attribution must actually reach the output**: add a 店铺/Store column to Step 3's ranking table (and the markdown template's table below) whenever `profileIds` has more than one entry, and add `profileId`/`profileName` to `structured_report`'s `ranking` entries in the same case — don't pull the per-store `select` fields in Step 2a/2b only to drop them before presenting.

## Output Format

### markdown mode

```markdown
# 商品诊断 · {profile_name}
**维度**：{asin / parentAsin / variant}　**范围**：{topN / all / 指定ASIN / 仅问题商品}
**周期**：{dateStart} ~ {dateEnd}
{If data may be incomplete due to T+2 delay, or a section is based on a partial sample, note it here}
{若 profileIds 涉及多个店铺，标题的 {profile_name} 不要写死单个店铺名——改成店铺列表或 "{N}个店铺"，具体归因见下方排名表的店铺列}

## 一、商品排名表

{列名用 "ASIN" 还是 "Parent ASIN" 取决于 granularity：asin/variant 用 "ASIN"，parentAsin 用 "Parent ASIN"——不要不管 granularity 都固定写 "ASIN"}
{仅当 profileIds 涉及多个店铺时才加"店铺"列——单店铺场景不要加这一列造成冗余}

| ASIN / Parent ASIN | 店铺（仅多店铺时） | 花费 | 广告销售额 | ACOS | 总销售额 | TACOS | 订单数 / 转化数 | 分层 |
|---|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... | ... | 明星/腰部/长尾/新品/濒死 |

## 二、生命周期分层概览

- 明星：{N} 个，贡献 {pct} 花费 / {pct} 销售额
- 腰部：{N} 个
- 长尾：{N} 个
- 新品：{N} 个（本周期内上架）
- 濒死：{N} 个 — 需要关注

## 三、变体对比（若 granularity=variant）

| 变体 ASIN | 花费占比 | ACOS | Buy Box % |
|---|---|---|---|
| ... | ... | ... | ... |

## 四、单品诊断卡（濒死 / 问题商品）

### {ASIN}
- 库存/资格状态：{...}
- Buy Box / 退货信号：{...}
- 关联操作记录（非 ASIN 专属，campaign/adGroup 层面）：{...，标注为关联而非确定因果}

## 五、优化建议

1. **{保/优/撤}** {ASIN}
   - 依据：{data}
2. ...

---
_生成时间：{timestamp} · 数据源：SparkX AI MCP · Skill: sparkx-product-diagnosis v{version}_
```

### structured_report mode

```json
{
  "dimension": "asin",
  "period": {"start": "...", "end": "..."},
  "dataFreshnessWarning": null,
  "ranking": [{"entityId": "...", "entityType": "asin|parentAsin", "profileId": null, "profileName": null, "spend": ..., "sales": ..., "acos": null, "totalSalesAmount": ..., "tacos": null, "orderCount": ..., "conversions": ..., "tier": "star|core|longTail|new|declining"}],
  "tierSummary": {"star": {"count": ..., "spendShare": ...}, "core": {...}, "longTail": {...}, "new": {...}, "declining": {...}},
  "variantComparison": null,
  "diagnosticCards": [{"entityId": "...", "entityType": "asin|parentAsin", "inventoryStatus": "...", "eligibilityIssue": null, "buyBoxSignal": null, "correlatedChanges": [...]}],
  "recommendations": [{"verdict": "keep|optimize|cut", "entityId": "...", "entityType": "asin|parentAsin", "action": "...", "evidence": "..."}]
}
```
`entityId`/`entityType` replace a bare `"asin"` key precisely so each entry is self-describing — a consumer reading one `ranking`/`diagnosticCards`/`recommendations` entry in isolation (not alongside the top-level `dimension`) can still tell whether `entityId` is a child or parent ASIN without cross-referencing back to the top of the payload. `profileId`/`profileName` are `null` when `profileIds` is a single store (nothing to disambiguate); populate them per "Multi-Store and Currency" whenever `profileIds` spans more than one — don't pull the per-store `select` fields upstream and then drop them here.

## Data Boundaries

- **No SKU-level margin/profitability** — this needs the customer's own cost data, out of scope for this skill (a candidate for the "combine with your own business data" pattern used elsewhere in this product, not something this skill computes on its own).
- **Lifecycle tier cutoffs are heuristic**, not a certified business classification — always show the underlying numbers (spend share, ACOS, trend) alongside the tier label so the customer can judge, don't present the tier as an automated verdict beyond dispute.
- **`get_entity_metadata` has no historical-snapshot capability** — inventory/eligibility status in Step 5's diagnostic card reflects the *current* state, not necessarily the state at the time of the decline. Say so if the timing matters and can't be confirmed.
- **`variant` granularity requires an anchor** (a named parent or child ASIN) — there is no "compare all variants across the whole catalog at once" mode; see "Granularity" above.
- **`TotalSalesAmount`/`TACOS` only exist for Seller Central profiles** — Vendor data uses `OrderedRevenue`/`OrderedTACOS` or `ShippedRevenue`/`ShippedTACOS`, and no field reports account type in advance. Follow Step 2a's retry procedure; do not classify the account from nulls alone.

## Example Call

**User input**:
> 看下 Demo US 最近 30 天有哪些 ASIN 表现不好

**Skill flow**:
1. Resolve the profile: `get_user_authorized_context` → find Demo US's `profileId`
2. `scope = underperformingOnly`, window = trailing 30 days ending yesterday
3. Run Steps 2-6
4. Output the markdown report — in Chinese, since the user asked in Chinese

## Error Handling

Follows the shared error envelope used by both underlying tools (`isError`/`errorType`, see [`references/platform-notes.md`](references/platform-notes.md)).

| Situation | Handling |
|---|---|
| `profileIds` is empty | Follow "Resolving `profileIds`" above — ask only when those rules require it |
| Any call returns `isError: true` | Handle per `errorType` — `invalid_params` usually means a construction bug in this skill's own call; `rate_limited` → wait `retryAfterSeconds` |
| `effectiveProfileIds` doesn't match requested `profileIds` | Explain the scope mismatch before concluding "no data" |
| An ASIN has `Sales = 0` | `ACOS` is undefined — report "no ad-attributed sales this period," don't compute it against a zero denominator |
| An ASIN has `TotalSalesAmount = 0` | `TACOS` is undefined — report "no total sales this period," independently of whether `Sales` is also zero |
| `get_operation_log` returns `truncated: true` | Split into sub-windows per its "Getting a Complete Count" procedure |
| A degraded/sampled section | Disclose what was covered; don't fail the whole diagnosis over one segment's pagination trouble |

## Not Covered by This Skill

- Account-wide structural share analysis → `sparkx-ads-structure-analysis`
- Periodic WoW/MoM cadence recaps → `sparkx-weekly-ads-report` / `sparkx-monthly-ads-report`
- Search-term/keyword-level diagnosis → a dedicated skill (not yet built)
- SKU-level margin/profitability (needs the customer's own cost data)
