# Changelog

本文件记录 SparkX AI MCP Skills 与配套文档的版本变化。

## [Unreleased]

## [1.3.7] - 2026-11-10

### Added

- `sparkx-query-entity-metadata` adds five new entity types — `brandEntity`, `store`, `pageAsins`, `asset`, `sdAudience` (new reference `sb-sd-creation-entities.md`); `amcAudience` is extended to `sponsoredDisplay` (SD's AMC audience uses the T00030 `audienceSameAs` field, not the three campaign-level fields); adds the `budgetType` field on campaign (sortable, not filterable; SP stores an empty string and returns `daily` as a fallback, but sorting uses the raw stored value) plus new references `budget-usage.md`, `campaign-audience.md`, `ai-group-effective-config.md`, `suggestion-entities.md`.
- `sparkx-create-campaign` expands from SP-only to SP/SB/SD plus portfolios: five new reference files (`create-sb-campaign.md`, `create-sd-campaign.md`, `create-sb-ad-group.md`, `create-sd-ad-group.md`, `create-portfolio.md`).
- `sparkx-query-operation-log` documents `operationSources` filtering, clarifies Mode A pagination (resolve which branch applies from the response's `page`/`pageSize`/`hasNextPage` vs `limit`/`truncated`), and adds the three `data.totalSize` conventions (counts rows not entities, an omitted value is not zero, only an empty-first-page zero is trustworthy) plus the `changeField` parameter.
- `sparkx-edit-ads` expands from 25 to 29 routes: `adGroup.updateName` / `updateBid`, `campaign.updateName` / `updateDates` (the latter two execute directly; a rename batch is not atomic per-row).
- `sparkx-edit-ai-group` / `sparkx-query-operation-log` document the new `smartCreationName` rename mode for SD managed groups: exclusive (cannot combine with other fields), exactly one id, 1-255 code points, rejects zero-width characters instead of silently stripping them, five pre-flight rejection conditions, and `124035` must not be retried blindly; no operation log entry is written while AI is off.
- `sparkx-create-campaign` / platform notes document the new three-outcome mapping for AMC audience validation (rewritten per b25a35c3), split into two distinct `invalid_params` cases — an empty audience pool vs. a non-empty pool that doesn't contain the given id — with opposite remediation.
- An authoritative attribution-window table, previously uncovered by any Skill: SP·Seller 7 days / SP·Vendor 14 days (click-only), SB 14 days, SD 14 days (click+view combined), DSP per advertiser lookback; `storeType` comes from `get_user_authorized_context`. Cross-ad-type ACOS/ROAS/CVR rankings are partly a window artifact; Seller SP and Vendor SP are not comparable; SD includes a conversion type SP has none of. `sparkx-ads-structure-analysis` (whose default dimension is `campaignType`) gets an explicit warning against moving budget based on ACOS differences caused by this alone.

### Changed

- `sparkx-query-entity-metadata`'s budget-usage reference is rewritten against the platform's own tooltip wording and live measurements: `dateEnd` may be set to tomorrow (timezone headroom, not "today only"); `budgetSnapshot` is not `dailyBudget` (a campaign configured at `dailyBudget=400.00` was observed on the platform's own budget panel at `122.83% / $3.11`, and the snapshot moves intraday as budget rules fire — never compute budget usage against `dailyBudget`/`currentBudget`); the percentage denominator is the full selected window length (confirmed by reverse-solving six rows from one platform query, all resolving to the same ~697.3h denominator) — don't sort by `outOfBudgetPercentage` on short-lived campaigns, use `outOfBudgetMinutes` instead; removed the unsupported "near-real-time" claim and clarified that a null `lastOutOfBudgetTime` means "no record in the last 30 days", not "never out of budget".
- The platform-wide "T+2 delay" claim (previously stated in all 14 shared platform-notes files) is withdrawn — it had no supporting source and contradicts a live measurement (same-day `Spend`/`Impressions`/`Clicks` increased within ~12 minutes on a repeat query; historical days were byte-identical). Replaced with two separate, accurate statements: today's data is still accumulating (why `dateEnd` defaults back to yesterday, and "today" is the store's own local day), and the 7-14 day attribution window keeps backfilling conversions — waiting two days does not make a number final. `sparkx-weekly-ads-report` / `sparkx-monthly-ads-report`'s old trigger ("add the caveat only when within 2 days of today") was wrong — a Monday weekly report's entire week sits inside the attribution window — and is replaced with an unconditional disclosure plus an explicit WoW/MoM window-mismatch warning.
- `get_entity_metadata`'s `entities` parameter is not enum-validated server-side: `keyword` / `audience` / `productLine` all silently return 0 rows with no error. `EntityType` has exactly 9 real values; keyword-level operations land under `target`, and placement bid adjustments land under `placement`, not `campaign`. The prior text called `audience` "a bug to be fixed" and listed the default entity set as "all except `audience`" when it is actually "all except `productLine`".
- `bidRangeType=1` is a bid coefficient, not a percentage (confirmed against the platform's own "Optimize base bids" display) — corrected in 8 places; `bidRange` requires a strict `min < max`.

### Fixed

- Bulk bid-strategy edits no longer silently accept `ruleBased` or tolerate unrelated/duplicate/ended-campaign fields in the same batch.
- `get_entity_metadata`'s one-sided `>=`/`<=` filters are rejected — both bounds are required together; `campaignState`/`costType` are documented as case-sensitive.
- `queryType` on entities other than `target`/`searchTerm` now errors instead of being silently ignored.
- `service_unavailable` is documented for two more sources: the creative asset library and the AMC audience pool.
- SD creative failures have no public remediation tool; the previous guidance ("retry only the failed ad group's creative") described something that can't actually be done — replaced with reporting `creativeFailures` and pointing the user to the console.

### Versions

- `sparkx-create-campaign` `1.0.5` -> `1.1.0`, `sparkx-edit-ads` `1.1.7` -> `1.2.0` (both reflect real new coverage and route-count changes). `sparkx-query-ads-performance` / `sparkx-query-entity-metadata` `1.4.9` -> `1.4.10`, `sparkx-query-operation-log` `1.3.8` -> `1.3.9`, `sparkx-create-ai-group` / `sparkx-edit-ai-group` `1.2.4` -> `1.2.5`, `sparkx-delete-ai-group` `1.0.9` -> `1.0.10`, `sparkx-weekly-ads-report` `1.1.5` -> `1.1.6`, `sparkx-monthly-ads-report` `1.2.2` -> `1.2.3`, `sparkx-ads-structure-analysis` `1.1.6` -> `1.1.7`, `sparkx-product-diagnosis` `1.2.3` -> `1.2.4`, `sparkx-promo-reset` `1.0.4` -> `1.0.5`. `sparkx-search-term-diagnosis` is unchanged at `1.0.4`.

## [1.3.6] - 2026-11-03

### Added

- `sparkx-query-ads-performance` documents the `ilike` operator and a Text matching section: `ilike` for case-insensitive matching, `like` only when case-sensitivity is explicitly requested, with an intent-to-pattern table and the `campaignAudience` exception (use its `search` parameter instead).
- `sparkx-query-entity-metadata` adds the ASIN BSR category fields (`asinBsrCategoryId` / `asinBsrCategoryName` and their parent equivalents, returned only — no filtering or sorting), the `orderBy` restrictions per entity, and an explicit note that `ilike` is **not** accepted by this tool.
- `sparkx-edit-ads` documents the four confirmation failure messages verbatim, separates the confirmation-service outage by phase (Phase 1 issues no token; Phase 2 cannot verify one that was issued), and adds a table mapping `errorType` plus message prefix to the right response.

### Changed

- `sparkx-edit-ads` keyword routes: `campaignType` and `matchType` are now documented as **required** with their enum values, instead of "send it". Both are validated before the preview is issued, so a bad value is rejected with the exact parameter path and no `confirmToken` comes back.
- Preview field lists are complete rather than indicative: `keyword` and `target` `updateBid` carry nine fields each (`target` uses `targetText` and has no `matchType`), `productAd` `archive` carries five, and the `updateStatus` previews are spelled out per entity.
- The token-survival rules are split by where the failure happens. The routes that validate the whole batch up front reject before the token is touched, so a field or nested-`profileId` rejection no longer consumes it there.
- Text-matching guidance in the shared platform notes is now tool-specific: each tool's Skill defines its own operators, case sensitivity and wildcard handling, and the rules must not be carried across tools.

### Fixed

- `matchType` was documented as **not** enum-validated, with the explicit claim that any string passes through. The opposite is true, and the stale text also told you not to pre-filter. A request missing `matchType` previously failed only at execution time with a generic error that named no field. The matching `ilike` guidance was also missing from this brand's mirror entirely and has been brought in line.
- SB negative keywords were documented as unrestricted at campaign level, with an instruction not to filter those items out. `sponsoredBrands` with `businessType=campaign` is rejected on both `updateStatus` and `copy`, before anything is written.
- The bid preview was described as reading the current bid, and `projectedBid: null` as a lookup failure. The preview never queries the live bid: `previousBid` is echoed back from the request and `projectedBid` is computed from it, so a preview that looks right is not evidence the baseline is current.
- The `get_ads_perf` operator list omitted `!=`, `isNull` and `isNotNull`, all of which are supported and already used elsewhere in the docs. `notin` is **not** supported on that path — only `campaignAudience` accepts it — although the server's own error text lists it.
- `keywordCurrentBid` cannot be used to verify a bid write: on the stores where it reads `0` it stays `0` after a successful write. Read `keywordBid` back instead, and report an unmoved value as accepted-but-unconfirmed rather than re-sending or falling back to pausing the keyword.
- The `like` wildcard note claimed that `%` is stripped and replaced with an automatic leading and trailing `%`. That holds for `get_entity_metadata`, not for `get_ads_perf`, where the pattern reaches SQL unchanged.

### Versions

- `sparkx-query-ads-performance` and `sparkx-query-entity-metadata` `1.4.8` -> `1.4.9`, `sparkx-query-operation-log` `1.3.7` -> `1.3.8`, `sparkx-edit-ads` `1.1.6` -> `1.1.7`, `sparkx-weekly-ads-report` `1.1.4` -> `1.1.5`, `sparkx-monthly-ads-report` `1.2.1` -> `1.2.2`, `sparkx-ads-structure-analysis` `1.1.5` -> `1.1.6`, `sparkx-product-diagnosis` `1.2.2` -> `1.2.3`. The other six Skills are unchanged.

## [1.3.5] - 2026-10-27

### 新增

- `sparkx-create-campaign` 覆盖 `create_sp_ad_group`：在已有 SP Campaign 下新建广告组，含推广商品、投放与否定。新增参考文件 `create-sp-ad-group.md`。活动创建按批次 all-or-nothing，广告组创建是非原子的 `partial_success`，两者分别写明。
- `sparkx-edit-ads` 从 20 条路由扩到 25 条：新增广告组合成员关系、组合预算与起止日期、广告组状态。新增参考文件 `write-ad-group.md` 与 `write-portfolio.md`。
- `sparkx-query-entity-metadata` 补品类/品牌定向 ID 与投放状态。

### 变更

- 商品诊断的下滑判定新增最低样本基线：`recentSalesBaselineOrders`（默认 `5`）与 `recentSalesBaselineAmount`（默认一个 `T`）。没有它们时 `$1.00 -> $0.70` 也算 30% 下滑。两个参数都可由客户覆盖，并在结构化结果中回显，同时带 `recentSalesBaselineAmountSource`，便于复现分类。
- `totalDailyBudget` 两面都写清楚：它是成员预算之和，没有任何东西把它当上限强制执行；但它可写，写它会按比例重算每个启用成员的日预算，因此写入前必须在预览里说明影响面。
- 操作日志补充回填与量级两条：日志会回填约两天，所以计数是运行那一刻的计数；AI 活跃账户的机器行可达每小时数百条，一天的 AI 变更装不进 1,000 行上限。
- 写入限流（20 calls/min，按 tenant+tool 与 user+tool 分别计）补齐到所有涉及写入的 Skill，此前只在部分文件中有。
- 回读规则纳入镜像延迟：元数据镜像可落后亚马逊 20 分钟以上，回读不一致不等于写失败，也绝不构成重发的理由，该行报 `pending sync`；`ambiguous_write` 或 `timeout` 之后结果明确标为未知，而不是"已写入"。

### 修复

- `*ActionStatus` 这组字段名并不存在。8 个文件共 56 处是错的，字段参考开头的提示框还专门拿它当例子。真实字段是 `budgetDaypartStatus`、`budgetDynamicStatus`、`budgetRedistributeStatus`。未知字段会被静默丢弃，所以按旧名字写的调用返回成功而开关从未变动。
- `keywordCurrentBid` 在 Skill 里有三种互相矛盾的说法——两处要求拿它当调价基准，一处警告它会读到 `0`。统一为：以 `keywordBid` 为基准，`keywordCurrentBid` 仅作参考，且必须判 `0`。
- `targetCurrentBid` 原描述为"可能与 `targetBid_` 不同"。这只对关键词成立；其他定向类型下两个字段映射同一列，永远不可能不同，因此"相等"不能被读成"AI 没调过"。
- `changedBy: Amazon Console` 是来源而不是操作人——它表示改动来自亚马逊侧，不计入人工修改。共修正 10 处，包括共享的归因规则和大促复位的复位清单，这类行在回滚前必须先说明来源。
- `bidRangeType=1` 标注为单位未确认，并移除原来 `0.01`-`100` 的"百分比"校验：按系数理解，该边界会拒掉合法值又放行非法值。`budgetNumType` 与 `bidRangeType` 的枚举行拆开，这是此前四处口径不一致的根源。
- `get_entity_metadata` 的未知 `select` 字段是丢弃而非拒绝——写进全部 14 份共享 platform-notes，并说明这与 filter/metric 的 `invalid_params` 是两种行为。
- `currentBudget = 0` 与 `asinPrice = 0` 是哨兵值（当天无 AI 调整记录；未回填），不是零预算或免费商品，且 `>=` 过滤会静默丢掉这类行。
- `get_operation_log entities:['audience']` 对任何查询都返回 0 行，因此空结果不携带任何信息，不能读成"这段时间没有改动"。
- 删除"内部 ID 是小整数、亚马逊 ID 是 15-19 位"的位数启发式。同一条日志行会同时带两者，长度不是契约——按字段名判断。
- 跨表比对：同一窗口同一对象的两个数字来自不同表就会有细微差异。一个判断，一个来源。

### 版本

- `sparkx-query-ads-performance` `1.4.7` -> `1.4.8`、`sparkx-query-entity-metadata` `1.4.7` -> `1.4.8`、`sparkx-query-operation-log` `1.3.6` -> `1.3.7`、`sparkx-create-ai-group` 与 `sparkx-edit-ai-group` `1.2.3` -> `1.2.4`、`sparkx-edit-ads` `1.1.5` -> `1.1.6`、`sparkx-create-campaign` `1.0.4` -> `1.0.5`、`sparkx-weekly-ads-report` `1.1.3` -> `1.1.4`、`sparkx-monthly-ads-report` `1.2.0` -> `1.2.1`、`sparkx-ads-structure-analysis` `1.1.4` -> `1.1.5`、`sparkx-product-diagnosis` `1.2.1` -> `1.2.2`、`sparkx-search-term-diagnosis` 与 `sparkx-promo-reset` `1.0.3` -> `1.0.4`。`sparkx-delete-ai-group` 保持 `1.0.9`。

## [1.3.4] - 2026-10-22

### 新增

- `aiGroup` 新增只读字段 `hasAdvice`（仅限开通按行动空间力度的账号）：`true` 表示有可直接应用的人格推荐，`false` 表示没有，`null` 表示推荐服务暂时不可用。`null` 明确写为"未知"而不是"没有"；该字段不可过滤，字段缺失也不能用来判定账号类型。
- 补充网关对 `save_sp_sb_ai_managed_group` 的 `evidence` / `isApplyP` 硬约束：最多 4 条、每个 service 最多一次、`personality` 必须 `1`-`5`、SB 不能传 `service=placement`、编辑时每条的 `aiGroupId` 必须是 `0` 或等于组 ID。

### 变更

- **对消费 JSON 的下游是破坏性变更**：`sparkx-monthly-ads-report` 的 `structured_report` 中 `newProducts` 改名为 `newlyAdvertisedProducts`，并新增 `existingProductsNewlyAdvertised`。
- 操作日志的时间戳有三种时钟而不是两种：广告实体单店铺用店铺时间、多店铺用 UTC；SP/SB 托管组是 UTC；SD 托管组用下游数据库时区，没有任何地方声明是哪个。因此可能返回 SD 托管组行的查询给不了统一的时区标签，排序也从"newest first"改为按原始时间戳字符串排序。全部 24 份 platform-notes 同步。
- 鉴权失败：token 无效或过期现在返回 401/403 而不是 503。这是永久错误，应重新鉴权而不是重试。覆盖 16 份 platform-notes。

### 修复

- `get_operation_log` 的 `resourceIds` 对 `campaign` 和 `adGroup` 要求亚马逊 ID。商品诊断原来教的是内部 ID，传进去匹配不到任何行且不报错——调用成功返回空，和"确实没人动过"长得一模一样。改为三跳解析：`productAd` 取内部 ID、`campaign` 实体换 `amazonCampaignId`、`adGroup` 实体换 `amazonAdGroupId`，第三跳不能省。`campaign`、`adGroup`、`aiGroup` 现在是三次独立调用并显式传 `entities`，这也恢复了真实分页。
- `changeBy: manual` 现在被服务端直接拒绝（忽略大小写，含 `IN`、`NOT_IN` 或混选）。此前 Skill 的说法只是"会漏掉邮箱归属的变更"。共修正 7 处；`Manual` 标记为展示值而非过滤值。

## [1.3.3] - 2026-10-21

### 变更

- 商品诊断把原来那个五选一的生命周期标签拆成**两个正交的轴**。起因是客户反馈公开的定义看不明白；根因不是文案，而是那一个标签把两件互不相干的事压在了一起，用运营语言读会得到几个讲不通的结论：一个产品的"生命周期"取决于它在你账户里的花费排名；明星和衰退互斥；换个时间窗口生命周期就变了；没有成熟期；衰退只看广告订单，而广告订单随你改出价预算而动。
  - **投放分层**（`star` / `core` / `longTail` / `noAdSpend`）：按本期花费份额加 ACOS，账户相关、窗口相关，回答"钱花在哪"。
  - **生命阶段**（`new` / `growth` / `mature` / `declining` / `insufficientData`）：按 SP 投放时长加独立的 12 整周总销售额趋势，产品固有，不随报告周期变。
  - 明星 × 衰退是单标签表达不了、也最有价值的一格。
- 新增 Step 2f：按周一聚合的 12 周周粒度序列。用 12 周不是 13 周——84 天一次调用拿得完，91 天超 `get_ads_perf` 的 90 天上限。两端对齐周一/周日，否则尾部残周会被读成不存在的下跌。同比伴随调用往前推 364 天，周一仍是周一。
- 衰退有两条路径：缓降（归一化斜率 <= `-0.10` 且回撤 >= `0.25`）或断崖（回撤 >= `0.50` 单独成立）。

### 修复

- 小时与 AMS 数据的 AI 指标是占位值：`AISpend` / `AISales` 回 0，`AIACOS` / `AIROAS` 回 null，和 `keywordPlacement` 一样。原文只在 `keywordPlacement` 上写了这条，容易被理解成 hourly 可以拆 AI 和手动。AI 归因只能走日粒度。结构分析里的 hour-of-day 表不再出 AI 列。
- 小时数据的时间戳是店铺本地 IANA 时区，不是 UTC。指南不再回避"晚上 8 点达峰"这类说法，但要求注明是店铺本地时间，夏令时切换当天按歧义处理。
- 三处互相打架的时效口径统一为证据支持的说法：约 2 小时出首次数据，之后会回填，最终稳定窗口未知。T+2 是日粒度管线自己的数字，不是 hourly 归因完成的时点。最近的小时按 `provisional`（可读但可能被上修）处理，不是 `incomplete`。

## [1.3.2] - 2026-10-20

### 新增

- 创建与编辑托管组两个 Skill 各新增参考文件 `ai-personality.md`，覆盖按行动空间的 AI 人格。账号分两类，只在工具调用时才判定：新账号上组级 `aiPersonality` 在写入前即被拒，改用 `aiActionSettings` 里的 12 个 `*AiPersonality`（或批量 `operation=actionSpaceIntensity`）。SB 只支持其中 6 个，传其余 6 个（含传 `null`）整单拒绝。排期与托管组形状不同：人格字段必须嵌进各优化模块，周排期带人格整单拒绝，固定日期排期省略某项不是"保持原值"而是回落到该排期的 `aiPersonality`。
- 分析类 Skill 的第二批内容：父 ASIN 本身不可投放时展开成子 ASIN；同一广告组下的变体为何分不了按 ASIN 的预算；读完小时数据后实际能改什么（开关与人格可写，小时矩阵不可写）；停之前先查谁依赖它，并优先暂停而不是不可逆的归档；竞品 ASIN 定向的三步流程，先从建议里剔除客户自己的 ASIN。

### 变更

- platform-notes 补充 `capability_unavailable` 错误说明。
- 14 个 Skill 各升一个 patch，以线上 Skill Hub 的版本为基准（线上此前比仓库高一个 patch）。顶层 release `v1.3.1` -> `v1.3.2`。

## [1.3.1] - 2026-10-13

### 新增

- 新增可选 Skill `sparkx-search-term-diagnosis` `1.0.0`：按固定、可复现的规则诊断搜索词，覆盖花费分布、品牌/非品牌与关键词/ASIN 分类、否词候选、扶正候选和精准词碎片；门槛由店铺客单价与目标 ACOS 推导。
- 新增可选 Skill `sparkx-promo-reset` `1.0.0`：找回大促期间人为修改的出价、预算、广告位溢价和托管组设置及其大促前的值，可全部复位，也可按大促后表现分阶段回落，并提供执行前预览、撤销数据和执行后回读。

### 变更

- 三个查询 Skills 对齐最新的报表、元数据、操作日志、广告位、ID 空间和聚合口径：`sparkx-query-ads-performance` `1.4.2` -> `1.4.3`，`sparkx-query-entity-metadata` `1.4.2` -> `1.4.3`，`sparkx-query-operation-log` `1.3.2` -> `1.3.3`。
- 托管组 Skills 补齐平台模板选择、当前排期行为与最新读写约束：`sparkx-create-ai-group` `1.1.4` -> `1.2.0`，`sparkx-edit-ai-group` `1.1.5` -> `1.2.0`，`sparkx-delete-ai-group` `1.0.6` -> `1.0.7`。
- 广告周报、广告月报、广告结构分析和商品诊断按当前查询边界与诊断规则扩展，四个 Skill 均从 `1.0.6` 升至 `1.1.0`。
- 可选 Skills 从 4 个增加到 6 个，Plugin 与发布清单升级为 `v1.3.1`，共包含 14 个 Skills。

### 修复

- 受众分两个人群池,不是一个。`create_sp_sb_campaign` 与 `batch_update_ads` +
  `updateAudienceBid` 都需要 `audienceSegmentType`,传错类别会被接受、正常入库,
  但在亚马逊侧永不生效。Skills 现已写明两个取值、说明活动行不携带该类型,
  并要求向用户确认而不是猜测。`sparkx-create-campaign` `1.0.0` -> `1.0.1`,
  `sparkx-edit-ads` `1.1.0` -> `1.1.1`。
- `get_ads_perf(factEntity='campaignAudience')` 并非 AMC 专属;活动是否出现取决于
  受众报表表中是否有其记录,而不是是否绑定了受众。空结果不再被描述为「未绑定受众」,
  该问题应读 `entity: campaign` 并判断 `audienceId != ""`。
  `sparkx-query-ads-performance` `1.4.0` -> `1.4.1`,
  `sparkx-query-entity-metadata` `1.4.0` -> `1.4.1`。
- 托管组创建现在默认开启 AI，跟进服务端将 `aiStatus` 改为非必填的变更。Skill 要求
  确认预览中写明 AI 将立即开始优化，并区分 SP/SB（省略该字段）与 SD（`status` 无服务端
  默认值，必须显式传递）。`sparkx-create-ai-group` `1.1.3` -> `1.1.4`。
- 排期写入跟随两项服务端修复重做。删除从 `isActive: false` 迁移到 `operation: "delete"`；
  `isActive` 已废弃但**仍会删除**，而读取侧同名字段表示“当前不在生效窗口内”，
  因此读取结果不得原样回写。`weekDays` 现在读写两侧都是 `1`-`7`（写入侧原为 `0`-`6`）；
  省略的排期不受影响——保存是按 id 的 upsert，不是整批覆盖。
  `sparkx-edit-ai-group` `1.1.4` -> `1.1.5`。
- SB 否定关键词不再支持 `state: "paused"`，服务端在预览前即拒绝整批。归档是唯一替代
  且不可逆，必须由用户明确选择，不得自动替换。`sparkx-edit-ads` `1.1.1` -> `1.1.2`。
- 补齐了“返回空结果而不报错”这类失败模式的说明：ID 过滤的值属于另一个 ID 空间时，
  筛选合法但匹配不到任何行，静默返回 0 行。空结果排查清单已涵盖该场景。
  `sparkx-query-entity-metadata` `1.4.1` -> `1.4.2`，`sparkx-query-ads-performance` `1.4.1` -> `1.4.2`，
  `sparkx-query-operation-log` `1.3.1` -> `1.3.2`，四个分析类 Skill `1.0.5` -> `1.0.6`。
- 根据服务端新增的校验更正了受众绑定说明：`audienceId` 非空时 `audienceSegmentType` 必填，
  且服务端会在创建任何活动前核对 ID 是否属于所报的受众池——配不上会拒绝整个请求，
  而不是存下一个永不生效的绑定。`sparkx-create-campaign` `1.0.1` -> `1.0.2`。
- 性能侧的广告位枚举是错的，而填错的值会静默返回 0 行、不报错——读起来就像"这个店铺没有
  广告位数据"。`placement.placement_` 实际返回的是带 `SP-`/`SB-` 前缀的展示字符串；
  `topOfSearch` / `productPage` / `restOfSearch` 属于 `get_entity_metadata(entity='placement')`，
  是另一套取值空间。三处同名的 placement 值空间现已在 Skill 中逐一区分。
- 广告位竞价调整以元数据侧为准，性能侧不可信：它的 `SB-Top of Search on-Amazon` 行取的是
  **首页**的调整值，SB 真正的搜索结果顶部取不到，Sponsored Display 完全没有广告位数据，
  负数 `multiplier_` 也不是任何人配置过的百分比。另外补充了可能占某店铺四分之一 SP 曝光的
  无归属桶，并把中英文标签对齐产品页面——包括 SP 的"首页"指搜索结果**第一页**、
  SB 的"首页"指亚马逊网站**首页**。
- 操作日志的 `placementTypes` 原写"确认完整，恰好 4 个"，实为 7 个。
- 用下层维度拆分某个实体会让数字翻倍且不报错：广告组查询加上 `productAd.asin_` 后，
  整个广告组的花费和单量会复制到每个 ASIN 上，于是零转化的商品显示出健康的 ACOS。
  `SKILL.md` 不再说自动 JOIN 无需留意；它点明 `productAd` 才是按商品拆分的实体，
  并把它与"在商品范围内查 target / search term"区分开——后者保持原 `factEntity`、改用广告组
  收窄。而且这个收窄是三步不是两步：元数据侧返回内部 ID，性能侧按 Amazon ID 过滤，
  中间那次换算不做就会静默返回空。真正的 target × 商品交叉拆分不支持，不得拿前两者顶替。
- 共享平台说明新增"结果偏大/对不上账"一节，与既有的"结果为空"排查清单对称：去掉多余维度重跑
  一次，确认拆分之和等于整体。触发条件限定在商品维度，常规查询不受影响。同时补充了直接过滤
  事实表的 `p.` 前缀，以及哪些事实实体真的带 `p.adGroupId_`。
- 后续广告位与跨实体聚合修复统一并入上方列出的 `v1.3.1` 最终 Skill 版本，未单独发布中间版本。

## [1.3.0] - 2026-09-17

### 新增

- 新增必装 Skill `sparkx-create-campaign` `1.0.0`，对应 `create_sp_sb_campaign`（`amazon_sa_campaign_create:write`）。当前支持创建 SP Campaign，可配置广告组、推广商品、自动/关键词/商品投放、否定投放、广告位和可选 AMC 受众；暂不支持创建 SB/SD Campaign。
- `sparkx-edit-ads` `1.0.1` → `1.1.0`：新增广告位加价与 AMC 受众加价编辑，现覆盖 20 条操作路由，其中 11 条使用服务端两阶段确认。

### 变更

- 查询 Skills 按当前工具契约更新 Campaign 受众、实体 ID、日期形态、币种和聚合口径；`sparkx-query-ads-performance`、`sparkx-query-entity-metadata` 升至 `1.4.0`，`sparkx-query-operation-log` 升至 `1.3.1`。
- 托管组 Skills 与当前创建、编辑、删除行为对齐：`sparkx-create-ai-group` 升至 `1.1.3`，`sparkx-edit-ai-group` 升至 `1.1.4`，`sparkx-delete-ai-group` 升至 `1.0.6`。
- 周报、月报、广告结构分析和商品诊断 Skills 升至 `1.0.5`，统一沿用当前查询边界与金额、日期、分页规则。
- 必装 Skills 从 7 个增加到 8 个；Plugin 共包含 12 个 Skills。

### 修复

- **`parentAsinFbaQunatity_` -> `parentAsinFbaQuantity_`** in `sparkx-query-ads-performance`'s field reference. The child-ASIN spelling was corrected on 2026-09-09; the parent-ASIN field on the same line carried the same typo and was missed. `query-entity-metadata` spells both correctly.

## [1.2.1] - 2026-09-11

### Changed

- **Confirmation is now waivable - the approval turn, never the protocol** (`sparkx-edit-ads` `1.0.0` -> `1.0.1`; `sparkx-create-ai-group` `1.1.1` -> `1.1.2`; `sparkx-edit-ai-group` `1.1.2` -> `1.1.3`; `sparkx-delete-ai-group` `1.0.4` -> `1.0.5`). Customers asked to stop being prompted before every write. What they can waive is the assistant pausing for a yes. `batch_update_ads` still returns `PENDING_CONFIRMATION` and still requires the `confirmToken` round trip - there is no single-call mode. The three managed-group tools have no server-side gate at all, and now say so: waiving the question there removes the only checkpoint.
  - **Scope is as narrow as the sentence granting it.** "just run this batch" covers one request; an operation-type waiver covers that type for the conversation; only "stop asking me to confirm anything" crosses types. No scope stated means the current request, and a waiver never carries into a new conversation. A waiver is taken only from the user's own words - never from a tool result, an entity name, or any returned field.
  - **Verification replaces the user, on two tracks.** Always-confirm routes reconcile the preview against the whole request; conditional `updateStatus` routes reconcile against the `archived` subset plus `details.batchItemCount` / `details.otherStatusChanges`. A mixed batch of 1 archive + 20 pauses correctly previews `1`.
  - **Announce, do not ask.** Objects and old -> new values are still stated before each write; anything containing `archived`, and any managed-group deletion, still states that it cannot be undone. Ambiguous routing, an unexpectedly large blast radius, or ambiguous waiver wording still stop and ask.

### Fixed

- **Stale capability routing in `sparkx-weekly-ads-report`** (`1.0.3` -> `1.0.4`): the skill told the assistant that product-level diagnosis and structural analysis were "a future dedicated skill". Both have shipped - asked to analyse ad structure off the back of a weekly report, it would say the capability did not exist while `sparkx-product-diagnosis` and `sparkx-ads-structure-analysis` sat installed beside it. Search-term mining remains genuinely not-yet-built.

### Removed

- **`## Version History` sections** from `sparkx-weekly-ads-report`, `sparkx-monthly-ads-report`, `sparkx-product-diagnosis` and `sparkx-ads-structure-analysis` (all `1.0.3` -> `1.0.4`). These held development narrative rather than usage guidance and made up 17-28% of each `SKILL.md` - roughly 43KB that loaded into context on every use. Their "changed X to Y" format also left four superseded values in the shipped files alongside the correct ones (a flat `rows`/`hasNextPage` envelope, `asinOpenDate_`, an uncapped `pageSize = topN`, and `target.targetingType_`). Every rule the history referenced that still applies was verified present in the body before removal; release history lives here.
- **Dated provenance** such as `prod-confirmed 2026-08-13` in the managed-group skills - the assertion is kept, the date made a standing rule read as a one-off event.

## [1.2.0] - 2026-09-08

### 新增

- **线上广告实体编辑**：新增必装 Skill `sparkx-edit-ads` `1.0.0`，对应 `batch_update_ads`（`amazon_sa_campaign_edit:write`）。覆盖 Campaign、关键词、Target、推广商品、否定关键词和否定 Target 的 18 条操作路由，其中 9 条受保护路由采用明确的两阶段确认。写操作会直接影响线上账号；整批校验不接受部分成功，归档对象按 fail-closed 处理，下游结果不明确时不得向用户报告成功。
- **Vendor ASIN 指标口径**（`sparkx-query-ads-performance` `1.1.0` → `1.2.0`，关联工单 BC-9770）：`TotalSalesAmount`/`OrderCount`/`UnitCount`/`TACOS` 在 Vendor 行取 shipped 口径（而非 ordered），与 Seller 行统一，可在混合查询中直接聚合。新增 `OrderedRevenue`/`OrderedTACOS`（仅 `distributorView_=MANUFACTURING` 下有值）与 `ShippedRevenue`/`ShippedTACOS`（两个视图均有值）的适用范围说明。新增 Vendor 维度自动锁定说明：底表每个 `(profileId, date, ASIN)` 最多 4 行（`distributorView_` × `sellingProgram_`），不锁维度会导致广告指标和 `GlanceViews` 膨胀最多 4 倍；服务端默认锁定 `MANUFACTURING` + `RETAIL`，`meta.appliedDefaults` 声明实际生效的默认值。补充混合 Seller+Vendor 查询时统一指标可直接聚合、Vendor 专属指标需按 `storeType_` 分组的说明。

### 修正

- **托管组完整配置解释**（`sparkx-query-entity-metadata`，版本待发布时统一调整）：新增客户展示层，按提问语言使用页面名称，默认隐藏后端字段和规则编号；将品牌/非品牌/竞品模式从 AI 行动空间中独立展示；区分目标类型的页面大类与实际选项，中文 `targetType=2` 展示为“保持订单稳定”而非“控制成本”或英文枚举；AI 人格直接展示 `1`-`5` 数字，不替换或追加“激进”等描述；明确 `aiAutomation.*.status` 表示 AI/Rule 模式而非启用状态；补全规则 4/5 的 `isSelf=1/2/3` 作用范围及历史窗口语义；按表现调预算把预算上下限合并回对应策略，并将“自定义设置”与“频率设置”分组，正确解释为次日店铺时间 00:00 将预算设置为配置值；补充分时预算“降低比例”到“相对当前日预算的生效预算比例”的换算，并避免将预算上限误称为实际投放比例。同步修正完整读取示例中关于 `select` 的错误说明。
- **小时级（AMS）时区确认**（`sparkx-query-ads-performance`，同上版本区间）：`date`/`hour` 已确认为 profile 的本地 IANA 时区（非 UTC）；数据延迟约 2 小时（远快于日级 T+2）。
- **小时级查询暂时没有已验证的商品身份关联路径**：`select` 中加入 `productAd.asin_`/`productAd.sku_` 会报 `业务错误`/`business_error`（无法连接 CTE）；`factEntity: productAd` 本身拒绝 `timeGranularity: hourly`。仅验证了 `productAd.*` 这一种组合，`asin.*` 维度、以及日级 `campaign`+`productAd` 组合是否同样失败均未测试，不要外推。
- **15 个月回看边界为闭区间**：实测确认 `dateStart` 恰好等于 15 个月前的截止日期时查询成功，仅早于该日期才报错（`start.isBefore(earliest)` 语义）。此前文档误写为"边界当天即报错"。

## [1.1.1] - 2026-08-25

基于线上 `v1.1.0` 一次升级，对齐 MCP Server `pre` 分支的当前行为，并补齐小时级（AMS）数据、托管组排期、规则模式配置读取与解释。

### 新增

- **小时级 / AMS 数据**（`sparkx-query-ads-performance` `1.0.0` → `1.1.0`）：新增 `timeGranularity`（`daily` / `hourly`，**hourly 仅 `factEntity=campaign`，覆盖 SP+SB+SD**）与新 factEntity `keywordPlacement`（关键词×广告位，天然小时级、**仅 SP**）。两者**日期跨度上限 7 天**（非 90 天）；非 campaign 实体传 `hourly` **直接报错**，不再按天降级。`keywordPlacement` 的字段命名是**请求侧裸名、响应侧带 `_` 后缀**（继 searchTerm 之后的第二个命名例外），枚举也与 `placement` 实体不同（`matchType_` 为大写、`placement` 为展示串），且指标集受限（仅基础 + Same/Other-SKU + 六个派生比率；NTB、DPV/视频/可见展示/展示份额、ASIN 业务指标均不可用，AI 指标恒为 `0`/`null` 占位）。新增示例 `example-hourly-ams.md`。
- **托管组排期读取**（`sparkx-query-entity-metadata` `1.1.3` → `1.2.0`）：新增 entity `aiGroup_schedule`，契约与其他实体不同 —— `profileIds` 必须恰好 1 个、`filters` 只能且必须含 `aiGroupId`、忽略分页与排序、一次返回全部排期。新增示例 `example-ai-group-schedule.md`。周重复排期（`timeType=2`）的 `optimizeType`/`acos`/`aiPersonality` 继承自主托管组，须从主组读取。
- **规则模式（RBA）规则配置读取**（同上）：规则模式下的条件、动作、条件项、周期与分时矩阵可从 `aiGroup` 的 `aiAutomation.{ruleType}` 读取（规则 2/4/5/13/17/19/20/181/182）；已确认叶子带 `...Text` 文案，未确认叶子原样透传。**可读不可写** —— 撤销原先"RBA 配置不可读写"的表述。新增 `references/automation-rule-reading.md`，补充分时调价系数、分时预算恢复、预算利用率、条件组 AND/OR、策略优先级、回溯排除周期、广告位计算与 Campaign 定时启停等帮助中心业务语义。
- **自动化规则查询边界**（同上）：明确 `entity=automationRule` 只返回指定 Campaign 已启用的规则类型，不返回模板名称、条件、动作或频率；`aiGroup.aiAutomation` 只表示托管组行动空间内嵌的 Rule 配置，不等同于账户级自动化模板库。商品库存规则为 SKU/商品维度，当前两个入口均不能可靠读取其配置。
- **托管组排期写入**（`sparkx-edit-ai-group` `1.0.4` → `1.1.0`）：新增 `save_sp_sb_ai_group_schedule`（仅 SP/SB）的完整参数契约 —— `id` 空=新建 / `>0`=更新、`isActive=false`+`id`=删除、`timeType=1` 固定窗口需自带三项基础设置、**`timeType=2` 传这三项直接报错**、词库设置被服务端静默剥离、重叠由下游返回 `Schedule_Date_Overlap`。撤销原先"排期不支持且后端 rejects"的表述。
- **托管组模板**（`sparkx-create-ai-group` `1.0.3` → `1.1.0`，`sparkx-edit-ai-group` `1.1.0`）：新增 `get_ai_group_template`（列表 / 详情，读操作但走写 scope）与三个写工具的 `templateId` 参数；用户传参优先于模板值，优先级 `templateId` > `operation` > 普通字段编辑。模板中规则 4/5 若配置为"指定广告活动的广告组"（`isSelf=2` 且规则开启）会被拒绝。**模板本身只读** —— MCP 无法创建 / 编辑 / 删除模板。
- **小时维度结构分析**（`sparkx-ads-structure-analysis` `1.0.0` → `1.0.1`）：新增 `breakdownBy: hourOfDay`，并写明其 campaign 专属和单次 7 天窗口约束；仅覆盖请求窗口子集时声明抽样，完整分段覆盖时不得误称抽样。

### 修正（与服务端实际行为不一致，会导致调用失败或误导）

- **`profileIds` 改为全有或全无**：三个读工具与写工具都要求请求的每个 `profileId` 均已授权，任一越权 → 整请求失败（`Requested profileIds contain unauthorized values`）。**撤销**原先"越权 ID 被静默丢弃、交集为空返回空结果集"的表述，并相应重写空结果诊断流程。
- **Scope 名称修正**：`amazon_sa:performance:read` → `amazon_sa_performance_data:read`、`amazon_sa:ads_configuration:read` → `amazon_sa_ads_configuration:read`、`amazon_sa:ads_logs:read` → `amazon_sa_ads_logs:read`；写侧补齐实名 `amazon_sa_managed_group:write` 与 `amazon_sa_managed_group_delete:write`。
- **分页越界行为分叉**：`get_ads_perf` / `get_entity_metadata` 的 `pageSize`（>500 或 ≤0）与 `page`（≤0）现在直接报错，不再 clamp；`get_operation_log` 仍为静默 clamp。派生 `pageSize` 需两端兜底（`sparkx-product-diagnosis` 的 `min(topN, 500)` 改为 `max(1, min(topN, 500))`）。
- **`get_operation_log` 的 `createdDate` 时区不固定**（`sparkx-query-operation-log` `1.1.1` → `1.2.0`）：`aiGroup` 恒 UTC；`campaign`/`adGroup`/`target`/`placement` 在单 `profileId` 时为店铺本地时间、多 `profileId` 时为 UTC（实测：同一条记录相差 7 小时）。**撤销**原先"平台规范空白、不要猜"的处理，改为按实测写明；并要求标注时区、禁止混用单店与多店结果、提示混合实体响应的时间排序不可靠。
- **`language` 默认值**：`get_ads_perf` 的默认语言是 `en` 而非 `zh`（非法值静默回落 `en`）。
- **SB 不支持字段改为硬报错**：SB 组上启用 SP 专属行动空间字段（`bidAmazonBusinessStatus`、`btb*`、`bidDaypartStatus`、`bidPerformanceStrictAcosStatus`、`bidAdPlace*`、`tos/pdp/ros` 上下限、`structPause*`，共 16 项）会整请求失败并一次列出全部违规字段，不再"静默忽略"。
- **`aiGroup` 读回是"当前有效配置"的投影**：先按 `campaignType` 裁剪（SD 无 bid/struct/brand 行动空间且 automation 全清空；SB 无 struct 与广告位/B2B 系列），再按开关与模式收敛（关闭的开关丢弃其依赖字段；AI 模式的规则整条不返回；Rule 模式移除仅 AI 展示的参数）。**字段缺失 ≠ 未配置 ≠ 写入失败** —— 写后校验须先看开关再看依赖字段。
- **AI / Rule 模式判断**：撤销“空 `aiAutomation` 等于全部 AI 驱动”的过度结论，改为先读取 `aiActionSettings` 配对开关，再结合是否保留 `aiAutomation.{ruleType}` 判断关闭、AI 或 Rule 模式；创建后的回查同样按有效配置投影解释。
- **`aiAutomation` 语义与字段名**：写侧为平铺字段（`bidDaypartStatus`、`targetHarvestRuleStatus`、`negativeTargetRuleStatus`、`budgetDaypartRuleStatus` + `budgetDaypartExcuteDays`、`budgetPerformanceRuleStatus`、`placementAdjustmentRuleStatus`、`pauseCampaignRuleStatus`、`bidPerformanceRuleStatus`、`targetPauseSupplementRuleStatus`），**`0`=AI 模式、`1`=Rule 模式（本工具不支持）** —— 与"1=启用"的直觉相反；读侧按规则号键返回。
- **`edit_sd_ai_managed_group` 的 `optimizeType`** 接受 `1`/`2`/`3`（`3`=boost volume），此前文档只写 1/2。
- **`delete_ai_managed_group` 路由 fail-fast**（`sparkx-delete-ai-group` `1.0.2` → `1.0.3`）：`campaignType` 无法判定时直接报错，不再猜测；入口补上删除前确认所需的托管组枚举词汇表。
- **错误封套两种形状**：工具级错误用 `errorType`，管道级错误（限流、鉴权、下游业务、超时）用 `error`；响应新增 `requestId`（排障凭据，报错时应转述给用户）。补充实际限流额度（IP 60/min、token 前缀 300/min、tenant/user 维度读 120/min、写 20/min，Redis 不可用时 fail-closed 返回 429）。
- **`get_operation_log` 的 `currency` 可能是字面量 `"mixed"`**（跨币种），不是币种代码，不可用于格式化或求和。
- **批量操作命名与禁区**（`sparkx-edit-ai-group`）：补充服务端规范的 camelCase 操作名（大小写与下划线不敏感），并把词库相关的 4 个操作（`NEGATIVE_TARGET`、`BRAND_TARGET`、`TARGET_PAUSED_ADD`、`TARGET_HARVEST_ACTION`）统一标注为批量模式下不可用。

### 文档一致性

- `skills/README.md` 版本表补齐至各 `SKILL.md` 实际版本（此前落后 4 处），Scope 列改为实名。
- `skills/manifest.json`：`release` → `v1.1.1`、`updated_at` → `2026-08-25`；字段统一为 `mcp_tools`（数组）与 `scopes`（数组），并为全部 10 个 skill 补齐工具与 scope。
- 全部 Skill 的版本统一放在 frontmatter `metadata.version`，并将安装检查指引同步为读取该字段，以通过 Codex Skill frontmatter 校验。
- 四个可选 Skill 的 Version History 补上 `1.0.0` 与 `1.0.1` 条目（此前停在 v0.x），并清理了指向未随包发布的设计草稿的引用。
- 读侧 `platform-notes.md` 的自述改为通用措辞，7 份副本现为逐字节一致（此前自称"仅 3 个读 skill 各有一份"）。
- 写侧共享读取说明同步采用同一套 AI / Rule 模式判断，避免创建、编辑和删除前后检查沿用“空 `aiAutomation` 等于全部 AI”的错误口径。
- 修正自检发现的跨文档矛盾：SB Rule 模式配置可读但不可写；创建侧规则 4/5/182 字段明确标为只读上下文；排期分页字段明确为顶层响应字段；Vendor 指标回退不再仅凭空值直接判定账户类型。
- 版本发布改为以 `main` 分支线上 `manifest.json` 为基线；同一未发布批次内的多轮本地修正合并为一次版本升级，不从本地临时版本连续递增。

### 随 1.1.1 一并发布的历史未发布条目

以下条目此前累积在 `[Unreleased]` 中，未单独发版。

- **sparkx-query-entity-metadata** `1.1.0` → `1.1.1`。
- **sparkx-query-operation-log** `1.1.0` → `1.1.1`。
- **sparkx-create-ai-group** `1.0.0` → `1.0.1`：增加业务术语消歧、写入前强制澄清检查，并修正创建时预算与目标字段的映射。
- **sparkx-edit-ai-group** `1.0.0` → `1.0.1`：增加业务术语消歧，区分需求澄清与写入授权，并按调用路径处理状态枚举。
- **sparkx-query-entity-metadata** `1.1.1` → `1.1.2`：补充托管组总预算汇总口径及其按比例调整 Campaign 预算的行为。
- **sparkx-create-ai-group** `1.0.1` → `1.0.2`：明确托管组预算、按表现调预算增量上限、预算重新分配作用范围及创建确认要求。
- **sparkx-edit-ai-group** `1.0.1` → `1.0.2`：补充固定值/百分比、Campaign/整组预算作用模型，可靠查询启用 Campaign，并在写入前展示完整影响。
- **sparkx-delete-ai-group** `1.0.0` → `1.0.1`：不再依赖 Campaign `aiGroupId` 服务端过滤，改为完整分页后本地校验托管组归属。
- **sparkx-create-ai-group** `1.0.2` → `1.0.3`：增加 Strict ACOS / ACOS 优先模式 指引（`bidPerformanceStrictAcosStatus` —— 仅 SP；前置 `targetType=2` + `bidPerformanceStatus=1` + `aiPersonality>=3`；Auto Pacing 优先；取舍需确认），并在消歧中与"设置目标 ACOS"区分开。
- **sparkx-edit-ai-group** `1.0.2` → `1.0.3`：同样的 Strict ACOS 指引，外加消歧交叉引用。
- **sparkx-edit-ai-group** `1.0.3` → `1.0.4`：预算上限预览查询启用 Campaign 改为服务端按 `aiGroupId` 过滤（campaign 支持），替代原先"拉全量 + 本地过滤"。
- **sparkx-delete-ai-group** `1.0.1` → `1.0.2`：删前抓取 Campaign 列表改为服务端按 `aiGroupId` 过滤 —— **撤销 1.0.1 的本地过滤做法**，因为按 underlying ads API，campaign 支持 `aiGroupId` 过滤。
- **sparkx-query-entity-metadata** `1.1.2` → `1.1.3`：明确 campaign 实体**全部返回字段均可筛选**（无例外 —— 含 `aiGroupId`、`portfolioId`、`campaign*Date` 等）。
- 增加 Skill 版本检查指引：AI Agent 在安装或更新时对比本地 `SKILL.md` 与远端 `manifest.json`，发现本地版本较低时提醒用户更新。
- 增加 OAuth 请求前校验要求：AI Agent 必须按 MCP 授权流程完成 discovery，并在发送请求前校验协议要求的全部必填字段。

## [1.1.0] - 2026-08-18

### 变更

- MCP 连接新增 OAuth 授权，与现有 MCP Token 两种方式并行支持。
- Plugin 内置配置继续使用 MCP Token；支持 OAuth 的客户端可通过 Custom Connector 或手动配置连接。
- 更新 README、安装说明、连接验证和 401 排障指引，明确 OAuth 与 MCP Token 两条配置路径。
- 新增 3 个 **1.0.0 必装 Skills**：`sparkx-create-ai-group`、`sparkx-edit-ai-group`、`sparkx-delete-ai-group`，覆盖 SP、SB、SD AI 托管组的创建、编辑和删除。
- 明确托管组写操作会直接修改线上配置，要求执行前确认、执行后回查。
- 补充当前能力边界：不支持排期、模板和词库设置；RBA 配置不可读取或修改，支持 RBA → AI，不支持 AI → RBA。

## [1.0.0] - 2026-07-28

首个版本（对应 MCP Server v1.0.0 · 数据查询）。

### 新增

- 3 个**必装 Skills**：
  - **sparkx-query-ads-performance** `1.0.0` — 广告效果查询 Skill，对应 MCP tool `get_ads_perf`（scope：`amazon_sa:performance:read`）
  - **sparkx-query-entity-metadata** `1.0.0` — 实体配置 / 元数据查询 Skill，对应 MCP tool `get_entity_metadata`（scope：`amazon_sa:ads_configuration:read`）
  - **sparkx-query-operation-log** `1.0.0` — 操作日志查询 Skill，对应 MCP tool `get_operation_log`（scope：`amazon_sa:ads_logs:read`）
- 4 个**可选 Skills**（位于 `skills/optional/`，装完必装 Skills 后按需添加）：
  - **sparkx-weekly-ads-report** `0.9.4` — 广告周报
  - **sparkx-monthly-ads-report** `0.5.6` — 广告月报
  - **sparkx-ads-structure-analysis** `0.2.3` — 广告结构分析
  - **sparkx-product-diagnosis** `0.1.11` — 商品诊断
- `skills/manifest.json` 机器可读版本清单（含 `required` 字段区分必装 / 可选）
- README 与安装说明（Claude / ChatGPT Codex / WorkBuddy / Cherry Studio / 扣子 Coze / OpenClaw / Hermes / Cursor 等客户端配置）
