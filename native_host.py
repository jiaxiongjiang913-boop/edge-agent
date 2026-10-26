"""One fixed native-messaging action: start this installation's local broker."""
import json
import os
from pathlib import Path
import re
import struct
import sys
from launch import ensure_service

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'native' / 'com.edge_agent.launcher.json'
MAX_MESSAGE = 4096


class HostError(ValueError):
    pass


def read_message(stream):
    header = stream.read(4)
    if len(header) != 4:
        raise HostError('消息帧不完整')
    length = struct.unpack('<I', header)[0]
    if not 0 < length <= MAX_MESSAGE:
        raise HostError('消息长度无效')
    body = stream.read(length)
    if len(body) != length:
        raise HostError('消息帧不完整')
    try:
        return json.loads(body.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise HostError('消息格式无效') from None


def write_message(stream, value):
    data = json.dumps(value, ensure_ascii=False).encode('utf-8')
    stream.write(struct.pack('<I', len(data)) + data)
    stream.flush()


def validate_origin(origin, manifest):
    if not re.fullmatch(r'chrome-extension://[a-p]{32}/', origin or ''):
        raise HostError('扩展来源无效')
    if origin not in manifest.get('allowed_origins', []):
        raise HostError('此扩展未获授权')


def dispatch(message):
    if not isinstance(message, dict) or set(message) != {'action'} or message['action'] != 'ensure_service':
        raise HostError('仅支持启动本地连接服务')
    current = ensure_service()
    return {'ok': True, 'healthy': True, 'app': 'EdgeAgent', 'version': current['version']}


def main():
    if os.name == 'nt':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    source, output = sys.stdin.buffer, sys.stdout.buffer
    try:
        if not MANIFEST.is_file():
            raise HostError('本机启动组件尚未安装')
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        validate_origin(sys.argv[1] if len(sys.argv) > 1 else '', manifest)
        result = dispatch(read_message(source))
    except HostError as exc:
        result = {'ok': False, 'error': str(exc)}
    except Exception:
        result = {'ok': False, 'error': '本地服务启动失败，请重试或检查服务日志'}
    write_message(output, result)


if __name__ == '__main__':
    main()
