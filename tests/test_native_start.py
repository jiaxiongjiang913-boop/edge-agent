import io
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_host


def framed(value):
    encoded = json.dumps(value, ensure_ascii=False).encode('utf-8')
    return struct.pack('<I', len(encoded)) + encoded


def test_binary_frame_round_trip():
    stream = io.BytesIO()
    native_host.write_message(stream, {'ok': True, 'text': '服务已启动'})
    stream.seek(0)
    assert native_host.read_message(stream) == {'ok': True, 'text': '服务已启动'}


@pytest.mark.parametrize('data', [b'', b'\x01', struct.pack('<I', 4097), struct.pack('<I', 4)+b'{}', struct.pack('<I', 1)+b'x'])
def test_invalid_frames_rejected(data):
    with pytest.raises(native_host.HostError):
        native_host.read_message(io.BytesIO(data))


def test_origin_allowlist_is_exact():
    origin = 'chrome-extension://' + 'a'*32 + '/'
    native_host.validate_origin(origin, {'allowed_origins': [origin]})
    for invalid in ['https://example.com/', 'chrome-extension://'+'b'*32+'/', origin+'extra']:
        with pytest.raises(native_host.HostError):
            native_host.validate_origin(invalid, {'allowed_origins': [origin]})


@pytest.mark.parametrize('message', [[], {}, {'action':'stop'}, {'action':'ensure_service','path':'arbitrary.exe'}])
def test_only_fixed_start_action_allowed(message):
    with patch.object(native_host, 'ensure_service') as start:
        with pytest.raises(native_host.HostError):
            native_host.dispatch(message)
        start.assert_not_called()


def test_valid_start_response_has_no_credentials():
    with patch.object(native_host, 'ensure_service', return_value={'version':'0.3.0','token':'DO_NOT_EXPOSE'}) as start:
        assert native_host.dispatch({'action':'ensure_service'}) == {
            'ok':True, 'healthy':True, 'app':'EdgeAgent', 'version':'0.3.0'}
        start.assert_called_once_with()
