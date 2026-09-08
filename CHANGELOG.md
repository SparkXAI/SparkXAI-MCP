# Changelog

本文件记录 SparkX AI MCP Skills 与配套文档的版本变化。

## [Unreleased]

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
- **sparkx-delete-ai-group** `1.0.1` → `1.0.2`：删前抓取 Campaign 列表改为服务端按 `aiGroupId` 过滤 —— **撤销 1.0.1 的本地过滤做法**，因为按 sparkxads API，campaign 支持 `aiGroupId` 过滤。
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
