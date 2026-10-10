#!/usr/bin/env python3
"""Freeze a corrected Hayward run, inspect its preflight, then run inversions."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
parser.add_argument('--phase', required=True, choices=['preflight', 'invert'])
parser.add_argument('--threads', type=int, default=4)
args = parser.parse_args()
if not re.fullmatch('[a-zA-Z0-9_-]+', args.variant) or args.threads < 1:
    parser.error('Use a simple variant name and positive thread count')
out = ROOT/'data'/('hayward_'+args.variant)
build = ROOT/'tmp/hayward_runs'/args.variant
env = dict(os.environ, TMPDIR=str(ROOT/'tmp'), OMP_NUM_THREADS=str(args.threads),
           OPENBLAS_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
execution = None

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

def relative(path):
    return str(path.relative_to(ROOT))

def run(command, name):
    command = [relative(x) if isinstance(x, Path) else x for x in command]
    if execution is not None:
        execution['current_command'] = command
        (out/'inversion_execution.json').write_text(json.dumps(execution, indent=2)+'\n')
    with (out/(name+'_stdout.txt')).open('w') as stdout, (out/(name+'_stderr.txt')).open('w') as stderr:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)

if args.phase == 'preflight':
    if out.exists() or build.exists():
        parser.error('Choose a fresh variant; prior data and evidence are preserved')
    out.mkdir(parents=True)
    snapshot = build/'source'
    snapshot.mkdir(parents=True)
    names = ['initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv',
             'selection_manifest.json', 'authoritative_ids_required', 'event_pairs.csv',
             'event_selection.csv', 'initial_geographic_events.csv', 'excluded_picks.csv']
    for name in names:
        shutil.copyfile(ROOT/'data/hayward'/name, out/name)
    config = (ROOT/'configs/hayward.cfg').read_text()
    (out/'run.cfg').write_text(config+'\n# Assessed starting discretization; refinement is recorded separately.\n'
                             'ray_initializer 1\nfmm_spacing 0.5\n')
    sources = [Path('CMakeLists.txt'), Path(__file__).resolve().relative_to(ROOT),
               *[p.relative_to(ROOT) for p in sorted((ROOT/'src').glob('*')) if p.is_file()]]
    for source in sources:
        target = snapshot/source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/source, target)
    def normalize(info):
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ''
        info.pax_headers = {}
        return info
    with tarfile.open(out/'source_snapshot.tar.gz', 'w:gz') as archive:
        for source in sources:
            archive.add(snapshot/source, arcname=str(source), filter=normalize)
    run(['cmake', '-S', snapshot, '-B', build/'compiled'], 'configure')
    run(['cmake', '--build', build/'compiled', '-j', '2'], 'compile')
    binary = build/'compiled/dd'
    tracked = [out/name for name in names]+[out/'run.cfg', out/'source_snapshot.tar.gz', binary]
    manifest = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'base_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=str(ROOT), universal_newlines=True).strip(),
        'scope': 'Same authoritative Hayward cohort and inverse settings; corrected ray initializer/optimizer',
        'baseline': 'data/hayward/run_manifest.json', 'threads': args.threads,
        'binary': relative(binary), 'source_sha256': {str(p):sha(snapshot/p) for p in sources},
        'sha256': {relative(p):sha(p) for p in tracked},
        'limitations': ['0.5-km field/path spacing is a starting field discretization, not a universal first-arrival accuracy certificate.',
                        'The same 32-ray refinement/derivative sample and full initial absolute-ray support are inspected before inversion.',
                        'Changes combine the first-arrival initializer and constrained ray optimizer; they do not isolate either change.']}
    (out/'run_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    run([binary,'linearize',out/'run.cfg',out,'initial'], 'initial_linearize')
    run([binary,'raycheck',out/'run.cfg',out,'initial'], 'initial_raycheck')
    absolute = rows(out/'initial_linearization_rows.csv')
    observations = rows(out/'observations.csv')
    expected = {str(i):r for i,r in enumerate(observations) if r['type']=='0'}
    sample = rows(out/'initial_ray_convergence.csv')
    derivative = rows(out/'initial_ray_derivatives.csv')
    failures = []
    if len(absolute) != len(expected) or {r['observation_row'] for r in absolute} != set(expected):
        failures.append('Absolute-ray support count changed')
    for row in absolute:
        original = expected[row['observation_row']]
        # Solver tables use 12 significant digits; preserve that known output
        # serialization rather than introducing a travel-time tolerance here.
        if float(row['observed']) != float(format(float(original['value']), '.12g')):
            failures.append('Changed observed value at linearization row '+row['row'])
        for key,value in original.items():
            if key not in ['j','type','value'] and row[key] != value:
                failures.append('Changed observation identity at linearization row '+row['row']+': '+key)
        if row['ray_converged']!='1' or row['ray_initialization_succeeded']!='1':
            failures.append('Failed initial ray at identified linearization row '+row['row'])
        if not all(math.isfinite(float(row[k])) for k in ['ray_time','ray_projected_gradient','ray_raw_gradient']):
            failures.append('Nonfinite initial ray at identified linearization row '+row['row'])
    events, stations = rows(out/'initial_events.csv'), rows(out/'stations.csv')
    support = set((int(r['i']), int(r['station'])) for r in observations)
    support.update((int(r['j']), int(r['station_j'])) for r in observations if int(r['j'])>=0)
    ordered = sorted(support)
    count = min(32, len(ordered))
    selected = [ordered[0 if count==1 else n*(len(ordered)-1)//(count-1)] for n in range(count)]
    expected_samples = {(str(n),str(i),str(k)) for n,(i,k) in enumerate(selected)}
    actual_samples = {(r['diagnostic_row'],r['event'],r['station']) for r in sample}
    if len(sample)!=count or actual_samples!=expected_samples:
        failures.append('Deterministic ray sample changed')
    if support != {(int(r['i']),int(r['station'])) for r in expected.values()}:
        failures.append('Absolute linearization does not cover the complete observation support')
    grid = rows(out/'initial_grid.csv')
    bounds = {axis:(min(float(r[axis]) for r in grid),max(float(r[axis]) for r in grid)) for axis in ['x','y','z']}
    expected_components = set()
    for n,(i,k) in enumerate(selected[:8]):
        for axis,key in enumerate(['x','y','z']):
            value = float(events[i][key])
            if bounds[key][0] <= value-.01 and value+.01 <= bounds[key][1]:
                expected_components.add((str(n),str(i),str(k),str(axis)))
    actual_components = {(r['diagnostic_row'],r['event'],r['station'],r['axis']) for r in derivative}
    if len(derivative)!=len(expected_components) or actual_components!=expected_components:
        failures.append('Derivative component support changed')
    identifiers = rows(out/'initial_ray_identifiers.csv')
    expected_joins = set()
    for n,(i,k) in enumerate(selected):
        for q,r in enumerate(observations):
            if (int(r['i']),int(r['station']))==(i,k):
                expected_joins.add((str(n),str(i),str(k),str(q),'i'))
            if (int(r['j']),int(r['station_j']))==(i,k):
                expected_joins.add((str(n),str(i),str(k),str(q),'j'))
    join_columns = ['diagnostic_row','event','station','observation_row','observation_event_side']
    if len(identifiers)!=len(expected_joins) or {tuple(r[k] for k in join_columns) for r in identifiers}!=expected_joins:
        failures.append('Sample observation associations changed')
    for row in identifiers:
        originals = [('observation_', observations[int(row['observation_row'])], {'i','j','station','type','value'}),
                     ('source_',events[int(row['event'])],{'id','x','y','z','t'}),
                     ('receiver_',stations[int(row['station'])],{'id','x','y','z','t'})]
        for prefix,original,omit in originals:
            if any(row[prefix+k]!=v for k,v in original.items() if k not in omit):
                failures.append('Changed native sample metadata at diagnostic row '+row['diagnostic_row'])
    for row in sample:
        if not all(math.isfinite(float(row[k])) for k in ['production_time','refined_time','difference',
                    'production_gradient','refined_gradient','production_raw_gradient','refined_raw_gradient']):
            failures.append('Nonfinite sample at diagnostic row '+row['diagnostic_row'])
        if any(row[k]!='1' for k in ['production_converged','refined_converged',
                                     'production_initialization_succeeded','refined_initialization_succeeded']):
            failures.append('Failed sample at diagnostic row '+row['diagnostic_row'])
    for row in derivative:
        if not all(math.isfinite(float(row[k])) for k in ['production_derivative','refined_derivative',
                                                          'finite_difference','production_error','refined_error']):
            failures.append('Nonfinite derivative at diagnostic row '+row['diagnostic_row'])
        if any(row[k]!='1' for k in ['plus_converged','minus_converged',
                                     'plus_initialization_succeeded','minus_initialization_succeeded']):
            failures.append('Failed derivative perturbation at diagnostic row '+row['diagnostic_row'])
    preflight = {'absolute_rays':len(absolute), 'sample_rays':len(sample), 'derivative_components':len(derivative),
                 'sample_identity_associations':len(identifiers),
                 'failures':failures, 'max_sample_time_difference_s':max(abs(float(r['difference'])) for r in sample),
                 'max_source_component_difference_s_per_km':max(abs(float(r['production_error'])) for r in derivative),
                 'status':'ready_for_accuracy_review' if not failures else 'failed_checks_preserved',
                 'identity_files':['initial_linearization_rows.csv','initial_ray_identifiers.csv'],
                 'sha256':{p.name:sha(p) for p in sorted(out.glob('initial_*csv'))}}
    (out/'preflight.json').write_text(json.dumps(preflight, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in preflight.items() if k!='sha256'}, indent=2))
    raise SystemExit(bool(failures))

manifest = json.loads((out/'run_manifest.json').read_text())
for name, digest in manifest['sha256'].items():
    if sha(ROOT/name) != digest:
        raise ValueError('Frozen run input or binary changed: '+name)
preflight = json.loads((out/'preflight.json').read_text())
if preflight['failures']:
    raise ValueError('Resolve recorded preflight failures before inversion')
for name, digest in preflight['sha256'].items():
    if sha(out/name) != digest:
        raise ValueError('Recorded preflight evidence changed: '+name)
if args.threads != manifest['threads']:
    raise ValueError('Use the recorded preflight thread count')
if any((out/(mode+'_history.csv')).exists() for mode in ['dd','standard','loc1d']):
    raise ValueError('A run already started; inspect its existing handle and preserve its evidence')
binary = ROOT/manifest['binary']
execution = {'status':'running', 'started_utc':datetime.now(timezone.utc).isoformat(),
             'threads':args.threads, 'return_code':None}
# Exclusive creation reserves the phase before any subprocess/log write.
# A failed or interrupted phase keeps this record; it is never auto-restarted.
with (out/'inversion_execution.json').open('x') as stream:
    stream.write(json.dumps(execution, indent=2)+'\n')
try:
    for mode in ['dd','standard','loc1d']:
        run([binary,'invert',out/'run.cfg',out,mode], mode+'_invert')
        run([binary,'raycheck',out/'run.cfg',out,mode], mode+'_raycheck')
        run([binary,'linearize',out/'run.cfg',out,mode], mode+'_linearize')
except BaseException as error:
    execution.update(status='failed', return_code=getattr(error,'returncode',None), error=str(error),
                     finished_utc=datetime.now(timezone.utc).isoformat())
    (out/'inversion_execution.json').write_text(json.dumps(execution, indent=2)+'\n')
    raise
execution.update(status='finished', return_code=0, finished_utc=datetime.now(timezone.utc).isoformat())
(out/'inversion_execution.json').write_text(json.dumps(execution, indent=2)+'\n')
(out/'inversions_finished.json').write_text(json.dumps({
    'finished_utc':datetime.now(timezone.utc).isoformat(), 'modes':['dd','standard','loc1d'],
    'scope':'Configured runs and diagnostics finished; scientific convergence and reproduction require output review.'}, indent=2)+'\n')
