#!/usr/bin/env python3
"""Replay the unchanged B optimizer with reviewed, observational curvature hooks."""
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
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OLD_TABLES = ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')
NEW_TABLES = ('curvature_pairs.csv', 'curvature_components.csv.gz', 'curvature_selected_geometry.csv',
              'curvature_selected_cuts.csv', 'curvature_initialization.csv', 'curvature_seed_metadata.csv',
              'curvature_memory_events.csv')


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


def records(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as stream:
        for row in csv.DictReader(stream):
            yield row


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
    controls, rational, build = [local(v) for v in (args.controls, args.rational_controls, args.build)]
    for a in (out, build):
        need(not a.exists(), 'Fresh output/build required')
        for b in (controls, rational, build if a == out else out):
            need(a != b and a not in b.parents and b not in a.parents, 'Disjoint paths required')
    prepared = load(controls / 'prepared.json')
    control, review = load(controls / 'controls_summary.json'), load(controls / 'controls_review.json')
    need(control['status'] == 'passed' and control['prepared_sha256'] == sha(controls / 'prepared.json'),
         'Missing/stale capture controls')
    need(review['status'] == 'passed' and review['controls_summary_sha256'] == sha(controls / 'controls_summary.json'),
         'Missing/stale capture review')
    rational_summary, rational_review = load(rational / 'summary.json'), load(rational / 'review.json')
    need(rational_summary['status'] == 'passed' and rational_review['status'] == 'passed' and
         rational_review['summary_sha256'] == sha(rational / 'summary.json'), 'Missing/stale rational review')
    need((prepared['path_spacing_km'], prepared['field_spacing_km'], prepared['maximum_updates'], prepared['threads']) ==
         (.03125, .125, 1000, 1), 'Changed frozen B settings')
    pins = dict(prepared['input_sha256'])

    def pin(path, expected=None):
        actual = sha(path)
        need(expected is None or actual == expected, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = actual

    for name, digest in control['source_sha256'].items():
        pin(local(name), digest)
    for name, digest in control['output_sha256'].items():
        pin(controls / name, digest)
    for name, digest in rational_summary['source_sha256'].items():
        pin(local(name), digest)
    for name, digest in rational_summary['output_sha256'].items():
        pin(rational / name, digest)
    for name, digest in prepared['prepared_file_sha256'].items():
        pin(controls / name, digest)
    for directory in (controls, rational):
        for path in directory.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                pin(path)
    for name, digest in pins.items():
        need(sha(local(name)) == digest, 'Changed original input: ' + name)
    helper = ROOT / 'diagnostics/reconstruct_curvature_capture.py'
    need(sha(helper) == sha(rational / 'source/reconstruct_curvature_capture.py'), 'Rational helper differs from controls')
    for path in (helper, Path(__file__).resolve()):
        pin(path)
    need(sha(Path(prepared['compiler'])) == prepared['compiler_sha256'], 'Original compiler changed')
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    for directory in ('source', 'inputs'):
        shutil.copytree(str(controls / directory), str(out / directory))
    shutil.copyfile(str(helper), str(out / 'source/diagnostics/reconstruct_curvature_capture.py'))
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'launcher.py'))
    for name in ('identified_ray.csv', 'observed_optimizer.hpp.diff', 'check_ray_stopping.cpp.diff'):
        shutil.copyfile(str(controls / name), str(out / name))
    for name in ('prepared.json', 'controls_summary.json', 'controls_review.json'):
        shutil.copyfile(str(controls / name), str(out / 'inputs' / ('capture_' + name)))
    for name in ('summary.json', 'review.json'):
        shutil.copyfile(str(rational / name), str(out / 'inputs' / ('rational_' + name)))
    need(list(records(out / 'identified_ray.csv')) == [prepared['native_context']], 'Copied identity changed')
    result = dict(prepared)
    result.update(status='prepared_neutral_curvature_replay', prepared_utc=utc(), input_sha256=pins,
                  build=str(build.relative_to(ROOT)), launcher_sha256=sha(Path(__file__).resolve()),
                  capture_controls_sha256=sha(controls / 'controls_summary.json'),
                  capture_review_sha256=sha(controls / 'controls_review.json'),
                  rational_controls_sha256=sha(rational / 'summary.json'),
                  rational_review_sha256=sha(rational / 'review.json'))
    result['source_sha256'] = {str(p.relative_to(out / 'source')): sha(p)
                               for p in (out / 'source').rglob('*') if p.is_file()}
    result['prepared_file_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'prepared.json', result)
    print(str(out / 'prepared.json'), flush=True)


def validate_capture(out, prepared):
    for name, digest in prepared['expected_old_table_sha256'].items():
        need(sha(out / name) == digest, 'Observation hooks changed frozen B output: ' + name)
    values = list(records(out / 'results.csv'))
    need(len(values) == 2 and all(v['logged_matches_unobserved_variant'] == '1' for v in values),
         'Observed/unobserved numerical neutrality failed')
    fmm = [v for v in values if v['initialization'] == 'fmm']
    need(len(fmm) == 1, 'Missing FMM result')
    run_id, observation = fmm[0]['run_id'], prepared['native_context']['observation_index']
    history = {int(r['iteration']): r for r in records(out / 'history.csv')
               if r['run_id'] == run_id and r['phase'] == 'accepted'}
    pairs = list(records(out / 'curvature_pairs.csv'))
    need([int(r['iteration']) for r in pairs] == sorted(history) == list(range(1000)),
         'Incomplete or changed accepted-pair inventory')
    for pair in pairs:
        row = history[int(pair['iteration'])]
        need(pair['run_id'] == run_id and pair['observation_index'] == observation and
             pair['update'] == row['updates'] and pair['retained'] == row['curvature_pair_accepted'] and
             float(pair['accepted_action_s']) == float(row['time_s']) and
             float(pair['step']) == float(row['accepted_step']) and
             int(pair['memory_after_size']) == int(row['memory_pairs']), 'Pair/history join changed')
    selected = set(prepared['selected_iterations'])
    inventory = {}
    for row in records(out / 'curvature_selected_geometry.csv'):
        key = (int(row['iteration']), row['state'])
        nodes = inventory.setdefault(key, [])
        need(int(row['node']) == len(nodes), 'Selected geometry node order changed')
        nodes.append(row)
        need(all(math.isfinite(float(row[a])) for a in 'xyz'), 'Nonfinite captured path')
    need(set(inventory) == {(i, state) for i in selected for state in ('base', 'accepted')},
         'Selected iteration/state inventory changed')
    for (iteration, state), path in inventory.items():
        need(len(path) == int(fmm[0]['path_nodes']), 'Selected path topology changed')
        for endpoint, prefix in ((path[0], 'source'), (path[-1], 'receiver')):
            need(all(float(endpoint[a]) == float(prepared['native_context'][prefix + '_' + a + '_km']) for a in 'xyz'),
                 'Captured endpoint changed')
    counts = {}
    for name in OLD_TABLES + NEW_TABLES:
        count = 0
        for row in records(out / name):
            need(row['observation_index'] == observation and
                 row['run_id'] in ({v['run_id'] for v in values} if name in OLD_TABLES else {run_id}),
                 'Native captured table identity changed: ' + name)
            count += 1
        counts[name] = count
    need(counts['curvature_seed_metadata.csv'] == 1, 'Missing/ambiguous FMM seed metadata')
    kinds = {}
    for row in records(out / 'curvature_initialization.csv'):
        kind = row['kind']
        need(kind in ('raw_fmm_seed', 'post_resampling_and_merge'), 'Unknown seed representation')
        need(int(row['node']) == kinds.get(kind, 0), 'Seed node sequence changed')
        kinds[kind] = kinds.get(kind, 0) + 1
    need(set(kinds) == {'raw_fmm_seed', 'post_resampling_and_merge'} and min(kinds.values()) >= 3,
         'Incomplete saved initialization')
    return values, counts, kinds


def run(out):
    prepared, review = load(out / 'prepared.json'), load(out / 'prelaunch_review.json')
    need(prepared['status'] == 'prepared_neutral_curvature_replay' and review['status'] == 'passed' and
         review['prepared_sha256'] == sha(out / 'prepared.json') and
         review['launcher_sha256'] == prepared['launcher_sha256'] == sha(Path(__file__).resolve()), 'Stale native launch review')

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
                                     env=dict(os.environ, OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')))
            record['pid'] = child.pid
            save(out / 'summary.json', summary)
            save(out / 'execution.json', execution)
            code = child.wait()
        record.update(status='completed', return_code=code, finished_utc=utc())
        child = None
        save(out / 'summary.json', summary)
        need(code == 0, stage + ' failed')

    try:
        build = local(prepared['build'])
        binary = build / 'observe'
        command('compile', [prepared['compiler'], '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                            '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC',
                            out / 'source/diagnostics/check_ray_stopping.cpp', '-lstdc++fs', '-o', binary])
        summary['binary_sha256'] = sha(binary)
        command('runtime_libraries', ['ldd', binary])
        summary['runtime_library_sha256'] = {token: sha(Path(token))
            for line in (out / 'runtime_libraries_stdout.log').read_text().splitlines() for token in line.split()
            if token.startswith('/') and Path(token).is_file()}
        command('observe', [binary, out / 'inputs/initial_grid.csv', out / 'identified_ray.csv', out, '1000', '0.03125', '0.125'])
        raw = out / 'curvature_components.csv'
        raw_hash, raw_bytes = sha(raw), raw.stat().st_size
        with raw.open('rb') as source, (out / 'curvature_components.csv.gz').open('wb') as destination:
            with gzip.GzipFile(filename='', mode='wb', fileobj=destination, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed, 1048576)
        restored = hashlib.sha256()
        with gzip.open(str(out / 'curvature_components.csv.gz'), 'rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                restored.update(block)
        need(restored.hexdigest() == raw_hash, 'Lossless component compression failed')
        retained_raw = build / 'curvature_components.csv'
        need(not retained_raw.exists(), 'Raw retention path already exists')
        raw.rename(retained_raw)
        summary['component_storage'] = dict(format='gzip', uncompressed_sha256=raw_hash,
            uncompressed_bytes=raw_bytes, local_retained_raw_file=str(retained_raw.relative_to(ROOT)),
            lossless_readback_verified=True)
        values, counts, kinds = validate_capture(out, prepared)
        command('exact_sums', [sys.executable, out / 'source/diagnostics/reconstruct_curvature_capture.py',
            '--pairs', out / 'curvature_pairs.csv', '--components', out / 'curvature_components.csv.gz',
            '--output', out / 'exact_sums'])
        exact = load(out / 'exact_sums/summary.json')
        need(exact['status'] == 'completed_exact_sums_of_saved_binary64_components' and exact['counts']['pairs'] == 1000,
             'Incomplete rational reconstruction')
        need(exact['counts']['rounded_dot_mismatches'] == 0, 'Recorded dot differs from reconstruction')
        for name in OLD_TABLES + NEW_TABLES + ('exact_sums/exact_sums.csv',):
            save(out / (name + '.identifiers.json'), dict(file=name, file_sha256=sha(out / name),
                join_key='observation_index', join_value='3426', native_context=prepared['native_context'],
                context_csv='identified_ray.csv', context_sha256=sha(out / 'identified_ray.csv'),
                basis='Synthetic initial geometry retains provider event/origin/channel identities; no observed pick is invented'))
        verify()
        summary.update(status='completed_neutral_curvature_capture', results=values, capture_counts=counts,
            initialization_nodes=kinds, exact_sums=exact['counts'], old_tables_byte_identical=True,
            observed_paths_and_arrays_match_unobserved_variant=True,
            limitations=['Frozen B action, gradients, optimizer, seeds, Armijo, stopping and update budget are unchanged.',
                         'The selected FMM ray remains nonconverged after 1000 updates; capture completion is not scientific acceptance.',
                         'Exact rational sums concern saved binary64 S/Y and rounded movements, not an exact continuum Hessian.',
                         'Positive sy does not establish an informative replacement pair; no retention decision is changed.',
                         'The 19 selected paths and cut predicates do not reconstruct all unexported intermediate geometry.',
                         'Recorded action-total equality does not certify an exact Fermat action equality or descent.'])
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
    parser.add_argument('--controls')
    parser.add_argument('--rational-controls')
    parser.add_argument('--build')
    args = parser.parse_args()
    os.chdir(str(ROOT))
    out = local(args.output)
    if args.phase == 'prepare':
        need(all((args.controls, args.rational_controls, args.build)), 'Preparation requires both controls and build')
        prepare(args, out)
    else:
        run(out)


if __name__ == '__main__':
    main()
