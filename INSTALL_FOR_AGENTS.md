# 给任意 Agent 的安装与接入说明

本文件适用于 Codex、豆包工作、Kimi、Claude、Gemini、DeepSeek Harness 等 Agent 的本地工作模式。用户将公开仓库网址和安装指令发送给 Agent 后，Agent 先读取本文件，再下载并执行安装。安装不需要调用任何特定品牌的模型 API，也不要求 Codex。

## 先判断工作环境

- Agent 能在这台 Windows 电脑执行 PowerShell、运行 Python，并访问此项目目录：可以安装，并通过命令行操作 Edge。
- Agent 客户端支持本地 stdio MCP：安装后将生成的 MCP 配置导入或合并到客户端，可直接调用浏览器工具。
- Agent 只有云端沙盒或聊天能力：不能直接操作用户电脑的 Edge。应说明需要本地执行端或本地 MCP 客户端，不要把云端的 `127.0.0.1` 当成用户电脑，不宣称已安装。

“工作模式”名称本身不代表已获得本地命令或 MCP 权限。以当前客户端实际提供的工具为准；豆包、Kimi、Claude、Gemini 的网页端、桌面端、CLI 可能具备不同能力。

## 安装

1. 从公开仓库 https://github.com/jiaxiongjiang913-boop/edge-agent 获取项目。优先下载 https://github.com/jiaxiongjiang913-boop/edge-agent/releases/latest/download/EdgeAgent-portable.zip 并解压，也可通过 Git 克隆。无需 GitHub 登录或访问令牌，不要求用户先手动下载。若项目已在本机，直接使用该目录。项目保持在长期使用的位置；工作目录按当前电脑用户要求选择数据盘。
2. 在项目目录执行环境准备。将解释器替换为当前电脑已有的 Python 3.11 或更新版本，遵循当前电脑的环境规则：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -PythonPath '<python.exe实际路径>' -PrepareOnly
   ```

   安装脚本先检查 Edge。缺少时会提示官方地址及 `Download-Edge.ps1` 命令并停止，不自动下载或安装。用户同意下载后可运行：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Download-Edge.ps1 -Install
   ```

   下载器从微软官方地址获取安装器并检查微软签名。用户完成浏览器安装后，重新运行准备命令。没有 Python 时，提示用户从 [Python 官方网站](https://www.python.org/downloads/windows/) 安装，不擅自改用客户端云端的 Python。

3. 首次安装需要在 Edge 的 `edge://extensions` 开启“开发人员模式”，加载项目的 `extension` 文件夹，并记录扩展卡片的实际 ID。需要人工完成的浏览器权限操作，提示用户完成；不要修改浏览器安全策略或复制其他电脑的扩展 ID。
4. 取得扩展 ID 后完成注册：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -ExtensionId '<本机扩展ID>' -SkipDependencies
   ```

5. 首次点击 Edge Agent 图标授权接入，然后检查：

   ```powershell
   .\.venv\Scripts\python.exe -B cli.py status
   .\.venv\Scripts\python.exe -B cli.py tabs
   ```

   `connected=true` 且 `browser_scope=true` 才表示完成浏览器连接。若未连接，报告具体缺少哪一步，不用“安装成功”代替连接结果。

双击 `Install.cmd` 则运行交互安装，无需先配置任何 Agent。

## 选择接入方式

### 本地命令行

使用 `.venv\Scripts\python.exe -B cli.py`。先 `status`，已授权浏览器任务中未连接则 `start`，随后 `tabs`。再按实际标签 ID 执行 `snapshot`、`fill`、`select`、`click`、`navigate`、`new-tab`、`activate`、`close-tab`、`eval`、`screenshot`。具体参数见子命令 `--help`。

### 本地 MCP

安装器生成 `runtime/mcp-config.local.json`，内容是当前电脑的解释器、MCP 脚本路径和编码设置，不含配对令牌。合并其中的 `edge-agent` 条目，不覆盖客户端已有配置。路径发生移动后重新安装并重新生成此文件。

| Agent / 客户端 | 接入方式 |
| --- | --- |
| 豆包工作或其他桌面工作模式 | 有本地命令工具时使用 CLI；提供本地 MCP 配置入口时使用生成的配置。没有该能力时明确说明限制，不编造配置位置。 |
| Kimi Code CLI | 将配置合并到用户或项目的 `mcp.json`，或使用 `/mcp-config` 添加本地 stdio 服务。旧版 Kimi CLI 使用该版本提供的 `kimi mcp` 或配置入口。 |
| Claude Desktop | 将 `mcpServers` 条目合并到客户端的本地 MCP 配置，再重启客户端。 |
| Claude Code | 用客户端的 `claude mcp add` 注册本地命令，解释器和参数取自生成的 JSON。 |
| Gemini CLI | 将 `mcpServers` 条目合并到 `settings.json`，然后查看 `/mcp` 连接状态。 |
| 其他本地 MCP 客户端 | 选择 stdio 类型；command 使用 JSON 的 `command`，args 使用 `args`；按客户端要求导入。 |

MCP 暴露 13 个工具：`edge_status`、`edge_start`、`edge_tabs`、`edge_snapshot`、`edge_click`、`edge_fill`、`edge_select`、`edge_navigate`、`edge_new_tab`、`edge_activate`、`edge_close_tab`、`edge_evaluate`、`edge_screenshot`。MCP 启动进程时不会自动连接浏览器；由当前已授权任务调用 `edge_start`。截图直接以图片返回。

## 操作与隐私

只执行当前用户授权的浏览器任务。用户主动暂停时保持暂停；验证码和身份确认交给用户。不要自动重放超时操作。任务结束不关闭用户浏览器、不停止常驻服务；MCP 客户端退出只结束 MCP 适配器。

不要打印、复制或上传 `runtime/`、`native/`、`.venv/`、`extension/connection.json`，也不要上传客户端历史、Cookie、截图或 `*.local.json`。新电脑重新生成本机路径和随机配对凭据。MCP 读到的网页内容会交给当前 Agent，浏览器登录态仍留在本机。

## 官方资料

- [Microsoft Edge 官方下载](https://www.microsoft.com/edge/download)
- [MCP Python SDK 与本地接入](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)
- [Kimi Code MCP 配置](https://moonshotai.github.io/kimi-code/en/customization/mcp.html)
- [Gemini CLI MCP 配置](https://geminicli.com/docs/tools/mcp-server/)
- [Claude 本地 MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
- [豆包开放平台](https://open.doubao.com/)
