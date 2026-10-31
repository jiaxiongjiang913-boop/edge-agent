---
name: edge-agent
description: 通过已安装的本机 Edge Agent 扩展控制已登录的 Edge 浏览器。用户要求使用 Edge Agent、浏览器扩展接入，或继续已有扩展连接时使用；不用于原生应用控制。
---

# Edge Agent 浏览器接入

点击扩展图标可启动本地服务并接入整个 Edge；空白新标签页也可以连接。复用用户已有的浏览器与登录状态。

使用本技能的 `scripts/edge_agent.py`，解释器选用 Edge Agent 安装目录的 `.venv/Scripts/python.exe`；若本机另有用户指定的解释器规则，遵循本机规则。安装后的 `installation.local.json` 记录产品目录，也可以用 `EDGE_AGENT_ROOT` 指定。不要把本机路径或配置回填到共享技能源码。

先调用 `status` 核对实际状态。`connected=true` 且 `browser_scope=true` 才表示浏览器已接入。已授权的浏览器任务中，未连接时先由助手调用 `start` 启动本机服务和现有 Edge，再读取 `status`、`tabs`。首次扩展权限确需用户点击时才提示。缺少 Edge 时提示官方安装入口；不要复制浏览器配置、扫描调试端口或启动另一份浏览器来替代扩展。标签页的 `id` 是浏览器实际 ID，不是列表索引。

入口命令：

```text
edge_agent.py status
edge_agent.py start
edge_agent.py tabs
edge_agent.py new-tab --url https://example.com
edge_agent.py activate --tab 123
edge_agent.py snapshot --tab 123
edge_agent.py fill --tab 123 --label 姓名 --value 示例
edge_agent.py select --tab 123 --label 城市 --value 示例
edge_agent.py click --tab 123 --text 查询
edge_agent.py eval --tab 123 --file <脚本路径>
edge_agent.py screenshot --tab 123 --output <图片路径>
edge_agent.py navigate --tab 123 --url https://example.com
edge_agent.py close-tab --tab 123
```

先读取页面或标签列表，再根据真实状态操作。页面定位可用 `--selector` 替代 `--label` 或 `--text`；匹配不唯一时缩小范围，不猜测。`eval` 在网页上下文运行 JavaScript；浏览器内部页面仅支持标签管理。验证码和人工身份确认交给用户。超时可能已产生副作用，先核查页面，不自动重放操作。

连接只是执行通道，具体操作仍以当前用户请求为准。用户主动暂停时保持暂停。聊天结束、任务结束或脚本退出不代表要断开连接，不在清理阶段调用 `stop`、暂停扩展或关闭浏览器。仅在用户明确要求停止时使用对应入口。

凭据位于产品的 `runtime/` 和 `extension/connection.json`。不打印、共享或写入记忆；新电脑重新安装并生成自己的凭据。

支持本地 MCP 的 Agent 可改用仓库的 `mcp_server.py`，安装时生成的配置在产品目录 `runtime/mcp-config.local.json`。跨 Agent 的完整安装流程见仓库根目录 `INSTALL_FOR_AGENTS.md`。
