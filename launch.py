"""Shared on-demand launcher for the extension and maintenance shortcut."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser
from server import prepare

ROOT = Path(__file__).resolve().parent


def health(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/health', timeout=.6) as response:
            data = json.load(response)
        return data if data.get('app') == 'EdgeAgent' and data.get('running') is True else None
    except Exception:
        return None


def healthy(port):
    return health(port) is not None


@contextmanager
def startup_lock(root, port):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    identity = hashlib.sha256(f'{Path(root).resolve()}|{port}'.casefold().encode()).hexdigest()[:24]
    handle = kernel.CreateMutexW(None, False, 'Local\\EdgeAgentStartup_' + identity)
    if not handle:
        raise RuntimeError('无法创建本地服务启动锁')
    acquired = False
    try:
        result = kernel.WaitForSingleObject(handle, 20000)
        acquired = result in (0, 128)
        if not acquired:
            raise RuntimeError('本地服务正在启动，请稍后重试')
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def ensure_service(root=ROOT, port=None):
    root = Path(root).resolve()
    if port is None:
        config_file = root / 'runtime' / 'config.json'
        port = json.loads(config_file.read_text(encoding='utf-8'))['port'] if config_file.exists() else 18765
    with startup_lock(root, port):
        current = health(port)
        if current:
            return current
        prepare(root, port)
        interpreter = Path(sys.executable).resolve().with_name('pythonw.exe')
        if not interpreter.is_file():
            interpreter = Path(sys.executable).resolve()
        if not interpreter.is_file():
            raise RuntimeError('本地 Python 运行环境不可用')
        with (root / 'runtime' / 'server.log').open('a', encoding='utf-8') as log:
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            kwargs = dict(cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True,
                          env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            args = [str(interpreter), '-B', str(root / 'server.py'), '--root', str(root), '--port', str(port)]
            try:
                process = subprocess.Popen(args, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kwargs)
            except PermissionError:
                process = subprocess.Popen(args, creationflags=flags, **kwargs)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            current = health(port)
            if current:
                return current
            if process.poll() is not None:
                raise RuntimeError('本地服务启动失败，请检查服务日志')
            time.sleep(.15)
        raise RuntimeError('本地服务启动超时，请重试')


def main():
    ensure_service()
    config = json.loads((ROOT / 'runtime' / 'config.json').read_text(encoding='utf-8'))
    webbrowser.open(f'http://127.0.0.1:{config["port"]}/')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None, str(exc), 'Edge Agent 启动失败', 0x10)
