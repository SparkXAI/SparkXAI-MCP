---
name: sparkx-asin-deep-dive
description: >-
  Diagnose one named ASIN or parent ASIN: why sales fell or ACOS rose, where traffic comes from,
  whether its ad structure is fragmented, and which variants deserve budget. Combine account ad
  data with SQP / ABA demand and share, limited competitorProduct data and brand peer benchmarks;
  use the customer's SellerSprite for organic rank and broader category comparisons when available.
  Use for "这个 ASIN 为什么销售下滑 / ACOS 为什么高" or "哪个子体该留". Read-only recommendations.
  To find which products need diagnosis first, use sparkx-product-diagnosis; for search-term
  negatives or harvest decisions use sparkx-search-term-diagnosis.
  For store-, category- or brand-level SQP analysis use sparkx-sqp-insight.
metadata:
  version: 1.0.0
---

# ASIN Deep Dive

`sparkx-product-diagnosis` answers **which products have a problem**. This skill answers **why this
one does**, for a single ASIN or parent ASIN, and it is the heavier of the two by design — it pulls
targeting, search terms, placements and operation logs that a catalogue-wide pass cannot afford.

## Scope: This Is an Orchestration Skill, Not a New MCP Tool

It calls `get_user_authorized_context`, `get_ads_perf`, `get_entity_metadata` and
`get_operation_log`, and uses `get_market_search_perf` / `get_peer_benchmark` when the question
and coverage warrant them. It can also use the customer's own SellerSprite MCP when connected.
It writes nothing. Every "pause", "lower the bid", "add a negative" in the
output is **a recommendation for a human to execute**, and the report must never say "已优化".

Three things it deliberately does not do itself, because another skill already does them:

| Not here | Where | Why not duplicate it |
|---|---|---|
| Negative-keyword and harvest decisions | `sparkx-search-term-diagnosis` | It derives its thresholds from the store's own order value and target ACOS; a second copy would drift from it |
| Account-wide channel / marketplace / portfolio share | `sparkx-ads-structure-analysis` | Different unit — that one divides an account, this one dives into a product |
| Judging which AI managed-group switches should be on | A managed-group audit | The action space differs per ad type (SP, SB and SD do not expose the same switches). **Do not write a fixed switch list into this skill** — see "Managed groups" below |

## Output Language: Always Match the User, Never Hard-Code Chinese or English

The templates below are written in Chinese because that matches this product's primary customer
base. They are **structural illustrations, not literal text**. Produce the report in whatever
language the user asked in, and set `get_ads_perf`'s `language` parameter to match.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `asin` | string | **Yes** | — | The ASIN to diagnose. A parent ASIN switches the report to parent mode (all children covered) |
| `profileIds` | array[long] | No | — | Resolved the same way as the rest of the family; the ownership gate below must pass before anything is pulled |
| `granularity` | enum | No | inferred | `asin` \| `parentAsin`. Inferred from whether `asin` resolves to a parent; state which mode you ran in |
| `dateStart` / `dateEnd` | string (`YYYY-MM-DD`) | No | Trailing 30 days ending yesterday | The analysis window. The comparison window is the immediately preceding equal-length period |
| `focus` | enum | No | `balanced` | `balanced` \| `traffic` \| `structure` \| `acos` \| `variants` — which module to go deepest on. `balanced` gives all of them equal depth |
| `targetAcos` | number | No | — | The customer's own target or break-even ACOS. **Without it, efficiency judgements are relative to this product's own baseline and must be labelled 盈利阈值待确认.** Never substitute an industry figure |
| `thresholds` | object | No | the defaults in each section | Customer overrides for any analysis cut-point — `wasteClicksMin`, `wasteSpendMin`, `lowStockDays`, `autoCampaignsMax`, `fragmentCampaignsMax`, `concentrationTop`. **Echo the values you actually used**, so a reader can reproduce every classification |

**Every number in this skill is an analysis cut-point, not a rule.** They live in `thresholds`
with a stated default and must be printed in the output. A threshold that appears only in prose
cannot be tuned per customer and cannot be audited — and a bid or budget figure hard-coded into a
published skill is a review finding, not a feature.

## Step 0 · Two gates, in this order

### 0a. Profile ownership — hard gate, blocks everything

Call `get_user_authorized_context`. A tool being listed is **not** proof of a connection: it must
return `userId` and authorized profiles for the tenant that owns this ASIN. Then confirm the ASIN actually sits in
that profile with `get_entity_metadata` (`entity=asin`) — **not** by requiring product-ad rows.
A product that was never advertised, whose ads were removed, or that runs only SB/SD (where the
promoted-product dimension does not exist) has no product-ad rows and is still perfectly ownable
and diagnosable. When ownership holds but no ad rows come back, say so and run the modules that
business and configuration data can still support.

If this fails, **stop**. Do not produce a report with estimated, remembered or placeholder ad
figures. A diagnosis whose advertising half is invented is worse than no diagnosis.

### 0b. Market and competitor data — platform first, SellerSprite for the rest

Several of these questions are answerable from this platform, and those come first because they
need no third-party entitlement. Load `sparkx-query-market-data` for them - **it is a dependency
of this skill, not an alternative to it**: its reference files carry the coverage limits, week
alignment and low-sample rules these modules rest on, and the numbers cannot be read correctly
without them. Each of its two tools degrades on its own:

| Missing | What changes |
|---|---|
| `sparkx-query-market-data` not installed | Both market modules (market position, competitors from ABA) run the substitute path in [`sellersprite-fallback.md`](references/sellersprite-fallback.md) |
| `sqp:read` (or menu permission `MCP_tool_SQP_ABA`) only | SQP / ABA modules run the substitute path; the brand peer background still runs if `benchmark:read` is there |
| `benchmark:read` (or menu permission `MCP_tool_benchmark`) only | Only the brand peer background line is dropped; SQP / ABA demand, share and top-3 still run |

Say which permission was missing and what it would have added; never drop a module whose own
permission is present.

| Question | Where |
|---|---|
| Demand for the ASIN's terms, and our share of it | `get_market_search_perf` (SQP) |
| Who else is taking the clicks on those terms | the ABA top-3 columns on the same rows - **candidates, not confirmed competitors**, see below |
| Which similar or related products appear in the current recommendation report | `get_entity_metadata(entity=competitorProduct)`, when the parent ASIN and permission are available; top 60 per report type, refreshed daily |
| Whether the **brand** this ASIN belongs to runs above or below its peers | `get_peer_benchmark`, as background only |

⚠️ **ABA top-3 ASINs are not automatically competitors.** They are whatever took the most
clicks on that **search term**, which can include this store's own products, sibling variants
of the same parent, or items from a different category that happen to rank for the term. Check
each one's identity before naming it a competitor - against the store's own ASIN list, and
against `competitorProduct` where that is available. Describing an own-brand ASIN as a
competitor in a customer report is the error this prevents.

⚠️ **The ad half and the market half cover different periods.** Ad metrics cover the date range
you requested (typically the last 30 days); SQP and ABA are aligned outward to whole weeks
(Sunday-Saturday), so their window is wider and rarely starts on the same day. Label each
section with the period that produced it, and never compute a ratio that mixes the two.

`competitorProduct` needs one authorized profile, the product's parent ASIN from
`entity=asin`, `reportType=1` (similar) or `2` (related), and `All_Product_List` permission.
It returns a current, daily offline top-60 list per report type, not all competitors or a
historical comparison. An empty report with no update time is not proof of no competitors;
`star` is the star rating, while `rating` is the review count.

⚠️ **`get_peer_benchmark` has no ASIN-level and no campaign-level grain.** A row is
brand x browse category x ad product x campaign goal, and its own value is the brand's total.
It can never say this ASIN is efficient or inefficient. Use it only to frame the brand's
position - "the brand sits below its peer median on ROAS for SP conversion campaigns" - and
only when a default-node row exists for that brand and category. Then attribute the ASIN's
result to this ASIN's own evidence, not to the brand row. The usage rules are in
`sparkx-query-market-data`'s `references/peer-benchmark.md`; read them before quoting a
percentile.

Two limits decide whether that path exists at all, and both must be checked before promising
it: market search data covers **Seller profiles in US, CA, UK, DE, FR, IT, ES and JP only**,
and a peer benchmark needs a default category node for the brand - roughly 4 in 10 brand x
category cells have none. When either is missing, say which one and move on.

**SellerSprite still owns what the platform cannot answer**: organic (non-ad) keyword rank,
category-wide position against sellers who are not our advertising peers, and broader competitor
coverage beyond the ABA top 3 and the available competitorProduct reports. The latter can include
products this account never targeted; do not describe it as a targeting-only list.
**Detect it by calling it, not by reading a tool list** — the tool name can be present while
the account has no entitlement.

| Branch | What to do |
|---|---|
| **Connected** (a cheap probe returns data) | Run the full market modules |
| **Not connected** | Tell the user once what connecting SellerSprite would add beyond the available platform data — organic keyword rank, broader category and competitor comparisons — and what the report already answered without it. Let them decide |
| **Declined, or no response** | Run the substitute path in [`sellersprite-fallback.md`](references/sellersprite-fallback.md). **Do not leave the sections blank** |

The substitute path fills only gaps left after the available platform market and competitor data.
It can use price and BSR within the account, product targets the account is paying for, and ad
share of total sales. Each section must name its source and what that source cannot answer.

## Step 1 · Evidence scope — fix it before any number is quoted

Read [`evidence-scope.md`](references/evidence-scope.md) and keep its table in front of you for the
whole run. One mistake accounts for most wrong ASIN diagnoses: quoting an ad group's or campaign's
numbers as if they were this ASIN's. They are only this ASIN's when the row is product-ad level.

Label every figure with the scope that produced it. "包含该 ASIN 的广告组表现" and "该 ASIN 的商品
广告表现" are different claims and the second does not follow from the first.

## Step 2 · Pull

Two performance windows (current and the preceding equal-length period) at these grains, scoped to
this ASIN's campaigns and ad groups: `productAd` (ASIN-specific), `adGroup`, `target`, `searchTerm`,
`placement`, and `asin` for business totals (`TotalSalesAmount`, `Sessions`, `TACOS`,
`BuyBoxPercentage`). Configuration from `get_entity_metadata` (`campaign`, `adGroup`, `productAd`,
`asin`, `aiGroup`). History from `get_operation_log`, scoped to the carrying campaigns/ad groups.

**The operation-log completeness gate**: before writing any sentence of the form "只有 N 次人工操作"
or "AI 只在某天动过", confirm the log is fully paginated and covers the whole window. An incomplete
log reads exactly like an inactive account.

## Step 3 · The modules

Run all of them under `balanced`; go deepest on the one `focus` names. Each module states its own
evidence scope and its own cut-points.

1. **市场位置** — SQP term demand and share where covered; SellerSprite for broader category
   comparisons, or the account price/BSR substitute for the remaining gap
2. **竞品** — ABA top-3 for named terms, the current `competitorProduct` list when available,
   SellerSprite for broader comparisons, and product-target spend from `target` rows with
   `queryType: product` for "which ASINs are we paying to target, and do they pay back"
3. **流量结构** — organic vs ad share, entrance concentration (Top1/Top2/Top5 share of orders,
   sales and spend). Two ratios, both available without SellerSprite and **not interchangeable**:
   `TACOS` is ad **spend** over total sales (what the business pays for advertising), while
   ad-sales share is ad-**attributed sales** over `TotalSalesAmount` (how much of the business
   advertising brings in). Name which one each figure is
4. **广告结构** — targeting mix by match type, duplicate bidding, fragmentation and concentration.
   Method and the CPC/CVR/CPA joint rule in [`ad-structure.md`](references/ad-structure.md)
5. **SB / SD / 受众** — coverage and efficiency by ad type; audience binding is read from
   `campaignId`-level configuration, and an empty `audienceId` on SD means *unsupported*, not unbound
6. **变体与库存** — parent mode only. Per-child spend share, efficiency, stock cover and Buy Box.
   Pause recommendations carry scope, replacement entrance and re-entry condition
7. **ACOS 机制归因** — why the same clicks stopped converting. Mechanism before identity: find the
   change point first, then test more than one hypothesis, then grade the evidence A/B/C

### Managed groups: report what the API returned, judge nothing

If this ASIN's campaigns sit in AI managed groups, report the facts — group name, state, objective,
target ACOS, actual ACOS, whether it is meeting target — **and whatever action-space switches that
group actually returned, exactly as many as came back.**

**Do not write a switch list into this skill.** The action space differs by ad type, so any fixed
count is wrong for two of the three types. Read, report, and say that deciding which switches
should change is a managed-group audit, not part of this report.

## Step 4 · Output

Markdown by default. Lead with the answer, not the method:

```
# ASIN 诊断 · {asin} · {date_start} ~ {date_end}

对比期：{compare_start} ~ {compare_end}（等长前置）
数据路径：广告 SparkX 直连｜市场 {SQP/ABA + 同行基准 / 卖家精灵 / 替代口径（纯 SparkX）}——每节标明来源
{盈利阈值待确认（客户未提供目标 ACOS）}

## 结论

{两三句。先说这个 ASIN 到底怎么了，再说最该先改的一件事}

## 一、生意与广告总盘
## 二、市场位置{（替代口径）}
## 三、竞品{（替代口径：我们在打谁）}
## 四、流量结构
## 五、广告结构
## 六、SB / SD / 受众
## 七、变体与库存        {父 ASIN 模式}
## 八、ACOS 机制归因
## 九、托管组现状（事实，不含判断）
## 十、建议与验证方式

---
_数据路径：{...}　阈值：{echo the thresholds actually used}　Skill: sparkx-asin-deep-dive v{version}_
```

Every recommendation carries **action + target + evidence + how to verify it**. A recommendation
without a verification condition cannot be reviewed next period, which is the only way anyone finds
out whether this report was right.

## What this skill must not do

1. **No writes.** Not one. Execution goes to `sparkx-edit-ads` / `sparkx-edit-ai-group`, each with
   its own confirmation flow.
2. **No invented market data.** Missing SellerSprite does **not** mean the substitute path on its
   own — first use the platform's SQP / ABA and, where a default-node row exists, the brand peer
    benchmark; use `competitorProduct` when available. The substitute path covers only what is
    left (organic rank, broader category and competitor comparisons). Label every section with the
    path that produced it, and never give a
   remembered or estimated competitor figure.
3. **No ASIN-level peer claim.** Peer benchmarks are brand x category; saying "this ASIN beats its
   peers" is not something the data can support.
4. **No fixed managed-group switch list.** Report what came back.
5. **No industry-default target ACOS.** Without the customer's number, judge relative to this
   product's own baseline and say so.
6. **Correlation is not causation.** An operation that coincides with a decline is a lead. It
   becomes an attribution only when the mechanism holds and the alternatives are excluded.
7. **No claim that a cut will not cost sales.** Cross-SKU attribution is missing, so every
   reduction is a reversible small-step test with a stated verification window.

## Files

| File | Contents |
|---|---|
| [`references/data-contract.md`](references/data-contract.md) | Call-level rules: the two ID systems, disallowed joins, per-entity notes, pagination, the operation-log completeness gate, metric recomputation |
| [`references/evidence-scope.md`](references/evidence-scope.md) | What each data grain can and cannot prove. Read before quoting any figure |
| [`references/sellersprite-fallback.md`](references/sellersprite-fallback.md) | The three substitute analyses when SellerSprite is absent, and what each cannot answer |
| [`references/ad-structure.md`](references/ad-structure.md) | Targeting mix, duplicate bidding, concentration, and the CPC/CVR/CPA joint rule |
| [`references/platform-notes.md`](references/platform-notes.md) | Shared platform behaviour (auth, errors, pagination, currency) |
