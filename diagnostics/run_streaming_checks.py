#!/usr/bin/env python3
"""Rebuild isolated storage checks; never runs a full simulation/inversion."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
parser.add_argument('--baseline', default='deeae0e')
args = parser.parse_args()
if not args.variant.replace('_', '').replace('-', '').isalnum():
    raise ValueError('Variant must contain letters, digits, underscores or hyphens')
out = Path('data/development/loma_streaming') / args.variant
out.mkdir(parents=True, exist_ok=False)
cache = Path('tmp/loma_streaming_checks') / args.variant
cache.mkdir(parents=True, exist_ok=False)
env = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='2')

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

manifest = {'status': 'running', 'scope': 'Storage/identity validation and tiny invented one-step inversions only; no full Loma arrivals or inversion',
            'baseline_commit': subprocess.check_output(['git', 'rev-parse', args.baseline]).decode().strip(),
            'source_sha256': {}, 'input_sha256': {}, 'commands': [], 'checks': {}}

def save():
    (out / 'summary.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')

def run(name, command, expected=0):
    start = time.time()
    with (out / (name+'_stdout.log')).open('w') as stdout, (out / (name+'_stderr.log')).open('w') as stderr:
        result = subprocess.run(list(map(str, command)), env=env, stdout=stdout, stderr=stderr)
    manifest['commands'].append({'name': name, 'argv': list(map(str, command)), 'exit_code': result.returncode, 'seconds': time.time()-start})
    save()
    if result.returncode != expected:
        raise RuntimeError(name+' exited '+str(result.returncode))

try:
    drivers = ['check_external_inputs.cpp', 'check_forward_integration.cpp', 'check_matrix_storage.cpp', 'check_streaming_observations.cpp']
    legacy_names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', args.baseline, 'src']).decode().splitlines()
    source_names = sorted(str(p) for p in Path('src').glob('*') if p.suffix in ('.hpp', '.cpp'))
    source_names += ['diagnostics/'+name for name in drivers] + ['diagnostics/run_streaming_checks.py']
    for name in source_names:
        target = out / 'current_source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(name, str(target))
        manifest['source_sha256'][name] = sha(target)
    for name in legacy_names:
        target = out / 'legacy_source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', 'show', args.baseline+':'+name]))
    legacy_diag = out / 'legacy_source/diagnostics'
    legacy_diag.mkdir()
    for name in ['check_external_inputs.cpp', 'check_forward_integration.cpp']:
        text = subprocess.check_output(['git', 'show', args.baseline+':diagnostics/'+name]).decode()
        if name == 'check_external_inputs.cpp':
            # Preserve baseline evidence: only fix a stale named-column check,
            # and let the unchanged checks use this run's isolated fixture dir.
            (legacy_diag / 'check_external_inputs_unmodified.cpp').write_text(text)
            text = text.replace('convergence.header.back()=="diagnostic_row"',
                                'std::find(convergence.header.begin(),convergence.header.end(),"diagnostic_row")!=convergence.header.end()')
            text = text.replace('const std::string dir = "tmp/external_input_checks/fixture";',
                                'const std::string dir = argc > 2 ? argv[2] : "tmp/external_input_checks/fixture";')
            text = text.replace('argc==2 ? argv[1]', 'argc>=2 ? argv[1]')
        (legacy_diag / name).write_text(text)
    manifest['legacy_driver_adjustments'] = 'External check: diagnostic_row named presence instead of final-column position; optional isolated fixture path. No numerical thresholds changed.'
    inputs = out / 'identified_input_snapshot'
    inputs.mkdir()
    for name in ['observations.csv', 'initial_events.csv', 'stations.csv']:
        source = Path('data/hayward') / name
        target = inputs / name
        shutil.copyfile(str(source), str(target))
        manifest['input_sha256']['data/hayward/'+name] = sha(target)
        assert sha(source) == sha(target)
    flags = ['g++', '-std=c++17', '-O2', '-fopenmp']
    for label in ['legacy', 'current']:
        base = out / (label+'_source')
        for name in ['check_external_inputs', 'check_forward_integration']:
            exe = cache / (label+'_'+name)
            run('compile_'+label+'_'+name, flags+[base / ('diagnostics/'+name+'.cpp'), '-lstdc++fs', '-o', exe])
        fixture = out / (label+'_external')
        run(label+'_external', [cache/(label+'_check_external_inputs'), out/(label+'_external.json'), fixture])
        forward = out / (label+'_forward')
        forward.mkdir()
        run(label+'_forward', [cache/(label+'_check_forward_integration'), forward])
    matrix_driver = out / 'current_source/diagnostics/check_matrix_storage.cpp'
    for label in ['legacy', 'current']:
        header = (ROOT / out / (label+'_source/src/core.hpp')).resolve()
        flags2 = flags + ['-DMATRIX_HEADER="'+str(header)+'"']
        if label == 'legacy':
            flags2 += ['-DLEGACY_MATRIX']
        run('compile_'+label+'_matrix', flags2+[matrix_driver, '-o', cache/(label+'_matrix')])
        run(label+'_matrix', [cache/(label+'_matrix')])
    assert (out/'legacy_matrix_stdout.log').read_bytes() == (out/'current_matrix_stdout.log').read_bytes()
    manifest['checks']['ordered_operator_and_27_lsqr_systems_bitwise_equal'] = True
    for family in ['external', 'forward']:
        compared = []
        legacy = out / ('legacy_'+family)
        current = out / ('current_'+family)
        for path in sorted(legacy.rglob('*.csv')):
            relative = path.relative_to(legacy)
            assert path.read_bytes() == (current/relative).read_bytes(), str(relative)
            compared.append(str(relative))
        manifest['checks'][family+'_identical_csv_files'] = compared
    driver = out / 'current_source/diagnostics/check_streaming_observations.cpp'
    run('compile_streaming_observations', flags+[driver, '-lstdc++fs', '-o', cache/'observations'])
    fixture = out / 'streaming_observations'
    run('streaming_observations', [cache/'observations', fixture, inputs])
    manifest['checks']['streaming'] = json.loads((fixture/'summary.json').read_text())
    with (inputs/'observations.csv').open(newline='') as a, (fixture/'real_roundtrip.csv').open(newline='') as b:
        left, right = csv.reader(a), csv.reader(b)
        assert next(left) == next(right)
        rows = cells = 0
        while True:
            x, y = next(left, None), next(right, None)
            if x is None or y is None:
                assert x is None and y is None
                break
            assert x[5:] == y[5:] and list(map(int, x[:4])) == list(map(int, y[:4])) and float(x[4]) == float(y[4])
            rows += 1
            cells += len(x)-5
    manifest['checks']['real_roundtrip'] = {'rows': rows, 'identical_metadata_cells': cells, 'numeric_values_equal': True}
    input_names = ['initial_events.csv', 'truth_events.csv', 'stations.csv', 'initial_grid.csv', 'truth_grid.csv', 'observations.csv', 'fixture.cfg']
    for label in ['legacy', 'current']:
        target = out / (label+'_identified_synthetic')
        target.mkdir()
        for name in input_names:
            shutil.copyfile(str(fixture/name), str(target/name))
        for mode in ['dd', 'standard', 'loc1d']:
            exe = cache/(label+'_check_forward_integration')
            run(label+'_identified_'+mode, [exe, '--solver', 'invert', target/'fixture.cfg', target, mode])
            run(label+'_identified_'+mode+'_linearize', [exe, '--solver', 'linearize', target/'fixture.cfg', target, mode])
        run(label+'_identified_raycheck', [exe, '--solver', 'raycheck', target/'fixture.cfg', target, 'initial'])
    identical = []
    for path in sorted((out/'legacy_identified_synthetic').glob('*.csv')):
        assert path.read_bytes() == (out/'current_identified_synthetic'/path.name).read_bytes(), path.name
        identical.append(path.name)
    manifest['checks']['identified_synthetic_identical_csv_files'] = identical
    preflight = out/'preflight_only'
    preflight.mkdir()
    for name in input_names:
        shutil.copyfile(str(fixture/name), str(preflight/name))
    with (preflight/'fixture.cfg').open('a') as stream:
        stream.write('matrix_preflight_only 1\n')
    run('preflight_only', [cache/'current_check_forward_integration', '--solver', 'invert', preflight/'fixture.cfg', preflight, 'dd'])
    assert (preflight/'dd_matrix_preflight.csv').read_bytes() == (out/'current_identified_synthetic/dd_matrix_preflight.csv').read_bytes()
    assert len((preflight/'dd_history.csv').read_text().splitlines()) == 1
    assert not (preflight/'dd_grid.csv').exists() and not (preflight/'dd_events.csv').exists()
    manifest['checks']['actual_preflight_matches_assembled_matrix_without_solve'] = True
    # Record all artifact hashes before removing only the large, reproducible
    # invented stress CSV and real roundtrip; the immutable real input stays.
    manifest['output_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'summary.json'}
    manifest['rebuildable_large_outputs_omitted'] = ['streaming_observations/invented_stress.csv', 'streaming_observations/real_roundtrip.csv']
    for name in manifest['rebuildable_large_outputs_omitted']:
        (out/name).unlink()
    manifest['status'] = 'passed'
    save()
except BaseException as exc:
    manifest['status'] = 'failed'
    manifest['failure'] = str(exc)
    save()
    raise
print(str(out/'summary.json'))
