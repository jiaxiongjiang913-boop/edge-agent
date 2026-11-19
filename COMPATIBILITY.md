# Agent 接入与验证范围

所有客户端使用同一个本机 CLI / stdio MCP 接口；“工作模式”的名称本身不能保证本地执行能力。

| 客户端 | 配置 | 验证范围 |
| --- | --- | --- |
| Codex CLI / 支持本地 MCP 的 Codex 客户端 | 合并 `runtime/mcp-codex.local.toml` 的 `mcp_servers.edge-agent` | 已通过本机 Codex app-server 的 MCP 初始化与 19 个工具发现；未启动模型回合，非全任务验收 |
| Claude Desktop / Claude Code | 通用 JSON 的 command、args、env；按客户端入口注册 stdio | 通用配置；未在此电脑安装实测 |
| Kimi Code | 通用 JSON；按当前客户端 MCP 配置入口导入 | 通用配置；未在此电脑安装实测 |
| Gemini CLI | 通用 JSON 的 `mcpServers` 条目 | 通用配置；未在此电脑安装实测 |
| 豆包工作、DeepSeek Harness 等 | 提供本机命令工具时运行 CLI；支持本地 stdio MCP 时使用通用配置 | 取决于具体客户端；未宣称全部产品版本实测 |

安装器生成的是本机绝对路径配置，不能把这台电脑的配置复制给另一台电脑。新电脑重新安装并生成配置。

MCP 协议集成测试覆盖当前与 legacy 握手、19 个工具的发现、状态读取、填写、截图、等待、上传以及工作流模板读取。协议测试使用隔离的本地测试服务，不等同于每个品牌客户端的真实操作验收。

本机实际 MCP 调用还通过了安装诊断、Edge 快照、科研模板读取、文件下载及状态查询。真实 Edge 页面验收通过封闭/开放 Shadow DOM 的可信点击、同源 iframe 填写、富文本输入、异步等待、文件上传、指定 E 盘目录下载及字节内容核对。

本机 Codex 验证使用进程内临时配置，未修改用户配置。已安装的 CLI 对原配置中的 Windows sandbox 名称不兼容，测试进程临时使用该 CLI 支持的 `unelevated` 值。此问题不改变 MCP 配置格式，也未更改用户原值。

工具总表：`edge_status`、`edge_start`、`edge_tabs`、`edge_snapshot`、`edge_click`、`edge_fill`、`edge_select`、`edge_navigate`、`edge_new_tab`、`edge_activate`、`edge_close_tab`、`edge_evaluate`、`edge_screenshot`、`edge_doctor`、`edge_wait`、`edge_upload`、`edge_download`、`edge_download_status`、`edge_workflow`。
