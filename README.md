# Edge Agent

当前正式版 **0.4.1**。以本机当前可用的 Edge Agent 功能为基础，保留整个浏览器接入、按需启动、自动重连与命令行操作，增加通用 Agent 安装流程及标准 stdio MCP 接口。包含扩展、本地服务、13 个 MCP 工具、CLI、安装脚本和可选技能。

**给 Codex、豆包工作、Kimi、Claude、Gemini、DeepSeek Harness 等 Agent 安装：将本仓库网址和安装指令发送给它的工作 / Agent 模式，要求先读取 [INSTALL_FOR_AGENTS.md](INSTALL_FOR_AGENTS.md)。** 能执行本地命令或连接本机 stdio MCP 的客户端可以接入。具体能力以客户端为准，云端聊天或沙盒本身不能控制用户电脑的 Edge。

公开仓库：[edge-agent](https://github.com/jiaxiongjiang913-boop/edge-agent)。[下载最新安装包](https://github.com/jiaxiongjiang913-boop/edge-agent/releases/latest/download/EdgeAgent-portable.zip)，无需登录 GitHub。

## 在另一台 Windows 电脑安装

1. 下载上方最新安装包并解压，也可用 Git 克隆公开仓库，或在仓库页面选择 **Code → Download ZIP**。无需 GitHub 账号或访问令牌。将目录放到长期保留的位置，例如 `E:\Tools\EdgeAgent`。不要直接在压缩包里运行。
2. 确认已安装 **Microsoft Edge**。缺少时安装器会提示并停止，不会自动下载。按需访问 [Edge 官方下载](https://www.microsoft.com/edge/download)，或执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\Download-Edge.ps1 -Install`，从微软下载并校验安装器签名后安装。
3. 安装 Python 3.11 或更新版本。双击 **Install.cmd**，它会在项目内创建 `.venv` 并安装 `requirements.txt`。也可以在 PowerShell 中指定已安装的解释器：

   ```powershell
   .\Install.ps1 -PythonPath 'E:\Python\python.exe'
   ```

4. 按安装脚本提示打开 `edge://extensions`，启用“开发人员模式”，点击“加载解压缩的扩展”，选择项目内的 **extension** 文件夹。
5. 在扩展卡片中复制 **Edge Agent 的 ID**，粘贴回安装窗口。脚本只为当前 Windows 用户注册本机启动组件，无需管理员权限。新路径或新电脑的扩展 ID 可能不同，要使用实际显示的 ID。
6. 把扩展固定到工具栏并点击图标。首次连接会在此电脑生成新的随机配对凭据；显示“浏览器已连接”后即可使用。浏览器账号由你在新电脑自行登录。

日常只需点击扩展图标，无需开机自启。维护时可用 **Start.cmd** 打开本地管理页，或用 **Stop.cmd** 主动停止服务。管理页为 `http://127.0.0.1:18765/`。服务固定使用本机端口 18765；如端口被其他程序占用，先解决冲突。

`Install.ps1 -PrepareOnly` 可先完成环境准备并生成通用 MCP 配置；取得扩展 ID 后再用 `-ExtensionId <扩展ID> -SkipDependencies` 完成注册。安装需要联网下载 Python 依赖。

更新现有安装时，先保存浏览器中的工作并主动停止旧服务，将新文件放回原安装目录、运行安装程序，然后在扩展管理页重新加载扩展。一次仅保留一套活动安装使用端口 18765；不要把旧的 `runtime/` 或 `native/` 上传到仓库。原电脑当前正在使用的版本不会因下载新版而被后台替换。

## 命令行与 Codex 技能

在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -B cli.py status
.\.venv\Scripts\python.exe -B cli.py start
.\.venv\Scripts\python.exe -B cli.py tabs
.\.venv\Scripts\python.exe -B cli.py snapshot --tab 123
```

支持 `new-tab`、`activate`、`close-tab`、`fill`、`select`、`click`、`eval`、`screenshot`、`navigate`；参数见 `cli.py --help` 及子命令的 `--help`。标签页 ID 以 `tabs` 返回值为准。截图选择用户要求的数据盘输出路径。

通用 MCP 配置在 `runtime/mcp-config.local.json`，将其中 `mcpServers.edge-agent` 合并到客户端即可，不能用它覆盖已有服务配置。该文件只含本机路径与编码选项，不含浏览器配对令牌。MCP 服务使用官方 Python SDK，支持当前和旧版握手；客户端配置与接入说明见 [INSTALL_FOR_AGENTS.md](INSTALL_FOR_AGENTS.md)。

可选安装 Codex 技能（默认写入当前电脑的 Codex 技能目录）：

```powershell
.\.venv\Scripts\python.exe -B install_skill.py
```

要将技能也放在指定数据盘，可用 `--destination 'E:\AgentSkills'`，然后在 Codex 使用的技能目录建立指向 `E:\AgentSkills\edge-agent` 的目录联接，或按该电脑的技能配置方式载入。安装器遇到已有同名技能会停止，避免覆盖。安装后的本地配置记录此电脑的产品路径，不会提交到仓库。也可直接调用仓库内 `skills/edge-agent/scripts/edge_agent.py`。

## 迁移与隐私边界

- 仓库只包含源码、通用图标、技能、安装说明和测试。未包含原电脑的用户名、个人目录、邮箱、浏览器配置、Cookie、登录状态、历史标签、日志、截图或旧 Git 历史。提交作者使用中性名称和邮箱。
- `runtime/`、`native/`、`.venv/`、`extension/connection.json`、`*.local.json` 等本机生成文件已忽略。不要使用 `git add -f` 上传这些文件，也不要直接把整个使用中的项目目录压缩分享。
- 新电脑会独立生成令牌与启动配置，无需从原电脑复制它们。原电脑的安装和连接不受此仓库影响。
- 本仓库公开提供源码和安装包，地址及所有者会显示 GitHub 账号名。源码和提交作者信息的去标识化不改变仓库所属账号。
- 扩展接入后可以控制该浏览器的全部标签页，并可在普通网页执行脚本。只将此通道用于你授权的任务；验证码由你完成。服务仅绑定 `127.0.0.1`，不需要开放路由器或防火墙端口。

移动已安装的项目目录后，应重建 `.venv` 并重新运行安装程序；Python 虚拟环境不适合直接搬家。重新登记扩展 ID，并重新安装技能或更新它的本机路径配置。多台电脑分别安装。

## 开发验证

```powershell
.\.venv\Scripts\python.exe -B -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests
```

测试不会更改真实 Edge 的本机启动注册；测试文件和配对数据放在临时目录中。当前目标平台为 Windows + Microsoft Edge。
