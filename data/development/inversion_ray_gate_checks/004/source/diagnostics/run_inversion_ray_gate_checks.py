#!/usr/bin/env python3
"""Test inverse forward rejection on invented geometry and parent-code parity."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--baseline', default='609f04a')
    args = parser.parse_args()
    if not args.variant.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Use a simple variant name')
    out = ROOT / 'data/development/inversion_ray_gate_checks' / args.variant
    build = ROOT / 'tmp/inversion_ray_gate_checks' / args.variant
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    summary = dict(status='running', scope='Invented geometry; no real inversion', commands=[])
    environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='4',
                       OPENBLAS_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')

    def save():
        (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')

    def run(name, command):
        command = list(map(str, command))
        start = time.monotonic()
        with (out / (name + '_stdout.log')).open('w') as stdout, (out / (name + '_stderr.log')).open('w') as stderr:
            code = subprocess.call(command, cwd=str(ROOT), env=environment, stdout=stdout, stderr=stderr)
        summary['commands'].append(dict(name=name, argv=command, return_code=code, seconds=time.monotonic() - start))
        save()
        if code:
            raise RuntimeError(name + ' failed')

    def inputs(source, target, configuration):
        target.mkdir()
        for name in ('initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv', 'truth_grid.csv'):
            shutil.copyfile(str(source / name), str(target / name))
        shutil.copyfile(str(configuration), str(target / 'run.cfg'))

    try:
        names = [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'src').glob('*')) if p.is_file()]
        names += ['diagnostics/check_inversion_ray_gate.cpp', 'diagnostics/run_inversion_ray_gate_checks.py']
        summary['source_sha256'] = {name: sha(ROOT / name) for name in names}
        for name in names:
            target = out / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(ROOT / name), str(target))
        baseline = subprocess.check_output(['git', 'rev-parse', args.baseline], cwd=str(ROOT)).decode().strip()
        summary['baseline_commit'] = baseline
        old_names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', baseline, 'src'], cwd=str(ROOT)).decode().splitlines()
        for name in old_names:
            target = out / 'baseline_source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=str(ROOT)))
        flags = ['g++', '-std=c++17', '-O2', '-fopenmp']
        run('compile_component', flags + [out / 'source/diagnostics/check_inversion_ray_gate.cpp', '-lstdc++fs', '-o', build / 'component'])
        run('component', [build / 'component', out / 'fixture'])
        run('compile_baseline', flags + [out / 'baseline_source/src/main.cpp', '-lstdc++fs', '-o', build / 'baseline'])
        fixture = out / 'fixture'
        old = out / 'baseline_success'
        inputs(fixture, old, fixture / 'fixture.cfg')
        run('baseline_success', [build / 'baseline', 'invert', old / 'run.cfg', old, 'loc1d'])
        same = []
        for path in sorted(fixture.glob('loc1d_*.csv')):
            assert path.read_bytes() == (old / path.name).read_bytes(), path.name
            same.append(path.name)
        assert len(same) == 7
        old_preflight = out / 'baseline_preflight'
        inputs(fixture / 'preflight', old_preflight, fixture / 'preflight/run.cfg')
        run('baseline_preflight', [build / 'baseline', 'invert', old_preflight / 'run.cfg', old_preflight, 'dd'])
        for name in ('dd_preflight_ray_status.csv', 'dd_matrix_preflight.csv', 'dd_history.csv'):
            assert (old_preflight / name).read_bytes() == (fixture / 'preflight' / name).read_bytes(), name
        old_failed = out / 'baseline_unchecked'
        inputs(fixture / 'current_failure', old_failed, fixture / 'current_failure/run.cfg')
        run('baseline_unchecked', [build / 'baseline', 'invert', old_failed / 'run.cfg', old_failed, 'dd'])
        history = rows(old_failed / 'dd_history.csv')
        assert history and int(history[0]['ray_converged_count']) < int(history[0]['ray_count'])
        assert (old_failed / 'dd_grid.csv').exists() and (old_failed / 'dd_events.csv').exists()
        for name, digest in summary['source_sha256'].items():
            assert sha(ROOT / name) == digest == sha(out / 'source' / name), name
        summary.update(status='passed', component_checks=json.loads((fixture / 'summary.json').read_text()),
                       successful_inverse_outputs_byte_identical=same,
                       diagnostic_preflight_outputs_byte_identical=True,
                       parent_demonstrably_used_unconverged_rays=True,
                       binary_sha256={name: sha(build / name) for name in ('component', 'baseline')})
        summary['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                                      if p.is_file() and p != out / 'summary.json'}
        save()
    except BaseException as error:
        summary.update(status='failed', error_type=type(error).__name__, error=str(error))
        summary['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                                      if p.is_file() and p != out / 'summary.json'}
        save()
        raise
    print(str(out / 'summary.json'))


if __name__ == '__main__':
    main()
