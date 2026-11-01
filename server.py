"""Local broker for the user-controlled Edge Agent extension."""
import argparse
import asyncio
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import time
import uuid
from aiohttp import web, WSMsgType

VERSION = '0.4.1'
DEFAULT_ROOT = Path(__file__).resolve().parent
OPS = {'snapshot', 'fill', 'select', 'click', 'eval', 'screenshot', 'navigate', 'new_tab', 'activate', 'close_tab'}

def prepare(root, port=18765):
    root = Path(root).resolve()
    runtime = root / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    config_path = runtime / 'config.json'
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if config['port'] != port:
            raise ValueError('端口与已有配置不一致，请使用原端口')
    else:
        config = {'port': port, 'token': secrets.token_urlsafe(32)}
        temp = config_path.with_suffix('.tmp')
        temp.write_text(json.dumps(config), encoding='utf-8')
        os.replace(temp, config_path)
    extension = root / 'extension'
    extension.mkdir(exist_ok=True)
    (extension / 'connection.json').write_text(json.dumps({
        'url': f'ws://127.0.0.1:{port}/ws', 'token': config['token']
    }), encoding='utf-8')
    return config

class Broker:
    def __init__(self, root, config):
        self.root = Path(root)
        self.config = config
        self.ws = None
        self.tabs = {}
        self.enabled = False
        self.browser_scope = False
        self.pending = {}
        self.locks = {}
        self.started = time.time()
        self.stop = asyncio.Event()

    def status(self):
        return {'version': VERSION, 'pid': os.getpid(), 'running': True,
                'connected': self.ws is not None and not self.ws.closed,
                'enabled': self.enabled, 'browser_scope': self.browser_scope, 'tabs': list(self.tabs.values()),
                'pending': len(self.pending), 'uptime': int(time.time()-self.started)}

    def disconnected(self, ws):
        if self.ws is not ws:
            return
        self.ws = None
        self.tabs = {}
        self.enabled = False
        self.browser_scope = False
        for future in list(self.pending.values()):
            if not future.done():
                future.set_exception(ConnectionError('扩展连接已断开；命令没有自动重试'))
        self.pending.clear()

    async def command(self, tab_id, op, args, timeout=30):
        if op not in OPS:
            raise ValueError('不支持的命令')
        tab_id = int(tab_id)
        if not isinstance(args, dict):
            raise ValueError('args 必须为对象')
        lock = self.locks.setdefault(tab_id, asyncio.Lock())
        async with lock:
            if not self.ws or self.ws.closed or not self.enabled:
                raise ConnectionError('扩展尚未连接或已暂停，请点击扩展图标接入')
            if not self.browser_scope:
                raise ValueError('浏览器尚未接入，请点击 Edge Agent 扩展图标')
            if op != 'new_tab' and tab_id not in self.tabs:
                raise ValueError('该标签页不存在于已接入的浏览器')
            ws = self.ws
            request_id = uuid.uuid4().hex
            future = asyncio.get_running_loop().create_future()
            self.pending[request_id] = future
            try:
                await ws.send_json({'type': 'command', 'id': request_id,
                                    'tab_id': tab_id, 'op': op, 'args': args})
                return await asyncio.wait_for(future, timeout=max(.05, min(float(timeout), 120)))
            except asyncio.TimeoutError:
                raise TimeoutError('命令等待超时，可能已执行；没有自动重试，请先核查页面') from None
            finally:
                self.pending.pop(request_id, None)
                if not future.done():
                    future.cancel()

@web.middleware
async def boundary(request, handler):
    broker = request.app['broker']
    port = broker.config['port']
    if request.host not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
        raise web.HTTPForbidden(text='Host 被拒绝')
    origin = request.headers.get('Origin')
    local = {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}
    extension_origin = bool(origin and re.fullmatch(r'chrome-extension://[a-p]{32}', origin))
    if request.path == '/ws':
        if not extension_origin:
            raise web.HTTPForbidden(text='仅接受浏览器扩展连接')
    elif origin and origin not in local:
        raise web.HTTPForbidden(text='来源被拒绝')
    if request.headers.get('Sec-Fetch-Site') == 'cross-site':
        raise web.HTTPForbidden(text='跨站请求被拒绝')
    if request.path.startswith('/api/'):
        expected = 'Bearer ' + broker.config['token']
        if not hmac.compare_digest(request.headers.get('Authorization', ''), expected):
            raise web.HTTPUnauthorized(text='未授权')
    try:
        response = await handler(request)
    except (ValueError, TypeError, KeyError) as exc:
        response = web.json_response({'ok': False, 'error': str(exc)}, status=400)
    except ConnectionError as exc:
        response = web.json_response({'ok': False, 'error': str(exc)}, status=503)
    except TimeoutError as exc:
        response = web.json_response({'ok': False, 'error': str(exc)}, status=504)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

async def health(request):
    b = request.app['broker']
    return web.json_response({'app': 'EdgeAgent', 'version': VERSION, 'running': True,
                              'connected': b.ws is not None and not b.ws.closed})

async def status(request):
    return web.json_response(request.app['broker'].status())

async def tabs(request):
    return web.json_response({'tabs': list(request.app['broker'].tabs.values())})

async def command(request):
    data = await request.json()
    result = await request.app['broker'].command(data['tab_id'], data['op'], data.get('args', {}), data.get('timeout', 30))
    return web.json_response({'ok': True, 'result': result})

async def shutdown(request):
    request.app['broker'].stop.set()
    return web.json_response({'ok': True, 'message': '本地服务正在停止，浏览器保持打开'})

async def websocket(request):
    b = request.app['broker']
    if b.ws and not b.ws.closed:
        raise web.HTTPConflict(text='已有扩展连接')
    ws = web.WebSocketResponse(max_msg_size=32*1024*1024, heartbeat=25)
    await ws.prepare(request)
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=5)
        if first.get('type') != 'auth' or not hmac.compare_digest(str(first.get('token', '')), b.config['token']):
            await ws.close(code=1008, message=b'unauthorized')
            return ws
        if b.ws and not b.ws.closed:
            await ws.close(code=1008, message=b'already connected')
            return ws
        b.ws = ws
        await ws.send_json({'type': 'welcome', 'version': VERSION})
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                continue
            data = json.loads(message.data)
            kind = data.get('type')
            if kind == 'ping':
                await ws.send_json({'type': 'pong'})
            elif kind == 'state':
                b.enabled = data.get('enabled') is True
                b.browser_scope = data.get('browser_scope') is True
                b.tabs = {int(t['id']): {'id': int(t['id']), 'title': str(t.get('title', ''))[:500], 'url': str(t.get('url', ''))[:4000],
                                       'windowId': t.get('windowId'), 'index': t.get('index'), 'active': bool(t.get('active')),
                                       'controllable': bool(t.get('controllable'))}
                          for t in data.get('tabs', []) if isinstance(t.get('id'), int)} if b.browser_scope else {}
            elif kind == 'result':
                future = b.pending.get(data.get('id'))
                if future and not future.done():
                    if data.get('ok'):
                        future.set_result(data.get('result'))
                    else:
                        future.set_exception(ValueError(str(data.get('error', '扩展命令失败'))))
    except (asyncio.TimeoutError, ValueError, TypeError, KeyError, ConnectionError):
        await ws.close(code=1008, message=b'invalid message')
    finally:
        b.disconnected(ws)
    return ws

async def dashboard(request):
    path = request.app['broker'].root / 'dashboard.html'
    return web.Response(text=path.read_text(encoding='utf-8'), content_type='text/html', headers={
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"})

async def dashboard_js(request):
    b = request.app['broker']
    script = (b.root / 'dashboard.js').read_text(encoding='utf-8')
    script = script.replace('__TOKEN__', json.dumps(b.config['token']))
    script = script.replace('__PRODUCT_ROOT__', json.dumps(str(b.root.resolve())))
    return web.Response(text=script, content_type='application/javascript')

def make_app(root=DEFAULT_ROOT, port=18765, config=None):
    root = Path(root)
    app = web.Application(middlewares=[boundary], client_max_size=2*1024*1024)
    app['broker'] = Broker(root, config or prepare(root, port))
    app.add_routes([web.get('/health', health), web.get('/', dashboard), web.get('/dashboard.js', dashboard_js),
                    web.get('/ws', websocket), web.get('/api/status', status), web.get('/api/tabs', tabs),
                    web.post('/api/command', command), web.post('/api/shutdown', shutdown)])
    return app

async def main(root, port):
    app = make_app(root, port)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, '127.0.0.1', port).start()
    path = Path(root) / 'runtime' / 'server.pid'
    path.write_text(str(os.getpid()), encoding='ascii')
    try:
        await app['broker'].stop.wait()
    finally:
        ws = app['broker'].ws
        if ws:
            await ws.close(code=1001, message=b'service stopped')
        await runner.cleanup()
        path.unlink(missing_ok=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--port', type=int, default=18765)
    ns = parser.parse_args()
    try:
        asyncio.run(main(ns.root, ns.port))
    except KeyboardInterrupt:
        pass
