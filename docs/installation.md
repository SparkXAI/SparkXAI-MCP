# SparkX AI MCP 安装说明

> **🤖 致 AI Agent：如果你正在替用户执行本文档的配置，"配置 MCP"和"安装 Skills"是一个整体任务。** 完成 MCP 连接验证后，你必须继续安装 7 个必装 Skills（[`skills/`](../skills/) 目录，无需询问用户），然后逐个介绍该目录下标记为可选的 4 个 Skills 并询问用户是否安装。只配置连接不装 Skills 视为任务未完成。

完整走完 4 步：**选择授权方式 → 连接并验证 MCP → 安装 Skills → 开始使用**。全程约 5 分钟。

> 前提：你需要一个**支持 MCP 的 AI 助手**。最简单、最推荐用 **WorkBuddy**（国内）或 **Claude**（海外，Desktop 应用或 Code CLI）；也支持 ChatGPT Codex、Cherry Studio、扣子 Coze、OpenClaw、Hermes、Cursor、Cline 等。

---

## 第一步 · 选择授权方式

SparkX AI MCP 支持 OAuth 和 MCP Token 两种授权方式。两种方式使用相同的 Server URL 和 MCP Tools。

### 方式 A · OAuth

适用于支持 MCP OAuth 的客户端。连接时会打开 SparkX 登录授权页面，无需创建、复制或保存 Token。授权完成后，客户端会自动维护连接状态。

### 方式 B · MCP Token

适用于暂不支持 OAuth 的客户端、自动化脚本，或企业要求使用固定凭证的场景。

1. 登录 SparkX 后台，点击右上角账号菜单，进入 **MCP & Skills**。
2. 点击「**新建 Token**」，按需选择有效期、授权范围、店铺范围和数据权限。
3. **立即复制并妥善保存**生成的 Token。关闭弹窗后无法再次查看，遗失后需重新创建。

> ⚠️ MCP Token 是访问凭证，请勿共享或粘贴到公开的对话、文档和代码仓库中。

---

## 第二步 · 在你的 AI 助手里配置 MCP

两种授权方式使用同一个 MCP Server。请根据客户端是否支持浏览器授权、使用环境及企业凭证管理要求选择。

- **Server URL**：`https://mcp.sparkx.cn/mcp`
- **传输方式**：Streamable HTTP

### 方式一 · 一句话配置（推荐）

在能让 AI 自己动手配置的客户端（WorkBuddy、Claude、ChatGPT Codex、Cherry Studio、扣子 Coze 等）里，直接把下面这段发给它：

```text
请阅读以下 GitHub 仓库，并按说明配置 SparkX AI MCP 和安装 Skills：
https://github.com/SparkXAI/SparkXAI-MCP

SparkX AI MCP 支持 OAuth 和 MCP Token 两种授权方式。
请先检查当前客户端支持哪些授权方式，简要说明两种方式分别适合哪些场景，并让我确认使用哪一种方式后再开始授权。
如果选择 OAuth，需要授权时请打开登录页面让我完成授权。
使用 OAuth 时，请遵循 MCP Authorization 规范；发送任何 OAuth 请求前，先校验 discovery 得到的端点和全部必填字段，不要省略或猜测协议参数。

配置完成后，请调用 get_user_authorized_context 验证连接。
```

> **🤖 致 AI Agent：** 执行上述配置时，请根据你所在客户端的实际配置方式，将 MCP 配置写入正确的配置文件。注意区分不同客户端使用的配置文件名称（如 `mcp.json`、`.mcp.json`、`mcp_config.json`、`config.toml`、`config.yaml` 等），不要混淆。

助手会根据你确认的授权方式配置 MCP、完成授权、验证连接并安装必装 Skills。返回已授权的店铺列表即表示连接成功。

- **WorkBuddy**：在对话中直接发送上面的配置提示词。
- **Claude**：打开 Claude → 切到 **Code 标签页** → 粘贴上面这段。
- **ChatGPT Codex**：直接把这段发给 Codex（它会写进 `~/.codex/config.toml`）。
- **Cherry Studio / 扣子 Coze**：在对话里发给对应智能体即可。

若客户端不支持让 AI 代配，按下方「手动配置」在设置里添加。

### 方式二 · Plugin 安装

#### 桌面端 App

> 普通 Claude Desktop / Claude 网页版的 Chat 模式请使用下方 [Custom Connector](#claude-desktop-与-claude-网页版custom-connector无需配置文件) 连接 MCP。Custom Connector 只提供 MCP Tools，Skills 需要在 **Settings → Skills** 中单独添加。以下 marketplace 安装流程仅适用于 Claude Code Desktop。

##### Claude Code Desktop

1. 切换到 **Code** 标签页。
2. 点击输入框旁的 **+ → Plugins → Add plugin**，打开 Plugin browser。
3. 在 **Marketplaces** 中选择从 repository 添加，输入 `SparkXAI/SparkXAI-MCP`。
4. 找到并安装 **SparkX AI MCP**。Plugin 会同时安装 MCP server 和全部 11 个 Skills。

> **注意：**Claude Code Desktop 不支持 `/plugin` 命令。该命令仅用于 Claude Code CLI；桌面端请使用 Plugin browser。

##### ChatGPT Desktop · Codex

1. 点击左侧边栏的 **Plugins**。
2. 点击右上角的 **Add → Add a marketplace**。
3. 输入 `SparkXAI/SparkXAI-MCP` 并添加 marketplace。
4. 在 **Plugins** 中找到新添加的 marketplace，然后安装 **SparkX AI MCP**。
5. 新建一个 Codex 任务，MCP server 和全部 11 个 Skills 将在新任务中可用。

> **注意：**ChatGPT 桌面端 Codex 不支持 `/plugin` 或 `/plugins` 命令。`/plugins` 仅用于 Codex CLI；桌面端必须通过左侧边栏的 Plugins 操作。

桌面端界面参考：[Claude Code Desktop](https://code.claude.com/docs/en/desktop#install-plugins) · [ChatGPT / Codex Plugins](https://learn.chatgpt.com/docs/plugins)

#### 命令行 CLI

##### Claude Code CLI

```text
/plugin marketplace add SparkXAI/SparkXAI-MCP
/plugin install sparkx-ai-mcp@sparkx-ai
```

##### Codex CLI

```bash
codex plugin marketplace add SparkXAI/SparkXAI-MCP
codex
```

进入 Codex CLI 后输入 `/plugins`，从 `sparkx-ai` marketplace 中选择并安装 **SparkX AI MCP**，然后启动新会话。

Plugin 会同时安装 MCP server 和全部 11 个 Skills。当前 Plugin 配置使用 `SPARKX_AI_TOKEN`；设置环境变量并启动新会话。若选择 OAuth，请使用下方 OAuth 配置。

### 方式三 · 手动配置

> ⚠️ **配置完成 ≠ 安装完成**：添加 MCP server 后，务必继续 [第三步 · 安装 Skills](#第三步--安装-skills)。必装的 7 个 Skills 直接决定查询准确率和受支持写操作的执行质量。

> **🤖 致 AI Agent：** 以下列出多种客户端的配置示例，每种客户端的配置文件名称和格式各不相同。请根据用户实际使用的客户端，选择对应的配置方式写入正确的文件，不要混淆不同客户端的配置文件。

#### OAuth

> **🤖 AI Agent / 自研客户端 OAuth 请求前检查：**请遵循 [MCP Authorization 规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)，先完成 authorization server discovery，再构造请求。发送 authorization request 或 token request 前，必须校验 discovery 得到的端点和当前流程要求的全部字段。尤其要在两类请求中都传递 `resource=https://mcp.sparkx.cn/mcp`，使用 Authorization Code + PKCE（`S256`）并保证 `code_verifier` 匹配，使用与注册信息完全一致的 `redirect_uri`，同时生成并校验 `state`。如果必需的元数据或字段缺失、冲突，应停止并报告问题，不得猜测参数或发送不完整请求。标准 MCP 客户端通常会自动处理这些要求，不要让用户把 OAuth 参数拼接到 Server URL。

##### Claude Desktop 与 Claude 网页版：Custom Connector（无需配置文件）

Claude Desktop 和 Claude 网页版可以通过 Custom Connector 直接连接远程 MCP Server，无需编辑 `mcp.json`、安装 Node.js 或运行 `npx`。

1. 根据套餐添加连接器：
   - **Pro / Max**：打开 **Customize → Connectors → + → Add custom connector**。
   - **Team / Enterprise**：由组织的 Owner 或 Primary Owner 打开 **Organization settings → Connectors → Add → Custom → Web**。普通成员不能自行添加。
2. 添加时填写：
   - **Name**：`SparkX AI MCP`
   - **Remote MCP server URL**：`https://mcp.sparkx.cn/mcp`
3. 点击 **Add**。Team / Enterprise 成员随后在 **Customize → Connectors** 中找到该连接器并点击 **Connect**；Pro / Max 用户直接点击 **Connect**。
4. 在打开的浏览器页面中登录 SparkX 并确认个人授权。
5. 返回 Claude，连接器显示 **Connected** 后即可使用 MCP Tools，无需重启。

##### Claude Code CLI / Desktop 的 Code 标签页

```bash
claude mcp add --transport http sparkx-ai-mcp https://mcp.sparkx.cn/mcp
```

添加后输入 `/mcp`，选择 `sparkx-ai-mcp` 并按提示打开浏览器完成授权。

##### ChatGPT Codex

```bash
codex mcp add sparkx-ai-mcp --url https://mcp.sparkx.cn/mcp
codex mcp login sparkx-ai-mcp
```

第二条命令会打开 SparkX 登录授权页面。完成授权后返回 Codex。

##### 其他支持 OAuth 的 MCP 客户端

在客户端的 MCP 设置中添加远程 / Streamable HTTP server：

```text
https://mcp.sparkx.cn/mcp
```

选择 **OAuth**、**登录**或**授权**，并按客户端提示完成浏览器授权。

> **OAuth 兼容性：**客户端必须在 authorization request 和 token request 中传递 `resource`，其值为完整的 MCP Server URL：`https://mcp.sparkx.cn/mcp`。符合 MCP OAuth 规范的客户端会自动处理，用户无需手动配置，也不要将 `resource` 拼接到 Server URL。自研客户端或手动实现 DCR + PKCE 时需要显式支持，并遵守上方请求前检查要求。

#### MCP Token

##### Claude Code CLI / Desktop 的 Code 标签页

```bash
claude mcp add --transport http sparkx-ai-mcp https://mcp.sparkx.cn/mcp --header "Authorization: Bearer <你的TOKEN>"
```

建议保持默认的 **local scope**（仅当前项目文件夹），token 不会散落到其他项目。

##### Claude Desktop（Chat，UI 无 Bearer 选项时）

编辑 `claude_desktop_config.json`（Windows：`%APPDATA%\Claude\`；macOS：`~/Library/Application Support/Claude/`），用 `mcp-remote` 包一层后重启：

```json
{
  "mcpServers": {
    "sparkx-ai-mcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.sparkx.cn/mcp", "--header", "Authorization: Bearer ${SPARKX_AI_TOKEN}"],
      "env": { "SPARKX_AI_TOKEN": "<你的token>" }
    }
  }
}
```

##### ChatGPT Codex（`~/.codex/config.toml`）

```toml
[mcp_servers.sparkx-ai-mcp]
url = "https://mcp.sparkx.cn/mcp"
bearer_token_env_var = "SPARKX_AI_TOKEN"
http_headers = {}
```

##### OpenClaw

```bash
openclaw mcp add sparkx-ai-mcp \
  --url https://mcp.sparkx.cn/mcp \
  --transport streamable-http \
  --header "Authorization: Bearer $SPARKX_AI_TOKEN"
```

> ⚠️ 旧版 OpenClaw 有个 bug：streamable-http 不转发自定义 Authorization 头（约 2026 年 4 月底起已修复）。遇到 401 先升级到最新版。

##### Hermes（`~/.hermes/config.yaml`）

```yaml
mcp_servers:
  sparkx-ai-mcp:
    url: "https://mcp.sparkx.cn/mcp"
    headers:
      Authorization: "Bearer ${SPARKX_AI_TOKEN}"
```

然后在 Hermes 里运行 `/reload-mcp`。

##### 其他 MCP 客户端（Cursor、Cline 等）

在客户端的 MCP 设置里添加一个远程 / Streamable HTTP server，填上面的 URL 和 `Authorization: Bearer <你的TOKEN>` 请求头即可。

---

### 环境变量配置（SPARKX_AI_TOKEN）

仅使用 MCP Token 时需要配置该环境变量。Codex、Hermes 等客户端可从 `SPARKX_AI_TOKEN` 读取 Token，避免把凭证直接写入配置文件。

#### macOS / Linux

临时（当前终端会话有效）：

```bash
export SPARKX_AI_TOKEN=<你的token>
```

永久（写入 shell 配置文件）：

```bash
# zsh（macOS 默认）
echo 'export SPARKX_AI_TOKEN=<你的token>' >> ~/.zshrc && source ~/.zshrc

# bash
echo 'export SPARKX_AI_TOKEN=<你的token>' >> ~/.bashrc && source ~/.bashrc
```

#### Windows

临时（当前 PowerShell 会话有效）：

```powershell
$env:SPARKX_AI_TOKEN = "<你的token>"
```

永久（写入用户环境变量，重启终端后生效）：

```powershell
[System.Environment]::SetEnvironmentVariable("SPARKX_AI_TOKEN", "<你的token>", "User")
```

或通过图形界面：「系统属性」→「高级」→「环境变量」→「用户变量」→「新建」，变量名填 `SPARKX_AI_TOKEN`，变量值填你的 token。

> ⚠️ Token 包含完整权限凭证，不要写入版本控制仓库，不要明文粘贴到聊天记录里。



### 验证连接

完成 OAuth 或 MCP Token 配置后，让助手调用 `get_user_authorized_context`：

| 结果 | 含义 |
|------|------|
| 返回你的 userId 和授权的 profileIds | ✅ 配置成功 |
| 客户端提示登录或授权 | OAuth 尚未完成，按提示打开页面授权 |
| 返回 401 | OAuth 已失效或被撤销，或 MCP Token 错误、过期、被禁用或缺少权限 |
| 超时 | 检查网络 |

---

## 第三步 · 安装 Skills

Skills 在本仓库 [`skills/`](../skills/) 目录，分两类：

> **致 AI Agent：** 安装或更新前，读取 [`skills/manifest.json`](../skills/manifest.json)，并与本地同名 Skill 的 `SKILL.md` `metadata.version` 比较。本地版本更低时，列出需要更新的 Skill 并提醒用户；正常查询期间不要重复检查。

**必装（7 个）**——覆盖基础查询、托管组管理和广告实体编辑：

- `sparkx-query-ads-performance` — 广告效果查询
- `sparkx-query-entity-metadata` — 实体配置查询
- `sparkx-query-operation-log` — 操作日志查询
- `sparkx-create-ai-group` — 创建 AI 托管组
- `sparkx-edit-ai-group` — 编辑单个或批量 AI 托管组
- `sparkx-delete-ai-group` — 删除 AI 托管组
- `sparkx-edit-ads` — 编辑支持的线上 Campaign、关键词、Target、推广商品和否定投放设置

**可选（4 个）**——进阶分析场景，装完必装的再按需添加（位于 [`skills/`](../skills/)）：

- `sparkx-weekly-ads-report` — 广告周报
- `sparkx-monthly-ads-report` — 广告月报
- `sparkx-ads-structure-analysis` — 广告结构分析
- `sparkx-product-diagnosis` — 商品诊断

按你的助手选安装方式：

- **能让 AI 自己动手的助手**（Claude Code、ChatGPT Codex、Cursor 等）：把 Skill 目录发给它，说一句"帮我把 7 个必装 Skill 装上"，可选 Skills 按需加装。
- **聊天 / 界面类助手**（Claude 网页版或桌面 App、Cherry Studio、扣子 Coze 等）：在各自设置里手动添加（以 Claude 为例：设置 → Skills → 上传，逐个添加）。

---

## 第四步 · 开始查询

四步走：1）让助手列出你授权的店铺 → 2）选一个店铺 → 3）用自然语言提问 → 4）拿走结果（让它导出表格 / 图表 / 放进报告）。

**示例提示词：**

- 表现：
  - "上周花费最高的 10 个 campaign，带 ACOS。"
  - "这个产品线过去 8 周的 TACOS 趋势。"
  - "本周相比上周 ACOS 上升最多的 5 个 campaign。"
- 配置：
  - "列出所有启用的 SP campaign 及其日预算。"
  - "这个 ASIN 的库存、标题和广告类型资格。"
- 操作日志：
  - "过去 7 天 AI 自动调价的记录。"
  - "谁在什么时候改了这个 campaign 的预算？"

**进阶**：让助手把多个查询综合成一份周报、导出 CSV/Excel，或结合你的成本/目标算出真实利润；把常用提示词做成可复用模板。

---

## 常见问题

**Q：返回 401 Unauthorized？**
先确认使用的授权方式。OAuth 用户请重新登录授权，并确认授权未被撤销；MCP Token 用户请检查 Token 是否过期、复制完整、未被禁用且具备所需权限。旧版 OpenClaw 用户请先升级客户端。

**Q：能查多久以前的数据？**
效果数据和操作日志约可回溯最近 15 个月。效果数据默认到天；广告活动维度还支持小时级（AMS）数据，另有关键词×广告位的小时级视图，这两种小时级查询的日期跨度上限为 7 天。

**Q：数据是实时的吗？**
与 SparkX AI 平台数据更新节奏一致，非秒级实时。

**Q：能查哪些店铺？**
取决于你的 SparkX 账号权限及本次 OAuth 或 MCP Token 的授权范围，最终可见范围不会超过账号本身的权限。

**Q：这一版支持哪些写操作？**
v1.2.0 支持创建、编辑和删除 AI 托管组，也支持修改 Campaign 预算、状态和 SP 竞价策略，管理关键词和 Target 的状态与竞价、推广商品及支持的否定投放。写操作会直接修改线上配置并生效，执行前必须核对 Profile 和对象，在要求确认的操作中确认具体变更，并在执行后回查。暂不支持创建 Campaign 或使用独立删除操作，但支持通过状态更新归档 Campaign。

**Q：托管组管理有哪些暂不支持的设置？**
词库相关设置暂不支持。托管组排期已支持读写（仅 SP/SB，SD 无排期工具）；模板可读取并套用到托管组，但模板本身只能在平台里创建和编辑。RBA 规则配置现在可以读取（含条件、动作、周期与分时矩阵），但不能通过 MCP 修改；允许将行动空间从 RBA 切换为 AI，仍不支持从 AI 切换为 RBA。
