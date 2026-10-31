import asyncio
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from aiohttp.test_utils import TestClient, TestServer
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_setup
import server


@pytest.mark.parametrize('mode', ['2026-07-28', 'legacy'])
def test_stdio_handshake_and_browser_operations(tmp_path, mode):
    async def check():
        app = server.make_app(tmp_path, config={'port': 0, 'token': 'test-only-token'})
        async with TestClient(TestServer(app, host='127.0.0.1')) as broker_client:
            app['broker'].config['port'] = broker_client.port
            runtime = tmp_path / 'runtime'
            runtime.mkdir()
            (runtime / 'config.json').write_text(json.dumps(app['broker'].config), encoding='utf-8')
            ws = await broker_client.ws_connect('/ws', headers={'Origin': 'chrome-extension://' + 'a' * 32})
            await ws.send_json({'type': 'auth', 'token': 'test-only-token'})
            assert (await ws.receive_json())['type'] == 'welcome'
            await ws.send_json({'type': 'state', 'enabled': True, 'browser_scope': True,
                                'tabs': [{'id': 7, 'title': 'Fixture', 'url': 'https://example.test/'}]})
            process = StdioServerParameters(command=sys.executable, args=['-B', str(ROOT / 'mcp_server.py')], env={
                'EDGE_AGENT_ROOT': str(tmp_path), 'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
                'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1',
            })
            async with Client(process, mode=mode, read_timeout_seconds=20) as client:
                listing = await client.list_tools()
                assert len(listing.tools) == 13
                assert {'edge_start', 'edge_tabs', 'edge_snapshot', 'edge_screenshot'} <= {t.name for t in listing.tools}
                result = await client.call_tool('edge_status')
                data = json.loads(result.content[0].text)
                assert data['connected'] is True
                assert 'token' not in data
                result = await client.call_tool('edge_tabs')
                assert json.loads(result.content[0].text)['tabs'][0]['id'] == 7
                pending = asyncio.create_task(client.call_tool('edge_fill', {'tab_id': 7, 'label': 'Name', 'value': 'Example'}))
                command = await asyncio.wait_for(ws.receive_json(), 10)
                assert command['op'] == 'fill'
                assert command['args'] == {'label': 'Name', 'value': 'Example'}
                await ws.send_json({'type': 'result', 'id': command['id'], 'ok': True, 'result': {'filled': True}})
                assert not (await pending).is_error
                invalid = await client.call_tool('edge_click', {'tab_id': 7, 'selector': '#a', 'text': 'A'})
                assert invalid.is_error
                screenshot = asyncio.create_task(client.call_tool('edge_screenshot', {'tab_id': 7}))
                command = await asyncio.wait_for(ws.receive_json(), 10)
                assert command['op'] == 'screenshot'
                await ws.send_json({'type': 'result', 'id': command['id'], 'ok': True,
                                    'result': {'data': base64.b64encode(b'fixture-image').decode()}})
                image = await screenshot
                assert image.content[0].type == 'image'
                assert image.content[0].mime_type == 'image/png'
            assert not ws.closed, 'MCP adapter shutdown must not close the browser connection'
            await ws.close()
    asyncio.run(check())


def test_generated_mcp_config_has_local_paths_but_no_pairing_secret(tmp_path):
    config = json.loads(agent_setup.generate(tmp_path).read_text(encoding='utf-8'))
    entry = config['mcpServers']['edge-agent']
    assert entry['command'] == str(Path(sys.executable).resolve())
    assert entry['args'] == ['-B', str(tmp_path / 'mcp_server.py')]
    assert 'token' not in json.dumps(config).lower()


def test_installer_prompts_for_missing_edge_before_creating_environment(tmp_path):
    for name in ('Install.ps1', 'Edge.ps1'):
        shutil.copy2(ROOT / name, tmp_path / name)
    env = {**os.environ, 'ProgramFiles': str(tmp_path), 'ProgramFiles(x86)': str(tmp_path),
           'LOCALAPPDATA': str(tmp_path), 'PATH': str(Path(os.environ['SYSTEMROOT']) / 'System32')}
    powershell = Path(os.environ['SYSTEMROOT']) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                             '-File', str(tmp_path / 'Install.ps1'), '-PrepareOnly', '-PythonPath', sys.executable],
                            env=env, capture_output=True, timeout=20)
    output = result.stdout.decode('utf-8', 'replace')
    assert result.returncode != 0
    assert 'Microsoft Edge was not found' in output
    assert 'https://www.microsoft.com/edge/download' in output
    assert not (tmp_path / '.venv').exists()
    assert not (tmp_path / 'downloads').exists()
