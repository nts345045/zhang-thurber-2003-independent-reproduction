#!/usr/bin/env python3
"""Trace every failed initial absolute ray at a declared finer discretization.

This is a diagnostic subset; it does not replace the full-cohort preflight.
The executable and every source/event/station identity come from the frozen run.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
parser.add_argument('--variant', required=True)
parser.add_argument('--spacing', type=float, required=True)
parser.add_argument('--field-spacing', type=float,
                    help='Keep a declared field spacing while refining the path')
args = parser.parse_args()
if not all(re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in [args.run, args.variant]):
    parser.error('Run and variant must be plain names')
if not 0 < args.spacing < .5:
    parser.error('Choose a finer positive spacing than 0.5 km')
field_spacing = args.field_spacing if args.field_spacing is not None else args.spacing
if not 0 < field_spacing <= .5:
    parser.error('Field spacing must be positive and no coarser than 0.5 km')
data = Path('data') / ('hayward_' + args.run)
out = Path('data/development') / ('hayward_initial_failure_refinement_' + args.variant)
out.mkdir(parents=True, exist_ok=False)
summary = dict(status='preparing', scope='Every failed initial ray; diagnostic only, no full-cohort gate or inversion',
               path_spacing_km=args.spacing, field_spacing_km=field_spacing, threads=4)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save():
    temporary = out / 'summary.json.new'
    temporary.write_text(json.dumps(summary, indent=2) + '\n')
    temporary.replace(out / 'summary.json')


try:
    manifest = json.loads((data / 'run_manifest.json').read_text())
    ledger = json.loads((data / 'preflight_execution.json').read_text())
    require(any(c['stage'] == 'initial_linearize' and c['return_code'] == 0 for c in ledger['completed_commands']),
            'Initial linearization is not complete')
    for name, expected in manifest['sha256'].items():
        require(sha(Path(name)) == expected, 'Frozen input changed: ' + name)
    names, observations = table(data / 'observations.csv')
    ray_names, rays = table(data / 'initial_linearization_rows.csv')
    failed = [r for r in rays if r['ray_converged'] != '1']
    require(len(set(r['observation_row'] for r in failed)) == len(failed) > 0, 'Invalid failed support')
    require('original_observation_row' not in names, 'Source index column already exists')
    with (out / 'observations.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=names + ['original_observation_row'], lineterminator='\n')
        writer.writeheader()
        for ray in failed:
            original = observations[int(ray['observation_row'])]
            require(original['type'] == '0', 'Expected only absolute observations')
            for name in ['i', 'station', 'event_i_resource_id', 'origin_i_resource_id', 'pick_i_resource_id',
                         'channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end']:
                require(original[name] == ray[name], 'Native observation join changed: ' + name)
            writer.writerow(dict(original, original_observation_row=ray['observation_row']))
    with (out / 'original_failed_rows.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=ray_names, lineterminator='\n')
        writer.writeheader()
        writer.writerows(failed)
    for name in ['initial_events.csv', 'stations.csv', 'initial_grid.csv', 'authoritative_ids_required']:
        shutil.copyfile(str(data / name), str(out / name))
    config = (data / 'run.cfg').read_text()
    for name, spacing in [('ray_spacing', args.spacing), ('fmm_spacing', field_spacing)]:
        config, count = re.subn(r'^' + name + r'\s+0\.5\s*$', name + ' ' + str(spacing), config, flags=re.MULTILINE)
        require(count == 1, 'Unexpected original discretization: ' + name)
    (out / 'run.cfg').write_text(config)
    shutil.copyfile(str(data / 'run_manifest.json'), str(out / 'parent_run_manifest.json'))
    shutil.copyfile(__file__, str(out / 'refine_initial_failures.py'))
    summary.update(original_run=str(data), failed_ray_count=len(failed), original_full_ray_count=len(rays),
                   binary=manifest['binary'], binary_sha256=sha(Path(manifest['binary'])),
                   original_input_sha256={name: digest for name, digest in manifest['sha256'].items()},
                   source_rows_sha256=sha(data / 'initial_linearization_rows.csv'),
                   diagnostic_input_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file()})
    argv = [manifest['binary'], 'linearize', str(out / 'run.cfg'), str(out), 'initial']
    start = time.time()
    with (out / 'stdout.log').open('w') as stdout, (out / 'stderr.log').open('w') as stderr:
        child = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                                 env=dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='4'))
        summary.update(status='running', command=argv, driver_pid=os.getpid(), child_pid=child.pid)
        save()
        code = child.wait()
    summary.update(return_code=code, seconds=time.time() - start)
    require(code == 0, 'Frozen diagnostic linearization failed')
    _, refined = table(out / 'initial_linearization_rows.csv')
    require(len(refined) == len(failed), 'Refinement changed diagnostic support')
    for before, after in zip(failed, refined):
        require(after['original_observation_row'] == before['observation_row'], 'Original index was lost')
        for name in names:
            if name not in ['type', 'value', 'j']:
                require(after[name] == observations[int(before['observation_row'])][name], 'Saved metadata changed: ' + name)
    summary.update(status='completed', converged=sum(r['ray_converged'] == '1' for r in refined),
                   maximum_projected_gradient_s_per_km=max(float(r['ray_projected_gradient']) for r in refined),
                   maximum_absolute_time_change_s=max(abs(float(a['ray_time']) - float(b['ray_time'])) for a, b in zip(failed, refined)))
    for name, expected in manifest['sha256'].items():
        require(sha(Path(name)) == expected, 'Frozen run changed during diagnostic: ' + name)
    summary['output_sha256'] = {p.name: sha(p) for p in out.iterdir() if p.is_file() and p.name != 'summary.json'}
except BaseException as error:
    summary.update(status='failed', failure=str(error))
    save()
    raise
save()
print(out / 'summary.json', flush=True)
