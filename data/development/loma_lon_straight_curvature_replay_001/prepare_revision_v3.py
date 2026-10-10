#!/usr/bin/env python3
"""Preserve v2; close its post-Popen bookkeeping interruption window."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

old = json.loads((HERE / 'prepared_v2.json').read_text())
for name, expected in old['output_sha256'].items():
    if sha(HERE / name) != expected:
        raise RuntimeError('Previously prepared file changed: ' + name)
ast.parse((HERE / 'run_v3.py').read_text())
new = dict(old)
new['superseded_preparation_sha256'] = sha(HERE / 'prepared_v2.json')
new['revision_scope'] = 'Move post-Popen PID/ledger bookkeeping inside the child cleanup try; preserve v2 and all numerical/input files. Neither earlier preparation executed compiler or native calls. README_execution.md supersedes earlier commands/prose.'
new['execution_runner'] = 'run_v3.py'
new['output_sha256'] = dict(old['output_sha256'])
for name in ('prepared_v2.json', 'prepare_revision_v3.py', 'run_v3.py', 'README_execution.md'):
    new['output_sha256'][name] = sha(HERE / name)
with (HERE / 'prepared_v3.json').open('x') as f:
    json.dump(new, f, indent=2, allow_nan=False)
    f.write('\n')
print(sha(HERE / 'prepared_v3.json'))
