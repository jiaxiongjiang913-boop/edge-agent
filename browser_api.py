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
    # Trusted browser input is delivered to the active tab. Activate this task's
    # actual target before clicking; otherwise CDP may acknowledge a no-op.
    if operation == 'click':
        request('/api/command', {'tab_id': tab_id, 'op': 'activate', 'args': {}, 'timeout': 30}, root=ROOT)
    response = request('/api/command', {'tab_id': tab_id, 'op': operation,
                                      'args': arguments or {}, 'timeout': timeout}, root=ROOT)
    return response['result']


def target(selector, label, key):
    return locate(selector=selector, **{key: label})


def locate(selector='', text='', label='', ref=None, frame=''):
    values = {'selector': selector, 'text': text, 'label': label, 'ref': ref}
    chosen = {key: value for key, value in values.items() if value is not None and value != ''}
    if len(chosen) != 1 or ('ref' in chosen and (isinstance(ref, bool) or int(ref) <= 0)):
        raise ValueError('请只提供 selector、text、label 或有效 ref 其中一项')
    if frame:
        chosen['frame'] = frame
    return chosen


def wait(tab_id, selector='', text='', ref=None, frame='', state='visible', timeout=30):
    if not 0 <= timeout <= 110:
        raise ValueError('等待时长必须在 0 到 110 秒之间')
    args = {} if state == 'ready' else locate(selector=selector, text=text, ref=ref, frame=frame)
    return command(tab_id, 'wait', {**args, 'state': state, 'wait_timeout': timeout}, timeout=timeout + 5)


def upload(tab_id, files, selector='', ref=None, frame=''):
    if not files:
        raise ValueError('至少需要一个文件')
    paths = [Path(file).expanduser().resolve() for file in files]
    if any(not path.is_file() for path in paths):
        raise ValueError('上传文件不存在或不是普通文件')
    return command(tab_id, 'upload', {**locate(selector=selector, ref=ref, frame=frame), 'files': [str(path) for path in paths]})


def download(tab_id, directory, selector='', ref=None, frame='', timeout=60):
    if not 0 < timeout <= 110:
        raise ValueError('下载等待时长必须在 0 到 110 秒之间')
    target_dir = Path(directory).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    return command(tab_id, 'download', {**locate(selector=selector, ref=ref, frame=frame),
                   'directory': str(target_dir), 'wait_timeout': timeout}, timeout=timeout + 5)


def workflow(name):
    if name not in ('literature-search', 'reference-check'):
        raise ValueError('模板名称必须为 literature-search 或 reference-check')
    return {'name': name, 'instructions': (Path(__file__).resolve().parent / 'workflows' / (name + '.md')).read_text(encoding='utf-8')}
