import asyncio
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import make_app

class BrokerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = make_app(Path(self.tmp.name), config={'port': 0, 'token': 'test-only-token'})
        self.client = TestClient(TestServer(self.app, host='127.0.0.1'))
        await self.client.start_server()
        self.b = self.app['broker']
        self.b.config['port'] = self.client.port
        self.auth = {'Authorization': 'Bearer test-only-token'}

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    async def extension(self):
        ws = await self.client.ws_connect('/ws', headers={'Origin': 'chrome-extension://'+'a'*32})
        await ws.send_json({'type': 'auth', 'token': 'test-only-token'})
        self.assertEqual((await ws.receive_json())['type'], 'welcome')
        await ws.send_json({'type': 'state', 'enabled': True, 'browser_scope': True, 'tabs': [{'id': 7, 'title': 'Test', 'url': 'http://example.test/'}]})
        for _ in range(20):
            if 7 in self.b.tabs: break
            await asyncio.sleep(.01)
        return ws

    async def test_auth_and_origin_boundaries(self):
        self.assertEqual((await self.client.get('/api/status')).status, 401)
        response = await self.client.get('/api/status', headers=self.auth)
        self.assertEqual(response.status, 200)
        response = await self.client.get('/health', headers={'Origin': 'https://hostile.example'})
        self.assertEqual(response.status, 403)
        response = await self.client.get('/health', headers={'Host': 'rebind.example'})
        self.assertEqual(response.status, 403)
        response = await self.client.get('/dashboard.js', headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(response.status, 403)
        with self.assertRaises(Exception):
            await self.client.ws_connect('/ws', headers={'Origin': 'https://hostile.example'})

    async def test_only_joined_tabs_can_receive_commands(self):
        ws = await self.extension()
        with self.assertRaisesRegex(ValueError, '不存在于已接入'):
            await self.b.command(8, 'fill', {'value': 'bad'})
        with self.assertRaisesRegex(ValueError, '不支持'):
            await self.b.command(7, 'Browser.close', {})
        task = asyncio.create_task(self.b.command(7, 'snapshot', {}))
        command = await ws.receive_json()
        await ws.send_json({'type': 'result', 'id': command['id'], 'ok': True, 'result': {'title': 'Test'}})
        self.assertEqual(await task, {'title': 'Test'})

    async def test_commands_on_one_tab_are_serial(self):
        ws = await self.extension()
        first = asyncio.create_task(self.b.command(7, 'fill', {'value': 'first'}))
        second = asyncio.create_task(self.b.command(7, 'click', {}))
        command = await ws.receive_json()
        read = asyncio.create_task(ws.receive_json())
        await asyncio.sleep(.05)
        self.assertFalse(read.done(), 'second command must wait for the first result')
        await ws.send_json({'type': 'result', 'id': command['id'], 'ok': True, 'result': 1})
        self.assertEqual(await first, 1)
        command2 = await asyncio.wait_for(read, 1)
        self.assertEqual(command2['op'], 'click')
        await ws.send_json({'type': 'result', 'id': command2['id'], 'ok': True, 'result': 2})
        self.assertEqual(await second, 2)

    async def test_disconnect_fails_pending_without_replay(self):
        ws = await self.extension()
        task = asyncio.create_task(self.b.command(7, 'click', {}))
        await ws.receive_json()
        await ws.close()
        with self.assertRaises(ConnectionError):
            await task
        self.assertFalse(self.b.pending)
        self.assertFalse(self.b.tabs)
        await self.extension()
        self.assertEqual(len(self.b.pending), 0)

    async def test_timeout_does_not_replay_or_consume_late_result(self):
        ws = await self.extension()
        task = asyncio.create_task(self.b.command(7, 'click', {}, timeout=.05))
        command = await ws.receive_json()
        with self.assertRaises(TimeoutError):
            await task
        self.assertFalse(self.b.pending)
        await ws.send_json({'type': 'result', 'id': command['id'], 'ok': True, 'result': 'late'})
        await ws.send_json({'type': 'ping'})
        self.assertEqual((await ws.receive_json())['type'], 'pong')
        self.assertFalse(self.b.pending)

    async def test_invalid_ws_token_cannot_register_tabs(self):
        ws = await self.client.ws_connect('/ws', headers={'Origin': 'chrome-extension://'+'b'*32})
        await ws.send_json({'type': 'auth', 'token': 'wrong'})
        result = await ws.receive()
        self.assertEqual(result.type, WSMsgType.CLOSE)
        self.assertIsNone(self.b.ws)

if __name__ == '__main__':
    unittest.main(verbosity=2)
