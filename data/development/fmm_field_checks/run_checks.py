#!/usr/bin/env python3
"""Rebuild invented FMM field tests; no production solver or real observations."""
import csv
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/development/fmm_field_checks'
TMP = ROOT / 'tmp/fmm_field_checks'
TMP.mkdir(parents=True, exist_ok=True)
binary = TMP / 'check_fmm_field'
command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
           'diagnostics/check_fmm_field.cpp', '-o', str(binary)]
subprocess.check_call(command, cwd=str(ROOT))
result = subprocess.run([str(binary), str(OUT / 'results.csv')], cwd=str(ROOT),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True)
paths = ['diagnostics/first_arrival_fmm.hpp', 'diagnostics/check_fmm_field.cpp',
         'src/core.hpp', 'data/development/fmm_field_checks/run_checks.py',
         'data/development/fmm_field_checks/results.csv', str(binary.relative_to(ROOT))]
summary = {
    'reviewed_utc': datetime.datetime.utcnow().isoformat() + 'Z',
    'purpose': 'Invented FMM field/extraction fixtures only; no real data, ray bending, or inversion.',
    'command': 'python3 data/development/fmm_field_checks/run_checks.py',
    'compiler_command': command,
    'exit_code': result.returncode,
    'stdout': result.stdout,
    'stderr': result.stderr,
    'status': 'passed' if result.returncode == 0 else 'failed',
    'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
    'limitations': [
        'These tests establish endpoint preservation, decreasing auxiliary field times, feasible homogeneous action bounds, and explicit invalid-input failure.',
        'They do not establish first-arrival branch completeness or final bent-ray accuracy. The independent first-arrival audit records near-crossover branch failures of this first-order initializer.',
        'The 36 homogeneous cases include nine coincident source/receiver cases; three additional synthetic full-domain paths test extraction at practical field size.',
        'Timing is a single measurement while other authorized processes are active, not a performance guarantee.',
        'The 1e-12 second homogeneous lower-bound allowance covers floating-point path-action roundoff and is not a ray-convergence tolerance.']}
if result.returncode == 0:
    with (OUT / 'results.csv').open() as f:
        rows = list(csv.DictReader(f))
    summary['path_cases'] = len(rows)
    summary['full_domain_build_seconds'] = float(rows[-1]['build_seconds'])
    summary['full_domain_nodes'] = int(rows[-1]['nodes'])
    summary['maximum_endpoint_error_km'] = max(float(r['endpoint_error_km']) for r in rows)
    summary['nondecreasing_field_steps'] = sum(int(r['nondecreasing_field_steps']) for r in rows)
    summary['extraction_fallback_steps'] = sum(int(r['fallback_steps']) for r in rows)
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
print(result.stdout, end='')
print(result.stderr, end='')
if result.returncode:
    raise SystemExit(result.returncode)
