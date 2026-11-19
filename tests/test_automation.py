"""Contract tests for local file handling, diagnostics and timeout bounds."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import browser_api
import diagnostics


def test_upload_only_for_explicit_existing_files(tmp_path):
    chosen = tmp_path / 'file with spaces.txt'
    chosen.write_text('test', encoding='utf-8')
    with patch.object(browser_api, 'command', return_value={'uploaded': True}) as send:
        browser_api.upload(7, [str(chosen)], ref=9)
        assert send.call_args.args == (7, 'upload', {'ref': 9, 'files': [str(chosen.resolve())]})
        send.reset_mock()
        with pytest.raises(ValueError):
            browser_api.upload(7, [str(tmp_path / 'missing')], selector='#file')
        send.assert_not_called()


def test_trusted_click_activates_its_target_before_sending_input():
    with patch.object(browser_api, 'request', return_value={'result': {'clicked': True}}) as send:
        assert browser_api.command(7, 'click', {'ref': 9})['clicked']
        assert [call.args[1]['op'] for call in send.call_args_list] == ['activate', 'click']
        assert all(call.args[1]['tab_id'] == 7 for call in send.call_args_list)


def test_wait_timeouts_leave_a_response_margin_and_do_not_mutate():
    with patch.object(browser_api, 'command', return_value={'matched': True}) as send:
        browser_api.wait(7, selector='#ready', timeout=4)
        assert send.call_args.kwargs['timeout'] == 9
        assert send.call_args.args[1] == 'wait'
        with pytest.raises(ValueError):
            browser_api.wait(7, selector='#ready', timeout=111)
        with pytest.raises(ValueError):
            browser_api.wait(7, timeout=1)


def test_download_uses_explicit_directory_and_bounds(tmp_path):
    destination = tmp_path / 'requested data folder'
    with patch.object(browser_api, 'command', return_value={'state': 'complete'}) as send:
        browser_api.download(7, destination, ref=8, timeout=10)
        assert destination.is_dir()
        assert send.call_args.args[2]['directory'] == str(destination.resolve())
        assert send.call_args.kwargs['timeout'] == 15
        with pytest.raises(ValueError):
            browser_api.download(7, destination, ref=8, timeout=0)


def test_doctor_is_read_only_and_omits_pairing_and_browser_content(tmp_path):
    with patch('cli.request', return_value={'running': True, 'connected': True, 'browser_scope': True,
                'version': '0.5.0', 'token': 'secret-sentinel', 'tabs': [{'title': 'private-sentinel'}]}):
        report = diagnostics.diagnose(tmp_path)
    encoded = json.dumps(report)
    assert 'secret-sentinel' not in encoded
    assert 'private-sentinel' not in encoded
    assert str(tmp_path) not in encoded
    assert not list(tmp_path.iterdir())
    assert report['ready'] is False
    assert any(c['check'] == 'native_host' and c['action'] for c in report['checks'])


def test_templates_are_agent_neutral_and_do_not_claim_absence_means_fake():
    result = browser_api.workflow('reference-check')
    assert '原文件默认只读' in result['instructions']
    assert '不得改写为“虚假”' in result['instructions']
    with pytest.raises(ValueError):
        browser_api.workflow('../runtime/config')


def test_doctor_can_report_missing_dependencies_without_importing_them(tmp_path):
    result = subprocess.run([sys.executable, '-S', '-B', str(ROOT / 'cli.py'), '--root', str(tmp_path), 'doctor'],
                            env={**os.environ, 'PYTHONPATH': '', 'PYTHONIOENCODING': 'utf-8'},
                            capture_output=True, text=True, encoding='utf-8', timeout=10)
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert {c['check'] for c in data['checks'] if 'missing' in c['message']} >= {'aiohttp', 'mcp'}
