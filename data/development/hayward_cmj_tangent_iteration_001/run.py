#!/usr/bin/env python3
"""One frozen compile and bounded two-polygon tangent history; no Ray flags."""
import csv
import datetime
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BENCH = ROOT/'data/development/hayward_cmj_fixed_polygon_kernel_001'
POST = ROOT/'data/development/hayward_cmj_post_half_step_tangent_001'
POST_REVIEW = ROOT/'data/development/hayward_cmj_post_half_step_tangent_review_001/review.json'
COMPARISON = ROOT/'data/development/hayward_cmj_half_gradient_comparison_001'
LIFECYCLE = ROOT/'data/development/hayward_cmj_tangent_step_001/run.py'
TABLES = ('summary.csv','updates.csv','trials.csv','directions.csv','paths.csv','gradients.csv','edges.csv')


def require(ok, message):
    if not ok: raise ValueError(message)


def now(): return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream: return json.load(stream)


def save(path, value):
    with path.open('x') as stream: json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False); stream.write('\n')


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,str(path)); result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result); return result


def table(path):
    with path.open(newline='') as stream: return list(csv.DictReader(stream))


def gates(identities):
    for folder, review_path, prefix, status in (
            (BENCH,BENCH/'review.json','','completed_fixed_polygon_comparison'),
            (POST,POST_REVIEW,'native_','completed_bounded_post_half_tangent_and_support')):
        review=read(review_path); summary=read(folder/'summary.json'); execution=read(folder/'execution.json'); outer=read(folder/'outer_reaping.json')
        require(review['status']=='passed' and summary['status']==status and execution['return_code']==0
                and summary['native_contexts']==identities==outer['native_contexts'], 'Reviewed terminal geometry/evaluator gate')
        for key,name in ((prefix+'prepared_sha256','prepared.json'),(prefix+'summary_sha256','summary.json'),
                         (prefix+'execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
            require(review[key]==sha(folder/name), 'Terminal review binding: '+key)
        require(outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0
                and outer['summary_sha256']==sha(folder/'summary.json') and outer['execution_sha256']==sha(folder/'execution.json'), 'Prior outer reaping')
    comparison=read(COMPARISON/'summary.json')
    require(comparison['status']=='completed_saved_half_gradient_comparison' and comparison['native_contexts']==identities
            and comparison['benchmark_review_sha256']==sha(BENCH/'review.json')
            and comparison['post_half_review_sha256']==sha(POST_REVIEW), 'Saved half-gradient comparison gate')
    require(read(COMPARISON/'source_review.json')['status']=='passed'
            and comparison['source_review_sha256']==sha(COMPARISON/'source_review.json'), 'Reviewed comparison source')
    receipt=read(COMPARISON/'execution_receipt.json')
    require(receipt['status']=='passed' and receipt['return_code']==0 and receipt['child_reaped']
            and receipt['native_contexts']==identities and receipt['summary_sha256']==sha(COMPARISON/'summary.json')
            and receipt['checker_sha256']==comparison['checker_sha256']==sha(COMPARISON/'check_saved.py'), 'Reaped half-comparator receipt')
    for name,digest in receipt['output_sha256'].items(): require(sha(COMPARISON/name)==digest, 'Comparator receipt output: '+name)
    for item in identities:
        original=item['native_context']['original_status']
        require(item['station']==160 and len(item['catalog_uses'])==9 and original['ray_converged']==original['ray_derivatives_evaluated']=='0'
                and all(original['source_d'+axis]=='' for axis in 'xyz'), 'Original native flags/blank partials')
    copied=read(HERE/'input_copy.json')
    require(copied['native_contexts_sha256']==sha(HERE/'native_contexts.json')
            and copied['benchmark_review_sha256']==sha(BENCH/'review.json'), 'Reviewed saved input-copy binding')
    for item in copied['copies']:
        require(sha(HERE/item['copy'])==item['copy_sha256']==sha(ROOT/item['source'])==item['source_sha256'], 'Exact saved numeric input copy')


def readback(parser, identities):
    records={name:table(HERE/'results'/name) for name in TABLES if name!='directions.csv'}
    require([int(r['event']) for r in records['summary.csv']]==[981,987], 'Exact terminal case order')
    require(all(int(r['event']) in (981,987) and r['station']=='160' for rows in records.values() for r in rows), 'Complete native output roster')
    benchmark={name:table(BENCH/'results'/name) for name in ('totals.csv','edges.csv','gradients.csv')}
    mismatches=[]; cases=[]; direction_counts={981:0,987:0}
    with (HERE/'results/directions.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            event=int(row['event']); require(event in direction_counts and row['station']=='160', 'Direction native roster')
            for key in ('qx','qy','qz'):
                require(math.isfinite(float(row[key])) and float(row[key]).hex()==float.fromhex(row[key+'_hex']).hex(), 'Direction finite binary64/hex')
            direction_counts[event]+=1
    for identity,summary in zip(identities,records['summary.csv']):
        event=identity['event']; n=1029 if event==981 else 1031
        selected={name:[r for r in rows if int(r['event'])==event] for name,rows in records.items()}
        require(all(r['station']=='160' for rows in selected.values() for r in rows), 'All table native receiver indices')
        updates=int(summary['updates']); trials=selected['trials.csv']; history=selected['updates.csv']
        require(0<=updates<=1000 and len(history)==updates+1 and [int(r['update']) for r in history]==list(range(updates+1)), 'Complete bounded accepted history')
        require(len(trials)==int(summary['trials'])<=24*int(summary['metric_calls'])
                and int(summary['path_eval_calls'])==updates+1
                and direction_counts[event]==(n-2)*int(summary['metric_calls']), 'Actual evaluator/metric/direction counts')
        require(sum(r['paired_armijo']=='1' for r in trials)==updates
                and int(summary['extra_segment_calls'])==(n-1)*(1+sum(r['action_evaluated']=='1' for r in trials)), 'Accepted/evaluated trial inventory')
        require(summary['original_convergence_flag']=='0' and summary['candidate_convergence_status']=='null'
                and all(summary[k]=='0' for k in ('trace_calls','field_calls','source_model_partials')), 'No Ray-status promotion or other calls')
        for row in trials:
            step=parser.number(row,'step',True); slope=parser.number(row,'nominal_slope',True)
            rhs=parser.number(row,'armijo_rhs_extended')
            require(step>0 and slope<0 and rhs<0 and 0<=int(row['attempt'])<24, 'Recorded descent and bounded fraction')
            if row['actual_slope_extended']!='': parser.number(row,'actual_slope_extended')
            if row['action_evaluated']=='1':
                paired=parser.number(row,'paired_change'); parser.number(row,'outer_change',True)
                require((paired<=rhs)==(row['paired_armijo']=='1'), 'Recorded paired Armijo decision')
            if row['paired_armijo']=='1':
                require(row['actual_descent']=='1' and row['no_op']=='0' and row['action_evaluated']=='1' and row['reason']=='accepted', 'Accepted actual descent/non-no-op')
        for row in history:
            for key in ('action','available_norm','ordinary_norm'): parser.number(row,key,True)
        for key in ('action','available_norm','ordinary_norm'):
            require(parser.number(summary,key,True)==parser.number(history[-1],key,True), 'Terminal history/state scalar join')
        post=read(POST/('event_%d.json.gz'%event)); blocked={tuple(v) for v in post['geometric_blocked_slots']}
        require(int(summary['fixed_slots'])==len(blocked), 'Reviewed half-step availability roster')
        for state in ('initial','final'):
            paths=[r for r in selected['paths.csv'] if r['state']==state]
            edges=[r for r in selected['edges.csv'] if r['state']==state]
            gradient=[r for r in selected['gradients.csv'] if r['state']==state]
            require([int(r['node']) for r in paths]==list(range(n)) and [int(r['edge']) for r in edges]==list(range(n-1))
                    and [(int(r['node']),int(r['axis'])) for r in gradient]==[(i,k) for i in range(1,n-1) for k in range(3)], 'Complete state arrays')
            require({(int(r['node']),int(r['axis'])) for r in gradient if r['available']=='0'}==blocked, 'Fixed available search mask')
            for row in paths:
                for key in 'xyz': parser.number(row,key,True)
            for row in edges: parser.number(row,'action',True)
            for row in gradient: parser.number(row,'component',True)
            if state=='initial':
                expected=post['coordinate_provenance']
                for row,saved in zip(paths,expected):
                    for axis,key in enumerate('xyz'):
                        require(float.fromhex(row[key+'_hex']).hex()==float.fromhex(saved['binary64_hex'][axis]).hex(), 'Exact accepted half initial coordinates')
                for name,actual,key,index in (('edges.csv',edges,'action','edge'),('gradients.csv',gradient,'component','node')):
                    old=[r for r in benchmark[name] if int(r['event'])==event and r['stage']=='3']
                    require(len(old)==len(actual), 'Benchmark initial inventory')
                    for row,prior in zip(actual,old):
                        require(row[index]==prior[index] and (name!='gradients.csv' or row['axis']==prior['axis']), 'Benchmark initial ordering')
                        if float.fromhex(row[key+'_hex']).hex()!=float.fromhex(prior[key+'_hex']).hex():
                            mismatches.append(dict(event=event,table=name,index=row[index],axis=row.get('axis'),actual_hex=row[key+'_hex'],benchmark_hex=prior[key+'_hex']))
                prior=next(r for r in benchmark['totals.csv'] if int(r['event'])==event and r['stage']=='3')
                if float.fromhex(history[0]['action_hex']).hex()!=float.fromhex(prior['action_hex']).hex():
                    mismatches.append(dict(event=event,table='totals.csv',actual_hex=history[0]['action_hex'],benchmark_hex=prior['action_hex']))
        cases.append(dict(identity,driver_summary=summary,initial_benchmark_bitwise_match=not any(v['event']==event for v in mismatches),
                          accepted_updates=updates,recorded_trials=len(trials),direction_rows=direction_counts[event]))
    result=dict(cases=cases,initial_mismatches=mismatches,
                interpretation='Bounded history in a feasible search subspace. Intermediate paired decisions are approximate; no complete stationarity or source-accuracy certificate.')
    save(HERE/'results/readback.json',result)
    require(not mismatches, 'Initial benchmark mismatch retained in readback; interpretation withheld')
    return result


def compress_directions(identities):
    source=HERE/'results/directions.csv'; target=Path(str(source)+'.gz'); raw_sha=sha(source); count=source.stat().st_size
    save(Path(str(target)+'.identifiers.json'),dict(native_contexts=identities,expected_file=str(target.relative_to(ROOT)),
         uncompressed_file=str(source.relative_to(ROOT)),uncompressed_sha256=raw_sha,prepared_sha256=sha(HERE/'prepared.json')))
    with source.open('rb') as inp, target.open('xb') as out:
        with gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as packed:
            for block in iter(lambda:inp.read(1048576),b''): packed.write(block)
    h=hashlib.sha256(); restored=0
    with gzip.open(str(target),'rb') as inp:
        for block in iter(lambda:inp.read(1048576),b''): h.update(block); restored+=len(block)
    require(h.hexdigest()==raw_sha and restored==count, 'Lossless direction archive verification')
    save(HERE/'results/compression.json',dict(native_contexts=identities,raw_file=source.name,raw_sha256=raw_sha,
         raw_bytes=count,gzip_file=target.name,gzip_sha256=sha(target),decompression_verified=True,after_child_reaped=True))
    source.unlink()


def main():
    prepared=read(HERE/'prepared.json'); approval=read(HERE/'prelaunch_review.json')
    require(approval['status']=='passed' and approval['prepared_sha256']==sha(HERE/'prepared.json'), 'Root prelaunch review required')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items(): require(sha(base/name)==digest, 'Changed pin: '+name)
        for name,digest in prepared['runtime_sha256'].items(): require(sha(name)==digest, 'Changed runtime: '+name)
        require(sha(sys.executable)==prepared['python']['sha256'], 'Changed Python executable')
    verify(); os.environ.update(prepared['environment']); identities=read(HERE/'native_contexts.json'); gates(identities)
    require(not any((HERE/name).exists() for name in ('execution.json','summary.json','results','build','logs')), 'Fresh execution paths required')
    parser=module(BENCH/'run.py','frozen_parser'); lifecycle=module(LIFECYCLE,'frozen_lifecycle')
    for name in ('results','build','logs'): (HERE/name).mkdir()
    for name in TABLES+('readback.json',):
        save(HERE/'results'/(name+'.identifiers.json'),dict(native_contexts=identities,expected_file=str((HERE/'results'/name).relative_to(ROOT)),
             original_convergence_flag='0',candidate_convergence_status=None,prepared_sha256=sha(HERE/'prepared.json')))
    for index in (0,1):
        for suffix in ('stdout','stderr'):
            name='command_%d.%s'%(index,suffix)
            save(HERE/'logs'/(name+'.identifiers.json'),dict(native_contexts=identities,expected_file=str((HERE/'logs'/name).relative_to(ROOT)),prepared_sha256=sha(HERE/'prepared.json')))
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),commands=[],native_contexts=identities,
                prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'))
    def update():
        temporary=HERE/'execution.json.new'; temporary.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n'); temporary.replace(HERE/'execution.json')
    def interrupted(sig,unused): raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted); signal.signal(signal.SIGINT,interrupted)
    update(); unsettled=[]; code=1; result=None
    try:
        for index,command in enumerate(prepared['commands']):
            item=dict(command=command,started_utc=now()); ledger['commands'].append(item); update()
            with (HERE/'logs'/('command_%d.stdout'%index)).open('x') as stdout, (HERE/'logs'/('command_%d.stderr'%index)).open('x') as stderr:
                mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
                try: child=subprocess.Popen(command,cwd=str(HERE),env=os.environ.copy(),stdout=stdout,stderr=stderr,start_new_session=True)
                except BaseException:
                    signal.pthread_sigmask(signal.SIG_SETMASK,mask); raise
                item['pid']=child.pid
                try:
                    update(); signal.pthread_sigmask(signal.SIG_SETMASK,mask); returned=child.wait()
                    if returned!=0 or lifecycle.group_members(child.pid): raise RuntimeError('Child failed or left a live writer')
                except BaseException:
                    cleanup=lifecycle.stop_group(child); item['cleanup']=cleanup
                    if cleanup['live_members'] or not cleanup['child_reaped']: unsettled.append(cleanup)
                    raise
                finally:
                    item.update(return_code=child.returncode,child_reaped=child.poll() is not None,finished_utc=now()); update()
        require((HERE/'logs/command_1.stdout').read_text().strip()=='cases=2 max_updates_per_case=1000 max_trials_per_update=24 trace_calls=0 field_calls=0 source_model_partials=0 convergence_promotions=0', 'Declared bounded driver completion')
        result=readback(parser,identities); compress_directions(identities); verify(); ledger['status']='completed_bounded_tangent_iteration'; code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int): code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
    finally:
        stable=not unsettled and all(c.get('child_reaped') for c in ledger['commands'])
        outputs={} if not stable else {str(p.relative_to(HERE)):sha(p) for folder in ('results','logs','build') for p in sorted((HERE/folder).rglob('*')) if p.is_file()}
        summary=dict(status=ledger['status'],error=ledger.get('error'),result=result,native_contexts=identities,
             prepared_sha256=sha(HERE/'prepared.json'),output_sha256=outputs,trace_calls=0,field_calls=0,source_model_partials=0,
             new_reference_integrations=0,original_convergence_flag='0',candidate_convergence_status=None)
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),outputs_stable=stable,unsettled_groups=unsettled,
                      summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs); update()
    return code


if __name__=='__main__': sys.exit(main())
