"""Find the installed browser even when an MCP host filters environment variables."""
import os
from pathlib import Path
import sys


def find_edge():
    candidates = []
    if sys.platform == 'win32':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
                try:
                    with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe',
                                        0, winreg.KEY_READ | view) as key:
                        candidates.append(Path(winreg.QueryValueEx(key, '')[0].strip('"')))
                except OSError:
                    pass
    bases = [Path(os.environ[key]) for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA') if os.environ.get(key)]
    system_drive = os.environ.get('SYSTEMDRIVE')
    if not system_drive and os.environ.get('SYSTEMROOT'):
        system_drive = Path(os.environ['SYSTEMROOT']).drive
    if system_drive:
        bases += [Path(system_drive + '/') / 'Program Files', Path(system_drive + '/') / 'Program Files (x86)']
    candidates.extend(base / 'Microsoft/Edge/Application/msedge.exe' for base in bases)
    for executable in dict.fromkeys(candidates):
        if executable.is_file():
            return executable
    raise RuntimeError('未安装 Microsoft Edge。请从 https://www.microsoft.com/edge/download 安装后重试。')
