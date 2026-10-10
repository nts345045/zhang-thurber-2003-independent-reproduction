#!/usr/bin/env python3
"""Pin a runner-only review correction without changing initial preparation."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

old = json.loads((HERE / 'prepared.json').read_text())
for name, expected in old['output_sha256'].items():
    if sha(HERE / name) != expected:
        raise RuntimeError('Original prepared file changed: ' + name)
ast.parse((HERE / 'run_reviewed.py').read_text())
new = dict(old)
new['superseded_preparation_sha256'] = sha(HERE / 'prepared.json')
new['revision_scope'] = 'Runner-only process-group termination/reaping and no-retrace wording correction; numerical driver, sources, inputs and settings unchanged; no compiler or native execution in initial preparation.'
new['execution_runner'] = 'run_reviewed.py'
new['output_sha256'] = dict(old['output_sha256'])
for name in ('prepared.json', 'prepare_revision.py', 'run_reviewed.py', 'README_reviewed.md'):
    new['output_sha256'][name] = sha(HERE / name)
with (HERE / 'prepared_v2.json').open('x') as f:
    json.dump(new, f, indent=2, allow_nan=False)
    f.write('\n')
print(sha(HERE / 'prepared_v2.json'))
