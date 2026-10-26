"""Install the portable skill with a machine-local repository reference."""
import argparse
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def install(destination):
    target = Path(destination).expanduser().resolve() / 'edge-agent'
    if target.exists():
        raise FileExistsError('目标已存在，请先检查已有的 edge-agent 技能，选择空的目标目录。')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'skills' / 'edge-agent', target)
    (target / 'installation.local.json').write_text(
        json.dumps({'root': str(ROOT)}, ensure_ascii=False, indent=2), encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills')
    args = parser.parse_args()
    install(args.destination)
    print('Edge Agent 技能已安装。')
