#!/usr/bin/env python3
"""Freeze and run the reviewed one-declaration accumulator experiment."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TABLES = ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def local(value):
    path = (ROOT / value).resolve()
    path.relative_to(ROOT)
    need(path != ROOT, 'Repository root is not a data/build path')
    return path


def rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as stream:
        return list(csv.DictReader(stream))


def prepare(args, out):
    controls, reference, build = [local(value) for value in (args.controls, args.reference, args.build)]
    for a in (out, build):
        need(not a.exists(), 'Fresh output/build required')
        for b in (controls, reference, build if a == out else out):
            need(a != b and a not in b.parents and b not in a.parents, 'Disjoint paths required')
    control, review = load(controls / 'controls_summary.json'), load(controls / 'controls_review.json')
    need(control['status'] == 'passed_controls' and control['total_checks'] == 182 and control['ray_traces'] == 0,
         'Require complete no-trace controls')
    need(review['status'] == 'passed' and review['controls_summary_sha256'] == sha(controls / 'controls_summary.json'),
         'Missing/stale controls review')
    need((control['path_spacing_km'], control['field_spacing_km'], control['maximum_updates'], control['threads']) ==
         (.03125, .125, 1000, 1), 'Unexpected experiment settings')
    pins = {}

    def pin(path, expected=None):
        actual = sha(path)
        need(expected is None or expected == actual, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = actual

    for name, digest in control['input_sha256'].items():
        pin(local(name), digest)
    for name, digest in control['artifact_sha256'].items():
        pin(controls / name, digest)
    for name in ('controls_summary.json', 'controls_review.json'):
        pin(controls / name)
    pin(Path(__file__).resolve())
    need(sha(Path(control['compiler'])) == control['compiler_sha256'], 'Original compiler changed')
    assessment, audit, ledger = [load(reference / name) for name in ('summary.json', 'review.json', 'execution.json')]
    need(assessment['status'] == 'comparison_complete' and audit['status'] == 'passed' and ledger['status'] == 'completed',
         'Reference comparison/review not complete')
    need(audit['summary_sha256'] == ledger['summary_sha256'] == sha(reference / 'summary.json') and
         audit['execution_sha256'] == sha(reference / 'execution.json'), 'Stale reference review/ledger')
    for name in ('summary.json', 'review.json', 'execution.json'):
        pin(reference / name)
    for name, digest in assessment['output_sha256'].items():
        pin(reference / name, digest)
    candidates = [r for r in rows(reference / 'comparison.csv.gz') if r['comparison_row'] == '3426']
    need(len(candidates) == 1, 'Ambiguous reference row')
    exact = candidates[0]
    context = control['native_context']
    need(exact['reference_eligible'] == '1' and exact['reference_candidate_count'] == '1', 'Ineligible reference')
    for key in ('event', 'station', 'source_event_resource_id', 'source_origin_resource_id'):
        need(exact[key] == context[key], 'Wrong native reference identity: ' + key)
    for key, value in exact.items():
        if key.startswith('receiver_') and key in context and key not in ('receiver_x', 'receiver_y', 'receiver_z'):
            need(value == context[key], 'Wrong receiver reference metadata: ' + key)
    for prefix in ('source', 'receiver'):
        for axis in 'xyz':
            need(float(exact['reference_' + prefix + '_' + axis]) == float(context[prefix + '_' + axis + '_km']),
                 'Reference geometry differs')
    need((assessment['time_limit_s'], assessment['source_euclidean_norm_limit_s_per_km']) == (2.5e-5, 3e-6),
         'Changed accuracy gates')
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    shutil.copytree(str(controls / 'source/outer_extended'), str(out / 'source'))
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'launcher.py'))
    (out / 'inputs').mkdir()
    for name in ('initial_grid.csv', 'identified_ray.csv', 'original_observer_summary.json', 'neutral_replay_summary.json'):
        shutil.copyfile(str(controls / 'inputs' / name), str(out / 'inputs' / name))
    for name in ('controls_summary.json', 'controls_review.json', 'single_change.diff'):
        shutil.copyfile(str(controls / name), str(out / 'inputs' / name))
    for name in ('summary.json', 'review.json', 'execution.json'):
        shutil.copyfile(str(reference / name), str(out / 'inputs' / ('reference_' + name)))
    save(out / 'inputs/reference_row.json', exact)
    shutil.copyfile(str(out / 'inputs/identified_ray.csv'), str(out / 'identified_ray.csv'))
    need(rows(out / 'identified_ray.csv') == [context], 'Copied identity differs')
    variant = control['variants']['outer_extended']['source_sha256']
    for name, digest in variant.items():
        need(sha(out / 'source' / name) == digest, 'Candidate source copy changed')
    prepared = dict(status='prepared_for_single_change_replay', prepared_utc=utc(), input_sha256=pins,
                    native_context=context, source_sha256=variant, launcher_sha256=sha(Path(__file__).resolve()),
                    compiler=control['compiler'], compiler_sha256=control['compiler_sha256'],
                    build=str(build.relative_to(ROOT)), path_spacing_km=.03125, field_spacing_km=.125,
                    maximum_updates=1000, threads=1, time_limit_s=2.5e-5, source_vector_limit_s_per_km=3e-6,
                    original_results=load(out / 'inputs/original_observer_summary.json')['results'])
    prepared['prepared_file_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'prepared.json', prepared)
    print(str(out / 'prepared.json'), flush=True)


def run(out):
    prepared, review = load(out / 'prepared.json'), load(out / 'prelaunch_review.json')
    need(prepared['status'] == 'prepared_for_single_change_replay' and review['status'] == 'passed' and
         review['prepared_sha256'] == sha(out / 'prepared.json') and
         review['launcher_sha256'] == prepared['launcher_sha256'] == sha(Path(__file__).resolve()), 'Stale launch review')

    def verify():
        for name, digest in prepared['input_sha256'].items():
            need(sha(local(name)) == digest, 'Changed original input: ' + name)
        for name, digest in prepared['prepared_file_sha256'].items():
            need(sha(out / name) == digest, 'Changed frozen input: ' + name)
        need(sha(Path(prepared['compiler'])) == prepared['compiler_sha256'], 'Compiler changed')

    verify()
    with os.fdopen(os.open(str(out / 'execution.lock'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), 'w') as stream:
        stream.write(str(os.getpid()) + '\n')
    summary = dict(prepared)
    summary.update(status='running', started_utc=utc(), driver_pid=os.getpid(), commands=[],
                   prepared_sha256=sha(out / 'prepared.json'), prelaunch_review_sha256=sha(out / 'prelaunch_review.json'))
    execution = dict(status='running', pid=os.getpid(), started_utc=utc())
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
            save(out / 'execution.json', execution)
            code = child.wait()
        record.update(status='completed', return_code=code, finished_utc=utc())
        child = None
        save(out / 'summary.json', summary)
        need(code == 0, stage + ' failed')

    try:
        binary = local(prepared['build']) / 'observe'
        command('compile', [prepared['compiler'], '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                            '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC',
                            out / 'source/diagnostics/check_ray_stopping.cpp', '-lstdc++fs', '-o', binary])
        summary['binary_sha256'] = sha(binary)
        command('runtime_libraries', ['ldd', binary])
        libraries = {}
        for line in (out / 'runtime_libraries_stdout.log').read_text().splitlines():
            for token in line.split():
                if token.startswith('/') and Path(token).is_file():
                    libraries[token] = sha(Path(token))
        summary['runtime_library_sha256'] = libraries
        command('observe', [binary, out / 'inputs/initial_grid.csv', out / 'identified_ray.csv', out, '1000', '0.03125', '0.125'])
        values, history, paths = [rows(out / name) for name in ('results.csv', 'history.csv', 'paths.csv')]
        need(len(values) == 2 and {r['initialization'] for r in values} == {'straight', 'fmm'} and
             all(r['logged_matches_unobserved_variant'] == '1' for r in values), 'Same-variant observation neutrality failed')
        exact = load(out / 'inputs/reference_row.json')
        grid = rows(out / 'inputs/initial_grid.csv')
        bounds = {axis: (min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)) for axis in 'xyz'}
        comparisons = []
        for result in values:
            need(result['observation_index'] == '3426' and result['max_updates'] == '1000' and
                 float(result['path_spacing_km']) == .03125, 'Wrong native run/settings')
            need(all(math.isfinite(float(result[key])) for key in
                     ('time_s', 'projected_gradient', 'raw_gradient', 'source_dx', 'source_dy', 'source_dz')), 'Nonfinite result')
            path = [r for r in paths if r['run_id'] == result['run_id']]
            need(len(path) == int(result['path_nodes']) and [int(r['node']) for r in path] == list(range(len(path))),
                 'Incomplete/unsorted path')
            need(all(r['observation_index'] == '3426' and all(bounds[a][0] <= float(r[a]) <= bounds[a][1] for a in 'xyz')
                     for r in path), 'Wrong native identity/nonfinite/outside path')
            for endpoint, prefix in ((path[0], 'source'), (path[-1], 'receiver')):
                need(all(float(endpoint[a]) == float(exact['reference_' + prefix + '_' + a]) for a in 'xyz'), 'Endpoint changed')
            trace = [r for r in history if r['run_id'] == result['run_id']]
            need(trace and all(r['observation_index'] == '3426' for r in trace), 'History identity mismatch')
            time_error = float(result['time_s']) - float(exact['reference_time_s'])
            source_error = math.sqrt(sum((float(result['source_d' + a]) - float(exact['reference_source_d' + a + '_s_per_km'])) ** 2
                                         for a in 'xyz'))
            comparisons.append(dict(run_id=result['run_id'], native_context=prepared['native_context'],
                                    time_error_s=time_error, source_error_euclidean_norm_s_per_km=source_error,
                                    time_limit_pass=abs(time_error) <= prepared['time_limit_s'],
                                    source_limit_pass=source_error <= prepared['source_vector_limit_s_per_km'],
                                    original_local_convergence_flag=result['converged'], final_history=trace[-1],
                                    accepted_curvature_pairs=sum(int(r['curvature_pair_accepted']) for r in trace)))
        for name in TABLES:
            table = rows(out / name)
            need(all(r['observation_index'] == '3426' and r['run_id'] in {v['run_id'] for v in values} for r in table),
                 'Native output table join changed: ' + name)
            save(out / (name + '.identifiers.json'), dict(file=name, file_sha256=sha(out / name), join_key='observation_index',
                 join_value='3426', native_context=prepared['native_context'], context_csv='identified_ray.csv',
                 context_sha256=sha(out / 'identified_ray.csv'),
                 basis='Synthetic initial geometry retains provider event/origin/channel identities; no observed pick is invented'))
        verify()
        summary.update(status='completed_single_change_diagnostic', results=values, continuous_reference_comparison=comparisons,
                       selected_run_id=min(values, key=lambda r: float(r['time_s']))['run_id'],
                       observed_paths_and_arrays_match_unobserved_variant=True,
                       original_before_change_evidence_preserved=True,
                       limitations=['Only the path_eval accumulator changed from double to long double; return remains double.',
                                    'Original segments, gradient, seeds, resampling, Armijo, stopping and 1000-update budget are unchanged.',
                                    'The before-change A ray is the already reviewed original observer and neutral replay; it is not rerun here.',
                                    'All local flags are recorded without relabeling; diagnostic completion is not scientific acceptance.',
                                    'One native ray cannot establish general convergence, global branch completeness or inversion readiness.'])
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
    parser.add_argument('--controls')
    parser.add_argument('--reference')
    parser.add_argument('--build')
    args = parser.parse_args()
    os.chdir(str(ROOT))
    out = local(args.output)
    if args.phase == 'prepare':
        need(all((args.controls, args.reference, args.build)), 'Preparation requires controls, reference and build')
        prepare(args, out)
    else:
        run(out)


if __name__ == '__main__':
    main()
