# 0.5.0 验证记录

- Python 自动测试：36 项通过。包括本地服务边界、断线/超时不重放、安装迁移、MCP 当前/legacy 握手、文件传输和原有文件不覆盖。存在 aiohttp `NotAppKeyWarning` 提示，不影响本次结果。
- Node 扩展边界测试：4 项通过。覆盖元素引用释放、快照值省略、等待取消和浏览器文件流读取/关闭。
- 真实 Edge 页面验收：12 项通过。覆盖默认省略字段值、封闭 Shadow DOM 引用与可信点击、开放 Shadow DOM 点击、同源 iframe、富文本、异步等待、原生文件输入、文件流完成、指定数据盘路径、文件字节内容与任务状态。
- 实际 stdio MCP 调用：6 项通过。覆盖 19 工具发现、诊断全部就绪、真实 Edge 快照、科研模板、文件下载及状态查询。
- 本机 Codex app-server：成功初始化并发现 19 个 MCP 工具，未启动模型回合，未更改用户客户端配置。

测试平台为 Windows + Microsoft Edge + Python 3.13；安装器要求 Python 3.11+。未在所有 Python 小版本或其他品牌客户端上完成真实整套任务验收。

## 复现

```powershell
.\.venv\Scripts\python.exe -B -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests
node --test tests/test_extension.cjs
```

浏览器验收使用本机隔离的测试网页与虚拟文件，未发布社交平台内容，未操作真实科研原始数据。文件流测试核对了保存位置、实际字节与同名文件保留；科研模板仅作为当前 Agent 执行流程，未宣称自动完成了特定论文检索。
