"""Shared local browser operations for command-line and MCP agents."""
import os
from pathlib import Path
import time

from cli import request

ROOT = Path(os.environ.get('EDGE_AGENT_ROOT', Path(__file__).resolve().parent)).resolve()


def status():
    try:
        return request('/api/status', root=ROOT)
    except (ValueError, OSError) as exc:
        return {'running': False, 'connected': False, 'message': str(exc)}


def start():
    from launch import ensure_service, open_dashboard
    ensure_service(ROOT)
    open_dashboard(ROOT)
    deadline = time.monotonic() + 8
    while True:
        result = status()
        if result.get('connected') or time.monotonic() >= deadline:
            break
        time.sleep(.25)
    if not result.get('connected'):
        result['message'] = '服务与 Edge 已启动；首次安装请点击扩展图标。若已主动暂停，请由用户恢复连接。'
    return result


def tabs():
    return request('/api/tabs', root=ROOT)


def command(tab_id, operation, arguments=None, timeout=30):
    response = request('/api/command', {'tab_id': tab_id, 'op': operation,
                                      'args': arguments or {}, 'timeout': timeout}, root=ROOT)
    return response['result']


def target(selector, label, key):
    if bool(selector) == bool(label):
        raise ValueError(f'请只提供 selector 或 {key} 其中一项')
    return {'selector': selector} if selector else {key: label}
