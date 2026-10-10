#!/usr/bin/env python3
"""Exclusive, reviewed execution: two archived straight calls, gate, two D calls."""
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAIRS = (8670, 8674)
SAVED_INITIALIZER = ('ray_initialization_attempted', 'ray_initialization_succeeded',
                    'ray_selected_fmm_seed', 'ray_direct_seed_time', 'ray_fmm_seed_time',
                    'ray_field_time', 'ray_extraction_fallback_steps', 'ray_extraction_message')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')

def read(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))

def verify(prepared):
    for name, expected in prepared['original_sha256'].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Original input/source changed: ' + name)
    for name, expected in prepared['runtime_sha256'].items():
        if sha(name) != expected:
            raise RuntimeError('Compiler/runtime changed: ' + name)
    for name, expected in prepared['output_sha256'].items():
        if sha(HERE / name) != expected:
            raise RuntimeError('Prepared file changed: ' + name)

def inspect(variant, context):
    out = HERE / 'results' / variant
    rows = read(out / 'scalars_17.csv')
    narrow = read(out / 'scalars_12.csv')
    paths = read(out / 'paths.csv')
    partials = read(out / 'model_partials.csv')
    grid = read(HERE / 'inputs/initial_grid.csv')
    axes = {a: (min(float(r[a]) for r in grid), max(float(r[a]) for r in grid)) for a in 'xyz'}
    results = []
    if len(rows) != 2 or len(narrow) != 2:
        raise RuntimeError('Incomplete scalar rows')
    for n, pair in enumerate(PAIRS):
        row, native = rows[n], context[n]
        i, k = divmod(pair, 52)
        if (int(row['event']), int(row['station'])) != (i, k):
            raise RuntimeError('Wrong scalar ordering')
        nodes = [r for r in paths if int(r['pair_index']) == pair]
        kernels = [r for r in partials if int(r['pair_index']) == pair]
        if len(nodes) != int(row['ray_path_points']) or len(kernels) != len(grid):
            raise RuntimeError('Incomplete path or derivative arrays')
        for collection, index in [(nodes, 'node'), (kernels, 'model_index')]:
            if [int(r[index]) for r in collection] != list(range(len(collection))):
                raise RuntimeError('Incomplete ordered output')
            for record in collection:
                if (int(record['event']), int(record['station'])) != (i, k):
                    raise RuntimeError('Output native index mismatch')
                for prefix, fields in [('source_', native['source_native']), ('receiver_', native['receiver_native'])]:
                    for key, value in fields.items():
                        if key not in ('id', 'x', 'y', 'z', 't') and record[prefix + key] != value:
                            raise RuntimeError('Full native output metadata mismatch')
        xyz = [[float(r[a]) for a in 'xyz'] for r in nodes]
        if any(not math.isfinite(x) or not axes[a][0] <= x <= axes[a][1]
               for p in xyz for a, x in zip('xyz', p)):
            raise RuntimeError('Nonfinite or out-of-domain path')
        if xyz[0] != [float(native['source_native'][a]) for a in 'xyz'] or xyz[-1] != [float(native['receiver_native'][a]) for a in 'xyz']:
            raise RuntimeError('Endpoint mismatch')
        if any(a == b for a, b in zip(xyz[:-1], xyz[1:])):
            raise RuntimeError('Zero-length output edge')
        if any(not math.isfinite(float(r[key])) for r in kernels for key in ('dT_dv', 'length')):
            raise RuntimeError('Nonfinite derivative array')
        for key in ('ray_time', 'ray_projected_gradient', 'ray_raw_gradient', 'source_dx', 'source_dy', 'source_dz'):
            if not math.isfinite(float(row[key])):
                raise RuntimeError('Nonfinite scalar')
        for key in ('ray_finite', 'ray_path_in_domain', 'ray_exact_source_endpoint', 'ray_exact_receiver_endpoint'):
            if row[key] != '1':
                raise RuntimeError('Failed returned-Ray gate: ' + key)
        for key in ('ray_initialization_attempted', 'ray_initialization_succeeded', 'ray_selected_fmm_seed'):
            if row[key] != '0':
                raise RuntimeError('Unexpected fresh initializer claim')
        reference = native['saved_comparison_row']
        error = [float(row['source_d' + a]) - float(reference['reference_source_d' + a + '_s_per_km']) for a in 'xyz']
        error_norm = math.sqrt(sum(x*x for x in error))
        time_error = float(row['ray_time']) - float(reference['reference_time_s'])
        results.append({'pair_index': pair, 'native_context': native, 'scalars_17': row,
            'time_error_s': time_error, 'source_error_xyz_s_per_km': error,
            'source_error_euclidean_norm_s_per_km': error_norm,
            'time_limit_pass': abs(time_error) <= 2.5e-5, 'source_limit_pass': error_norm <= 3e-6,
            'local_flag': int(row['ray_converged']),
            'strict_gradient_test_pass': float(row['ray_projected_gradient']) < 1e-7,
            'termination_scope': 'No history captured. A true flag above1e-7 implies the unchanged combined criterion; final-path scalar only.'})
    if len(paths) != sum(int(r['ray_path_points']) for r in rows) or len(partials) != 2*len(grid):
        raise RuntimeError('Unexpected additional output rows')
    return results

def main():
    prepared_path = HERE / 'prepared_v2.json'
    prepared = json.loads(prepared_path.read_text())
    review_path = HERE / 'prelaunch_review.json'
    review = json.loads(review_path.read_text())
    if review.get('status') != 'passed' or review.get('prepared_sha256') != sha(prepared_path):
        raise RuntimeError('Missing passed hash-bound preparation review')
    verify(prepared)
    ledger = {'status': 'running', 'started_utc': now(), 'prepared_sha256': sha(prepared_path),
              'prelaunch_review_sha256': sha(review_path), 'commands': [], 'native_calls_planned': 4}
    ledger_path = HERE / 'execution.json'
    dump(ledger_path, ledger)
    def update():
        temp = HERE / 'execution.json.new'
        with temp.open('w') as f:
            json.dump(ledger, f, indent=2, allow_nan=False)
            f.write('\n')
        os.replace(str(temp), str(ledger_path))
    unsettled_groups = []
    def group_members(pgid):
        result = []
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) == pgid and fields[0] != 'Z':
                    result.append(int(entry.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
        return result
    def signal_group(pgid, sig):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
    def terminate_and_reap(process):
        # Ignore a second interruption until the original child is reaped and
        # every live compiler/worker in its process group is accounted for.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal_group(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while group_members(process.pid) and time.monotonic() < deadline:
            time.sleep(.1)
        if group_members(process.pid):
            signal_group(process.pid, signal.SIGKILL)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        deadline = time.monotonic() + 10
        while group_members(process.pid) and time.monotonic() < deadline:
            time.sleep(.1)
        remaining = group_members(process.pid)
        if remaining or process.poll() is None:
            unsettled_groups.append({'pgid': process.pid, 'live_members': remaining,
                                     'direct_child_reaped': process.poll() is not None})
    def interrupted(sig, frame):
        raise RuntimeError('Interrupted by signal ' + str(sig))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', LC_ALL='C',
               TMPDIR=str(ROOT / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    ledger['environment'] = {k: env[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'LC_ALL', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE')}
    def command(stage, cmd):
        stdout, stderr = HERE / 'logs' / (stage + '.stdout.log'), HERE / 'logs' / (stage + '.stderr.log')
        item = {'stage': stage, 'command': cmd, 'started_utc': now()}
        ledger['commands'].append(item)
        ledger['current_stage'] = stage
        update()
        with stdout.open('x') as out, stderr.open('x') as err:
            process = subprocess.Popen(cmd, cwd=str(HERE), env=env, stdout=out, stderr=err, start_new_session=True)
            item['pid'] = process.pid
            update()
            try:
                code = process.wait()
                # A supervisor exit alone does not freeze descendants' logs.
                deadline = time.monotonic() + 10
                while group_members(process.pid) and time.monotonic() < deadline:
                    time.sleep(.1)
                if group_members(process.pid):
                    raise RuntimeError('Live process-group member after supervisor exit')
            except BaseException:
                terminate_and_reap(process)
                item['return_code'] = process.returncode
                item['finished_utc'] = now()
                item['unsettled_groups'] = list(unsettled_groups)
                raise
        item.update({'return_code': code, 'finished_utc': now(), 'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)})
        update()
        if code != 0:
            raise RuntimeError(stage + ' failed with code ' + str(code))
    try:
        for name in ('build', 'logs', 'results'):
            (HERE / name).mkdir()
        context = json.loads((HERE / 'inputs/native_context.json').read_text())
        variants = {}
        binaries = {}
        for variant in ('old', 'D'):
            binary = HERE / 'build' / ('trace_' + variant)
            cmd = [prepared['compiler']] + prepared['flags'] + [str(HERE / 'driver.cpp'),
                '-I' + str(HERE / 'source' / variant), '-o', str(binary), '-lstdc++fs']
            command('compile_' + variant, cmd)
            binaries[variant] = sha(binary)
            out = HERE / 'results' / variant
            out.mkdir()
            verify(prepared)
            command('trace_' + variant, [str(binary), str(HERE / 'inputs'), str(out)])
            variants[variant] = inspect(variant, context)
            if variant == 'old':
                old_rows = read(out / 'scalars_12.csv')
                expected = read(HERE / 'inputs/selected_status.csv')
                mismatches = [{'pair_index': PAIRS[n], 'column': key, 'expected': value, 'actual': old_rows[n].get(key)}
                    for n, row in enumerate(expected) for key, value in row.items()
                    if key not in SAVED_INITIALIZER and old_rows[n].get(key) != value]
                dump(HERE / 'old_parity.json', {'status': 'passed' if not mismatches else 'failed',
                    'compared_columns_per_pair': len(expected[0])-len(SAVED_INITIALIZER),
                    'excluded_saved_only_initializer_columns': list(SAVED_INITIALIZER),
                    'native_context': context, 'mismatches': mismatches})
                if mismatches:
                    raise RuntimeError('Original12-digit parity failed; D not executed')
        verify(prepared)
        summary = {'status': 'completed_four_calls', 'scope': 'Four native straight-trace replays; no receiver field construction, history instrumentation or inversion',
            'prepared_sha256': sha(prepared_path), 'prelaunch_review_sha256': sha(review_path),
            'old_parity_sha256': sha(HERE / 'old_parity.json'), 'binary_sha256': binaries,
            'variants': variants, 'time_limit_s': 2.5e-5, 'source_vector_norm_limit_s_per_km': 3e-6,
            'scientific_scope': 'Accuracy/status of these four calls only; no whole-cohort or global3D first-arrival acceptance',
            'D_change_scope': 'Extended action sum plus usable-curvature handling together; not isolated attribution',
            'old_parity_passed_before_D': True, 'original_inputs_and_sources_unchanged': True,
            'output_sha256': {str(p.relative_to(HERE)): sha(p) for sub in ('results', 'logs', 'build') for p in sorted((HERE/sub).rglob('*')) if p.is_file()}}
        dump(HERE / 'summary.json', summary)
        ledger.update({'status': 'completed', 'return_code': 0, 'finished_utc': now(),
                       'summary_sha256': sha(HERE / 'summary.json'), 'native_calls_completed': 4})
        update()
        print(ledger['summary_sha256'])
    except BaseException as error:
        ledger.update({'status': 'failed_preserved', 'finished_utc': now(), 'error': str(error),
                       'outputs_stable': not unsettled_groups, 'unsettled_process_groups': unsettled_groups,
                       'output_sha256': {} if unsettled_groups else {str(p.relative_to(HERE)): sha(p) for sub in ('results', 'logs', 'build')
                                         if (HERE/sub).exists() for p in sorted((HERE/sub).rglob('*')) if p.is_file()}})
        update()
        raise

if __name__ == '__main__':
    main()
