# Edge Agent

通过浏览器扩展，把当前已登录的 Microsoft Edge 接入本机脚本。包含 Manifest V3 扩展、Python 本地服务、按需启动组件、命令行工具和可选的 Codex 技能。迁移版基于 Edge Agent 0.3.0。

## 在另一台 Windows 电脑安装

1. 登录有权访问此私人仓库的 GitHub 账号，用 Git 克隆，或在仓库页面选择 **Code → Download ZIP** 并解压。将目录放到长期保留的位置，例如 `E:\Tools\EdgeAgent`。不要直接在压缩包里运行。
2. 安装 Python 3.10 或更新版本。双击 **Install.cmd**，它会在项目内创建 `.venv` 并安装 `requirements.txt`。也可以在 PowerShell 中指定已安装的解释器：

   ```powershell
   .\Install.ps1 -PythonPath 'E:\Python\python.exe'
   ```

3. 按安装脚本提示打开 `edge://extensions`，启用“开发人员模式”，点击“加载解压缩的扩展”，选择项目内的 **extension** 文件夹。
4. 在扩展卡片中复制 **Edge Agent 的 ID**，粘贴回安装窗口。脚本只为当前 Windows 用户注册本机启动组件，无需管理员权限。新路径或新电脑的扩展 ID 可能不同，要使用实际显示的 ID。
5. 把扩展固定到工具栏并点击图标。首次连接会在此电脑生成新的随机配对凭据；显示“浏览器已连接”后即可使用。浏览器账号由你在新电脑自行登录。

日常只需点击扩展图标，无需开机自启。维护时可用 **Start.cmd** 打开本地管理页，或用 **Stop.cmd** 主动停止服务。管理页为 `http://127.0.0.1:18765/`。服务固定使用本机端口 18765；如端口被其他程序占用，先解决冲突。

`Install.ps1 -ExtensionId <扩展ID>` 可跳过交互输入。依赖已安装时可附加 `-SkipDependencies`。安装需要联网下载 Python 依赖。

## 命令行与 Codex 技能

在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -B cli.py status
.\.venv\Scripts\python.exe -B cli.py tabs
.\.venv\Scripts\python.exe -B cli.py snapshot --tab 123
```

支持 `new-tab`、`activate`、`close-tab`、`fill`、`select`、`click`、`eval`、`screenshot`、`navigate`；参数见 `cli.py --help` 及子命令的 `--help`。标签页 ID 以 `tabs` 返回值为准。迁移版保留截图不得写入 C 盘的行为，选择其他数据盘的输出路径。

可选安装 Codex 技能（默认写入当前电脑的 Codex 技能目录）：

```powershell
.\.venv\Scripts\python.exe -B install_skill.py
```

要将技能也放在指定数据盘，可用 `--destination 'E:\AgentSkills'`，然后在 Codex 使用的技能目录建立指向 `E:\AgentSkills\edge-agent` 的目录联接，或按该电脑的技能配置方式载入。安装器遇到已有同名技能会停止，避免覆盖。安装后的本地配置记录此电脑的产品路径，不会提交到仓库。也可直接调用仓库内 `skills/edge-agent/scripts/edge_agent.py`。

## 迁移与隐私边界

- 仓库只包含源码、通用图标、技能、安装说明和测试。未包含原电脑的用户名、个人目录、邮箱、浏览器配置、Cookie、登录状态、历史标签、日志、截图或旧 Git 历史。提交作者使用中性名称和邮箱。
- `runtime/`、`native/`、`.venv/`、`extension/connection.json`、`*.local.json` 等本机生成文件已忽略。不要使用 `git add -f` 上传这些文件，也不要直接把整个使用中的项目目录压缩分享。
- 新电脑会独立生成令牌与启动配置，无需从原电脑复制它们。原电脑的安装和连接不受此仓库影响。
- GitHub 私人仓库的地址及所有者仍会显示 GitHub 账号名。这不等同于匿名托管；源码和提交作者信息的去标识化不改变仓库所属账号。
- 扩展接入后可以控制该浏览器的全部标签页，并可在普通网页执行脚本。只将此通道用于你授权的任务；验证码由你完成。服务仅绑定 `127.0.0.1`，不需要开放路由器或防火墙端口。

移动已安装的项目目录后，应重建 `.venv` 并重新运行安装程序；Python 虚拟环境不适合直接搬家。重新登记扩展 ID，并重新安装技能或更新它的本机路径配置。多台电脑分别安装。

## 开发验证

```powershell
.\.venv\Scripts\python.exe -B -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests
```

测试不会更改真实 Edge 的本机启动注册；测试文件和配对数据放在临时目录中。当前目标平台为 Windows + Microsoft Edge。
