# Edge Agent

当前版本 **0.5.0**。沿用已登录的 Edge，让具备本地工具能力的 Agent 完成网页操作。包含扩展、本地服务、19 个 MCP 工具、CLI、安装诊断，以及文献检索和参考文献核验两套 Agent 工作流模板。

本版增加文件上传、浏览器下载完成检查、条件等待，以及可访问性快照中的元素 `ref` 定位。可处理封装组件中的可访问控件；提供同源 iframe 与开放 Shadow DOM 定位。详细边界见下文。

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
6. 把扩展固定到工具栏并点击图标。首次连接会在此电脑生成新的随机配对凭据；显示“浏览器已连接”后运行 **Check.cmd** 或 `cli.py doctor` 检查每一项。浏览器账号由你在新电脑自行登录。

日常只需点击扩展图标，无需开机自启。维护时可用 **Start.cmd** 打开本地管理页，或用 **Stop.cmd** 主动停止服务。管理页为 `http://127.0.0.1:18765/`。服务固定使用本机端口 18765；如端口被其他程序占用，先解决冲突。

`Install.ps1 -PrepareOnly` 可先完成环境准备并生成通用 MCP 配置；取得扩展 ID 后再用 `-ExtensionId <扩展ID> -SkipDependencies` 完成注册。安装需要联网下载 Python 依赖。

更新现有安装时，先保存浏览器中的工作并主动停止旧服务，将新文件放回原安装目录、运行安装程序，然后在扩展管理页重新加载扩展。一次仅保留一套活动安装使用端口 18765；不要把旧的 `runtime/` 或 `native/` 上传到仓库。原电脑当前正在使用的版本不会因下载新版而被后台替换。

更新后重新加载扩展并接入；本版沿用既有权限。安装器可复用原目录记录的扩展 ID，迁移到新目录/电脑时仍需填写实际 ID。

## 命令行与 Codex 技能

在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -B cli.py status
.\.venv\Scripts\python.exe -B cli.py start
.\.venv\Scripts\python.exe -B cli.py tabs
.\.venv\Scripts\python.exe -B cli.py snapshot --tab 123
.\.venv\Scripts\python.exe -B cli.py doctor
.\.venv\Scripts\python.exe -B cli.py wait --tab 123 --selector '#result' --state visible --timeout 20
.\.venv\Scripts\python.exe -B cli.py upload --tab 123 --selector 'input[type=file]' --files 'E:\Data\selected.png'
.\.venv\Scripts\python.exe -B cli.py download --tab 123 --selector 'a#download' --directory 'E:\Data\Downloads'
.\.venv\Scripts\python.exe -B cli.py workflow reference-check
```

支持 `new-tab`、`activate`、`close-tab`、`fill`、`select`、`click`、`eval`、`screenshot`、`navigate`；参数见 `cli.py --help` 及子命令的 `--help`。标签页 ID 以 `tabs` 返回值为准。截图选择用户要求的数据盘输出路径。

### 复杂控件、等待与文件

- `snapshot` 的 `elements` 包含 `ref`、可访问角色和名称；将其中的 `ref` 传给 `click/fill/select/upload/download/wait`。页面跳转或重建控件后重新取快照，不保留旧编号。CLI/MCP 点击会先激活目标标签，再通过浏览器输入事件完成。
- 开放 Shadow DOM 可用 `#host >>> button`；同源 iframe 用 `--frame '#frame' --selector '#field'`。封闭 Shadow DOM 的可访问控件优先使用 `ref`。跨进程/跨域 iframe 的内部控件未保证可枚举，遇到缺失请打开对应页面，不把容器当按钮点击。
- `wait` 支持 `visible/hidden/attached/detached/enabled/ready`，最长 110 秒；只轮询状态，不重放点击或填写。`ready` 指文档加载完成，不代表所有异步业务均完成。
- `upload` 仅操作指定的真实文件输入框，文件路径在本机经 CDP 传入，不把文件内容编码成命令；仍应只选择用户授权的文件。
- `download` 在当前 Edge 页面网络上下文中读取已观察到的 HTTP/HTTPS 文件链接，分块传给本机服务并保存到指定目录，认证信息留在 Edge。任务状态由本机服务返回；文件只保存、不执行。普通导航、blob URL、JS 动态生成且没有实际文件链接的按钮不在此接口范围，可先按页面流程取得链接。权限或网络拦截如实报错。超时不自动重试。
- `download-status --tab <ID> --download-id <ID>` 查询本次本地服务为该标签页创建的文件传输，不读取用户的其他下载历史；ID 为工具返回的字符串。服务重启后传输状态记录不保留，已完成文件仍在指定目录。
- 快照默认省略表单字段的 `value`；需要核对填写结果时显式加 `--include-values`。网页正文和可见编辑内容仍可能包含私人信息，只用于当前授权任务。

### 科研工作流

`workflow literature-search` 和 `workflow reference-check` 返回给当前 Agent 执行的模板；MCP 对应 `edge_workflow`。检索按真实网页搜索、逐条读来源、保留 DOI/出版方链接；核验输出“信息一致 / 信息不匹配 / 待核查”。模板不会自行运行模型，也不把未找到的条目标为虚假。

模板源文件：[文献检索](workflows/literature-search.md)、[参考文献核验](workflows/reference-check.md)。

通用 MCP 配置在 `runtime/mcp-config.local.json`，将其中 `mcpServers.edge-agent` 合并到客户端即可，不能用它覆盖已有服务配置。该文件只含本机路径与编码选项，不含浏览器配对令牌。MCP 服务使用官方 Python SDK，支持当前和旧版握手；客户端配置与接入说明见 [INSTALL_FOR_AGENTS.md](INSTALL_FOR_AGENTS.md)。

Codex 使用安装器额外生成的 `runtime/mcp-codex.local.toml`，将条目合并到其配置；其他客户端使用通用 JSON，按各客户端实际入口配置。客户端实测范围见 [COMPATIBILITY.md](COMPATIBILITY.md)。

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
