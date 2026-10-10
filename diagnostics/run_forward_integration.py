#!/usr/bin/env python3
"""Exercise production dispatch, cache invalidation, CSVs and real epoch identity joins."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.variant):
    parser.error('Use letters, digits, underscores or hyphens for the variant')
out = ROOT / 'data/development' / ('forward_integration_' + args.variant)
build = ROOT / 'tmp/forward_integration' / args.variant
if out.exists() or build.exists():
    parser.error('Choose a fresh variant; existing evidence is preserved')
out.mkdir(parents=True)
snapshot = build / 'source'
sources = ['src/core.hpp', 'src/ray_metric.hpp', 'src/forward.hpp', 'src/first_arrival.hpp',
           'src/main.cpp', 'src/csv.hpp', 'src/ray_checks.hpp',
           'diagnostics/check_forward_integration.cpp', 'diagnostics/run_forward_integration.py']
for name in sources:
    target = snapshot / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
with (out / 'source_snapshot.tar.gz').open('wb') as raw:
    with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as archive:
            for name in sources:
                data = (snapshot / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o644
                archive.addfile(info, io.BytesIO(data))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

commands = []
def run(command, name):
    command = [str(value.relative_to(ROOT)) if isinstance(value, Path) else value for value in command]
    commands.append(command)
    result = subprocess.run(command, cwd=ROOT,
                            env=dict(os.environ, TMPDIR=str(ROOT/'tmp'), OMP_NUM_THREADS='2'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    (out / (name+'_stdout.txt')).write_text(result.stdout)
    (out / (name+'_stderr.txt')).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError('{} exited {}; evidence saved'.format(name, result.returncode))

binary = build / 'check_forward'
run(['c++', '-O3', '-std=c++17', '-fopenmp', '-Wall', '-Wextra', '-Wpedantic',
     snapshot/'diagnostics/check_forward_integration.cpp', '-lstdc++fs', '-o', binary], 'compile')
invented = out/'invented'
invented.mkdir()
run([binary, invented], 'invented')
# invert() also emits its legacy synthetic plotting grid. That output assumes
# the original sandwich fixture and is outside the scope of this small test.
(invented/'standard_slices.csv').unlink()
checks = read_csv(invented/'checks.csv')
failures = [row for row in checks if row['passed'] != '1']

# Preserve an actual DD across two archived epochs of the same channel, plus
# its two observed absolute picks. Only numeric solver indices are remapped.
source = ROOT/'data/hayward'
input_names = ['initial_events.csv', 'stations.csv', 'initial_grid.csv', 'observations.csv']
input_hashes = {name: digest(source/name) for name in input_names}
original_events = read_csv(source/'initial_events.csv')
original_stations = read_csv(source/'stations.csv')
original_observations = read_csv(source/'observations.csv')
dd = next(row for row in original_observations if row['type'] == '1' and row['station'] != row['station_j'])
event_ids = [int(dd['i']), int(dd['j'])]
station_ids = [int(dd['station']), int(dd['station_j'])]
selected = [next(row for row in original_observations if row['type'] == '0' and
                 int(row['i']) == i and int(row['station']) == k)
            for i,k in zip(event_ids,station_ids)] + [dd]
events = [dict(original_events[i], id=str(n)) for n,i in enumerate(event_ids)]
stations = [dict(original_stations[k], id=str(n)) for n,k in enumerate(station_ids)]
observations = []
for row in selected:
    mapped = dict(row)
    mapped['i'] = str(event_ids.index(int(row['i'])))
    mapped['j'] = '-1' if row['j'] == '-1' else str(event_ids.index(int(row['j'])))
    mapped['station'] = str(station_ids.index(int(row['station'])))
    mapped['station_j'] = '-1' if row['station_j'] == '-1' else str(station_ids.index(int(row['station_j'])))
    observations.append(mapped)
real = out/'identified_hayward'
real.mkdir()
write_csv(real/'initial_events.csv', events)
write_csv(real/'stations.csv', stations)
write_csv(real/'observations.csv', observations)
shutil.copyfile(source/'initial_grid.csv', real/'initial_grid.csv')
(real/'authoritative_ids_required').write_text('Archived authoritative observations; no new query or invented identifiers.\n')
config = real/'fixture.cfg'
config.write_text('authoritative_ids_required 1\nray_initializer 1\nfmm_spacing 0.5\nray_spacing 0.5\nray_iterations 1000\n')
manifest = {'purpose': 'Identity-preserving forward/CSV integration test; no reinversion',
            'input_sha256': input_hashes,
            'events': [dict(row, original_solver_id=str(i)) for row,i in zip(events,event_ids)],
            'stations': [dict(row, original_solver_id=str(k)) for row,k in zip(stations,station_ids)],
            'observations': observations,
            'numeric_remapping': 'Only id/i/j/station/station_j changed; provider records, epochs and hashes retained'}
(real/'selection_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
run([binary, '--solver', 'raycheck', config, real, 'initial'], 'identified_raycheck')
run([binary, '--solver', 'linearize', config, real, 'initial'], 'identified_linearize')
joins = read_csv(real/'initial_ray_identifiers.csv')
for joined in joins:
    row = observations[int(joined['observation_row'])]
    source_event = events[int(joined['event'])]
    receiver = stations[int(joined['station'])]
    for prefix, reference, omit in [('observation_', row, {'i','j','station','type','value'}),
                                    ('source_', source_event, {'id','x','y','z','t'}),
                                    ('receiver_', receiver, {'id','x','y','z','t'})]:
        for key,value in reference.items():
            if key not in omit and joined[prefix+key] != value:
                raise AssertionError('Identity join changed '+prefix+key)
linearized = read_csv(real/'initial_linearization_rows.csv')
for row in linearized:
    reference = observations[int(row['observation_row'])]
    for key,value in reference.items():
        if key not in {'i','j','station','type','value'} and row[key] != value:
            raise AssertionError('Linearization identity changed '+key)
forward = read_csv(real/'initial_ray_convergence.csv')
if len(forward) != 2 or len(linearized) != 2 or len(joins) != 4:
    raise AssertionError('Wrong observed-ray or metadata support')
for row in forward:
    if row['production_initialization_succeeded'] != '1' or row['refined_initialization_succeeded'] != '1':
        raise AssertionError('Identified ray extraction failed')
if any(digest(source/name) != sha for name,sha in input_hashes.items()):
    raise AssertionError('Original input changed during integration test')
summary = {'scope': 'Production wiring and metadata tests; not a manuscript inversion or global first-arrival certificate',
           'commands': commands, 'source_sha256': {name:digest(snapshot/name) for name in sources},
           'invented_checks': len(checks), 'failed_checks': failures,
           'real_observed_rays': len(forward), 'real_identity_associations': len(joins),
           'real_linearized_absolute_rows': len(linearized),
           'cross_native_epoch_dd_preserved': True, 'original_inputs_unchanged': True,
           'identified_ray_local_flags': [{k:r[k] for k in ['event','station','production_converged','refined_converged']}
                                        for r in forward],
           'sha256': {str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()}}
(out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['invented_checks','failed_checks','real_observed_rays','real_identity_associations']}))
if failures:
    raise SystemExit(1)
