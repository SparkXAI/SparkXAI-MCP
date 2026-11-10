# Managed-Group Customer Display

Use this guide whenever presenting an `aiGroup` or `aiGroup_schedule` configuration to a
customer. It defines the product-facing labels and grouping; the response object's nesting is a
transport schema, not the UI information architecture.

## Language and Raw Fields

- Match the user's language. A Chinese question gets Chinese product labels; an English question
  gets English product labels.
- Do not show backend keys (`bidPerformanceStatus`, `aiActionSettings`, `aiAutomation`), rule
  numbers (`Rule 17`, `ruleType=17`), or raw enum tokens in the main answer.
- Keep a raw key/code only when the user explicitly requests raw API data or technical debugging.
  Put it in a separate technical appendix, never in the customer-facing setting name.
- IDs may be shown when useful, but label them: `aiGroupId` becomes "托管组 ID" / "Managed-group
  ID", and `profileId` becomes "店铺 ID" / "Profile ID".

## Customer-Facing Sections

Use this order for a complete configuration:

1. Basic settings / 基础设置
2. Campaigns / 广告活动
3. Brand, non-brand, and competitor mode / 品牌/非品牌/竞品模式
4. AI Action Space / AI 行动空间
   - Bid optimization / 竞价优化
   - Budget optimization / 预算优化
   - Targeting optimization / 定向优化
   - Structure optimization / 结构优化
5. Automation rules / 自动化规则

## Managed-Group Objective

The objective has two UI levels: a category heading and the selected option. Present the selected
option as **Objective / 目标类型**; the category may be shown as secondary context but must not
replace the selected option. Map from `targetType` instead of copying a returned English enum text
into an answer in another language.

| Internal value | English option | 中文选项 | UI category / 页面大类 |
|---:|---|---|---|
| `1` | Drive growth | 推动增长 | Increase sales / 扩大销量 |
| `2` | Optimize ROAS | 保持订单稳定 | Drive efficiency / 控制成本 |
| `3` | Promotion sales boost | 活动冲量 | Increase sales / 扩大销量 |
| `4` | *(legacy value, no longer offered in the UI)* | *(旧值，UI 无对应选项)* | — |

A group read back with `targetType=4` is a **legacy value from before the current objective UI** — not a current option, and not the same thing as the separate "Budget utilization priority (Beta)" toggle (which is an independent switch, not part of `targetType`; see the create/edit skills' enum reference). Don't render a customer-facing objective name for it. Say the group predates the current objective options and, if the user wants to act on it, that changing it requires selecting one of `1`-`3`.

For a Chinese answer with value `2`, render:

> 目标类型：保持订单稳定
>
> 所属大类：控制成本

Do not render `Optimize ROAS（优化 ROAS / 控制成本，targetType=2）` in the main answer. The English
option, category, and backend value are three different concepts; raw codes belong only in a
technical appendix requested by the user.

## AI Personality

Show AI personality as its numeric level only in customer-facing managed-group and schedule
configuration output:

> AI 人格：4

Do not replace the number with a descriptive enum label such as "激进", "略激进", or
"Aggressive", and do not append the label in parentheses. The returned `aiPersonalityText` is
useful for parsing/debugging only; the product-facing value for this setting is the integer `1`-`5`.

`brandOptimization` is only a backend container. **It is not an AI Action Space section.** Show
`brandedStatus` / `competitorStatus` and their dependent settings in the separate brand/non-brand/
competitor section. When the mode is off, one concise off row is enough; when on, expand the
returned brand/competitor matching and list settings.

| Backend field | English | 中文 |
|---|---|---|
| `brandedStatus` | Brand mode | 品牌模式 |
| `brandedMatchType` / `brandedList` | Brand matching / word lists | 品牌判断条件 / 品牌词库 |
| `competitorStatus` | Competitor mode | 竞品模式 |
| `competitorMatchType` / `competitorList` | Competitor matching / word lists | 竞品判断条件 / 竞品词库 |

## Action-Space Labels

Use the product label, not the field name.

| Backend field | English | 中文 | Section |
|---|---|---|---|
| `bidPerformanceStatus` | Adjust bids by performance | 按表现调价 | Bid |
| `bidPerformanceStrictAcosStatus` | ACOS priority mode | ACOS 优先模式 | Bid, subordinate to performance bidding |
| `bidAdPlaceStatus` | Placement bid adjustment | 广告位调价 | Bid |
| `bidRangeStatus` | Bid range | 竞价范围 | Bid |
| `bidRangeType` / `bidRange` | Bid-range type and limits | 竞价范围类型和上下限 | Bid, subordinate to bid range |
| `bidDaypartStatus` | Bid dayparting | 分时调价 | Bid |
| `bidAdPlaceRangeStatus` | Placement-specific bid ranges | 按展示位置设置竞价范围 | Bid |
| `bidAmazonBusinessStatus` | Amazon Business bid adjustment | B2B 调价 | Bid |
| `btbRangeStatus` / `btbMin` / `btbMax` | B2B bid range | B2B 竞价范围 | Bid, subordinate to B2B bidding |
| `budgetDynamicStatus` | Adjust budget by performance | 按表现调预算 | Budget |
| `budgetRedistributeStatus` | Budget reallocation | 预算重新分配 | Budget |
| `budgetDaypartStatus` | Budget dayparting | 分时预算 | Budget |
| `negativeTargetStatus` | Add negative targets | 添加否定定向 | Targeting |
| `targetHarvestStatus` | Target harvesting | 定向收割 | Targeting |
| `targetPausedAddStatus` | Pause targets | 定向暂停 | Targeting |
| `structPauseProductStatus` | Pause products | 暂停商品 | Structure |
| `structPauseCampaignStatus` | Pause campaigns and ad groups | 暂停广告活动和广告组 | Structure |

Show every supported switch separately as on/off for a complete read. Subordinate fields belong
under their parent switch; they are not additional action spaces. Do not infer one switch from a
sibling field.

## Managed-Group Rule Names

The codes below are internal routing keys. Use only the product-facing name in the answer.

| Internal rule type | English customer label | 中文客户名称 |
|---:|---|---|
| `2` | Bid dayparting | 分时调价 |
| `4` | Target harvesting | 定向收割 |
| `5` | Add negative targets | 添加否定定向 |
| `13` | Budget dayparting | 分时预算 |
| `17` | Adjust budget by performance | 按表现调预算 |
| `19` | Placement bid adjustment | 广告位调价 |
| `20` | Pause campaigns and ad groups | 暂停广告活动和广告组 |
| `181` | Adjust bids by performance | 按表现调价 |
| `182` | Pause targets | 定向暂停 |

For example, render rule type `17` as:

> 按表现调预算：开启
>
> 运行方式：规则

Do not render "Rule 17", "预算规则（Budget rule）", or "规则状态：已启用
(Rule-driven)". The paired action-space switch supplies on/off; the retained rule entry supplies
the Rule operating mode.

## Complete-Read Shape

Prefer labels such as `设置 / 状态 / 配置`, not `字段 / 值`. Do not put backend keys in the
setting column. For a compact answer, keep off settings to one line and expand only enabled
settings and retained Rule configurations.
