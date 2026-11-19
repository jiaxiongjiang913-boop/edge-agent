"""Stream browser-fetched files to the explicitly requested local directory."""
import base64
import os
from pathlib import Path
import re
import uuid


class DownloadTransfer:
    def __init__(self, directory, tab_id, transfer_id):
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.tab_id, self.id = tab_id, transfer_id
        self.temporary = self.directory / ('.edge-agent-' + uuid.uuid4().hex + '.part')
        self.stream = None
        self.name = 'download.bin'
        self.count = 0
        self.state = 'pending'
        self.filename = None

    def begin(self, name):
        if self.state != 'pending':
            raise ValueError('下载已开始，不能重复初始化')
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(name)).strip(' .')[:180] or 'download.bin'
        if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', name):
            name = 'download-' + name
        self.name = name
        self.stream = self.temporary.open('xb')
        self.state = 'in_progress'

    def chunk(self, value, encoded):
        if self.state != 'in_progress' or not isinstance(value, str) or len(value) > 200000:
            raise ValueError('下载分块状态或长度无效')
        data = base64.b64decode(value, validate=True) if encoded else value.encode('utf-8')
        self.stream.write(data)
        self.count += len(data)

    def finish(self):
        if self.state != 'in_progress':
            raise ValueError('未收到下载文件流')
        self.stream.close()
        stem, suffix = Path(self.name).stem, Path(self.name).suffix
        for index in range(10000):
            target = self.directory / (self.name if index == 0 else f'{stem} ({index}){suffix}')
            try:
                # Reserve without overwriting an existing user file.
                with target.open('xb'):
                    pass
            except FileExistsError:
                continue
            try:
                os.replace(self.temporary, target)
            except OSError:
                target.unlink(missing_ok=True)
                raise
            self.filename = str(target)
            self.state = 'complete'
            return self.status()
        raise ValueError('同名文件过多，请选择新的下载目录')

    def abort(self):
        if self.stream and not self.stream.closed:
            self.stream.close()
        self.temporary.unlink(missing_ok=True)
        if self.state != 'complete':
            self.state = 'interrupted'

    def status(self):
        return {'id': self.id, 'state': self.state, 'filename': self.filename,
                'bytes_received': self.count, 'total_bytes': self.count if self.state == 'complete' else None}
