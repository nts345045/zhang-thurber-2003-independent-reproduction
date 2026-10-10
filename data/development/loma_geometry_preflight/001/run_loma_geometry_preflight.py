#!/usr/bin/env python3
"""Freeze the complete Loma geometry and diagnose its declared 104-ray sample."""
import argparse
import csv
import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--commit', required=True)
parser.add_argument('--variant', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+', args.variant):
    parser.error('Variant must contain only letters, digits, underscores, or hyphens')
commit = subprocess.check_output(['git', 'rev-parse', args.commit + '^{commit}']).decode().strip()
out = Path('data/development/loma_geometry_preflight') / args.variant
run_dir = Path('data/loma_lom_' + args.variant)
cache = Path('tmp/loma_geometry_preflight') / args.variant
# Atomic directory creation prevents two launches from sharing an output name.
out.mkdir(parents=True, exist_ok=False)
summary = {'status': 'preparing', 'commit': commit, 'run_directory': str(run_dir),
           'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'scope': 'Complete 724-source/52-receiver input geometry; 104 declared diagnostic rays only; no observations or inversion',
           'OMP_NUM_THREADS': 4, 'address_space_limit_bytes': 128 * 1024**3,
           'commands': [], 'source_sha256': {}, 'input_sha256': {}}
run_created = False

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_bytes(name):
    return subprocess.check_output(['git', 'show', commit + ':' + name])

def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))

def save():
    temporary = out / 'summary.json.new'
    temporary.write_text(json.dumps(summary, indent=2) + '\n')
    temporary.replace(out / 'summary.json')

def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**3, 128 * 1024**3))

def execute(name, command, limited=False):
    summary['status'] = name
    save()
    print(name, flush=True)
    start = time.time()
    with (out / (name + '_stdout.log')).open('w') as stdout, (out / (name + '_stderr.log')).open('w') as stderr:
        code = subprocess.call(list(map(str, command)), stdout=stdout, stderr=stderr,
                               env=dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='4'),
                               preexec_fn=limit_memory if limited else None)
    summary['commands'].append({'name': name, 'argv': list(map(str, command)),
                                'exit_code': code, 'seconds': time.time() - start})
    save()
    if code:
        raise RuntimeError(name + ' exited with code ' + str(code))

try:
    run_dir.mkdir(parents=True, exist_ok=False)
    run_created = True
    cache.mkdir(parents=True, exist_ok=False)
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, 'src']).decode().splitlines()
    for name in names:
        target = out / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_bytes(name))
        summary['source_sha256'][name] = sha(target)
    runner = Path('diagnostics/run_loma_geometry_preflight.py')
    shutil.copyfile(str(runner), str(out / runner.name))
    summary['runner_sha256'] = sha(out / runner.name)
    input_names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, 'data/loma_lom']).decode().splitlines()
    for name in input_names:
        target = run_dir / Path(name).name
        target.write_bytes(git_bytes(name))
        summary['input_sha256'][target.name] = sha(target)
    manifest = json.loads((run_dir / 'preparation_manifest.json').read_text())
    for name, expected in manifest['prepared_sha256'].items():
        assert sha(run_dir / name) == expected, name
    for name, expected in manifest['authoritative_raw_source_sha256'].items():
        assert hashlib.sha256(git_bytes('data/authoritative/loma_prieta/' + name)).hexdigest() == expected, name
    events, stations, samples = [rows(run_dir / name) for name in
                                ['truth_events.csv', 'stations.csv', 'ray_samples.csv']]
    assert len(events) == 724 and len(stations) == 52 and len(samples) == 104
    for table in [events, stations]:
        assert [int(r['id']) for r in table] == list(range(len(table)))
    assert len({r['event_resource_id'] for r in events}) == 724
    assert len({(r['channel_seed_id'], r['metadata_epoch_start'], r['metadata_epoch_end']) for r in stations}) == 52
    for name, prepared in [('selected_events.csv', events), ('selected_channels.csv', stations)]:
        original = list(csv.DictReader(io.StringIO(git_bytes('data/authoritative/loma_prieta/' + name).decode())))
        assert len(original) == len(prepared)
        assert all(all(b[k] == v for k, v in a.items()) for a, b in zip(original, prepared))
    keys = [(int(r['event']), int(r['station'])) for r in samples]
    assert len(set(keys)) == 104 and len({k for i, k in keys}) == 52
    for sample, (i, k) in zip(samples, keys):
        for prefix, source in [('source_', events[i]), ('receiver_', stations[k])]:
            assert all(sample[prefix + name] == value for name, value in source.items())
    points = [[float(r[a]) for a in 'xyz'] for r in events]
    pairs = sum(sum((a-b)**2 for a, b in zip(points[i], points[j])) < 20**2
                for i in range(724) for j in range(i+1, 724))
    assert pairs == 152834
    summary['input_checks'] = {'events': 724, 'receivers': 52, 'diagnostic_rays': 104,
                               'strict_below_20km_pairs': pairs, 'native_metadata_preserved': True,
                               'raw_source_hashes_verified': 2}
    summary['compiler'] = subprocess.check_output(['g++', '--version']).decode().splitlines()[0]
    binary = cache / 'dd'
    execute('compile', ['g++', '-std=c++17', '-O2', '-fopenmp', out / 'source/src/main.cpp',
                        '-lstdc++fs', '-o', binary])
    summary['binary_sha256'] = sha(binary)
    libraries = {}
    for line in subprocess.check_output(['ldd', str(binary)]).decode().splitlines():
        for word in line.split():
            if word.startswith('/') and Path(word).is_file():
                libraries[Path(word).name] = sha(Path(word))
    summary['linked_library_sha256'] = libraries
    execute('geometrycheck', ['/usr/bin/time', '-f', '%e %M', '-o', out / 'resource_usage.txt',
                             binary, 'geometrycheck', run_dir / 'run.cfg', run_dir, 'truth'], True)
    prefix = 'geometry_truth_ray_'
    convergence, derivatives, identities = [rows(run_dir / (prefix + name + '.csv'))
                                            for name in ['convergence', 'derivatives', 'identifiers']]
    assert len(convergence) == len(identities) == 104
    for n, (record, identity, key) in enumerate(zip(convergence, identities, keys)):
        i, k = key
        for row in [record, identity]:
            assert (int(row['diagnostic_row']), int(row['event']), int(row['station'])) == (n, i, k)
        for prefix, source in [('source_', events[i]), ('receiver_', stations[k])]:
            for name, value in source.items():
                if name not in ['id', 'x', 'y', 'z', 't']:
                    assert identity[prefix + name] == value, (n, name)
            for axis in 'xyz':
                # The diagnostic CSV uses the solver's declared 12-digit format.
                assert float(identity[prefix + axis]) == float(format(float(source[axis]), '.12g'))
    grid = rows(run_dir / 'truth_grid.csv')
    bounds = [(min(float(r[a]) for r in grid), max(float(r[a]) for r in grid)) for a in 'xyz']
    expected_derivatives = []
    for n, (i, k) in enumerate(keys[:8]):
        for axis, (lower, upper) in enumerate(bounds):
            value = points[i][axis]
            if lower <= value-.01 and value+.01 <= upper:
                expected_derivatives.append((n, i, k, axis))
    assert [(int(r['diagnostic_row']), int(r['event']), int(r['station']), int(r['axis']))
            for r in derivatives] == expected_derivatives
    nonfinite = []
    for table_name, table in [('convergence', convergence), ('derivatives', derivatives)]:
        for n, row in enumerate(table):
            for name, value in row.items():
                if not name.endswith('_extraction_message') and not math.isfinite(float(value)):
                    nonfinite.append({'table': table_name, 'row': n, 'column': name})
    flags = {name: sum(r[name] == '1' for r in convergence) for name in
             ['production_converged', 'refined_converged', 'production_initialization_succeeded',
              'refined_initialization_succeeded', 'production_selected_fmm_seed', 'refined_selected_fmm_seed']}
    flags.update({name: sum(r[name] == '1' for r in derivatives) for name in
                  ['plus_converged', 'minus_converged', 'plus_initialization_succeeded', 'minus_initialization_succeeded']})
    maximum = lambda table, name: max((abs(float(r[name])) for r in table
                                      if math.isfinite(float(r[name]))), default=None)
    summary['results'] = {'convergence_rows': len(convergence), 'identity_rows': len(identities),
                          'derivative_rows': len(derivatives), 'native_identity_matches': True,
                          'nonfinite_numeric_fields': nonfinite, 'flags': flags,
                          'maxima_scope': 'Finite values only; all nonfinite cells are listed separately',
                          'maximum_absolute_time_refinement_s': maximum(convergence, 'difference'),
                          'maximum_production_endpoint_error_s_per_km': maximum(derivatives, 'production_error'),
                          'maximum_refined_endpoint_error_s_per_km': maximum(derivatives, 'refined_error')}
    for name, expected in summary['input_sha256'].items():
        assert sha(run_dir / name) == expected, 'Input changed: ' + name
    summary['outputs_sha256'] = {p.name: sha(p) for p in run_dir.glob('geometry_truth_ray_*.csv')}
    summary['status'] = 'completed'
    summary['scientific_acceptance'] = 'Pending review of all flags and refinement/derivative values; no global first-arrival certificate and no automatic simulation launch'
except BaseException as error:
    summary['status'] = 'failed'
    summary['failure'] = str(error)
    summary['partial_outputs_sha256'] = {p.name: sha(p) for p in run_dir.glob('geometry_truth_ray_*.csv')} if run_created else {}
    save()
    raise
save()
print(str(out / 'summary.json'), flush=True)
