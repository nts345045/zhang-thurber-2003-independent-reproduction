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
parser.add_argument('--suite', choices=['full', 'closed-cell', 'mixed-order', 'seed-rules'], default='full')
parser.add_argument('--order', type=int, choices=[1, 2], default=1)
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
run_command = [str(binary), str(OUT / 'results.csv'), str(args.order)]
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
    'command': 'python3 data/development/fmm_field_checks/run_checks.py --variant {} --suite {} --order {}'.format(args.variant, args.suite, args.order),
    'suite': args.suite,
    'fmm_order': args.order,
    'run_command': [arg.replace(str(ROOT) + '/', '') for arg in run_command],
    'TMPDIR': 'tmp',
    'compiler_command': [arg.replace(str(ROOT) + '/', '') for arg in command],
    'exit_code': result.returncode,
    'stdout': result.stdout,
    'stderr': result.stderr,
    'status': 'passed' if result.returncode == 0 else 'failed',
    'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
    'limitations': [
        'These component tests do not establish first-arrival branch completeness or final bent-ray accuracy.',
        'The 1e-12 second homogeneous action allowance covers floating-point roundoff and is not a ray-convergence tolerance.']}
if args.suite == 'seed-rules':
    with (OUT / 'results.csv').open() as f:
        rows = list(csv.DictReader(f))
    summary['cases'] = len(rows)
    summary['half_open_reflection_failures'] = sum(1 for row in rows if row['closed_seed_cells'] == '0' and row['reflection_passed'] == '0')
    summary['closed_seed_reflection_failures'] = sum(1 for row in rows if row['closed_seed_cells'] == '1' and row['reflection_passed'] == '0')
    summary['off_grid_changed_cases'] = sum(1 for row in rows if row['geometry'] == 'off_grid' and row['off_grid_bitwise_unchanged'] == '0')
    summary['limitations'].append('Default half-open source-seed reflection failures are retained as a comparison; pass status applies to closed-cell-union symmetry, exact endpoints, monotone extraction, physical action bounds, and bitwise unchanged off-grid fields/paths.')
if args.suite == 'mixed-order':
    with (OUT / 'results.csv').open() as f:
        rows = list(csv.DictReader(f))
    summary['cases'] = sum(int(row['cases']) for row in rows)
    summary['failures'] = sum(int(row['failures']) for row in rows)
    summary['maximum_test_error_s'] = max(float(row['max_error_s']) for row in rows)
    scalar = [row for row in rows if not row['case'].startswith('point_source_')]
    reflected = [row for row in rows if row['case'].startswith('point_source_')]
    summary['maximum_scalar_root_error_s'] = max(float(row['max_error_s']) for row in scalar)
    summary['maximum_field_reflection_error_s'] = max(float(row['max_error_s']) for row in reflected)
    summary['maximum_error_in_epsilon_units'] = max(float(row['max_error_in_epsilon_units']) for row in rows)
    summary['limitations'].append('Local scalar roots are compared with independent long-double bisection; affine travel-time stencils and reflected point-source fields test consistency/symmetry. The 128-epsilon arithmetic allowance is not a ray accuracy criterion.')
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
    summary['full_domain_stencils'] = {name: int(rows[-1][name]) for name in [
        'first_order_direction_evaluations', 'second_order_direction_evaluations',
        'second_order_ineligible', 'causal_fallback_updates',
        'root_bisection_updates', 'second_neighbor_revisits']}
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
