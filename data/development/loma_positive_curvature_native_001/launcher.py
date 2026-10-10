#!/usr/bin/env python3
"""Freeze the reviewed isolated positive-curvature retention experiment."""
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
    controls, capture, build = [local(v) for v in (args.controls, args.capture, args.build)]
    baseline = local(args.baseline)
    for a in (out, build):
        need(not a.exists(), 'Fresh output/build required')
        for b in (controls, capture, baseline, build if a == out else out):
            need(a != b and a not in b.parents and b not in a.parents, 'Disjoint paths required')
    tests, tests_review = [load(controls / n) for n in ('summary.json', 'review.json')]
    native, native_review = [load(capture / n) for n in ('summary.json', 'review.json')]
    need(tests['status'] == tests_review['status'] == 'passed' and
         tests_review['summary_sha256'] == sha(controls / 'summary.json'), 'Missing/stale invented control review')
    need(native['status'] == 'completed_neutral_curvature_capture' and native_review['status'] == 'passed_saved_capture_review' and
         native_review['summary_sha256'] == sha(capture / 'summary.json'), 'Missing/stale native capture review')
    need(native['old_tables_byte_identical'] and native['observed_paths_and_arrays_match_unobserved_variant'],
         'Capture did not preserve original B outputs')
    need((native['path_spacing_km'], native['field_spacing_km'], native['maximum_updates'], native['threads']) ==
         (.03125, .125, 1000, 1), 'Changed B settings')
    pins = {}

    def pin(path, expected=None):
        actual = sha(path)
        need(expected is None or actual == expected, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = actual

    for name, digest in tests['input_sha256'].items():
        pin(local(name), digest)
    for name, digest in tests['output_sha256'].items():
        pin(controls / name, digest)
    for name, digest in native['input_sha256'].items():
        pin(local(name), digest)
    for name, digest in native['output_sha256'].items():
        pin(capture / name, digest)
    for directory in (controls, capture):
        for name in ('summary.json', 'review.json', 'execution.json'):
            pin(directory / name)
    for name in ('controller_completion.json', 'packaging_receipt.json'):
        pin(capture / name)
    pin(Path(__file__).resolve())
    b_summary, b_review, b_ledger = [load(baseline / n) for n in ('summary.json', 'review.json', 'execution.json')]
    need(b_summary['status'] == 'completed_seed_loaded_B_neutrality' and b_review['status'] == 'passed' and
         b_review['summary_sha256'] == sha(baseline / 'summary.json') and b_ledger['status'] == 'completed' and
         b_ledger['return_code'] == 0 and b_summary['original_five_tables_byte_identical'], 'Missing reviewed seed-loaded B parity')
    need(b_summary['native_context'] == native['native_context'], 'B/capture native context differs')
    for name in ('summary.json', 'review.json', 'execution.json', 'prepared.json', 'controller_completion.json'):
        pin(baseline / name)
    for name, digest in b_summary['output_sha256'].items():
        pin(baseline / name, digest)
    for name in TABLES:
        need(sha(baseline / name) == native['expected_old_table_sha256'][name], 'B original-table parity changed')
    source = controls / 'source/positive_curvature'
    expected_source = {name[len('positive_curvature/'):]: digest for name, digest in tests['source_sha256'].items()
                       if name.startswith('positive_curvature/')}
    need(expected_source and set(expected_source) ==
         {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}, 'Source inventory mismatch')
    for name, digest in expected_source.items():
        pin(source / name, digest)
    for name in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp'):
        before = (baseline / 'source' / name).read_text()
        after = (source / name).read_text()
        marker = '      if (sy > 1e-14) {'
        need(before.count(marker) == 1 and after == before.replace(marker, '      if (sy > 0) {', 1),
             'Not exactly the reviewed one-literal retention change: ' + name)
    for name in expected_source:
        if name not in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp', 'diagnostics/extracted_retention.hpp'):
            need(sha(source / name) == sha(baseline / 'source' / name), 'Other source changed: ' + name)
    need(sha(Path(native['compiler'])) == native['compiler_sha256'], 'Compiler changed')
    context = native['native_context']
    need(rows(capture / 'identified_ray.csv') == [context], 'Native context differs')
    for name in ('curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        sidecar = load(capture / (name + '.identifiers.json'))
        need(sidecar['file_sha256'] == sha(capture / name) and sidecar['native_context'] == context and
             sidecar['context_sha256'] == sha(capture / 'identified_ray.csv'), 'Saved seed identity/hash mismatch')
    out.mkdir(parents=True); build.mkdir(parents=True)
    shutil.copytree(str(source), str(out / 'source'))
    shutil.copytree(str(capture / 'inputs'), str(out / 'inputs'))
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'launcher.py'))
    shutil.copyfile(str(capture / 'identified_ray.csv'), str(out / 'identified_ray.csv'))
    for name in ('curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        for suffix in ('', '.identifiers.json'):
            shutil.copyfile(str(capture / (name + suffix)), str(out / 'inputs' / (name + suffix)))
    for directory, label in ((controls, 'controls'), (capture, 'capture'), (baseline, 'seed_loaded_B')):
        for name in ('summary.json', 'review.json', 'execution.json'):
            shutil.copyfile(str(directory / name), str(out / 'inputs' / (label + '_' + name)))
    prepared_source = ROOT / 'data/development/seeded_retention_prepared_001'
    pin(prepared_source / 'seed_loader_driver.diff')
    shutil.copyfile(str(prepared_source / 'seed_loader_driver.diff'), str(out / 'seed_loader_driver.diff'))
    for name in ('core.hpp.retention.diff', 'observed_optimizer.hpp.retention.diff'):
        pin(prepared_source / name)
        shutil.copyfile(str(prepared_source / name), str(out / name))
    expected = {name: sha(capture / name) for name in TABLES}
    need(expected == native['expected_old_table_sha256'], 'Original B outputs differ from neutral capture')
    result = dict(status='prepared_positive_curvature_diagnostic', prepared_utc=utc(), native_context=context,
        input_sha256=pins, source_sha256=expected_source, launcher_sha256=sha(Path(__file__).resolve()),
        compiler=native['compiler'], compiler_sha256=native['compiler_sha256'], build=str(build.relative_to(ROOT)),
        path_spacing_km=.03125, field_spacing_km=.125, maximum_updates=1000, threads=1,
        expected_old_table_sha256=expected, time_limit_s=2.5e-5, source_vector_limit_s_per_km=3e-6,
        candidate_basis='Full raw Candidate and metadata from reviewed neutral B capture; original trace performs its unchanged resampling',
        baseline_retention_predicate='sy > 1e-14', diagnostic_retention_predicate='sy > 0',
        seed_loaded_B_directory=str(baseline.relative_to(ROOT)), seed_loaded_B_review_sha256=sha(baseline / 'review.json'),
        safe_general_retention_rule_claimed=False, baseline_results=b_summary['results'])
    result['prepared_file_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'prepared.json', result)
    print(str(out / 'prepared.json'), flush=True)


def run(out):
    prepared, review = load(out / 'prepared.json'), load(out / 'prelaunch_review.json')
    need(prepared['status'] == 'prepared_positive_curvature_diagnostic' and review['status'] == 'passed' and
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
        summary.update(status='completed_positive_curvature_diagnostic', results=values, continuous_reference_comparison=comparisons,
                       selected_run_id=min(values, key=lambda r: float(r['time_s']))['run_id'],
                       observed_paths_and_arrays_match_unobserved_variant=True,
                       baseline_table_equalities={name: sha(out / name) == digest for name, digest in prepared['expected_old_table_sha256'].items()},
                       production_adoption=False, scientific_success=False,
                       limitations=['Only two retention literals in actual/observed trace changed from sy>1e-14 to sy>0.',
                                    'Same B outer action sum, gradients, raw saved seed, resampling, Armijo, stopping and1000-update budget.',
                                    'Seed loading separately preserves all five original B tables byte-for-byte.',
                                    'Positive curvature alone is unsafe generally: invented controls preserve subnormal reciprocal overflow and positive infinity admission.',
                                    'Native completion or local stopping does not establish informative curvature, global first arrival, general convergence or inversion readiness.'])
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
    parser.add_argument('--controls', default='data/development/seeded_retention_controls_001')
    parser.add_argument('--capture', default='data/development/loma_curvature_capture_native_001')
    parser.add_argument('--build')
    parser.add_argument('--baseline', default='data/development/loma_seed_loaded_b_native_001')
    args = parser.parse_args()
    os.chdir(str(ROOT)); out = local(args.output)
    if args.phase == 'prepare':
        need(args.build, 'Fresh build required')
        prepare(args, out)
    else:
        run(out)


if __name__ == '__main__':
    main()
