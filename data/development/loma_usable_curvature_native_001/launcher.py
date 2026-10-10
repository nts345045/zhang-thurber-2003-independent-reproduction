#!/usr/bin/env python3
"""Freeze and replay the reviewed isolated usable-curvature diagnostic."""
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


def group_members(pgid):
    members = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                members.append(int(path.parent.name))
        except (OSError, ValueError, IndexError):
            pass
    return members


def prepare(args, out):
    controls, baseline, build = [local(v) for v in (args.controls, args.baseline, args.build)]
    for a in (out, build):
        need(not a.exists(), 'Fresh output/build required')
        for b in (controls, baseline, build if a == out else out):
            need(a != b and a not in b.parents and b not in a.parents, 'Disjoint paths required')
    tests, tests_review, tests_ledger, helper_review = [load(controls / n) for n in
        ('summary.json', 'review.json', 'execution.json', 'helper_source_review.json')]
    native, native_review, native_ledger = [load(baseline / n) for n in ('summary.json', 'review.json', 'execution.json')]
    need(tests['status'] == tests_review['status'] == 'passed' and
         tests_review['summary_sha256'] == sha(controls / 'summary.json'), 'Missing/stale invented control review')
    need(tests_ledger['status'] == 'completed' and tests_ledger['return_code'] == 0 and
         helper_review['status'] == 'passed' and helper_review['summary_sha256'] == sha(controls / 'summary.json') and
         helper_review['execution_sha256'] == sha(controls / 'execution.json'), 'Missing/stale terminal helper review')
    need(native['status'] == 'completed_positive_curvature_diagnostic' and native_review['status'] == 'passed' and
         native_review['summary_sha256'] == sha(baseline / 'summary.json') and
         native_ledger['status'] == 'completed' and native_ledger['return_code'] == 0 and
         native_ledger['summary_sha256'] == sha(baseline / 'summary.json'), 'Missing/stale terminal C review')
    need(native['observed_paths_and_arrays_match_unobserved_variant'], 'C observation neutrality missing')
    need((native['path_spacing_km'], native['field_spacing_km'], native['maximum_updates'], native['threads']) ==
         (.03125, .125, 1000, 1), 'Changed C settings')
    need((native['time_limit_s'], native['source_vector_limit_s_per_km']) == (2.5e-5, 3e-6), 'Changed accuracy limits')
    pins = {}

    def pin(path, expected=None):
        actual = sha(path)
        need(expected is None or actual == expected, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = actual

    for name, digest in tests['input_sha256'].items():
        pin(local(name), digest)
    for name, digest in tests['source_sha256'].items():
        pin(local(name), digest)
    for name, digest in tests['output_sha256'].items():
        pin(controls / name, digest)
    for name, digest in native['input_sha256'].items():
        pin(local(name), digest)
    for name, digest in native['output_sha256'].items():
        pin(baseline / name, digest)
    for directory in (controls, baseline):
        for name in ('summary.json', 'review.json', 'execution.json'):
            pin(directory / name)
    pin(controls / 'helper_source_review.json')
    pin(baseline / 'controller_completion.json')
    pin(Path(__file__).resolve())
    source = controls / 'source/D'
    prefix = str(source.relative_to(ROOT)) + '/'
    expected_source = {name[len(prefix):]: digest for name, digest in tests['source_sha256'].items()
                       if name.startswith(prefix)}
    need(len(expected_source) == 21 and set(expected_source) ==
         {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}, 'Source inventory mismatch')
    baseline_source = native['source_sha256']
    need(len(baseline_source) == 20 and set(expected_source) - set(baseline_source) ==
         {'diagnostics/usable_ray_curvature.hpp'} and not set(baseline_source) - set(expected_source), 'Unexpected source roster')
    changed = set()
    for name, digest in expected_source.items():
        pin(source / name, digest)
        if name in baseline_source:
            pin(baseline / 'source' / name, baseline_source[name])
            need(sha(controls / 'source/C' / name) == baseline_source[name], 'Invented C differs from native C')
            if digest != baseline_source[name]:
                changed.add(name)
    need(changed == {'src/core.hpp', 'diagnostics/observed_optimizer.hpp'}, 'Unexpected C/D change')
    need(tests['prepared_sha256'] == 'eff5bffcb2f37e38e6bc646bc5aa425201b30b93de542ec8430ec2e1b341f524',
         'Unexpected reviewed source preparation')
    source_plan = ROOT / 'data/development/usable_ray_curvature_prepared_001'
    need(sha(source_plan / 'prepared.json') == tests['prepared_sha256'], 'Source plan changed')
    source_manifest = load(source_plan / 'prepared.json')
    for name, digest in expected_source.items():
        need(source_manifest['source_sha256']['D/' + name] == digest, 'Candidate source differs from reviewed preparation')
    need(sha(Path(native['compiler'])) == native['compiler_sha256'] == tests['compiler_sha256'], 'Compiler changed')
    context = native['native_context']
    need(len(context) == 199 and rows(baseline / 'identified_ray.csv') == [context], 'Native context differs')
    for name in ('curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        sidecar = load(baseline / 'inputs' / (name + '.identifiers.json'))
        need(sidecar['file_sha256'] == sha(baseline / 'inputs' / name) and sidecar['native_context'] == context and
             sidecar['context_sha256'] == sha(baseline / 'identified_ray.csv'), 'Saved seed identity/hash mismatch')
    expected = {name: sha(baseline / name) for name in TABLES}
    need(expected == native_review['diagnostic_C_table_sha256'], 'Reviewed C tables changed')
    out.mkdir(parents=True); build.mkdir(parents=True)
    shutil.copytree(str(source), str(out / 'source'))
    shutil.copytree(str(baseline / 'inputs'), str(out / 'inputs'))
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'launcher.py'))
    shutil.copyfile(str(baseline / 'identified_ray.csv'), str(out / 'identified_ray.csv'))
    for directory, label in ((controls, 'usable_controls'), (baseline, 'positive_C')):
        for name in ('summary.json', 'review.json', 'execution.json'):
            shutil.copyfile(str(directory / name), str(out / 'inputs' / (label + '_' + name)))
    for name in ('core.hpp.diff', 'observed_optimizer.hpp.diff'):
        pin(source_plan / name, source_manifest['source_sha256'][name])
        shutil.copyfile(str(source_plan / name), str(out / name))
    result = dict(status='prepared_usable_curvature_diagnostic', prepared_utc=utc(), native_context=context,
        input_sha256=pins, source_sha256=expected_source, launcher_sha256=sha(Path(__file__).resolve()),
        compiler=native['compiler'], compiler_sha256=native['compiler_sha256'], build=str(build.relative_to(ROOT)),
        path_spacing_km=.03125, field_spacing_km=.125, maximum_updates=1000, threads=1,
        expected_old_table_sha256=expected, time_limit_s=2.5e-5, source_vector_limit_s_per_km=3e-6,
        candidate_basis='Same full raw Candidate and metadata used in reviewed C; original trace performs unchanged resampling; no FMM field is constructed',
        baseline_directory=str(baseline.relative_to(ROOT)), baseline_review_sha256=sha(baseline / 'review.json'),
        baseline_retention_predicate='sy > 0', diagnostic_retention_predicate='finite positive computed sy and reciprocal; usable current-metric two-loop arithmetic',
        inherited_action_accumulator='long double outer sum, returning double, from baseline C',
        exact_curvature_sign_claimed=False, production_adoption=False, baseline_results=native['results'])
    result['prepared_file_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'prepared.json', result)
    print(str(out / 'prepared.json'), flush=True)


def run(out):
    prepared, review = load(out / 'prepared.json'), load(out / 'prelaunch_review.json')
    need(prepared['status'] == 'prepared_usable_curvature_diagnostic' and review['status'] == 'passed' and
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
        command('observe', [binary, out / 'inputs/initial_grid.csv', out / 'identified_ray.csv', out, '1000', '0.03125', '0.125',
                            out / 'inputs/curvature_initialization.csv', out / 'inputs/curvature_seed_metadata.csv'])
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
                                    diagnostic_local_convergence_flag=result['converged'], final_history=trace[-1],
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
        summary.update(status='completed_usable_curvature_diagnostic', results=values, continuous_reference_comparison=comparisons,
                       selected_run_id=min(values, key=lambda r: float(r['time_s']))['run_id'],
                       observed_paths_and_arrays_match_unobserved_variant=True,
                       baseline_table_equalities={name: sha(out / name) == digest for name, digest in prepared['expected_old_table_sha256'].items()},
                       production_adoption=False, scientific_success=False,
                       limitations=['Shared usable-curvature helper changes admission and checks current-metric two-loop arithmetic in actual/observed C source only.',
                                    'Same C long-double outer action sum, gradients, raw saved seed, resampling, Armijo, stopping and 1000-update budget.',
                                    'Every C numerical table is compared by full byte hash; differences, if any, remain explicit and are not relabeled neutral.',
                                    'Positive finite computed curvature is not an exact-sign or informative-curvature certificate; cancellation can change the sign.',
                                    'Unusable memory uses the existing cone fallback; an unusable fallback preserves its exception, with no accepted/converged Ray.',
                                    'Native completion or local stopping does not establish global first arrival, general convergence, production adoption or inversion readiness.'])
        summary['native_C_neutrality_pass'] = all(summary['baseline_table_equalities'].values())
        execution.update(status='completed', return_code=0)
    except BaseException as error:
        if child is not None:
            for sig, seconds in ((signal.SIGTERM, 2), (signal.SIGKILL, 5)):
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + seconds
                while group_members(child.pid) and time.monotonic() < deadline:
                    time.sleep(.1)
                if not group_members(child.pid):
                    break
            survivors = group_members(child.pid)
            execution['exception_child'] = dict(pid=child.pid, live_group_survivors=survivors,
                return_code=child.poll() if survivors else child.wait())
        summary.update(status='failed', failure=repr(error))
        execution.update(status='interrupted' if isinstance(error, InterruptedError) else 'failed', failure=repr(error))
        raise
    finally:
        summary['finished_utc'] = utc()
        alive = execution.get('exception_child', {}).get('live_group_survivors', [])
        summary['output_sha256'] = {} if alive else {str(p.relative_to(out)): sha(p)
            for p in out.rglob('*') if p.is_file() and not (p.parent == out and
            p.name in ('summary.json', 'summary.json.new', 'execution.json', 'execution.json.new'))}
        summary['partial_hashes_withheld_live_descendants'] = bool(alive)
        save(out / 'summary.json', summary)
        execution.update(finished_utc=utc(), summary_sha256=sha(out / 'summary.json'))
        save(out / 'execution.json', execution)
    print(str(out / 'summary.json'), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('prepare', 'run'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--controls', default='data/development/usable_ray_curvature_controls_001')
    parser.add_argument('--build')
    parser.add_argument('--baseline', default='data/development/loma_positive_curvature_native_001')
    args = parser.parse_args()
    os.chdir(str(ROOT)); out = local(args.output)
    if args.phase == 'prepare':
        need(args.build, 'Fresh build required')
        prepare(args, out)
    else:
        run(out)


if __name__ == '__main__':
    main()
