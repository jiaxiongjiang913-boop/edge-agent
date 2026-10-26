"""Run the CLI from a bundled checkout or a locally registered installation."""
import json
import os
from pathlib import Path
import runpy
import sys


def find_product():
    override = os.environ.get('EDGE_AGENT_ROOT')
    if override:
        product = Path(override).expanduser().resolve()
    else:
        skill = Path(__file__).resolve().parents[1]
        config = skill / 'installation.local.json'
        product = Path(json.loads(config.read_text(encoding='utf-8'))['root']).resolve() if config.exists() else skill.parents[1]
    if not (product / 'cli.py').is_file() or not (product / 'server.py').is_file():
        raise ValueError('找不到 Edge Agent；请运行仓库的 install_skill.py，或设置 EDGE_AGENT_ROOT。')
    return product


if __name__ == '__main__':
    try:
        product = find_product()
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    sys.path.insert(0, str(product))
    runpy.run_path(str(product / 'cli.py'), run_name='__main__')
