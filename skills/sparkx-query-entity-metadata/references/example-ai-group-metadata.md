# AI Group Metadata Query

List currently-running AI managed groups.

```json
{
  "profileIds": [4404871489220462],
  "entity": "aiGroup",
  "filters": {"aiStatus": 1},
  "userContext": "List currently-enabled AI managed groups"
}
```

**With a name filter and sort**:

```json
{
  "profileIds": [4404871489220462],
  "entity": "aiGroup",
  "filters": {
    "aiGroupName": {"like": "%growth%"},
    "aiStatus": 1
  },
  "orderBy": [{"field": "aiGroupName", "direction": "ASC"}],
  "userContext": "AI groups matching 'growth'"
}
```

Notes:
- Filters (`aiStatus`, `aiGroupName`) use `get_entity_metadata`'s camelCase convention (no `aiGroup.` prefix, no `_` suffix) — different from `get_ads_perf`.
- For a full configuration read, omit `select` so `aiActionSettings` and `aiAutomation` are both
  retained. If you do use `select`, explicitly include every needed top-level field; nested paths
  are not supported.
- `targetAcos` (if returned) is Tier 1 confirmed ×100/percentage — append `%` when presenting it.
- Unlike `get_ads_perf`, this tool's spec does not document support for custom SQL aggregate expressions (e.g. `count(distinct ...)`) in `select` — stick to the plain fields listed in the `aiGroup` field table.
- When the user asks for the complete setup, list every supported action-space switch separately,
  including off switches, then pair each on rule-capable switch with its AI/Rule mode. For rules
  `4`/`5`, expand `isSelf`, `campaignAd`, `day`, and `exceptDay` instead of reducing the rule to a
  phrase such as "30 days + 14-day conditions".

## Customer-facing presentation example

Do not reproduce backend keys as setting names. A Chinese complete read should follow this shape:

```text
基础设置
- 目标类型：保持订单稳定
- 所属大类：控制成本
- 目标 ACOS：24%
- AI 人格：4

品牌/非品牌/竞品模式
- 当前状态：关闭

AI 行动空间
竞价优化
- 按表现调价：开启（AI）
- 广告位调价：关闭
- 竞价范围：开启，固定值范围 $0.50-$1.13

预算优化
- 按表现调预算：开启（规则）
- 分时预算：关闭
- 预算重新分配：开启（AI）

自动化规则
按表现调预算
- 策略 1：当日 ACOS >= 70% 时，降低预算 40%，调整后不低于 $5
- 策略 2：当日 ACOS < 45% 时，提高预算 40%，调整后不超过 $15
- 频率设置：每天 00:00-24:00，每 30 分钟检查一次
- 自定义设置：开启；次日 00:00 将预算设置为 $3
```

For budget dayparting, preserve the page setting and explain any derived matrix:

```text
分时预算
- 00:00-03:00：基于当前日预算降低 98%，即按当前日预算的 2% 生效
- 03:00-05:00：基于当前日预算降低 92%，即按当前日预算的 8% 生效

相对当前日预算的生效预算比例（计算值）
- 小时 00、01、02：2%
- 小时 03、04：8%
```

The calculated percentage is the effective budget limit relative to the current daily budget. It
is not an actual-spend or delivery guarantee. Keep fixed-budget and amount-based operations in the
store currency rather than placing them in this percentage matrix.

Do not add `(aiActionSettings)`, `(aiAutomation)`, raw status fields, or `Rule 17` unless the user
explicitly asks for technical details.

> `filters` on this tool is a **flat field map** - multiple fields are implicitly ANDed.
> There are no `AND` / `OR` nodes; an `AND` key would be sent downstream as a field name
> and rejected.
