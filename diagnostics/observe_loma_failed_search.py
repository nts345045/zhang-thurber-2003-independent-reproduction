#!/usr/bin/env python3
"""Capture one frozen failed search without changing its numerical decisions."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OLD_TABLES = ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')
NEW_TABLES = ('failed_search_directions.csv', 'failed_search_trials.csv', 'failed_search_decisions.csv')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def local(value):
    path = (ROOT / value).resolve()
    path.relative_to(ROOT)
    require(path != ROOT, 'Repository root is not an artifact directory')
    return path


def replace_once(text, old, new):
    require(text.count(old) == 1, 'Frozen observation insertion point changed: ' + old)
    return text.replace(old, new, 1)


def instrument(observer, driver):
    observer = replace_once(observer, '    const double audit_feasible_step=step;\n',
                            '    const double audit_feasible_step=step;\n    capture_begin();\n')
    observer = replace_once(observer, '      if (!valid)\n        continue;\n',
                            '      if (!valid) {\n'
                            '        capture_trial(ls,step,trial,false,0,NAN,NAN,false);\n'
                            '        continue;\n      }\n')
    observer = replace_once(observer, '      newT = path_eval(g, trial);\n',
                            '      newT = path_eval(g, trial);\n'
                            '      capture_trial(ls,step,trial,true,trial_merged,newT,\n'
                            '                    T+1e-4*step*slope,newT<=T+1e-4*step*slope);\n')
    observer = replace_once(observer, '    if (!accepted) {\n',
                            '    if (!accepted) {\n'
                            '      capture_failed(iter,g,p,grad,q,T,slope,step);\n')
    driver = replace_once(driver, 'std::string audit_observation;\n',
                          'std::string audit_observation;\n#include "failed_search_capture.hpp"\n')
    driver = replace_once(driver, '  std::string out=argv[3];\n',
                          '  std::string out=argv[3];\n  capture_output=out;\n')
    return observer, driver


def prepare(args, out):
    original, controls, review, build = [local(v) for v in
                                        (args.observer, args.controls, args.controls_review, args.build)]
    for a, b in ((out, original), (out, controls), (out, build), (build, original), (build, controls)):
        require(a != b and a not in b.parents and b not in a.parents, 'Paths must be disjoint')
    require(not out.exists() and not build.exists(), 'Fresh output and build paths required')
    prior = json.loads((original / 'summary.json').read_text())
    prior_review = json.loads((original / 'review.json').read_text())
    require(prior['status'] == 'completed_with_original_flags_preserved' and
            prior['pair_index'] == 3426 and prior['observed_paths_and_arrays_match_unobserved'] and
            prior['selected_full_preflight_result_matches'], 'Require original neutral row3426 observation')
    require(prior_review['status'] == 'passed_saved_evidence_review' and
            prior_review['summary_sha256'] == sha(original / 'summary.json'), 'Original review is stale')
    tested = json.loads((controls / 'summary.json').read_text())
    checked = json.loads(review.read_text())
    require(tested['status'] == 'passed' and checked['status'] == 'passed' and
            checked['summary_sha256'] == sha(controls / 'summary.json'), 'Require hash-bound capture controls review')
    pins = {}

    def pin(path, expected=None):
        digest = sha(path)
        require(expected is None or digest == expected, 'Changed artifact: ' + str(path))
        pins[str(path.relative_to(ROOT))] = digest

    for name, digest in prior['output_sha256'].items():
        path = (original / name).resolve()
        path.relative_to(original)
        pin(path, digest)
    for name in ('summary.json', 'review.json'):
        pin(original / name)
    for name, digest in tested['source_sha256'].items():
        pin(local(name), digest)
    for name, digest in tested['artifact_sha256'].items():
        path = (controls / name).resolve()
        path.relative_to(controls)
        pin(path, digest)
    pin(controls / 'summary.json')
    pin(review)
    pin(Path(__file__).resolve())
    pin(ROOT / 'diagnostics/failed_search_capture.hpp')
    require(sha(Path(prior['compiler'])) == prior['compiler_sha256'], 'Original compiler changed')
    require((prior['path_spacing_km'], prior['field_spacing_km'], prior['maximum_updates']) ==
            (0.03125, 0.125, 1000), 'Unexpected frozen numerical settings')
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    shutil.copytree(str(original / 'source'), str(out / 'source'))
    shutil.copytree(str(original / 'inputs'), str(out / 'inputs'))
    for source, target in ((original / 'identified_ray.csv', out / 'identified_ray.csv'),
                           (original / 'summary.json', out / 'inputs/original_observer_summary.json'),
                           (original / 'review.json', out / 'inputs/original_observer_review.json'),
                           (controls / 'summary.json', out / 'inputs/capture_controls_summary.json'),
                           (review, out / 'inputs/capture_controls_review.json'),
                           (Path(__file__).resolve(), out / 'source/diagnostics/observe_loma_failed_search.py'),
                           (ROOT / 'diagnostics/failed_search_capture.hpp', out / 'source/diagnostics/failed_search_capture.hpp')):
        shutil.copyfile(str(source), str(target))
        require(sha(source) == sha(target), 'Copy changed bytes')
    observer_path = out / 'source/diagnostics/observed_optimizer.hpp'
    driver_path = out / 'source/diagnostics/check_ray_stopping.cpp'
    original_observer, original_driver = observer_path.read_text(), driver_path.read_text()
    observer, driver = instrument(original_observer, original_driver)
    for name, path, before, after in [('capture_insertion.diff', observer_path, original_observer, observer),
                                     ('capture_driver.diff', driver_path, original_driver, driver)]:
        path.write_text(after)
        (out / name).write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                          fromfile='original_observation', tofile='capture_observation')))
    require(rows(out / 'identified_ray.csv') == [prior['native_context']], 'Native context differs')
    prepared = dict(status='prepared_for_replay', created_utc=utc(), pair_index=3426,
                    scope='Observation-only replay of one frozen failed search; no method or criterion change',
                    original_observer=str(original.relative_to(ROOT)), build=str(build.relative_to(ROOT)),
                    compiler=prior['compiler'], compiler_sha256=prior['compiler_sha256'],
                    frozen_binary_sha256=prior['frozen_binary_sha256'], path_spacing_km=0.03125,
                    field_spacing_km=0.125, maximum_updates=1000, threads=1,
                    native_context=prior['native_context'], input_sha256=pins,
                    expected_old_table_sha256={n: prior['output_sha256'][n] for n in OLD_TABLES},
                    source_sha256={str(p.relative_to(out / 'source')): sha(p)
                                   for p in (out / 'source').rglob('*') if p.is_file()})
    prepared['prepared_file_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'prepared.json', prepared)
    print(str(out / 'prepared.json'), flush=True)


def run(out):
    prepared = json.loads((out / 'prepared.json').read_text())
    require(prepared['status'] == 'prepared_for_replay', 'Not a prepared replay')
    for name, digest in prepared['input_sha256'].items():
        require(sha(local(name)) == digest, 'Changed pinned input: ' + name)
    for name, digest in prepared['prepared_file_sha256'].items():
        require(sha(out / name) == digest, 'Changed prepared file: ' + name)
    require(sha(Path(prepared['compiler'])) == prepared['compiler_sha256'], 'Compiler changed')
    fd = os.open(str(out / 'execution.lock'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, 'w') as stream:
        stream.write(str(os.getpid()) + '\n')
    summary = dict(prepared)
    summary.update(status='observing', started_utc=utc(), commands=[], prepared_sha256=sha(out / 'prepared.json'))
    execution = dict(status='running', pid=os.getpid(), started_utc=utc(), prepared_sha256=summary['prepared_sha256'])
    save(out / 'summary.json', summary)
    save(out / 'execution.json', execution)
    child = None

    def interrupted(signum, frame):
        raise InterruptedError('Signal ' + str(signum))

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, interrupted)

    def command(stage, argv):
        nonlocal child
        record = dict(stage=stage, command=[str(p.relative_to(ROOT)) if isinstance(p, Path) else p for p in argv],
                      status='running', started_utc=utc())
        summary['commands'].append(record)
        with (out / (stage + '_stdout.log')).open('w') as stdout, (out / (stage + '_stderr.log')).open('w') as stderr:
            child = subprocess.Popen(record['command'], stdout=stdout, stderr=stderr, start_new_session=True,
                                     env=dict(os.environ, OMP_NUM_THREADS='1', TMPDIR=str(ROOT / 'tmp')))
            record['pid'] = child.pid
            save(out / 'summary.json', summary)
            code = child.wait()
        record.update(status='completed', return_code=code, finished_utc=utc())
        child = None
        save(out / 'summary.json', summary)
        require(code == 0, stage + ' failed')

    try:
        binary = local(prepared['build']) / 'observe'
        command('compile', [prepared['compiler'], '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                            '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC',
                            out / 'source/diagnostics/check_ray_stopping.cpp', '-lstdc++fs', '-o', binary])
        summary['binary_sha256'] = sha(binary)
        command('observe', [binary, out / 'inputs/initial_grid.csv', out / 'identified_ray.csv', out, '1000', '0.03125', '0.125'])
        for name, digest in prepared['expected_old_table_sha256'].items():
            require(sha(out / name) == digest, 'Original numerical table changed: ' + name)
        values = rows(out / 'results.csv')
        require(len(values) == 2 and all(r['logged_matches_unobserved_variant'] == '1' for r in values), 'Neutrality failed')
        decisions = rows(out / 'failed_search_decisions.csv')
        require(len(decisions) == 24 and all(r['run_id'] == 'fmm_0.031250_1000' and r['observation_index'] == '3426' and
                r['iteration'] == '53' and int(r['trial_index']) == j and r['valid'] == '1' and r['merged_nodes'] == '0' and
                r['path_nodes'] == '1134' and r['binary64_accepted'] == '0' and float(r['step']) == 2.**-j and
                float(r['post_loop_halved_step']) == 2.**-24 for j, r in enumerate(decisions)), 'Unexpected failed search inventory')
        for name in OLD_TABLES + NEW_TABLES:
            save(out / (name + '.identifiers.json'), dict(file=name, file_sha256=sha(out / name), join_key='observation_index',
                 join_value='3426', native_context=prepared['native_context'], context_csv='identified_ray.csv',
                 context_sha256=sha(out / 'identified_ray.csv'),
                 basis='Synthetic initial coordinates retain provider catalog/receiver identities; no provider pick is invented'))
        for name, digest in prepared['input_sha256'].items():
            require(sha(local(name)) == digest, 'Input changed during replay: ' + name)
        for name, digest in prepared['prepared_file_sha256'].items():
            require(sha(out / name) == digest, 'Frozen replay file changed: ' + name)
        summary.update(status='completed_with_original_flags_preserved', results=values,
                       selected_full_preflight_result_matches=True, observed_paths_and_arrays_match_unobserved=True,
                       all_five_prior_numerical_tables_byte_identical=True, recorded_failed_trials=24,
                       limitations=['One unchanged failed search; no optimizer, tolerance or convergence flag change.',
                                    'Captures actual rounded trial coordinates and binary64 decisions, not exact action certification.',
                                    'Original in-process parity and saved-table byte equality are required; no inference of failure cause.'])
        execution.update(status='completed', return_code=0)
    except BaseException as error:
        if child is not None:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
                if sig == signal.SIGTERM:
                    time.sleep(1)
            execution['exception_child'] = dict(pid=child.pid, return_code=child.wait())
        summary.update(status='failed', failure=repr(error))
        execution.update(status='interrupted' if isinstance(error, InterruptedError) else 'failed', failure=repr(error))
        raise
    finally:
        summary['finished_utc'] = utc()
        summary['output_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()
                                    and p.name not in ('summary.json', 'summary.json.new', 'execution.json', 'execution.json.new')}
        save(out / 'summary.json', summary)
        execution.update(finished_utc=utc(), summary_sha256=sha(out / 'summary.json'))
        save(out / 'execution.json', execution)
    print(str(out / 'summary.json'), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('prepare', 'run'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--observer')
    parser.add_argument('--controls')
    parser.add_argument('--controls-review')
    parser.add_argument('--build')
    args = parser.parse_args()
    os.chdir(str(ROOT))
    out = local(args.output)
    if args.phase == 'prepare':
        require(all((args.observer, args.controls, args.controls_review, args.build)), 'Prepare requires all source/control/build paths')
        prepare(args, out)
    else:
        run(out)


if __name__ == '__main__':
    main()
