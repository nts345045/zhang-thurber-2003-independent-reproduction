#!/usr/bin/env python3
"""Rebuild invented FMM field tests; no production solver or real observations."""
import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True, help='New evidence subdirectory; never overwrites the frozen baseline.')
parser.add_argument('--suite', choices=['full', 'closed-cell'], default='full')
args = parser.parse_args()
if not args.variant or Path(args.variant).name != args.variant or args.variant in ('.', '..'):
    parser.error('--variant must be a single directory name')
OUT = ROOT / 'data/development/fmm_field_checks' / args.variant
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'summary.json').exists() or (OUT / 'results.csv').exists():
    parser.error('Evidence already exists; select a new --variant')
TMP = ROOT / 'tmp/fmm_field_checks' / args.variant
TMP.mkdir(parents=True, exist_ok=True)
binary = TMP / 'check_fmm_field'
command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
           'diagnostics/check_fmm_field.cpp', '-o', str(binary)]
environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'))
subprocess.check_call(command, cwd=str(ROOT), env=environment)
run_command = [str(binary), str(OUT / 'results.csv')]
if args.suite != 'full':
    run_command.append(args.suite)
result = subprocess.run(run_command, cwd=str(ROOT), env=environment,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True)
paths = ['diagnostics/first_arrival_fmm.hpp', 'diagnostics/check_fmm_field.cpp',
         'src/core.hpp', 'data/development/fmm_field_checks/run_checks.py',
         str((OUT / 'results.csv').relative_to(ROOT)), str(binary.relative_to(ROOT))]
summary = {
    'reviewed_utc': datetime.datetime.utcnow().isoformat() + 'Z',
    'purpose': 'Invented FMM field/extraction fixtures only; no real data, ray bending, or inversion.',
    'command': 'python3 data/development/fmm_field_checks/run_checks.py --variant {} --suite {}'.format(args.variant, args.suite),
    'suite': args.suite,
    'run_command': run_command,
    'TMPDIR': environment['TMPDIR'],
    'compiler_command': command,
    'exit_code': result.returncode,
    'stdout': result.stdout,
    'stderr': result.stderr,
    'status': 'passed' if result.returncode == 0 else 'failed',
    'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
    'limitations': [
        'These component tests do not establish first-arrival branch completeness or final bent-ray accuracy.',
        'The 1e-12 second homogeneous action allowance covers floating-point roundoff and is not a ray-convergence tolerance.']}
if args.suite == 'closed-cell':
    with (OUT / 'results.csv').open() as f:
        rows = list(csv.DictReader(f))
    summary['path_cases'] = len(rows)
    summary['passed_cases'] = sum(int(row['success']) for row in rows)
    summary['limitations'].append('Only exact connection inside the closed receiver seed cell is tested, including reflected upper-face cases.')
if result.returncode == 0 and args.suite == 'full':
    with (OUT / 'results.csv').open() as f:
        rows = list(csv.DictReader(f))
    summary['path_cases'] = len(rows)
    summary['full_domain_build_seconds'] = float(rows[-1]['build_seconds'])
    summary['full_domain_nodes'] = int(rows[-1]['nodes'])
    summary['maximum_endpoint_error_km'] = max(float(r['endpoint_error_km']) for r in rows)
    summary['nondecreasing_field_steps'] = sum(int(r['nondecreasing_field_steps']) for r in rows)
    summary['extraction_fallback_steps'] = sum(int(r['fallback_steps']) for r in rows)
    summary['limitations'].extend([
        'The 36 homogeneous cases include nine coincident source/receiver cases; three additional synthetic full-domain paths test extraction at practical field size.',
        'Timing is a single measurement while other authorized processes are active, not a performance guarantee.'])
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
print(result.stdout, end='')
print(result.stderr, end='')
if result.returncode:
    raise SystemExit(result.returncode)
