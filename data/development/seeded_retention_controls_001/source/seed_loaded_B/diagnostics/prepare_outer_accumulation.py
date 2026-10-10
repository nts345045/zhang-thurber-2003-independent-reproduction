#!/usr/bin/env python3
"""Freeze and test a one-declaration outer-accumulator change; no ray run."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    temp = path.with_name(path.name + '.new')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    os.chdir(str(ROOT))
    out, build = [(ROOT / value).resolve() for value in (args.output, args.build)]
    original = ROOT / 'data/development/loma_initial_failure_3426_001'
    replay = ROOT / 'data/development/loma_failed_search_3426_001'
    for path in (out, build):
        path.relative_to(ROOT)
        need(path != ROOT and not path.exists(), 'Fresh repository-local directories required')
    for a, b in ((out, build), (out, original), (out, replay), (build, original), (build, replay)):
        need(a != b and a not in b.parents and b not in a.parents, 'Disjoint directories required')
    old, captured = load(original / 'summary.json'), load(replay / 'summary.json')
    for directory, summary in ((original, old), (replay, captured)):
        review = load(directory / 'review.json')
        need(summary['status'] == 'completed_with_original_flags_preserved' and
             review['status'] == 'passed_saved_evidence_review' and
             review['summary_sha256'] == sha(directory / 'summary.json'), 'Stale original/replay review')
    need(old['native_context'] == captured['native_context'] and
         rows(replay / 'identified_ray.csv') == [captured['native_context']], 'Native context differs')
    need((old['path_spacing_km'], old['field_spacing_km'], old['maximum_updates']) == (0.03125, 0.125, 1000),
         'Unexpected frozen numerical settings')
    need(sha(Path(old['compiler'])) == old['compiler_sha256'], 'Original compiler changed')
    pins = {}

    def pin(path, digest=None):
        actual = sha(path)
        need(digest is None or actual == digest, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = actual

    for directory, summary in ((original, old), (replay, captured)):
        for name in ('summary.json', 'review.json'):
            pin(directory / name)
        for name, digest in summary['output_sha256'].items():
            pin(directory / name, digest)
    for name in ('diagnostics/check_outer_accumulation.cpp', 'diagnostics/prepare_outer_accumulation.py'):
        pin(ROOT / name)
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    shutil.copytree(str(replay / 'inputs'), str(out / 'inputs'))
    for name in ('identified_ray.csv', 'failed_search_directions.csv', 'failed_search_trials.csv', 'failed_search_decisions.csv'):
        shutil.copyfile(str(replay / name), str(out / 'inputs' / name))
    shutil.copyfile(str(original / 'summary.json'), str(out / 'inputs/original_observer_summary.json'))
    shutil.copyfile(str(replay / 'summary.json'), str(out / 'inputs/neutral_replay_summary.json'))
    core = (original / 'source/src/core.hpp').read_text()
    start = core.index('double path_eval(')
    end = core.index('\n// Remove a redundant internal vertex', start)
    function = core[start:end]
    need(function.count('  double T = 0;') == 1, 'Changed outer-accumulator insertion point')
    modified_function = function.replace('  double T = 0;', '  long double T = 0;', 1)
    modified = core[:start] + modified_function + core[end:]
    old_header = function.replace('double path_eval(', 'double original_path_eval(', 1)
    summary = dict(status='preparing_controls', started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   scope='One-declaration path_eval accumulator experiment; controls only, no ray tracing',
                   input_sha256=pins, compiler=old['compiler'], compiler_sha256=old['compiler_sha256'],
                   original_observer=str(original.relative_to(ROOT)), neutral_replay=str(replay.relative_to(ROOT)),
                   native_context=old['native_context'], path_spacing_km=.03125, field_spacing_km=.125,
                   maximum_updates=1000, threads=1, commands=[], variants={})

    def command(stage, argv):
        record = dict(stage=stage, command=[str(p.relative_to(ROOT)) if isinstance(p, Path) else p for p in argv],
                      status='running')
        summary['commands'].append(record)
        save(out / 'controls_summary.json', summary)
        with (out / (stage + '_stdout.log')).open('w') as stdout, (out / (stage + '_stderr.log')).open('w') as stderr:
            process = subprocess.run(record['command'], stdout=stdout, stderr=stderr,
                                     env=dict(os.environ, OMP_NUM_THREADS='1', TMPDIR=str(ROOT / 'tmp')))
        record.update(status='completed', return_code=process.returncode)
        save(out / 'controls_summary.json', summary)
        need(process.returncode == 0, stage + ' failed')

    try:
        for name, extended in (('baseline', False), ('outer_extended', True)):
            source = out / 'source' / name
            shutil.copytree(str(original / 'source'), str(source))
            (source / 'src/core.hpp').write_text(modified if extended else core)
            (source / 'diagnostics/original_path_eval.hpp').write_text(old_header)
            shutil.copyfile(str(ROOT / 'diagnostics/check_outer_accumulation.cpp'), str(source / 'diagnostics/check_outer_accumulation.cpp'))
            shutil.copyfile(str(ROOT / 'diagnostics/prepare_outer_accumulation.py'), str(source / 'diagnostics/prepare_outer_accumulation.py'))
            if extended:
                (out / 'single_change.diff').write_text(''.join(difflib.unified_diff(core.splitlines(True), modified.splitlines(True),
                                                       fromfile='frozen_original_core.hpp', tofile='outer_extended_core.hpp')))
            else:
                need(sha(source / 'src/core.hpp') == old['source_sha256']['src/core.hpp'], 'Original core copy changed')
            variant = dict(extended_accumulator=extended,
                           source_sha256={str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()})
            summary['variants'][name] = variant
            binary = build / ('check_' + name)
            command('compile_' + name, [old['compiler'], '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                                        '-DOUTER_EXTENDED=' + str(int(extended)), source / 'diagnostics/check_outer_accumulation.cpp',
                                        '-lstdc++fs', '-o', binary])
            variant['control_binary_sha256'] = sha(binary)
            control_out = out / 'controls' / name
            control_out.mkdir(parents=True)
            command('controls_' + name, [binary, out / 'inputs/initial_grid.csv', out / 'inputs/failed_search_directions.csv',
                                         out / 'inputs/failed_search_trials.csv', out / 'inputs/failed_search_decisions.csv', control_out])
            checks = rows(control_out / 'checks.csv')
            need(len(checks) == 91 and all(row['passed'] == '1' for row in checks), 'Failed/incomplete component controls')
            variant['checks_passed'] = len(checks)
            native = rows(control_out / 'native_actions.csv')
            need(len(native) == 25 and [int(r['trial_index']) for r in native] == list(range(-1, 24)), 'Incomplete native controls')
            for table in ('checks.csv', 'native_actions.csv'):
                save(control_out / (table + '.identifiers.json'), dict(file=table, file_sha256=sha(control_out / table),
                     native_context=old['native_context'], identified_ray_sha256=sha(out / 'inputs/identified_ray.csv'),
                     scope='Native action controls refer to original pair3426; invented_* checks use only stated invented homogeneous geometry',
                     join_basis='run_id/observation_index/trial_index for native_actions; native_* check suffix is the trial index'))
        for name, digest in pins.items():
            need(sha(ROOT / name) == digest, 'Input changed during controls: ' + name)
        for name, variant in summary['variants'].items():
            for path, digest in variant['source_sha256'].items():
                need(sha(out / 'source' / name / path) == digest, 'Frozen variant source changed')
        summary.update(status='passed_controls', total_checks=182, ray_traces=0,
                       limitations=['Original segments, source/model derivatives, optimizer, Armijo condition, stopping and update budget are unchanged.',
                                    'Only the path_eval outer accumulator uses long double in the candidate; its public return remains double.',
                                    'Controls establish saved-path action/gradient behavior, not convergence of a newly optimized ray.',
                                    'The original failed ray and reviewed neutral replay are retained as the before-change evidence.'])
    except BaseException as error:
        summary.update(status='failed', failure=repr(error))
        raise
    finally:
        summary['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        summary['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()
                                     and p.name not in ('controls_summary.json', 'controls_summary.json.new')}
        save(out / 'controls_summary.json', summary)
    print(str(out / 'controls_summary.json'), flush=True)


if __name__ == '__main__':
    main()
