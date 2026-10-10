#!/usr/bin/env python3
"""Bounded O3 controls for adopting guarded inversion after Hayward004."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', required=True)
    args = parser.parse_args()
    if not args.variant.replace('_', '').isalnum(): raise ValueError('Use a simple variant')
    out = ROOT / 'data/development/hayward_guard_adoption_checks' / args.variant
    build = ROOT / 'tmp/hayward_guard_adoption_checks' / args.variant
    out.mkdir(parents=True); build.mkdir(parents=True)
    baseline = ROOT / 'tmp/hayward_runs/first_arrival_004/source'
    old_manifest = json.loads((ROOT / 'data/hayward_first_arrival_004/run_manifest.json').read_text())
    for name, digest in old_manifest['source_sha256'].items():
        if sha(baseline / name) != digest: raise ValueError('Frozen004 source changed: ' + name)
    summary = dict(status='running', scope='Invented geometry only; no real inversion or ray rerun',
                   commands=[], checks=[], baseline_source_sha256={}, guarded_source_sha256={})
    env = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', LC_ALL='C')
    def save():
        (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    def run(name, command, threads=4, expected=0):
        command = list(map(str, command)); start = time.monotonic()
        with (out / (name + '_stdout.log')).open('x') as stdout, (out / (name + '_stderr.log')).open('x') as stderr:
            code = subprocess.call(command, cwd=str(ROOT), env=dict(env, OMP_NUM_THREADS=str(threads)), stdout=stdout, stderr=stderr)
        summary['commands'].append(dict(name=name, command=command, threads=threads, return_code=code,
                                        elapsed_seconds=time.monotonic() - start))
        save()
        if (code == 0) != (expected == 0): raise ValueError('Unexpected command status: ' + name)
    def check(name, value):
        summary['checks'].append(dict(name=name, passed=bool(value)))
        if not value: raise ValueError(name)
    def copy_inputs(source, target, config):
        target.mkdir(parents=True)
        for name in ('initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv', 'truth_grid.csv'):
            shutil.copyfile(str(source / name), str(target / name))
        (target / 'run.cfg').write_text(config)
    def equal_files(a, b, pattern):
        names = sorted(p.name for p in a.glob(pattern))
        check('same_inventory_' + a.name + '_' + b.name, names == sorted(p.name for p in b.glob(pattern)) and bool(names))
        check('byte_parity_' + a.name + '_' + b.name, all((a / n).read_bytes() == (b / n).read_bytes() for n in names))
    try:
        sources = {}
        for label, source in [('baseline', baseline), ('guarded', ROOT)]:
            target = out / (label + '_source'); target.mkdir()
            names = ['CMakeLists.txt'] + ['src/' + p.name for p in sorted((source / 'src').iterdir()) if p.is_file()]
            names += ['diagnostics/check_external_inputs.cpp']
            if label == 'guarded': names += ['diagnostics/check_inversion_ray_gate.cpp']
            for name in names:
                p = source / name if not name.startswith('diagnostics/') else ROOT / name
                q = target / name; q.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(str(p), str(q))
            summary[label + '_source_sha256'] = {n:sha(target/n) for n in names}
            sources[label] = target
            run(label + '_configure', ['cmake', '-S', target, '-B', build / label])
            run(label + '_compile', ['cmake', '--build', build / label, '-j', '2'])
        flags = [(build / label / 'CMakeFiles/dd.dir/flags.make').read_text().split('CXX_FLAGS = ', 1)[1].splitlines()[0] for label in ('baseline', 'guarded')]
        check('same_CMake_O3_flags', flags[0] == flags[1] and '-O3' in flags[0] and '-fopenmp' in flags[0])
        compiler = next(line.split('=', 1)[1] for line in (build/'guarded/CMakeCache.txt').read_text().splitlines()
                        if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
        summary.update(compiler=compiler, compiler_sha256=sha(Path(compiler)), flags=flags[0])
        run('compiler_version', [compiler, '--version'])
        run('compile_guard_component', [compiler] + flags[0].split() + [sources['guarded'] / 'diagnostics/check_inversion_ray_gate.cpp', '-lstdc++fs', '-o', build / 'component'])
        for threads in (1, 4):
            fixture = out / ('component_t' + str(threads))
            run('component_t' + str(threads), [build / 'component', fixture], threads)
            check('component_t' + str(threads), json.loads((fixture/'summary.json').read_text())['status'] == 'passed')
            for label in ('baseline', 'guarded'):
                binary = build / label / 'dd'
                successful = out / (label + '_success_t' + str(threads))
                copy_inputs(fixture, successful, (fixture/'fixture.cfg').read_text())
                run(successful.name, [binary, 'invert', successful/'run.cfg', successful, 'loc1d'], threads)
                failure = out / (label + '_failure_t' + str(threads))
                copy_inputs(fixture/'current_failure', failure, (fixture/'current_failure/run.cfg').read_text())
                run(failure.name, [binary, 'invert', failure/'run.cfg', failure, 'dd'], threads, 0 if label == 'baseline' else 1)
                check(label+'_failure_contract_t'+str(threads), (failure/'dd_grid.csv').exists() == (label == 'baseline'))
                if label == 'guarded':
                    check('identified_failure_preserved_t'+str(threads), (failure/'dd_failed_forward_ray_failures.csv').exists() and (failure/'dd_last_accepted_grid.csv').exists())
                forward = out / (label + '_forward_t' + str(threads))
                # Same physical FMM/path spacings as004; the invented box is small.
                config = (fixture/'fixture.cfg').read_text() + '\nray_initializer 1\nfmm_spacing 0.125\nray_spacing 0.03125\n'
                copy_inputs(fixture, forward, config)
                run(forward.name+'_linearize', [binary, 'linearize', forward/'run.cfg', forward, 'initial'], threads)
                run(forward.name+'_raycheck', [binary, 'raycheck', forward/'run.cfg', forward, 'initial'], threads)
            equal_files(out/('baseline_success_t'+str(threads)), out/('guarded_success_t'+str(threads)), 'loc1d_*.csv')
            equal_files(out/('baseline_forward_t'+str(threads)), out/('guarded_forward_t'+str(threads)), 'initial_*csv')
        equal_files(out/'guarded_forward_t1',out/'guarded_forward_t4','initial_*csv')
        equal_files(out/'guarded_success_t1',out/'guarded_success_t4','loc1d_*.csv')
        # The shared external-input fixture exercises separate native DD epochs,
        # exact common receiver coordinates, source/model rows and metadata joins.
        for label in ('baseline','guarded'):
            run(label+'_external_compile', [compiler]+flags[0].split()+[sources[label]/'diagnostics/check_external_inputs.cpp','-lstdc++fs','-o',build/(label+'_external')])
            for threads in (1,4):
                folder=out/(label+'_external_t'+str(threads)); result=out/(folder.name+'.json')
                run(folder.name,[build/(label+'_external'),result,folder],threads)
                check(folder.name,json.loads(result.read_text())['status']=='passed')
        for threads in (1,4):
            equal_files(out/('baseline_external_t'+str(threads))/'cross_epoch',out/('guarded_external_t'+str(threads))/'cross_epoch','ray_*.csv')
        summary['binary_sha256']={label:sha(build/label/'dd') for label in ('baseline','guarded')}
        summary['original004_binary_sha256']=old_manifest['sha256'][old_manifest['binary']]
        summary['fresh_baseline_binary_identical_to004'] = summary['binary_sha256']['baseline'] == summary['original004_binary_sha256']
        summary['source_unchanged_after_controls']=all(sha(ROOT/n)==d for n,d in summary['guarded_source_sha256'].items())
        check('guarded_sources_unchanged',summary['source_unchanged_after_controls'])
        summary.update(status='passed', mathematical_evidence_reuse_eligible=True,
                       limitations=['Bounded invented controls plus source equivalence; no general compiler equivalence or3Dfirst-arrival certificate.',
                                    'Actual inversion remains gated on terminal full preflight and independent accuracy review.'])
    except BaseException as error:
        summary.update(status='failed',error=str(error)); raise
    finally:
        shutil.copyfile(str(Path(__file__).resolve()),str(out/'check_hayward_guard_adoption.py'))
        summary['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='summary.json'}
        save()
    print(json.dumps({'status':summary['status'],'checks':len(summary['checks']),'summary':str(out/'summary.json')},indent=2))


if __name__ == '__main__': main()
