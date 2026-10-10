#!/usr/bin/env python3
"""Saved-output comparison only; no compiled driver or action evaluation."""
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))

summary = json.loads((HERE / 'summary.json').read_text())
execution = json.loads((HERE / 'execution.json').read_text())
if summary['status'] != 'completed_four_calls' or execution['status'] != 'completed' or execution['return_code'] != 0:
    raise RuntimeError('Execution is not terminal success')
if execution['summary_sha256'] != sha(HERE / 'summary.json'):
    raise RuntimeError('Terminal summary pin mismatch')
for name, expected in summary['output_sha256'].items():
    if sha(HERE / name) != expected:
        raise RuntimeError('Changed saved output: ' + name)
old = rows(HERE / 'results/old/scalars_17.csv')
new = rows(HERE / 'results/D/scalars_17.csv')
context = json.loads((HERE / 'inputs/native_context.json').read_text())
changes = []
for i, (a, b) in enumerate(zip(old, new)):
    native = context[i]
    reference = native['saved_comparison_row']
    changed = {k: {'old': a[k], 'D': b[k]} for k in a if a[k] != b[k]}
    errors = {}
    for variant, row in [('old', a), ('D', b)]:
        delta = [float(row['source_d' + axis]) - float(reference['reference_source_d' + axis + '_s_per_km']) for axis in 'xyz']
        errors[variant] = {'source_error_xyz_s_per_km': delta,
            'source_error_norm_s_per_km': math.sqrt(sum(x*x for x in delta)),
            'time_error_s': float(row['ray_time']) - float(reference['reference_time_s'])}
    changes.append({'pair_index': native['pair_index'], 'native_context': native,
        'changed_scalar_columns_17': changed, 'D_minus_old_time_s': float(b['ray_time'])-float(a['ray_time']),
        'reference_errors': errors})
equality = {}
for name in ('scalars_12.csv', 'paths.csv', 'model_partials.csv'):
    a, b = HERE / 'results/old' / name, HERE / 'results/D' / name
    equality[name] = {'byte_identical': a.read_bytes() == b.read_bytes(), 'rows_per_variant': len(rows(a)),
                      'old_sha256': sha(a), 'D_sha256': sha(b)}
result = {'status': 'saved_readback_complete', 'summary_sha256': sha(HERE / 'summary.json'),
    'execution_sha256': sha(HERE / 'execution.json'), 'source_sha256': sha(Path(__file__).resolve()),
    'verified_output_pins': len(summary['output_sha256']), 'old_D_equalities': equality, 'pairs': changes,
    'interpretation': 'D leaves these final paths, derivatives and flags unchanged. Only action-total rounding differs. No iteration history or intermediate curvature was captured, so no equality of hidden trajectories or causal mechanism is asserted.',
    'scope': 'Two selected straight starts; no whole-cohort or FMM branch-selection acceptance'}
with (HERE / 'comparison.json').open('x') as f:
    json.dump(result, f, indent=2, allow_nan=False)
    f.write('\n')
print(sha(HERE / 'comparison.json'))
