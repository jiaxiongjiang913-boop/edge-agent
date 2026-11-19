"""Generate a host-neutral stdio MCP configuration for this computer only."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def generate(root=ROOT, interpreter=None):
    root = Path(root).resolve()
    config = {'mcpServers': {'edge-agent': {
        'command': str(Path(interpreter or sys.executable).resolve()),
        'args': ['-B', str(root / 'mcp_server.py')],
        'env': {'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'},
    }}}
    target = root / 'runtime' / 'mcp-config.local.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    entry = config['mcpServers']['edge-agent']
    codex = ['[mcp_servers.edge-agent]', 'command = ' + json.dumps(entry['command'], ensure_ascii=False),
             'args = ' + json.dumps(entry['args'], ensure_ascii=False),
             '', '[mcp_servers.edge-agent.env]']
    codex.extend(key + ' = ' + json.dumps(value) for key, value in entry['env'].items())
    (target.parent / 'mcp-codex.local.toml').write_text('\n'.join(codex) + '\n', encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate local MCP connection settings')
    parser.parse_args()
    print(generate())
