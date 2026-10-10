#!/usr/bin/env python3
"""Pin the executed checks and reproduce the two old finite-result omissions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'data/development/full_dd_resolution_checks'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
current, old_result = [json.loads(p.read_text()) for p in (HERE/'results.json', OLD/'results.json')]
for folder, report in ((HERE,current),(OLD,old_result)):
    for name, expected in report['source_sha256'].items():
        if sha(folder/'source'/name) != expected:
            raise ValueError('Source changed: ' + name)
old_checks = {r['name']: r for r in old_result['checks']}
new_checks = {r['name']: r for r in current['checks']}
if not current['passed'] or any(new_checks.get(k) != v for k,v in old_checks.items()):
    raise ValueError('Existing check result changed')
if len(current['checks']) != 39 or len(old_checks) != 34:
    raise ValueError('Unexpected check support')
spec = importlib.util.spec_from_file_location('old', str(OLD/'source/resolution_full_hayward.py'))
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
response = old.joint_resolution(np.diag([1.,1e-150]),np.zeros((0,2)),1,
    np.zeros(2),np.zeros((2,1)),np.array([[0.],[1e308]]))
condition = old.joint_resolution(np.diag([1.,1.,1e-155]),np.zeros((0,3)),1,
    np.zeros(3),np.zeros((3,1)))
old_omissions = dict(
    finite_input_unmasked_response_overflow=dict(
        ordinary_arrays_finite=all(np.all(np.isfinite(x)) for x in response[:2]),
        physical_response_positive_infinity=bool(np.isposinf(response[2][0,0])),
        ordinary_resolution=response[0].tolist(), ordinary_covariance=response[1].tolist()),
    finite_input_condition_overflow=dict(
        ordinary_arrays_finite=all(np.all(np.isfinite(x)) for x in condition[:2]),
        condition_positive_infinity=bool(np.isposinf(condition[3]['model_schur_condition_number']))))
if not all((old_omissions['finite_input_unmasked_response_overflow']['ordinary_arrays_finite'],
            old_omissions['finite_input_unmasked_response_overflow']['physical_response_positive_infinity'],
            old_omissions['finite_input_condition_overflow']['ordinary_arrays_finite'],
            old_omissions['finite_input_condition_overflow']['condition_positive_infinity'])):
    raise ValueError('Old omission not reproduced')
paths=[Path(__file__).resolve(),HERE/'results.json',OLD/'results.json',
       HERE/'source/resolution_full_hayward.py',HERE/'source/check_full_dd_resolution.py',
       OLD/'source/resolution_full_hayward.py',OLD/'source/check_full_dd_resolution.py',
       ROOT/'resolution_full_hayward.py',ROOT/'diagnostics/check_full_dd_resolution.py']
for name in ('resolution_full_hayward.py','check_full_dd_resolution.py'):
    maintained=ROOT/name if name=='resolution_full_hayward.py' else ROOT/'diagnostics'/name
    if sha(maintained)!=sha(HERE/'source'/name): raise ValueError('Maintained source changed')
report=dict(status='passed', scope='Invented algebra and saved-result readback only.',
    original_checks_exactly_unchanged=34, total_checks=39, old_frozen_omissions=old_omissions,
    input_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
    limitation='Finite conditioning is required for serialization; no finite condition-number accuracy threshold is introduced.')
with (HERE/'readback.json').open('x') as stream:
    stream.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(status='passed', original_checks_exactly_unchanged=34, old_omissions_reproduced=2)))
