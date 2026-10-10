#!/usr/bin/env python3
"""One original receiver field and two old/D configured ray comparisons."""
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EVENTS = (981, 987)
STATION = 160
MAX_UPDATES = 1000
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
    rows = read(out / 'status.csv')
    paths = read(out / 'paths.csv')
    starts = read(out / 'starts.csv')
    originals = read(HERE / 'inputs/original_status.csv')
    grid = read(HERE / 'inputs/trial_grid.csv')
    bounds = {a: (min(float(r[a]) for r in grid), max(float(r[a]) for r in grid)) for a in 'xyz'}
    if len(rows) != 2 or len(starts) != 4:
        raise RuntimeError('Incomplete replay output inventory')
    result = []
    for n, i in enumerate(EVENTS):
        row, expected = rows[n], originals[n]
        if (int(row['event']), int(row['station'])) != (i, STATION):
            raise RuntimeError('Native status ordering mismatch')
        for key, value in expected.items():
            if key in ('event', 'station', 'source_t') or key.startswith(('source_', 'receiver_')):
                if row[key] != value:
                    raise RuntimeError('Native status/geometry mismatch: ' + key)
        for key in ('source_dx', 'source_dy', 'source_dz'):
            if row[key] != '': raise RuntimeError('Action-only partial was populated')
        for key in ('ray_finite', 'ray_path_in_domain', 'ray_exact_source_endpoint', 'ray_exact_receiver_endpoint',
                    'ray_initialization_attempted', 'ray_initialization_succeeded'):
            if row[key] != '1': raise RuntimeError('Invalid finite/geometry/initializer output: ' + key)
        if row['ray_derivatives_evaluated'] != '0': raise RuntimeError('Unexpected derivative evaluation')
        for key in ('ray_time', 'ray_projected_gradient', 'ray_raw_gradient', 'ray_direct_seed_time', 'ray_fmm_seed_time', 'ray_field_time'):
            if not math.isfinite(float(row[key])): raise RuntimeError('Nonfinite output: ' + key)
        if not 0 <= int(row['ray_iterations']) <= MAX_UPDATES:
            raise RuntimeError('Unexpected update count')
        nodes = [r for r in paths if (int(r['event']),int(r['station'])) == (i,STATION)]
        if len(nodes) != int(row['ray_path_points']) or [int(r['node']) for r in nodes] != list(range(len(nodes))):
            raise RuntimeError('Path node inventory mismatch')
        for record in nodes + starts[2*n:2*n+2]:
            for key, value in expected.items():
                if key.startswith(('source_', 'receiver_')) and key not in ('source_x','source_y','source_z','source_t','source_dx','source_dy','source_dz','receiver_x','receiver_y','receiver_z'):
                    if record[key] != value: raise RuntimeError('Path/start native metadata mismatch')
        xyz = [[float(r[a]) for a in 'xyz'] for r in nodes]
        if any(not math.isfinite(v) or not bounds[a][0] <= v <= bounds[a][1] for point in xyz for a,v in zip('xyz',point)):
            raise RuntimeError('Nonfinite/out-of-box path')
        if xyz[0] != [float(row['source_'+a]) for a in 'xyz'] or xyz[-1] != [float(row['receiver_'+a]) for a in 'xyz']:
            raise RuntimeError('Exact endpoint mismatch')
        if any(a == b for a,b in zip(xyz[:-1],xyz[1:])): raise RuntimeError('Zero-length final edge')
        pair_starts = starts[2*n:2*n+2]
        if [(int(r['event']),int(r['station']),r['start']) for r in pair_starts] != [(i,STATION,'straight'),(i,STATION,'fmm')]:
            raise RuntimeError('Start ordering mismatch')
        for r in pair_starts:
            for key in ('time','projected_gradient','raw_gradient'):
                if not math.isfinite(float(r[key])): raise RuntimeError('Nonfinite start result')
        selected = int(float(pair_starts[1]['time']) < float(pair_starts[0]['time']))
        if int(row['ray_selected_fmm_seed']) != selected or row['ray_time'] != pair_starts[selected]['time']:
            raise RuntimeError('Original strict lower-action selection changed')
        if row['ray_direct_seed_time'] != pair_starts[0]['time'] or row['ray_fmm_seed_time'] != pair_starts[1]['time']:
            raise RuntimeError('Start action bookkeeping mismatch')
        for a,b in [('ray_converged','converged'),('ray_iterations','iterations'),('ray_merged_nodes','merged_nodes'),
                    ('ray_projected_gradient','projected_gradient'),('ray_raw_gradient','raw_gradient'),('ray_path_points','path_points')]:
            if row[a] != pair_starts[selected][b]: raise RuntimeError('Selected start status mismatch')
        result.append({'event':i,'station':STATION,'native_context':context[n], 'status':row,'starts':pair_starts,
            'strict_gradient_test_pass':float(row['ray_projected_gradient']) < 1e-7,
            'derived_loop_termination': 'update_budget_exhausted' if int(row['ray_iterations']) == MAX_UPDATES else
                'line_search_exhausted' if row['ray_converged'] == '0' else 'existing_local_stop',
            'termination_scope':'Inspected unchanged control flow; no per-iteration history or distinction between successful strict/combined exits when both apply.'})
    if len(paths) != sum(int(r['ray_path_points']) for r in rows): raise RuntimeError('Unexpected extra path rows')
    return result


def parity():
    original_status = read(HERE / 'inputs/original_status.csv')
    original_paths = read(HERE / 'inputs/original_paths.csv')
    actual_status = read(HERE / 'results/old/status.csv')
    actual_paths = read(HERE / 'results/old/paths.csv')
    passed = actual_status == original_status and actual_paths == original_paths
    result = {'status':'passed' if passed else 'failed_preserved',
              'status_rows_equal':actual_status == original_status,'selected_path_rows_equal':actual_paths == original_paths,
              'status_rows':len(actual_status),'path_rows':len(actual_paths),
              'basis':'Exact parsed CSV fields, including all 17-digit physical scalars, flags/counters, native strings and ordered selected-path coordinates',
              'input_sha256':{name:sha(HERE/name) for name in ('inputs/original_status.csv','inputs/original_paths.csv','results/old/status.csv','results/old/paths.csv')}}
    dump(HERE / 'old_parity.json',result)
    if not passed: raise RuntimeError('Original replay parity failed; no D evaluation permitted')
    return result

def main():
    prepared_path = HERE / 'prepared.json'
    prepared = json.loads(prepared_path.read_text())
    if prepared['settings']['maximum_updates'] != MAX_UPDATES:
        raise RuntimeError('Prepared cap differs from classifier')
    review_path = HERE / 'prelaunch_review.json'
    review = json.loads(review_path.read_text())
    if review.get('status') != 'passed' or review.get('prepared_sha256') != sha(prepared_path):
        raise RuntimeError('Missing passed hash-bound preparation review')
    verify(prepared)
    ledger = {'status': 'running', 'started_utc': now(), 'prepared_sha256': sha(prepared_path),
              'prelaunch_review_sha256': sha(review_path), 'commands': [], 'trace_subcalls_planned': 8, 'configured_evaluations_planned': 4, 'field_constructions_planned': 1}
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
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1', LC_ALL='C',
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
            try:
                item['pid'] = process.pid
                update()
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
        memory_bytes = prepared['settings']['address_space_limit_GiB'] * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        ledger['address_space_limit_GiB'] = prepared['settings']['address_space_limit_GiB']
        for name in ('build', 'logs', 'results'):
            (HERE / name).mkdir()
        context = json.loads((HERE / 'inputs/native_context.json').read_text())
        variants, binaries = {}, {}
        seed_pins = None
        for variant in ('old', 'D'):
            binary = HERE / 'build' / ('trace_' + variant)
            cmd = [prepared['compiler']] + prepared['flags'] + [str(HERE / 'driver.cpp'),
                '-I' + str(HERE / 'source' / variant), '-o', str(binary), '-lstdc++fs']
            command('compile_' + variant, cmd)
            binaries[variant] = sha(binary)
            out = HERE / 'results' / variant
            out.mkdir()
            verify(prepared)
            if variant == 'D':
                for name, expected in seed_pins.items():
                    if sha(HERE / 'results/old' / name) != expected: raise RuntimeError('Captured Candidate changed')
            command('forward_' + variant, [str(binary), str(HERE / 'inputs'), str(out), variant, str(HERE / 'results/old')])
            expected_log = 'configured_evaluations=2 trace_subcalls=4 field_constructions=' + ('1' if variant == 'old' else '0') + ' exact_candidate_roundtrips=2'
            if expected_log not in (HERE / 'logs' / ('forward_' + variant + '.stdout.log')).read_text().splitlines():
                raise RuntimeError('Missing completed driver call inventory')
            variants[variant] = inspect(variant, context)
            if variant == 'old':
                parity_result = parity()
                seed_pins = {name:sha(out / name) for name in ('candidate_metadata.csv','candidate_paths.csv')}
            else:
                for name, expected in seed_pins.items():
                    if sha(out/name) != expected or sha(HERE/'results/old'/name) != expected:
                        raise RuntimeError('D consumed/serialized Candidate differs from original')
        verify(prepared)
        comparisons=[]
        for old_result,new_result in zip(variants['old'],variants['D']):
            a,b=old_result['status'],new_result['status']
            comparisons.append({'event':int(a['event']),'station':int(a['station']), 'native_context':old_result['native_context'],
                'D_minus_old_time_s':float(b['ray_time'])-float(a['ray_time']),
                'old_flag':int(a['ray_converged']),'D_flag':int(b['ray_converged']),
                'old_selected_fmm':int(a['ray_selected_fmm_seed']),'D_selected_fmm':int(b['ray_selected_fmm_seed']),
                'old_updates':int(a['ray_iterations']),'D_updates':int(b['ray_iterations']),
                'old_projected_gradient':float(a['ray_projected_gradient']),'D_projected_gradient':float(b['ray_projected_gradient'])})
        summary={'status':'completed_four_configured_evaluations','prepared_sha256':sha(prepared_path),
                 'prelaunch_review_sha256':sha(review_path),'binary_sha256':binaries,'variants':variants,'comparisons':comparisons,
                 'old_parity_sha256':sha(HERE/'old_parity.json'),'candidate_sha256':seed_pins,
                 'field_constructions':1,'configured_evaluations':4,'trace_subcalls':8,
                 'derivatives_evaluated':False,'accuracy_reference_available':False,
                 'scope':'Standalone failed-trial old versus adopted-D comparison; no inverse restart, accepted update, full-cohort or global first-arrival claim',
                 'source_difference':'Reviewed outer action accumulation plus usable-curvature package; not a single-cause intervention',
                 'original_inputs_and_sources_unchanged':True,
                 'output_sha256':{str(p.relative_to(HERE)):sha(p) for sub in ('results','logs','build') for p in sorted((HERE/sub).rglob('*')) if p.is_file()}}
        dump(HERE/'summary.json',summary)
        ledger.update({'status':'completed','return_code':0,'finished_utc':now(),'summary_sha256':sha(HERE/'summary.json'),
                       'configured_evaluations_completed':4,'trace_subcalls_completed':8,'field_constructions_completed':1})
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
