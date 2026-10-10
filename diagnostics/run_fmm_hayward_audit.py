#!/usr/bin/env python3
"""Preserve native identities and failed flags in a controlled saved-model ray audit."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
parser.add_argument('--order', type=int, choices=[1, 2], default=1)
parser.add_argument('--closed-seed-cells', action='store_true')
args = parser.parse_args()
if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.variant):
    parser.error('Variant must contain only letters, digits, underscores, or hyphens')
BUILD = Path('tmp/fmm_hayward_variants') / args.variant
OUT = Path('data/development') / ('fmm_hayward_' + args.variant)
if (ROOT / BUILD).exists() or (ROOT / OUT).exists():
    parser.error('Choose a new variant to preserve existing evidence')
INPUT = Path('data/development/hayward_dd_top_layer_rays.csv')
GRID = Path('data/hayward/dd_grid.csv')
EVENTS = Path('data/hayward/dd_events.csv')
STATIONS = Path('data/hayward/stations.csv')
HISTORICAL = Path('data/development/fmm_hayward_audit/results.csv')
HISTORICAL_SUMMARY = Path('data/development/fmm_hayward_audit/summary.json')
def read(path):
    with (ROOT / path).open() as stream:
        return list(csv.DictReader(stream))
def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
inputs = read(INPUT)
events = {r['id']: r for r in read(EVENTS)}
stations = {r['id']: r for r in read(STATIONS)}
historical = {r['observation_index']: r for r in read(HISTORICAL)}
old_summary = json.loads((ROOT / HISTORICAL_SUMMARY).read_text())
fixed = [INPUT, GRID, EVENTS, STATIONS, HISTORICAL, HISTORICAL_SUMMARY,
         Path('src/main.cpp'), Path('src/core.hpp'), Path('src/csv.hpp'), Path('src/ray_checks.hpp')]
input_hashes = {str(path): sha(path) for path in fixed}
for path in fixed:
    if str(path) in old_summary['sha256'] and input_hashes[str(path)] != old_summary['sha256'][str(path)]:
        raise ValueError('Frozen comparison input/source changed: ' + str(path))
if len(inputs) != 186 or len(historical) != len(inputs) or set(historical) != {r['observation_index'] for r in inputs}:
    raise ValueError('Controlled comparison requires the same 186 identified historical rays')
for r in inputs:
    event, station = events[r['i']], stations[r['station']]
    for axis in 'xyz':
        if float(event[axis]) != float(r['dd_source_' + axis + '_km']) or float(station[axis]) != float(r['receiver_' + axis + '_km']):
            raise ValueError('Ray geometry differs from saved model')
    for key in ('event_resource_id', 'origin_resource_id'):
        if event[key] != r[key.replace('_resource_id', '_i_resource_id')]:
            raise ValueError('Event identity differs from saved model')
    for key in ('channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end'):
        if station[key] != r[key]:
            raise ValueError('Receiver identity differs from saved model: ' + key)
    if station['source_sha256'] != r['channel_source_sha256']:
        raise ValueError('Receiver metadata source hash differs from saved model')
    if any(historical[r['observation_index']][key] != value for key, value in r.items()):
        raise ValueError('Historical observation metadata differs from current input')

(ROOT / BUILD).mkdir(parents=True)
(ROOT / OUT).mkdir(parents=True)
snapshot = BUILD / 'source'
sources = ['diagnostics/check_fmm_hayward.cpp', 'diagnostics/first_arrival_fmm.hpp',
           'diagnostics/seeded_bending.py', 'diagnostics/run_fmm_hayward_audit.py',
           'src/main.cpp', 'src/core.hpp', 'src/ray_checks.hpp', 'src/csv.hpp']
for relative in sources:
    target = ROOT / snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / relative), str(target))
write_header(ROOT / snapshot / 'diagnostics/seeded_bending.hpp', ROOT / snapshot / 'src/core.hpp')
sources.append('diagnostics/seeded_bending.hpp')
archive_path = OUT / 'source_snapshot.tar.gz'
with (ROOT / archive_path).open('wb') as raw:
    with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as archive:
            for relative in sources:
                content = (ROOT / snapshot / relative).read_bytes()
                info = tarfile.TarInfo(relative)
                info.size = len(content)
                info.mode = 0o644
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                archive.addfile(info, io.BytesIO(content))
binary = BUILD / 'check_fmm_hayward'
command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
           str(snapshot / 'diagnostics/check_fmm_hayward.cpp'), '-o', str(binary), '-lstdc++fs']
environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='1')
compiled = subprocess.run(command, cwd=str(ROOT), env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
(ROOT / OUT / 'compile_stdout.txt').write_text(compiled.stdout)
(ROOT / OUT / 'compile_stderr.txt').write_text(compiled.stderr)
if compiled.returncode:
    print(compiled.stderr, end='')
    raise SystemExit(compiled.returncode)
output_path = OUT / 'results.csv'
run_command = [str(binary), str(GRID), str(INPUT), str(output_path), '0.5', str(args.order),
               'closed' if args.closed_seed_cells else 'original']
with (ROOT / OUT / 'stdout.txt').open('w') as stdout, (ROOT / OUT / 'stderr.txt').open('w') as stderr:
    result = subprocess.run(run_command, cwd=str(ROOT), env=environment, stdout=stdout, stderr=stderr)
for path in fixed:
    if sha(path) != input_hashes[str(path)]:
        raise ValueError('Frozen input changed during the audit: ' + str(path))
outputs = read(output_path)
by_index = {r['observation_index']: r for r in outputs}
if len(outputs) != len(inputs) or len(by_index) != len(inputs):
    raise ValueError('Ray count or unique observation mapping changed')
for before in inputs:
    after = by_index[before['observation_index']]
    if any(after[key] != value for key, value in before.items()):
        raise ValueError('Original ray metadata changed')

# Retain complete native identities in each comparison row as in the source table.
comparison_path = OUT / 'historical_comparison.csv'
with (ROOT / comparison_path).open('w', newline='') as stream:
    names = list(inputs[0]) + ['historical_extracted', 'historical_selected_converged',
             'historical_selected_action_s', 'current_extracted', 'current_selected_converged',
             'current_selected_action_s', 'current_minus_historical_action_s']
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator='\n')
    writer.writeheader()
    for before in inputs:
        now, old = by_index[before['observation_index']], historical[before['observation_index']]
        row = dict(before)
        row.update(historical_extracted=old['extracted'], historical_selected_converged=old['selected_converged'],
                   historical_selected_action_s=old['selected_action_s'], current_extracted=now['extracted'],
                   current_selected_converged=now['selected_converged'], current_selected_action_s=now['selected_action_s'],
                   current_minus_historical_action_s=float(now['selected_action_s'])-float(old['selected_action_s']))
        writer.writerow(row)
finite_fields = ['field_time_s', 'baseline_ray_time_s', 'baseline_ray_gradient', 'selected_action_s',
                 'action_reduction_s', 'source_derivative_change_s_per_km', 'selected_max_depth_km',
                 'selected_outside_nodes', 'selected_endpoint_error_km']
nonfinite = [r for r in outputs if any(not math.isfinite(float(r[key])) for key in finite_fields) or
             (r['extracted'] == '1' and any(not math.isfinite(float(r[key])) for key in
                                          ['seed_action_s', 'fmm_bent_time_s', 'fmm_bent_gradient']))]
files = [binary, archive_path, output_path, comparison_path] + sorted(p.relative_to(ROOT) for p in (ROOT / OUT).glob('*.txt'))
summary = {
    'purpose': 'Controlled feasible-path comparison for the same saved DD model and 186 identified rays; no reinversion or first-arrival certificate.',
    'command': 'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_hayward_audit.py ' + ' '.join(shlex.quote(a) for a in sys.argv[1:]),
    'compile_command': command, 'run_command': run_command, 'TMPDIR': 'tmp', 'OMP_NUM_THREADS': 1,
    'return_code': result.returncode, 'order': args.order, 'closed_seed_cells': args.closed_seed_cells,
    'selection': 'Exactly the frozen 186 absolute rays with DD-final source and receiver depths in [-1,0] km.',
    'ray_count': len(outputs), 'all_input_columns_and_native_identities_preserved': True,
    'auxiliary_spacing_km': .5, 'path_spacing_km': .5, 'optimizer_maximum_updates': 1000,
    'extraction_failures': [r for r in outputs if r['extracted'] != '1'],
    'selected_nonconverged': [r for r in outputs if r['selected_converged'] != '1'],
    'exact_endpoint_check_failures': [r for r in outputs if float(r['selected_endpoint_error_km']) != 0],
    'domain_failures': [r for r in outputs if float(r['selected_outside_nodes']) != 0],
    'action_increase_failures': [r for r in outputs if float(r['action_reduction_s']) < 0],
    'nonfinite_failures': nonfinite,
    'maximum_endpoint_error_km': max(float(r['selected_endpoint_error_km']) for r in outputs),
    'maximum_action_reduction_s': max(float(r['action_reduction_s']) for r in outputs),
    'rays_with_action_reduction_over_1_ms': sum(float(r['action_reduction_s']) > .001 for r in outputs),
    'input_sha256': input_hashes,
    'source_sha256': {name: hashlib.sha256((ROOT / snapshot / name).read_bytes()).hexdigest() for name in sources},
    'sha256': {str(path): sha(path) for path in files},
    'limitations': ['Compared with the frozen first-order audit, this variant combines the separately verified closed-receiver-cell extraction correction, the selected stencil order, and the selected source seed rule. It is not an isolated stencil-effect estimate.',
                    'Smaller feasible action contradicts optimality of a prior path; equal actions do not certify a global first arrival.',
                    'Source derivatives require stationary paths and path-spacing checks; optimizer or strict endpoint failures remain recorded without relaxing tolerances.',
                    'The targeted shallow-endpoint subset does not represent all rays. No production inversion, source, configuration, or input is changed.']}
failed = result.returncode != 0 or any(summary[name] for name in ['extraction_failures', 'selected_nonconverged',
         'exact_endpoint_check_failures', 'domain_failures', 'action_increase_failures', 'nonfinite_failures'])
summary['status'] = 'failed_checks_recorded' if failed else 'passed'
(ROOT / OUT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': summary['status'], 'ray_count': len(outputs),
                  'failure_counts': {name: len(summary[name]) for name in ['extraction_failures', 'selected_nonconverged',
                   'exact_endpoint_check_failures', 'domain_failures', 'action_increase_failures', 'nonfinite_failures']}}, indent=2))
raise SystemExit(1 if failed else 0)
