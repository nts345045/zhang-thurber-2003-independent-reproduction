#!/usr/bin/env python3
"""Saved source/preparation review only; no compiler or numerical call."""
import ast, hashlib, importlib.util, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((HERE/'prepared.json').read_text())
assert sha(HERE/'prepared.json')=='bf8a826e91b9d7554a74fca1e9c0c99d4b23c0b623c372a3d2048f786b63321c'
counts={}
for key,base in [('input_sha256',ROOT),('output_sha256',HERE),('runtime_sha256',Path('/'))]:
 for n,h in p[key].items():assert sha(base/n)==h,(key,n)
 counts[key]=len(p[key])
assert p['compile_flags']==['-std=gnu++17','-O3','-Wall','-Wextra','-Wpedantic','-fopenmp']
assert str(Path(p['compiler_path']).resolve()) in p['runtime_sha256']
spec=importlib.util.spec_from_file_location('reviewed_control_preparer',str(HERE/'source/diagnostics/run_trial_backtracking_checks.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
for variant in ('before','after'):
 base=(HERE/'source'/variant/'src/main.cpp').read_text()
 actual=(HERE/'source'/variant/'src/fixture_main.cpp').read_text()
 assert actual==mod.instrument(base)
 start=base.index('    double before = objective(');end=base.index('    double dv = 0, dx = 0;',start)
 assert base[start:end]==actual[actual.index('    double before = objective('):actual.index('    double dv = 0, dx = 0;',actual.index('    double before = objective('))]
 candidate=ROOT/'data/development/hayward_trial_backtracking_candidate_003'/variant
 for f in candidate.rglob('*'):
  if f.is_file():assert sha(f)==sha(HERE/'source'/variant/f.relative_to(candidate))
assert not any((HERE/n).exists() for n in ('execution.json','results','summary.json'))
review={'status':'passed','reviewer':'scientific_audit','prepared_sha256':sha(HERE/'prepared.json'),'review_source_sha256':sha(Path(__file__)),'verified_pin_counts':counts,'candidate_prepared_sha256':p['candidate_prepared_sha256'],'source_review':'The actual copied invert loop, trial construction, objective, halving and gate are retained. Only fixture opener, gate wrapper and solve-return call sites are redirected. The actual solve and rays run; altered returned Rays exercise pure/mixed reasons in the actual gate. No synthesized quality exception. Inert seams must preserve before/after files and captured ray statuses byte-for-byte.','control_scope':['Known half/quarter time-offset objective targets and actual ordinary nonlinear controls','All12 pure quality and invalid-model/quality mixtures, distinct valid-but-worse behavior','Current/final/mixed/unexpected fatal cases; native full reason rosters','Original unscaled source/model delta, LSQR diagnostics, fixed weights and all-row native metadata including zero row and both epochs','Reconstruction of clamped sources and exponential model from original state at each fraction','Deferred full-device write failures, prior artifacts/dangling symlinks and malformed snapshots','Tiny homogeneous5-to6-to5 cached/fresh fields with identical physical receiver and separate native epochs'],'execution_authorization':'Bounded invented controls only, using exact pinned compiler at unchanged production-compatible O3 flags. No real/native inverse, source adoption, full-cohort or failed-run restart.','limitations':['Fixture prescribed deltas are test inputs rather than claimed solver estimates; real solve/status is captured separately.','Short component runner is not the long-running native controller; interruption must not be mistaken for terminal success.','A passed harness would not certify a global3D first arrival or physical accuracy of future inverse trials.']}
with (HERE/'prelaunch_review.json').open('x') as f:json.dump(review,f,indent=2);f.write('\n')
print(sha(HERE/'prelaunch_review.json'))
