"""Generate machine-local launcher files and register them for the current user."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import winreg

HOST = 'com.edge_agent.launcher'
ROOT = Path(__file__).resolve().parent


def write_native_files(extension_id, root=ROOT, interpreter=None):
    if not re.fullmatch(r'[a-p]{32}', extension_id):
        raise ValueError('扩展 ID 必须为 32 位 a-p 字母')
    root = Path(root).resolve()
    python = Path(interpreter or sys.executable).resolve()
    if not (root / 'native_host.py').is_file() or not python.is_file():
        raise ValueError('本机启动组件或 Python 环境缺失')
    native = root / 'native'
    native.mkdir(exist_ok=True)
    wrapper = native / 'host.cmd'
    escaped_python = str(python).replace('%', '%%')
    wrapper.write_bytes(('@echo off\r\n@chcp 65001 >nul\r\n'
                         f'"{escaped_python}" -B -u "%~dp0..\\native_host.py" %*\r\n').encode('utf-8'))
    manifest = native / (HOST + '.json')
    value = {'name': HOST, 'description': 'Edge Agent on-demand launcher', 'path': str(wrapper),
             'type': 'stdio', 'allowed_origins': [f'chrome-extension://{extension_id}/']}
    temporary = manifest.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, manifest)
    return manifest


def install(extension_id, root=ROOT):
    manifest = write_native_files(extension_id, root)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf'Software\Microsoft\Edge\NativeMessagingHosts\{HOST}') as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(manifest))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--extension-id', required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--write-only', action='store_true', help='Generate files without changing the registry')
    args = parser.parse_args()
    if args.write_only:
        write_native_files(args.extension_id, args.root)
    else:
        install(args.extension_id, args.root)
    print('本机启动组件已生成。' if args.write_only else '本机启动组件已安装；打开 Edge 后点击 Edge Agent 即可连接。')
