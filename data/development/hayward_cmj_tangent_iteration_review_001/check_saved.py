#!/usr/bin/env python3
"""Saved iterator state/decision readback; no physical evaluator calls."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATA=ROOT/'data/development'
RUN=DATA/'hayward_cmj_tangent_iteration_001'
BENCH=DATA/'hayward_cmj_fixed_polygon_kernel_001'
POST=DATA/'hayward_cmj_post_half_step_tangent_001'
POST_REVIEW=DATA/'hayward_cmj_post_half_step_tangent_review_001/review.json'
CHECKS={}; PINS={}; arithmetic=None


def check(name,condition):
    CHECKS[name]=CHECKS.get(name,0)+1
    if not condition: raise ValueError(name)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''): h.update(block)
    return h.hexdigest()


def pin(path,digest):
    check('file pin',sha(path)==digest)
    name=str(path); check('consistent pin',name not in PINS or PINS[name]==digest); PINS[name]=digest


def read(path):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream: return json.load(stream)


def rows(path):
    with (gzip.open(str(path),'rt',newline='') if path.suffix=='.gz' else path.open(newline='')) as stream:
        reader=csv.DictReader(stream)
        check('unique CSV columns',len(reader.fieldnames)==len(set(reader.fieldnames)))
        for row in reader:
            check('complete CSV row',None not in row and None not in row.values())
            yield row


def number(row,key,wide=False):
    value=arithmetic.number(row,key,not wide)
    return value if wide else float.fromhex(row[key+'_hex'])


def bits_equal(a,b): return a.hex()==b.hex()
def path_equal(a,b): return len(a)==len(b) and all(bits_equal(x,y) for p,q in zip(a,b) for x,y in zip(p,q))


def dot(a,b):
    value=0.0
    for x,y in zip(a,b):
        product=x*y; value=value+product
    return value


def available(path,axes):
    fixed=set(); multiple=False
    for edge,(a,b) in enumerate(zip(path,path[1:])):
        faces=[k for k in range(3) if a[k]==b[k] and a[k] in axes[k][1:-1]]
        multiple=multiple or len(faces)>1
        fixed.update((i,k) for i in (edge,edge+1) if 0<i<len(path)-1 for k in faces)
    return fixed,multiple


def geometry_event(path,axes,fixed):
    for i,p in enumerate(path):
        if not all(math.isfinite(x) for x in p): return 'nonfinite_geometry'
        if not all(axes[k][0]<=p[k]<=axes[k][-1] for k in range(3)): return 'physical_box_event'
        if 0<i<len(path)-1 and any(p[k] in (axes[k][0],axes[k][-1]) for k in range(3)): return 'physical_box_event'
        if i:
            d=[x-y for x,y in zip(p,path[i-1])]; length=math.sqrt(dot(d,d))
            if not math.isfinite(length): return 'nonfinite_length'
            if length==0: return 'zero_edge_event'
            if length<1e-12: return 'existing_segment_cutoff_event'
    actual,multiple=available(path,axes)
    if multiple: return 'multiple_aligned_faces_event'
    if actual!=fixed: return 'availability_event'
    return ''


def initial_step(path,direction,axes):
    step=1.0
    for p,d in zip(path[1:-1],direction):
        for k,x in enumerate(d):
            if x>0: step=min(step,(axes[k][-1]-p[k])/x)
            if x<0: step=min(step,(axes[k][0]-p[k])/x)
    return step


def rounded_trial(path,direction,step,fixed):
    trial=[list(p) for p in path]
    for i,d in enumerate(direction,1):
        for k,x in enumerate(d):
            if (i,k) not in fixed:
                product=step*x                 # Separate binary64 multiply/add; no FMA.
                trial[i][k]=path[i][k]+product
    return trial


def arrays(records,state,n):
    p=[r for r in records['paths.csv'] if r['state']==state]
    g=[r for r in records['gradients.csv'] if r['state']==state]
    e=[r for r in records['edges.csv'] if r['state']==state]
    check('complete state arrays',[int(r['node']) for r in p]==list(range(n))
          and [(int(r['node']),int(r['axis'])) for r in g]==[(i,k) for i in range(1,n-1) for k in range(3)]
          and [int(r['edge']) for r in e]==list(range(n-1)))
    return [[number(r,k) for k in 'xyz'] for r in p],[number(r,'component') for r in g],[number(r,'action') for r in e],g


def case(identity,records,direction_groups,axes,benchmark,oracle):
    event=identity['event']; n=1029 if event==981 else 1031
    summary=records['summary.csv'][0]; history=records['updates.csv']; trials=records['trials.csv']
    updates=int(summary['updates']); metrics=int(summary['metric_calls'])
    check('history inventory',0<=updates<=1000 and [int(r['update']) for r in history]==list(range(updates+1)))
    check('no extra state labels',all(r['state'] in ('initial','final') for name in ('paths.csv','gradients.csv','edges.csv') for r in records[name]))
    start,g0,e0,grows=arrays(records,'initial',n); final,g1,e1,final_grows=arrays(records,'final',n)
    fixed,multiple=available(start,axes)
    post=read(POST/('event_%d.json.gz'%event))
    check('full native post join',all(post[k]==identity[k] for k in ('event','station','native_context','catalog_uses')))
    check('same accepted half geometry',path_equal(start,[[float.fromhex(x) for x in p['binary64_hex']] for p in post['coordinate_provenance']]))
    check('geometry-derived fixed slots',not multiple and fixed=={tuple(x) for x in post['geometric_blocked_slots']}
          and int(summary['fixed_slots'])==len(fixed) and geometry_event(start,axes,fixed)=='')
    for values in (grows,final_grows):
        check('complete fixed mask',{(int(r['node']),int(r['axis'])) for r in values if r['available']=='0'}==fixed
              and all(r['available'] in ('0','1') for r in values))
    polygon=next(p for p in oracle['polygons'] if p['event']==event and p['stage_integer']==3)
    check('oracle exact initial coordinates',[[Q(x) for x in p] for p in start]==[list(map(Q,p)) for p in polygon['coordinates_exact_rational']])
    tokens=(RUN/'inputs'/('%d_half.txt'%event)).read_text().split()
    check('input header',list(map(int,tokens[:4]))==[event,160,3,n] and len(tokens)==4+3*n)
    check('input binary64 initial path',path_equal(start,[[float(x) for x in tokens[i:i+3]] for i in range(4,len(tokens),3)]))
    mismatches=[]
    for name,actual,key in (('edges.csv',e0,'action'),('gradients.csv',g0,'component')):
        old=[r for r in benchmark[name] if int(r['event'])==event and r['stage']=='3']
        check('benchmark initial array inventory',len(old)==len(actual))
        for slot,(x,r) in enumerate(zip(actual,old)):
            y=number(r,key)
            if not bits_equal(x,y): mismatches.append(dict(table=name,slot=slot,actual_hex=x.hex(),benchmark_hex=y.hex()))
    old=next(r for r in benchmark['totals.csv'] if int(r['event'])==event and r['stage']=='3')
    if not bits_equal(number(history[0],'action'),number(old,'action')):
        mismatches.append(dict(table='totals.csv',actual_hex=history[0]['action_hex'],benchmark_hex=old['action_hex']))
    for row in history:
        for key in ('action','available_norm','ordinary_norm'): check('finite nonnegative history',number(row,key)>=0)
    check('no early target bypass',all(number(r,'available_norm')>1e-7 for r in history[:-1]))
    check('initial fraction absent',history[0]['accepted_step']==history[0]['accepted_step_hex']=='')
    for state,g,edges,row in (('initial',g0,e0,history[0]),('final',g1,e1,history[-1])):
        check('positive saved segment values',all(x>0 for x in edges))
        total=arithmetic.nearest(arithmetic.accumulated(map(Q,edges),64),53)
        check('saved segment outer total',Q(number(row,'action'))==total)
        free=[0.0 if (i,k) in fixed else g[3*(i-1)+k] for i in range(1,n-1) for k in range(3)]
        check('state norms from saved components',bits_equal(math.sqrt(dot(g,g)),number(row,'ordinary_norm'))
              and bits_equal(math.sqrt(dot(free,free)),number(row,'available_norm')))
    grouped={int(k):list(v) for k,v in itertools.groupby(trials,key=lambda r:r['update'])}
    check('ordered trial groups',[int(r['update']) for r in trials]==sorted(int(r['update']) for r in trials))
    path=start; accepted=0; seen=0; evaluated=0; contractions=0; pair_sums=0; accepted_paired=Q(0); terminal_reason=None
    attempts=[]; ordinary_disagreements=0
    for update in range(metrics):
        key,items=next(direction_groups,(None,None))
        check('direction group order',key==(event,update)); directions=list(items)
        check('complete direction nodes',[int(r['node']) for r in directions]==list(range(1,n-1)) and all(r['station']=='160' for r in directions))
        direction=[[number(r,k) for k in ('qx','qy','qz')] for r in directions]
        check('zero fixed search slots',all(direction[i-1][k]==0 for i,k in fixed))
        check('accepted state order',update==accepted and geometry_event(path,axes,fixed)=='')
        step=initial_step(path,direction,axes); trial_rows=grouped.get(update,[])
        if not (step>0 and math.isfinite(step)):
            check('empty physical step exit',not trial_rows and update==metrics-1); terminal_reason='physical_box_step_event'; break
        check('bounded attempts',1<=len(trial_rows)<=24 and [int(r['attempt']) for r in trial_rows]==list(range(len(trial_rows))))
        gradient=g0 if update==0 else (g1 if update==updates else None)
        if gradient is not None:
            nominal=dot(gradient,list(itertools.chain.from_iterable(direction)))
            check('nominal operand contraction',bits_equal(nominal,number(trial_rows[0],'nominal_slope')))
        base=number(history[update],'action'); accepted_this=False
        for attempt,row in enumerate(trial_rows):
            seen+=1; check('step halving and same nominal slope',bits_equal(step,number(row,'step'))
                            and bits_equal(number(row,'nominal_slope'),number(trial_rows[0],'nominal_slope')))
            slope=number(row,'nominal_slope'); check('strict recorded nominal descent',slope<0)
            rhs=arithmetic.nearest(arithmetic.nearest(Q(1e-4)*Q(step),64)*Q(slope),64)
            check('extended Armijo RHS',rhs==number(row,'armijo_rhs_extended',True))
            trial=rounded_trial(path,direction,step,fixed); reason=geometry_event(trial,axes,fixed); noop=trial==path
            check('fixed endpoints and normals',path_equal([trial[0],trial[-1]],[start[0],start[-1]])
                  and all(bits_equal(trial[i][k],start[i][k]) for i,k in fixed))
            check('recorded no-op',row['no_op']==str(int(noop)))
            if not reason and noop: reason='rounded_no_op'
            present=reason!='nonfinite_geometry'
            check('actual slope availability',(row['actual_slope_extended']!='')==present and (row['actual_slope_extended_hex']!='')==present)
            actual=number(row,'actual_slope_extended',True) if present else None
            check('actual descent sign',row['actual_descent']==str(int(present and actual<0)))
            if present and gradient is not None:
                products=(arithmetic.nearest(Q(gradient[3*(i-1)+k])*arithmetic.nearest(Q(trial[i][k])-Q(path[i][k]),64),64)
                          for i in range(1,n-1) for k in range(3))
                check('actual operand contraction',arithmetic.accumulated(products,64)==actual); contractions+=1
            if not reason and not actual<0: reason='rounded_non_descent'
            action=reason==''; check('action eligibility',row['action_evaluated']==str(int(action)))
            accepted_now=False
            if action:
                evaluated+=1; paired=number(row,'paired_change',True); change=number(row,'outer_change')
                # Similar positive totals satisfy Sterbenz: the recorded difference is exact.
                new=base+change
                check('recoverable recorded trial total',0<base/2<=new<=base*2 and Q(new)==Q(base)+Q(change)
                      and bits_equal(new-base,change))
                ordinary=new<=base+(1e-4*step)*slope; accepted_now=paired<=rhs
                check('ordinary and paired ledger decisions',row['ordinary_armijo']==str(int(ordinary)) and row['paired_armijo']==str(int(accepted_now)))
                ordinary_disagreements+=ordinary!=accepted_now
                reason='accepted' if accepted_now else 'paired_armijo_rejected'
                if updates==1 and update==0 and accepted_now:
                    check('single-update paired operands',arithmetic.accumulated((arithmetic.nearest(Q(a)-Q(b),64) for a,b in zip(e1,e0)),64)==paired); pair_sums+=1
                if accepted_now:
                    check('accepted update join',attempt==len(trial_rows)-1 and accepted<updates
                          and bits_equal(new,number(history[accepted+1],'action'))
                          and bits_equal(step,number(history[accepted+1],'accepted_step')))
                    accepted+=1; path=trial; accepted_this=True; accepted_paired+=paired
            else:
                check('absent unevaluated action',all(row[k]=='' for k in ('paired_change','paired_change_hex','outer_change','outer_change_hex'))
                      and row['ordinary_armijo']==row['paired_armijo']=='0')
            check('actual trial reason',reason==row['reason'])
            if reason not in ('accepted','paired_armijo_rejected','rounded_non_descent'):
                check('event terminates diagnostic',attempt==len(trial_rows)-1 and update==metrics-1); terminal_reason=reason
            step=step*0.5
        attempts.append(len(trial_rows))
        if not accepted_this:
            check('terminal failed update',update==metrics-1)
            if terminal_reason is None:
                check('halving budget exhausted',len(trial_rows)==24); terminal_reason='halving_budget'
    check('all trial groups consumed',set(grouped)==set(range(metrics))-(set([metrics-1]) if terminal_reason=='physical_box_step_event' else set()))
    check('reconstructed final path',path_equal(path,final) and geometry_event(final,axes,fixed)=='')
    check('accepted and attempted counts',accepted==updates and seen==len(trials)==int(summary['trials']) and metrics in (updates,updates+1))
    if updates==0: check('unchanged arrays with no accepted update',all(bits_equal(a,b) for a,b in zip(g0,g1)) and all(bits_equal(a,b) for a,b in zip(e0,e1)))
    if number(history[-1],'available_norm')<=1e-7:
        expected_stop='diagnostic_available_norm_reached'; check('target exit has no extra direction',metrics==updates)
    elif updates==1000:
        expected_stop='update_budget'; check('budget exit has no extra direction',metrics==updates)
    else:
        expected_stop=terminal_reason; check('failed exit has final direction',metrics==updates+1 and terminal_reason is not None)
    check('actual termination',summary['reason']==expected_stop)
    check('native call counts',int(summary['path_eval_calls'])==updates+1 and int(summary['extra_segment_calls'])==(n-1)*(1+evaluated))
    check('unchanged statuses',summary['original_convergence_flag']=='0' and summary['candidate_convergence_status']=='null'
          and all(summary[k]=='0' for k in ('trace_calls','field_calls','source_model_partials')))
    for key in ('action','ordinary_norm','available_norm'): check('final scalar join',bits_equal(number(summary,key),number(history[-1],key)))
    delta=Q(number(history[-1],'action'))-Q(number(history[0],'action'))
    exact_edges=sum((Q(a)-Q(b) for a,b in zip(e1,e0)),Q(0))
    changes=[number(b,'action')-number(a,'action') for a,b in zip(history,history[1:])]
    return dict(identity,reason=expected_stop,accepted_updates=updates,attempted_updates=metrics,trials=seen,
         action_evaluated_trials=evaluated,fixed_slots=len(fixed),attempt_counts=attempts,initial_benchmark_mismatches=mismatches,
         initial_available_norm_hex=history[0]['available_norm_hex'],final_available_norm_hex=history[-1]['available_norm_hex'],
         recorded_action_decreases=sum(v<0 for v in changes),recorded_action_equalities=sum(v==0 for v in changes),recorded_action_increases=sum(v>0 for v in changes),
         returned_action_change=delta,exact_sum_of_final_minus_initial_saved_double_edges=exact_edges,
         sum_of_recorded_accepted_paired_changes=accepted_paired,paired_ledger_minus_saved_endpoint_edge_delta=accepted_paired-exact_edges,
         ordinary_vs_paired_decision_differences=ordinary_disagreements,independent_actual_slope_contractions=contractions,
         independent_paired_edge_sums=pair_sums,original_convergence_flag='0',candidate_convergence_status=None,
         operand_scope='Every rounded geometry and scalar decision reconstructed. Intermediate gradient contractions and paired-edge sums lack saved operands and remain source-bound recorded values.')


def main():
    global arithmetic
    check('fresh review',not (HERE/'review.json').exists())
    approval=read(HERE/'source_review.json')
    check('checker source approval',approval['status']=='passed' and approval['checker_sha256']==sha(Path(__file__)))
    for key,name in (('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
        pin(RUN/name,approval[key])
    prepared=read(RUN/'prepared.json'); summary=read(RUN/'summary.json'); execution=read(RUN/'execution.json'); outer=read(RUN/'outer_reaping.json')
    check('terminal success',summary['status']==execution['status']=='completed_bounded_tangent_iteration' and summary['error'] is None
          and execution['return_code']==0 and execution['outputs_stable'] and execution['unsettled_groups']==[])
    check('owned outer reaping',outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_process_absent'] and outer['wrapper_pid']==execution['pid'])
    for key,name in (('prepared_sha256','prepared.json'),('summary_sha256','summary.json'),('execution_sha256','execution.json'),('prelaunch_review_sha256','prelaunch_review.json')): pin(RUN/name,outer[key])
    check('terminal preparation',summary['prepared_sha256']==execution['prepared_sha256']==sha(RUN/'prepared.json')
          and execution['summary_sha256']==sha(RUN/'summary.json') and summary['output_sha256']==execution['output_sha256'])
    prelaunch=read(RUN/'prelaunch_review.json')
    check('native prelaunch gate',prelaunch['status']=='passed' and prelaunch['prepared_sha256']==sha(RUN/'prepared.json')
          and execution['prelaunch_review_sha256']==sha(RUN/'prelaunch_review.json'))
    check('unchanged outer status and scope',summary['original_convergence_flag']=='0' and summary['candidate_convergence_status'] is None
          and all(summary[k]==0 for k in ('trace_calls','field_calls','source_model_partials','new_reference_integrations')))
    check('two reaped commands',[r['command'] for r in execution['commands']]==prepared['commands'] and len(execution['commands'])==2
          and all(r['return_code']==0 and r['child_reaped'] for r in execution['commands']))
    check('separate multiply/add compiler flag','-ffp-contract=off' in prepared['commands'][0])
    for base,key in ((ROOT,'input_sha256'),(RUN,'output_sha256'),(Path('/'),'runtime_sha256')):
        for name,digest in prepared[key].items(): pin(base/name,digest)
    for name,digest in summary['output_sha256'].items(): pin(RUN/name,digest)
    check('closed output inventory',set(summary['output_sha256'])=={str(p.relative_to(RUN)) for d in ('results','logs','build') for p in (RUN/d).rglob('*') if p.is_file()})
    bench_review=read(BENCH/'review.json'); pin(BENCH/'review_saved.py',bench_review['checker_sha256'])
    check('reviewed pure scalar helper',bench_review['status']=='passed')
    for folder,review,prefix in ((BENCH,bench_review,''),(POST,read(POST_REVIEW),'native_')):
        check('prior independent review',review['status']=='passed')
        for key,name in ((prefix+'prepared_sha256','prepared.json'),(prefix+'summary_sha256','summary.json'),
                         (prefix+'execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')): pin(folder/name,review[key])
    spec=importlib.util.spec_from_file_location('reviewed_saved_scalar_arithmetic',str(BENCH/'review_saved.py'))
    arithmetic=importlib.util.module_from_spec(spec); spec.loader.exec_module(arithmetic)
    identities=read(RUN/'native_contexts.json')
    check('full terminal native identities',identities==summary['native_contexts']==execution['native_contexts']==outer['native_contexts']==read(BENCH/'native_contexts.json')
          and [r['event'] for r in identities]==[981,987])
    catalog=list(rows(ROOT/'data/hayward/observations.csv'))
    pin(ROOT/'data/hayward/observations.csv','8c270875d675f07a5aa66d0471cd8f8a17c8f25b041e0eb6d2eb165784546a2c')
    for identity in identities:
        check('nine original catalog uses',identity['station']==160 and len(identity['catalog_uses'])==9)
        for use in identity['catalog_uses']: check('complete original catalog rows',catalog[use['zero_based_observation_row']]==use['original_row'])
        status=identity['native_context']['original_status']
        check('false original flags and blank source partials',status['ray_converged']==status['ray_derivatives_evaluated']=='0' and all(status['source_d'+k]=='' for k in 'xyz'))
    names=('summary.csv','updates.csv','trials.csv','directions.csv','paths.csv','gradients.csv','edges.csv','readback.json')
    for name in names:
        side=read(RUN/'results'/(name+'.identifiers.json'))
        check('prewritten native output sidecar',side['native_contexts']==identities and side['prepared_sha256']==sha(RUN/'prepared.json')
              and side['expected_file']==str((RUN/'results'/name).relative_to(ROOT)) and side['original_convergence_flag']=='0' and side['candidate_convergence_status'] is None)
    compression=read(RUN/'results/compression.json'); packed=RUN/'results/directions.csv.gz'
    side=read(Path(str(packed)+'.identifiers.json')); h=hashlib.sha256(); count=0
    with gzip.open(str(packed),'rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''): h.update(block); count+=len(block)
    check('lossless reaped direction archive',compression['native_contexts']==side['native_contexts']==identities
          and compression['raw_file']=='directions.csv' and compression['gzip_file']==packed.name
          and compression['gzip_sha256']==sha(packed) and compression['raw_sha256']==side['uncompressed_sha256']==h.hexdigest()
          and compression['raw_bytes']==count and compression['decompression_verified'] and compression['after_child_reaped'])
    check('archive path and preparation',side['prepared_sha256']==sha(RUN/'prepared.json') and side['expected_file']==str(packed.relative_to(ROOT))
          and side['uncompressed_file']==str((RUN/'results/directions.csv').relative_to(ROOT)) and not (RUN/'results/directions.csv').exists())
    records={name:list(rows(RUN/'results'/name)) for name in names if name.endswith('.csv') and name!='directions.csv'}
    check('two native table cases',[int(r['event']) for r in records['summary.csv']]==[981,987]
          and all(r['event'] in ('981','987') and r['station']=='160' for values in records.values() for r in values))
    directions=itertools.groupby(rows(packed),key=lambda r:(int(r['event']),int(r['update'])))
    grid=(RUN/'inputs/grid.txt').read_text().split(); dims=list(map(int,grid[:3])); axes=[]; offset=3
    for n in dims: axes.append(tuple(float(x) for x in grid[offset:offset+n])); offset+=n
    check('frozen grid shape',dims[0]*dims[1]*dims[2]==462 and len(grid)==offset+462)
    benchmark={name:list(rows(BENCH/'results'/name)) for name in ('totals.csv','edges.csv','gradients.csv')}; oracle=read(BENCH/'oracle.json.gz')
    reports=[case(identity,{name:[r for r in values if int(r['event'])==identity['event']] for name,values in records.items()},directions,axes,benchmark,oracle) for identity in identities]
    check('no extra directions',next(directions,None) is None)
    wrapper=read(RUN/'results/readback.json'); check('wrapper result binding',wrapper==summary['result'])
    check('wrapper case roster',[r['event'] for r in wrapper['cases']]==[981,987])
    for report,record in zip(reports,wrapper['cases']):
        check('wrapper native counts',all(report[k]==record[k] for k in ('event','station','native_context','catalog_uses','accepted_updates'))
              and report['trials']==record['recorded_trials'] and record['direction_rows']==report['attempted_updates']*((1029 if report['event']==981 else 1031)-2))
        check('wrapper driver summary',record['driver_summary']==next(r for r in records['summary.csv'] if int(r['event'])==report['event']))
        check('initial benchmark bridge',not report['initial_benchmark_mismatches'] and record['initial_benchmark_bitwise_match'])
    check('no initial mismatch hidden',wrapper['initial_mismatches']==[])
    for p in (Path(__file__),HERE/'README.md',HERE/'source_review.json'): pin(p,sha(p))
    for path,digest in list(PINS.items()): pin(Path(path),digest)
    review=dict(status='passed',native_prepared_sha256=sha(RUN/'prepared.json'),native_summary_sha256=sha(RUN/'summary.json'),native_execution_sha256=sha(RUN/'execution.json'),
         outer_reaping_sha256=sha(RUN/'outer_reaping.json'),checker_sha256=sha(Path(__file__)),source_review_sha256=sha(HERE/'source_review.json'),
         native_contexts=identities,cases=reports,checks=CHECKS,pure_scalar_checks=arithmetic.CHECKS,input_sha256=PINS,
         new_evaluator_calls=0,new_gradient_integrations=0,new_metric_calls=0,new_compiler_calls=0,
         limitations=['Intermediate contractions and edge differences are recorded approximate values; their omitted operands are not reconstructed.',
                      'This ledger does not certify exact intermediate or net Fermat decrease, full stationarity, source derivatives or first arrival.',
                      'Original flags remain false; the available-norm target applies only to this fixed search subspace. Final interval audit is separate.'])
    with (HERE/'review.json').open('x') as stream: json.dump(arithmetic.encoded(review),stream,indent=2,sort_keys=True,allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status='passed',review_sha256=sha(HERE/'review.json'))))


if __name__=='__main__': main()
