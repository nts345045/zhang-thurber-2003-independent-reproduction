#!/usr/bin/env python3
"""Observe one identified initial ray using its completed linearization's frozen code."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
parser.add_argument('--observation', type=int, required=True)
parser.add_argument('--variant', required=True)
parser.add_argument('--spacings', default='0.5,0.25')
parser.add_argument('--budgets', default='1000,4000')
parser.add_argument('--field-spacing', type=float,
                    help='Hold the field spacing fixed while varying path spacing')
args = parser.parse_args()
if not all(re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in [args.run, args.variant]):
    parser.error('Run and variant must be plain names')
if args.observation < 0:
    parser.error('Observation index must be nonnegative')
spacings = [float(value) for value in args.spacings.split(',')]
budgets = [int(value) for value in args.budgets.split(',')]
if not spacings or not budgets or any(not 0 < value <= 1 for value in spacings) or any(value <= 0 for value in budgets):
    parser.error('Use positive iteration budgets and path spacings no larger than 1 km')
if args.field_spacing is not None and not 0 < args.field_spacing <= 1:
    parser.error('Field spacing must be positive and no larger than 1 km')
data = Path('data') / ('hayward_' + args.run)
out = Path('data/development') / ('initial_ray_' + args.run + '_' + str(args.observation) + '_' + args.variant)
build = Path('tmp/initial_ray_diagnosis') / out.name
out.mkdir(parents=True, exist_ok=False)
build.mkdir(parents=True, exist_ok=False)
summary = dict(status='preparing', commands=[], observation_row=args.observation,
               scope='One frozen identified initial ray; observation hooks only; no inversion or production changes')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save():
    temporary = out / 'summary.json.new'
    temporary.write_text(json.dumps(summary, indent=2) + '\n')
    temporary.replace(out / 'summary.json')


def command(name, argv):
    record = dict(name=name, argv=list(map(str, argv)), status='running')
    summary['commands'].append(record)
    start = time.time()
    with (out / (name + '_stdout.log')).open('w') as stdout, (out / (name + '_stderr.log')).open('w') as stderr:
        child = subprocess.Popen(record['argv'], stdout=stdout, stderr=stderr,
                                 env=dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='4'))
        record['pid'] = child.pid
        save()
        code = child.wait()
    record.update(status='completed', exit_code=code, seconds=time.time() - start)
    save()
    require(code == 0, name + ' failed')


try:
    manifest = json.loads((data / 'run_manifest.json').read_text())
    ledger = json.loads((data / 'preflight_execution.json').read_text())
    require(any(c['stage'] == 'initial_linearize' and c['return_code'] == 0 for c in ledger['completed_commands']),
            'Initial linearization has not completed successfully')
    for name, expected in manifest['sha256'].items():
        require(sha(Path(name)) == expected, 'Frozen run hash changed: ' + name)
    inputs = [data / name for name in ['initial_events.csv', 'stations.csv', 'initial_grid.csv', 'initial_linearization_rows.csv']]
    summary['input_sha256'] = {str(p): sha(p) for p in inputs}
    rays, events, stations = read(inputs[3]), read(inputs[0]), read(inputs[1])
    matches = [r for r in rays if int(r['observation_row']) == args.observation]
    require(len(matches) == 1, 'Expected one selected absolute observation')
    selected = dict(matches[0], observation_index=str(args.observation))
    event, station = events[int(selected['i'])], stations[int(selected['station'])]
    require(event['event_resource_id'] == selected['event_i_resource_id'], 'Event identity mismatch')
    require(event['origin_resource_id'] == selected['origin_i_resource_id'], 'Origin identity mismatch')
    for name in ['channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end']:
        require(station[name] == selected[name], 'Receiver identity mismatch: ' + name)
    for prefix, native in [('source_', event), ('receiver_', station)]:
        for name, value in native.items():
            selected[prefix + name] = value
        for axis in 'xyz':
            selected[prefix + axis + '_km'] = native[axis]
    with (out / 'identified_ray.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected), lineterminator='\n')
        writer.writeheader()
        writer.writerow(selected)
    shutil.copyfile(str(data / 'initial_grid.csv'), str(out / 'initial_grid.csv'))
    source_root = Path(manifest['binary']).parent.parent / 'source'
    for name, expected in manifest['source_sha256'].items():
        if name.startswith('src/'):
            original = source_root / name
            require(sha(original) == expected, 'Frozen source hash changed: ' + name)
            target = out / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(original), str(target))
    commit = manifest['base_commit']
    for name in ['diagnostics/check_ray_stopping.cpp', 'diagnostics/run_ray_stopping.py', 'diagnostics/first_arrival_fmm.hpp']:
        target = out / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', 'show', commit + ':' + name]))
    # Reuse the reviewed observation-only hooks, never the historical launcher.
    recipe = (out / 'source/diagnostics/run_ray_stopping.py').read_text()
    first, last = recipe.index('def instrument(source):'), recipe.index('\nobserved_trace = ')
    context = dict(args=SimpleNamespace(production_hybrid=True, cone_hybrid=False, cone_metric=False, reduced_metric=False), pure_metric=False)
    exec(recipe[first:last], context)
    core = (out / 'source/src/core.hpp').read_text()
    first = core.index('Ray trace(const Grid &g,')
    last = core.index('\nstruct Entry {', first)
    original = core[first:last]
    observed = context['instrument'](original)
    (out / 'source/diagnostics/observed_optimizer.hpp').write_text(observed)
    (out / 'instrumentation.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), observed.splitlines(True), fromfile='trace.cpp', tofile='observed_trace.cpp')))
    target = out / 'source/diagnostics/check_ray_stopping.cpp'
    original = target.read_text()
    driver = original
    for old, new in [('if(argc!=6)', 'if(argc!=7)'), ('OUT BUDGETS SPACINGS', 'OUT BUDGETS SPACINGS AUX_SPACING'),
                     ('pos("dd_source_")', 'pos("source_")'),
                     ('first_arrival::Field field(g,b,.5,2,true);', 'first_arrival::Field field(g,b,std::stod(argv[6]),2,true);')]:
        require(driver.count(old) == 1, 'Driver adaptation location changed')
        driver = driver.replace(old, new, 1)
    target.write_text(driver)
    (out / 'driver_adaptation.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), driver.splitlines(True), fromfile='check_ray_stopping.cpp', tofile='initial_check_ray_stopping.cpp')))
    shutil.copyfile(__file__, str(out / 'source/diagnostics/run_initial_ray_diagnosis.py'))
    summary.update(source_commit=commit, source_sha256={str(p.relative_to(out / 'source')): sha(p) for p in (out / 'source').rglob('*') if p.is_file()})
    binary = build / 'check'
    command('compile', ['g++', '-std=c++17', '-O2', '-fopenmp', '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC',
                        out / 'source/diagnostics/check_ray_stopping.cpp', '-lstdc++fs', '-o', binary])
    summary['binary_sha256'] = sha(binary)
    results = []
    for spacing in spacings:
        label = 'spacing' + format(spacing, '.6f').replace('.', '_')
        field_spacing = args.field_spacing if args.field_spacing is not None else spacing
        target = out / label
        target.mkdir()
        command(label, [binary, out / 'initial_grid.csv', out / 'identified_ray.csv', target, args.budgets, str(spacing), str(field_spacing)])
        values = read(target / 'results.csv')
        require(len(values) == 2 * len(budgets) and all(r['logged_matches_unobserved_variant'] == '1' for r in values), 'Observer changed the frozen ray result')
        for row in values:
            row['field_spacing_km'] = field_spacing
        results.extend(values)
    candidates = [r for r in results if r['field_spacing_km'] == .5 and float(r['path_spacing_km']) == .5 and r['max_updates'] == '1000']
    if candidates:
        best = min(candidates, key=lambda r: float(r['time_s']))
        require(float(format(float(best['time_s']), '.12g')) == float(selected['ray_time']), 'Saved selected action changed')
        require(float(format(float(best['projected_gradient']), '.12g')) == float(selected['ray_projected_gradient']), 'Saved stopping gradient changed')
        require(best['converged'] == selected['ray_converged'], 'Saved convergence flag changed')
    for name, expected in summary['input_sha256'].items():
        require(sha(Path(name)) == expected, 'Input changed during diagnostic: ' + name)
    summary.update(status='completed_with_original_flags_preserved', results=results,
                   selected_initial_ray_matches=True if candidates else None,
                   limitations=['One identified initial ray; no global first-arrival claim.', 'The higher iteration budget is a diagnostic only.',
                                'Both starts are recomputed from the same original seed; no interrupted BFGS state is resumed.',
                                'CSV rows join native identities and epochs through identified_ray.csv and observation_index.'])
    summary['output_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p.name != 'summary.json'}
except BaseException as error:
    summary.update(status='failed', failure=str(error))
    save()
    raise
save()
print(out / 'summary.json', flush=True)
