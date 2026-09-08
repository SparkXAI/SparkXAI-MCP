# SparkX AI MCP Skills

配合 SparkX AI MCP 使用的官方 Skills，分两类：

- **必装（7 个）**：基础查询、托管组管理与广告编辑能力，请务必安装。
- **可选（4 个）**：面向具体分析场景的进阶玩法，按需安装。

## 必装 Skills

| Skill | 版本 | 对应 MCP Tool | 所需 Scope | 用途 |
|-------|------|--------------|-----------|------|
| [sparkx-query-ads-performance](sparkx-query-ads-performance/) | 1.3.0 | `get_ads_perf` | `amazon_sa_performance_data:read` | 查询广告效果指标：花费、ACOS、ROAS、趋势、排名、同环比，小时级（AMS）与关键词×广告位，以及 Vendor ASIN 指标口径（shipped/ordered、distributorView/sellingProgram） |
| [sparkx-query-entity-metadata](sparkx-query-entity-metadata/) | 1.3.0 | `get_entity_metadata` | `amazon_sa_ads_configuration:read` | 查询实体配置：广告活动 / 广告组 / 投放 / ASIN / 托管组的名称、状态、设置，以及托管组排期、Campaign 已启用规则类型与托管组规则模式配置 |
| [sparkx-query-operation-log](sparkx-query-operation-log/) | 1.3.0 | `get_operation_log` | `amazon_sa_ads_logs:read` | 查询操作日志：人工与 AI 的调价、调预算、启停记录（含时间戳时区规则） |
| [sparkx-create-ai-group](sparkx-create-ai-group/) | 1.1.1 | `create_sd_ai_managed_group` / `save_sp_sb_ai_managed_group` / `save_sp_sb_ai_group_schedule` / `get_ai_group_template` | `amazon_sa_managed_group:write` | 创建 SP、SB 或 SD AI 托管组，可套用平台模板，并可继续设置 SP/SB 排期 |
| [sparkx-edit-ai-group](sparkx-edit-ai-group/) | 1.1.2 | `edit_sd_ai_managed_group` / `save_sp_sb_ai_managed_group` / `save_sp_sb_ai_group_schedule` / `get_ai_group_template` | `amazon_sa_managed_group:write` | 编辑单个或批量 AI 托管组，套用模板，维护 SP/SB 排期 |
| [sparkx-delete-ai-group](sparkx-delete-ai-group/) | 1.0.4 | `delete_ai_managed_group` | `amazon_sa_managed_group_delete:write` | 删除 AI 托管组并释放或迁移 Campaign |
| [sparkx-edit-ads](sparkx-edit-ads/) | 1.0.0 | `batch_update_ads` | `amazon_sa_campaign_edit:write` | 批量编辑线上广告实体：广告活动预算 / 状态 / 竞价策略，关键词与投放的状态与竞价，推广商品，否定关键词与否定投放（共 18 条路由，其中 9 条需两阶段确认） |

## 可选 Skills

基于必装 Skill 的查询能力做进阶分析，装了必装 Skills 之后即可按需添加：

| Skill | 版本 | 用途 |
|-------|------|------|
| [sparkx-weekly-ads-report](sparkx-weekly-ads-report/) | 1.0.3 | 广告周报：KPI 环比卡片、7 天趋势、异常摘要、Top 变化榜、下周行动建议 |
| [sparkx-monthly-ads-report](sparkx-monthly-ads-report/) | 1.0.3 | 广告月报：全月 KPI（环比 + 同比）、结构拆解、商品与关键词分析、下月建议 |
| [sparkx-ads-structure-analysis](sparkx-ads-structure-analysis/) | 1.0.3 | 广告结构分析：按广告类型 / 站点 / 组合 / 工作日 / 小时维度拆解花费与效率，定位结构错配 |
| [sparkx-product-diagnosis](sparkx-product-diagnosis/) | 1.0.3 | 商品诊断：ASIN 健康度分层、变体对比、问题商品诊断卡、去留优化建议 |

## 版本

- **程序读取**：[`manifest.json`](manifest.json) 是机器可读的版本清单（每条含 `name`、`version`、`required`、`mcp_tools`（数组）、`scopes`（数组）、`path`、`description`），可通过固定地址获取：

  ```
  https://raw.githubusercontent.com/SparkXAI/SparkXAI-MCP/main/skills/manifest.json
  ```

- **人工查看**：每个 Skill 的版本号在其 `SKILL.md` frontmatter 的 `metadata.version` 字段；整体变更历史见 [CHANGELOG.md](../CHANGELOG.md)。
- **致 AI Agent**：在安装、更新或按本仓库说明配置 Skills 时，将本地 `SKILL.md` 的 `metadata.version` 与上述 manifest 中同名 Skill 的版本比较。本地版本更低时，列出过期 Skill 并提醒用户更新；正常 MCP 查询期间不要重复检查或打断用户。
- **发布基线**：准备发布时，以 `main` 分支线上 `manifest.json` 为版本基线。同一未发布批次内的多轮本地修正合并为一次版本升级，不从尚未发布的本地版本继续递增。
- 发布新版本时，`manifest.json` 与 frontmatter 会同步更新，并打对应的 git tag / GitHub Release。

## 安装

- **能让 AI 自己动手的助手**（Claude Code、ChatGPT Codex、Cursor 等）：把 Skill 目录发给它，说一句"帮我装上"。先装 7 个必装 Skill，再按需加可选的。
- **聊天 / 界面类助手**（Claude 网页版或桌面 App、Cherry Studio、扣子 Coze 等）：在各自设置里手动添加（以 Claude 为例：设置 → Skills → 上传，逐个添加）。

## 目录结构

```
skills/
├── manifest.json              # 机器可读版本清单
├── sparkx-query-ads-performance/     # 必装
├── sparkx-query-entity-metadata/     # 必装
├── sparkx-query-operation-log/       # 必装
├── sparkx-create-ai-group/           # 必装
├── sparkx-edit-ai-group/             # 必装
├── sparkx-delete-ai-group/           # 必装
├── sparkx-edit-ads/                  # 必装
├── sparkx-weekly-ads-report/         # 可选
├── sparkx-monthly-ads-report/        # 可选
├── sparkx-ads-structure-analysis/    # 可选
└── sparkx-product-diagnosis/         # 可选
```

每个 Skill 是一个独立目录，含 `SKILL.md`（name / description / metadata.version 与方法论）和 `references/`（字段参考、示例查询等）。
