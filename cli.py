"""Script entry point for an already running Edge Agent service."""
import argparse
import base64
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent

def request(path, payload=None, root=ROOT):
    config_path = root / 'runtime' / 'config.json'
    if not config_path.exists():
        raise ValueError('请打开 Edge 后点击 Edge Agent 扩展图标')
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    req = Request(f"http://127.0.0.1:{cfg['port']}{path}",
                  data=None if payload is None else json.dumps(payload).encode('utf-8'),
                  headers={'Authorization': 'Bearer '+cfg['token'], 'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=(payload or {}).get('timeout', 30)+5) as response:
            return json.load(response)
    except HTTPError as exc:
        body = exc.read().decode('utf-8', 'replace')
        try:
            body = json.loads(body).get('error', body)
        except ValueError:
            pass
        raise ValueError(body) from None
    except URLError:
        raise ValueError('本地服务未启动，请打开 Edge 后点击 Edge Agent 扩展图标') from None

def main(argv=None):
    p = argparse.ArgumentParser(description='Edge Agent 脚本控制')
    p.add_argument('--root', type=Path, default=ROOT)
    sub = p.add_subparsers(dest='op', required=True)
    for name in ('status', 'tabs', 'stop', 'start', 'doctor'):
        sub.add_parser(name)
    template = sub.add_parser('workflow')
    template.add_argument('name', choices=('literature-search', 'reference-check'))
    new = sub.add_parser('new-tab')
    new.add_argument('--url', default='about:blank')
    new.add_argument('--timeout', type=float, default=30)
    for name in ('snapshot', 'fill', 'select', 'click', 'eval', 'screenshot', 'navigate', 'activate', 'close-tab',
                 'wait', 'upload', 'download', 'download-status'):
        s = sub.add_parser(name)
        s.add_argument('--tab', type=int, required=True)
        s.add_argument('--timeout', type=float, default=30)
        if name == 'snapshot':
            s.add_argument('--max-length', type=int, default=10000)
            s.add_argument('--include-values', action='store_true')
            s.add_argument('--frame', default='')
        if name in ('fill', 'select', 'click', 'wait', 'upload', 'download'):
            targets = s.add_mutually_exclusive_group(required=name != 'wait')
            targets.add_argument('--selector')
            if name in ('click', 'wait'):
                targets.add_argument('--text')
            elif name in ('fill', 'select'):
                targets.add_argument('--label')
            targets.add_argument('--ref', type=int)
            s.add_argument('--frame', default='')
        if name == 'wait':
            s.add_argument('--state', choices=('visible', 'hidden', 'attached', 'detached', 'enabled', 'ready'), default='visible')
        if name == 'upload':
            s.add_argument('--files', type=Path, nargs='+', required=True)
        if name == 'download':
            s.add_argument('--directory', type=Path, required=True)
            s.set_defaults(timeout=60)
        if name == 'download-status':
            s.add_argument('--download-id', required=True)
        if name in ('fill', 'select'):
            s.add_argument('--value', required=True)
        if name == 'eval':
            g = s.add_mutually_exclusive_group(required=True)
            g.add_argument('--file', type=Path)
            g.add_argument('--expression')
        if name == 'screenshot':
            s.add_argument('--output', type=Path, required=True)
        if name == 'navigate':
            s.add_argument('--url', required=True)
    a = p.parse_args(argv)
    try:
        import browser_api
        browser_api.ROOT = a.root.resolve()
        if a.op == 'doctor':
            from diagnostics import diagnose
            result = diagnose(a.root)
        elif a.op == 'workflow':
            result = browser_api.workflow(a.name)
        elif a.op == 'wait':
            result = {'ok': True, 'result': browser_api.wait(a.tab, a.selector or '', a.text or '', a.ref, a.frame, a.state, a.timeout)}
        elif a.op == 'upload':
            result = {'ok': True, 'result': browser_api.upload(a.tab, a.files, a.selector or '', a.ref, a.frame)}
        elif a.op == 'download':
            result = {'ok': True, 'result': browser_api.download(a.tab, a.directory, a.selector or '', a.ref, a.frame, a.timeout)}
        elif a.op == 'click':
            args = browser_api.locate(selector=a.selector or '', text=a.text or '', ref=a.ref, frame=a.frame)
            result = {'ok': True, 'result': browser_api.command(a.tab, 'click', args, timeout=a.timeout)}
        elif a.op == 'start':
            result = browser_api.start()
        elif a.op in ('status', 'tabs'):
            result = request('/api/'+a.op, root=a.root)
        elif a.op == 'stop':
            result = request('/api/shutdown', {}, root=a.root)
        else:
            excluded = {'root', 'op', 'tab', 'timeout', 'output', 'file'}
            args = {k: v for k, v in vars(a).items() if k not in excluded and v is not None}
            if a.op == 'eval' and a.file:
                args['expression'] = a.file.read_text(encoding='utf-8-sig')
            result = request('/api/command', {'tab_id': getattr(a, 'tab', 0), 'op': a.op.replace('-', '_'), 'args': args, 'timeout': a.timeout}, root=a.root)
            if a.op == 'screenshot':
                target = a.output.resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base64.b64decode(result['result']['data'], validate=True))
                result = {'ok': True, 'path': str(target)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if a.op == 'doctor' and not result['ready'] else 0
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
