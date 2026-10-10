#!/usr/bin/env python3
"""Four fixed saved-path gradient decompositions; no trace or field calls."""
import csv
from fractions import Fraction as Q
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

def fraction_record(value):
    return {'exact_rational': str(value), 'float_display': float(value)}

def decompose(variant):
    rows = read(HERE/'results'/variant/'node_gradients.csv')
    norms = read(HERE/'results'/variant/'norms.csv')
    cases, top = [], []
    for saved in norms:
        event, station = int(saved['event']), int(saved['station'])
        chosen = [r for r in rows if int(r['event']) == event and int(r['station']) == station]
        assert [int(r['node']) for r in chosen] == list(range(int(saved['ray_path_points'])))
        assert chosen[0]['is_free'] == chosen[-1]['is_free'] == '0'
        assert all(r['is_free'] == '1' for r in chosen[1:-1])
        for r in (chosen[0], chosen[-1]):
            assert all(r[k] == '' for k in ('raw_gx','raw_gy','raw_gz','projected_gx','projected_gy','projected_gz'))
        totals = {basis:[Q(0)]*3 for basis in ('raw','projected')}
        near_totals = {basis:[Q(0)]*3 for basis in ('raw','projected')}
        near_nodes, components = [], []
        for r in chosen[1:-1]:
            near = abs(Q(float(r['x']))) < Q(1,1000000)
            if near: near_nodes.append(int(r['node']))
            for axis_index, axis in enumerate('xyz'):
                item={'row':r,'axis':axis}
                for basis in ('raw','projected'):
                    v=float(r[basis+'_g'+axis]); assert math.isfinite(v)
                    square=Q(v)**2
                    totals[basis][axis_index]+=square
                    if near:near_totals[basis][axis_index]+=square
                    item[basis]=square
                components.append(item)
        details={}
        for basis in ('raw','projected'):
            total=sum(totals[basis],Q(0)); assert total>0
            details[basis]={'total_squared_norm':fraction_record(total),
                'axis_squared_norm':{a:fraction_record(v) for a,v in zip('xyz',totals[basis])},
                'near_face_axis_squared_norm':{a:fraction_record(v) for a,v in zip('xyz',near_totals[basis])},
                'near_face_x_fraction_of_total':fraction_record(near_totals[basis][0]/total),
                'near_face_all_axes_fraction_of_total':fraction_record(sum(near_totals[basis],Q(0))/total)}
            ranked=sorted(components,key=lambda item:(-item[basis],int(item['row']['node']),item['axis']))[:20]
            for rank,item in enumerate(ranked,1):
                row=dict(item['row']); row.update(rank_basis=basis,rank=str(rank),axis=item['axis'],
                    component_s_per_km=item['row'][basis+'_g'+item['axis']],
                    exact_component_square=str(item[basis]),squared_fraction_of_total=format(float(item[basis]/total),'.17g'))
                top.append(row)
        case={'event':event,'station':station,'variant':variant,'saved_status_and_diagnostic_norms':saved,
              'near_face_free_nodes':near_nodes,'near_face_free_node_count':len(near_nodes),
              'free_node_count':len(chosen)-2,'squared_component_decomposition':details,
              'diagnostic_action_minus_recorded_action_s':float(saved['diagnostic_path_action'])-float(saved['ray_time'])}
        cases.append(case)
    assert [(c['event'],c['station']) for c in cases]==[(981,160),(987,160)]
    assert len(rows)==sum(c['free_node_count']+2 for c in cases)
    with (HERE/'results'/variant/'top_components.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(top[0])); writer.writeheader();writer.writerows(top)
    return cases

def main():
    prepared=json.loads((HERE/'prepared.json').read_text())
    review=json.loads((HERE/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(HERE/'prepared.json'):
        raise RuntimeError('Missing passed hash-bound source/preparation review')
    verify(prepared)
    source=ROOT/prepared['replay_package']
    terminal=json.loads((source/'review.json').read_text())
    if terminal.get('status')!='passed' or terminal['summary_sha256']!=sha(source/'summary.json'):
        raise RuntimeError('Original replay is not independently reviewed')
    ledger={'status':'running','started_utc':now(),'prepared_sha256':sha(HERE/'prepared.json'),
            'prelaunch_review_sha256':sha(HERE/'prelaunch_review.json'),'commands':[],
            'planned_fixed_path_evaluations':4,'trace_calls':0,'field_constructions':0}
    ledger_path=HERE/'execution.json';dump(ledger_path,ledger)
    def update():
        temporary=HERE/'execution.json.new'
        with temporary.open('w') as f:json.dump(ledger,f,indent=2,allow_nan=False);f.write('\n')
        os.replace(str(temporary),str(ledger_path))
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
        for name in ('build','logs','results'):(HERE/name).mkdir()
        cases=[]
        for variant in ('old','D'):
            binary=HERE/'build'/('gradient_'+variant)
            command('compile_'+variant,[prepared['compiler']]+prepared['flags']+[str(HERE/'gradient.cpp'),
                '-I'+str(source/'source'/variant),'-o',str(binary),'-lstdc++fs'])
            output=HERE/'results'/variant;output.mkdir()
            verify(prepared)
            command('evaluate_'+variant,[str(binary),str(source/'inputs/trial_grid.csv'),
                str(source/'results'/variant/'paths.csv'),str(source/'results'/variant/'status.csv'),str(output),variant])
            assert 'fixed_path_evaluations=2 trace_calls=0 field_constructions=0 norm_parity=passed' in (HERE/'logs'/('evaluate_'+variant+'.stdout.log')).read_text().splitlines()
            cases.extend(decompose(variant))
        verify(prepared)
        summary={'status':'completed_fixed_saved_path_decomposition','prepared_sha256':sha(HERE/'prepared.json'),
                 'cases':cases,'fixed_path_evaluations':4,'trace_calls':0,'field_constructions':0,
                 'all_recorded_17_digit_raw_and_projected_norms_reproduced':True,
                 'arithmetic':'Unchanged old/D path_eval and projected_ray_gradient; exact rational squared sums of exported binary64 free-knot components. Exact component sums need not equal the square of the rounded original norm.',
                 'selection':'Free nodes with abs(x)<1e-6 km, using exact rationals of stored binary64 coordinates; descriptive inventory only.',
                 'scope':'Fixed selected polygons only; no trace, field, optimization, source/model-partial output, new convergence flag, causation or first-arrival certificate.',
                 'output_sha256':{str(p.relative_to(HERE)):sha(p) for sub in ('build','logs','results') for p in sorted((HERE/sub).rglob('*')) if p.is_file()}}
        dump(HERE/'summary.json',summary)
        ledger.update(status='completed',return_code=0,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'),fixed_path_evaluations_completed=4)
        update();print(ledger['summary_sha256'])
    except BaseException as error:
        ledger.update(status='failed_preserved',finished_utc=now(),error=str(error),outputs_stable=not unsettled_groups,unsettled_process_groups=unsettled_groups,
            output_sha256={} if unsettled_groups else {str(p.relative_to(HERE)):sha(p) for sub in ('build','logs','results') if (HERE/sub).exists() for p in sorted((HERE/sub).rglob('*')) if p.is_file()})
        update();raise

if __name__=='__main__':main()
