"""Read-only installation diagnosis. Never returns pairing secrets or tab contents."""
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys


def diagnose(root=None):
    from browser_api import ROOT
    from version import VERSION
    root = Path(root or ROOT).resolve()
    checks = []

    def add(name, ok, message, action=''):
        checks.append({'check': name, 'status': 'ok' if ok else 'needs_attention',
                       'message': message, 'action': '' if ok else action})

    add('platform', sys.platform == 'win32', '目标平台为 Windows', '请在使用 Edge 的 Windows 电脑运行安装。')
    add('python', sys.version_info >= (3, 11), 'Python ' + sys.version.split()[0], '安装 Python 3.11+，重新运行 Install.ps1。')
    for package, expected in (('aiohttp', '3.13.2'), ('mcp', '2.3.0')):
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            installed = 'missing'
        add(package, installed == expected, f'{package}: {installed}；要求 {expected}',
            '使用安装环境运行 Install.ps1，或安装 requirements.txt。')
    from edge_browser import find_edge
    try:
        find_edge()
        edge = True
    except RuntimeError:
        edge = False
    add('edge', edge, 'Microsoft Edge 已安装' if edge else '未找到 Microsoft Edge',
        '请从 https://www.microsoft.com/edge/download 安装 Edge；不会自动下载。')
    manifest = root / 'native/com.edge_agent.launcher.json'
    registration_ok = False
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
        origins = data['allowed_origins']
        valid = len(origins) == 1 and re.fullmatch(r'chrome-extension://[a-p]{32}/', origins[0])
        if sys.platform == 'win32' and valid:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Edge\NativeMessagingHosts\com.edge_agent.launcher') as key:
                actual = winreg.QueryValueEx(key, '')[0]
            registration_ok = Path(actual).resolve() == manifest and Path(data['path']).is_file()
    except (OSError, ValueError, KeyError, TypeError):
        pass
    add('native_host', registration_ok, '当前目录的本机启动组件已注册' if registration_ok else '本机启动组件尚未注册或指向其他安装',
        '在 edge://extensions 加载此目录的 extension，再用实际扩展 ID 运行 Install.ps1 -ExtensionId <ID>。')
    pairing_ok = False
    try:
        cfg = json.loads((root / 'runtime/config.json').read_text(encoding='utf-8'))
        connection = json.loads((root / 'extension/connection.json').read_text(encoding='utf-8'))
        pairing_ok = (isinstance(cfg['token'], str) and len(cfg['token']) >= 32 and
                      connection['token'] == cfg['token'] and connection['url'] == f"ws://127.0.0.1:{cfg['port']}/ws")
    except (OSError, ValueError, KeyError, TypeError):
        pass
    add('pairing', pairing_ok, '本机配对配置一致' if pairing_ok else '本机配对配置未生成或不一致',
        '首次安装完成后启动服务；移动目录或手动改过配置时重新安装，不复制其他电脑的配对文件。')
    from cli import request
    try:
        service = request('/api/status', root=root)
    except (OSError, ValueError):
        service = {}
    add('service', service.get('running') is True, '本地服务已运行' if service else '本地服务未运行或当前目录未配对',
        '已授权浏览器任务中运行 cli.py start；若端口被占用，先检查已有安装。')
    if service:
        add('version', service.get('version') == VERSION, '服务版本 ' + str(service.get('version')) + '；源码版本 ' + VERSION,
            '保存浏览器工作，停止旧服务，更新原安装目录并重新加载扩展。')
        add('extension_version', service.get('extension_version') == VERSION,
            '扩展版本 ' + str(service.get('extension_version', 'unknown')) + '；要求 ' + VERSION,
            '在 edge://extensions 重新加载此安装目录的扩展，按浏览器提示确认权限后连接。')
    add('browser', service.get('connected') is True and service.get('browser_scope') is True,
        '整个 Edge 浏览器已连接' if service.get('connected') else '浏览器尚未连接',
        '首次安装请点击 Edge Agent 图标授权接入；用户主动暂停后由用户恢复。')
    mcp_ok = False
    try:
        config = json.loads((root / 'runtime/mcp-config.local.json').read_text(encoding='utf-8'))
        entry = config['mcpServers']['edge-agent']
        mcp_ok = Path(entry['command']).is_file() and str(root / 'mcp_server.py') in entry['args']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    add('mcp_config', mcp_ok, '本机通用 MCP 配置有效' if mcp_ok else '本机 MCP 配置未生成或目录已移动',
        '用安装环境运行 agent_setup.py，将生成的条目合并到客户端。')
    return {'version': VERSION, 'ready': all(c['status'] == 'ok' for c in checks), 'checks': checks,
            'privacy': '报告不包含令牌、扩展 ID、浏览器标签、个人路径或已填写的表单内容。'}
