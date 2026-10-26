import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install_native_host
import install_skill
import launch
import server


def load_skill(path):
    spec = importlib.util.spec_from_file_location('portable_skill', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_manifest_uses_this_machine_paths_and_exact_origin(tmp_path):
    root = tmp_path / 'moved project with spaces'
    root.mkdir()
    (root / 'native_host.py').write_text('# fixture', encoding='utf-8')
    with patch.object(install_native_host.winreg, 'CreateKey') as registry:
        manifest = install_native_host.write_native_files('a' * 32, root)
        registry.assert_not_called()
    data = json.loads(manifest.read_text(encoding='utf-8'))
    assert data['allowed_origins'] == ['chrome-extension://' + 'a' * 32 + '/']
    assert Path(data['path']) == root / 'native' / 'host.cmd'
    wrapper = Path(data['path']).read_text(encoding='utf-8')
    assert str(Path(sys.executable).resolve()).replace('%', '%%') in wrapper
    assert '"%~dp0..\\native_host.py"' in wrapper
    with pytest.raises(ValueError):
        install_native_host.write_native_files('invalid-id', root)


def test_pairing_is_unique_per_install_and_stable_on_restart(tmp_path):
    first = server.prepare(tmp_path / 'first')
    second = server.prepare(tmp_path / 'second')
    assert first['token'] != second['token']
    assert len(first['token']) >= 32
    assert server.prepare(tmp_path / 'first') == first
    connection = json.loads((tmp_path / 'first' / 'extension' / 'connection.json').read_text())
    assert connection['token'] == first['token']


def test_bundled_and_installed_skill_find_repository(tmp_path, monkeypatch):
    monkeypatch.delenv('EDGE_AGENT_ROOT', raising=False)
    bundled = load_skill(ROOT / 'skills' / 'edge-agent' / 'scripts' / 'edge_agent.py')
    assert bundled.find_product() == ROOT
    target = install_skill.install(tmp_path / 'skills')
    installed = load_skill(target / 'scripts' / 'edge_agent.py')
    assert installed.find_product() == ROOT
    with pytest.raises(FileExistsError):
        install_skill.install(tmp_path / 'skills')
    moved = tmp_path / 'another checkout'
    moved.mkdir()
    for name in ('cli.py', 'server.py'):
        (moved / name).touch()
    monkeypatch.setenv('EDGE_AGENT_ROOT', str(moved))
    assert installed.find_product() == moved


def test_launcher_uses_current_python_without_touching_real_service(tmp_path):
    fake_python = tmp_path / 'python.exe'
    fake_python.touch()
    pythonw = tmp_path / 'pythonw.exe'
    pythonw.touch()
    root = tmp_path / 'product'
    with patch.object(launch, 'startup_lock'), patch.object(launch, 'health', side_effect=[None, {'app': 'EdgeAgent'}]), \
         patch.object(launch.sys, 'executable', str(fake_python)), patch.object(launch.subprocess, 'Popen') as start:
        launch.ensure_service(root)
        assert start.call_args.args[0][0] == str(pythonw)
        assert start.call_args.args[0][2] == str(root / 'server.py')
        assert start.call_args.kwargs['cwd'] == root


def test_dashboard_injects_new_installation_path(tmp_path):
    import asyncio

    async def check():
        root = tmp_path / 'moved installation'
        root.mkdir()
        (root / 'dashboard.js').write_bytes((ROOT / 'dashboard.js').read_bytes())
        app = server.make_app(root, config={'port': 0, 'token': 'test-only-token'})
        async with TestClient(TestServer(app, host='127.0.0.1')) as client:
            app['broker'].config['port'] = client.port
            response = await client.get('/dashboard.js')
            text = await response.text()
            assert response.status == 200
            assert json.dumps(str(root.resolve())) in text
            assert '__PRODUCT_ROOT__' not in text
            assert '__TOKEN__' not in text
    asyncio.run(check())
