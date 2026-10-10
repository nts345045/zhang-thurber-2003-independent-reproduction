#!/usr/bin/env python3
"""Read saved capture records only; never import or execute a ray evaluator."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'data/development/loma_curvature_capture_native_001'
RUN='fmm_0.031250_1000'
PAIR='3426'
OLD=('results.csv','history.csv','paths.csv','path_gradient_checks.csv','cone_metric.csv')
NEW=('curvature_pairs.csv','curvature_components.csv.gz','curvature_selected_geometry.csv',
     'curvature_selected_cuts.csv','curvature_initialization.csv','curvature_seed_metadata.csv','curvature_memory_events.csv')


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def load(path):return json.loads(path.read_text())


def records(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(str(path),'rt',newline='') as f:
        for row in csv.DictReader(f):yield row


def number(value):
    result=float(value);need(math.isfinite(result),'Nonfinite required numeric field');return result


def fraction(value):return Q.from_float(number(value))


def dot(a,b):
    total=0.
    for x,y in zip(a,b):total+=x*y
    return total


def norm3(a):return math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])


def ids(text):return [int(x) for x in text.split(';')] if text else []


def same_key(row,iteration=None):
    need(row['run_id']==RUN and row['observation_index']==PAIR,'Captured native join mismatch')
    if iteration is not None:need(int(row['iteration'])==iteration,'Captured iteration order mismatch')


def point(row):return [number(row[a]) for a in 'xyz']


def verify_map(base,mapping):
    for name,digest in mapping.items():need(sha(base/name)==digest,'Hash mismatch: '+str(base/name))


def representative(pair,rows,result):
    ss=yy=sy=absolute=actual_dot=movement_error=Q(0);different=0
    for row in rows:
        for axis in 'xyz':
            s,y,a=(fraction(row[prefix+axis]) for prefix in ('s_','y_','rounded_displacement_'))
            sy+=s*y;absolute+=abs(s*y);ss+=s*s;yy+=y*y;actual_dot+=a*y
            movement_error+=(a-s)**2;different+=a!=s
    expected={'exact_stored_s_dot_y':sy,'exact_actual_displacement_dot_y':actual_dot,
              'exact_s_squared':ss,'exact_y_squared':yy,'exact_sum_absolute_products':absolute,
              'exact_displacement_difference_squared':movement_error,
              'exact_dot_minus_computed_sy':sy-fraction(pair['computed_sy'])}
    for key,value in expected.items():need(Q(result[key])==value,'Independent rational mismatch: '+key)
    need(int(result['rounded_displacement_different_components'])==different,'Different movement count mismatch')
    need(result['exact_normalized_cancellation_ratio']==('' if absolute==0 else str(sy/absolute)),
         'Exact cancellation ratio mismatch')


def main():
    need(not (OUT/'review.json').exists() and not (HERE/'readback.json').exists(),'Review output already exists')
    summary,execution,prepared,controller,packaging=[load(OUT/name) for name in
        ('summary.json','execution.json','prepared.json','controller_completion.json','packaging_receipt.json')]
    need(summary['status']=='completed_neutral_curvature_capture' and execution['status']=='completed' and
         execution['return_code']==0 and execution['summary_sha256']==sha(OUT/'summary.json'),'Native capture not terminal')
    need(controller['status']=='completed' and controller['summary_sha256']==sha(OUT/'summary.json') and
         controller['execution_sha256']==sha(OUT/'execution.json') and
         controller['launch_sha256']==sha(OUT/'launch.json'),'Controller terminal links mismatch')
    need(controller['child_reaped'] is True and controller['driver_return_code']==0 and
         controller['controller_sha256']==sha(OUT/'controller.py'),'Controller child lifecycle mismatch')
    need(all(c['status']=='completed' and c['return_code']==0 for c in summary['commands']),'Incomplete recorded child command')
    need(summary['prepared_sha256']==sha(OUT/'prepared.json') and
         summary['prelaunch_review_sha256']==sha(OUT/'prelaunch_review.json'),'Preparation/review link mismatch')
    need(load(OUT/'prelaunch_review.json')['status']=='passed','Prelaunch review not passed')
    verify_map(ROOT,prepared['input_sha256']);verify_map(OUT,prepared['prepared_file_sha256'])
    verify_map(OUT/'source',summary['source_sha256']);verify_map(OUT,summary['output_sha256'])
    verify_map(OUT,controller['log_sha256'])
    need(sha(Path(summary['compiler']))==summary['compiler_sha256'],'Compiler pin changed')
    need(sha(ROOT/summary['build']/'observe')==summary['binary_sha256'],'Binary pin changed')
    verify_map(Path('/'),summary['runtime_library_sha256'])
    baseline=ROOT/prepared['baseline']
    for name,digest in prepared['expected_old_table_sha256'].items():
        need(sha(OUT/name)==sha(baseline/name)==digest,'Frozen B table changed: '+name)
    for file in (OUT/'source/src').glob('*'):
        if file.is_file():need(file.read_bytes()==(baseline/'source/src'/file.name).read_bytes(),'Numerical source changed')
    context=prepared['native_context']
    need(list(records(OUT/'identified_ray.csv'))==[context] and summary['native_context']==context,'Full native context mismatch')
    need(context['observation_index']==PAIR,'Wrong native pair')
    for name in OLD+NEW+('exact_sums/exact_sums.csv',):
        side=load(OUT/(name+'.identifiers.json'))
        need(side['file_sha256']==sha(OUT/name) and side['native_context']==context and
             side['join_key']=='observation_index' and side['join_value']==PAIR and
             side['context_sha256']==sha(OUT/'identified_ray.csv'),'Native sidecar mismatch: '+name)
    # The metadata-only attachment is separate from the frozen numerical output.
    storage=summary['component_storage'];raw=ROOT/storage['local_retained_raw_file']
    need(sha(raw)==storage['uncompressed_sha256'] and raw.stat().st_size==storage['uncompressed_bytes'],
         'Retained raw components mismatch')
    raw_side_path=raw.with_name(raw.name+'.identifiers.json')
    raw_side=load(raw_side_path)
    need(raw_side['file_sha256']==storage['uncompressed_sha256'] and raw_side['native_context']==context and
         raw_side['join_key']=='observation_index' and raw_side['join_value']==PAIR and
         raw_side['context_sha256']==sha(OUT/'identified_ray.csv') and ROOT/raw_side['context_csv']==OUT/'identified_ray.csv',
         'Raw component identity attachment mismatch')
    need(packaging['status']=='completed_metadata_attachment' and
         packaging['native_summary_sha256']==sha(OUT/'summary.json') and
         packaging['native_execution_sha256']==sha(OUT/'execution.json') and
         packaging['controller_completion_sha256']==sha(OUT/'controller_completion.json'),
         'Metadata attachment terminal links mismatch')
    need(ROOT/packaging['gzip_file']==OUT/'curvature_components.csv.gz' and
         ROOT/packaging['raw_file']==raw and ROOT/packaging['raw_identifiers_file']==raw_side_path and
         packaging['gzip_sha256']==sha(OUT/'curvature_components.csv.gz') and
         packaging['raw_sha256']==storage['uncompressed_sha256'] and
         packaging['raw_identifiers_sha256']==sha(raw_side_path) and packaging['raw_bytes']==storage['uncompressed_bytes'],
         'Metadata attachment storage mismatch')
    need(ROOT/packaging['context_csv']==OUT/'identified_ray.csv' and packaging['context_sha256']==sha(OUT/'identified_ray.csv') and
         packaging['native_context']==context,'Metadata attachment full native context mismatch')
    verify_map(ROOT,packaging['input_sha256']);verify_map(ROOT,packaging['output_sha256'])
    uncompressed=hashlib.sha256();uncompressed_bytes=0
    with gzip.open(str(OUT/'curvature_components.csv.gz'),'rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            uncompressed.update(block);uncompressed_bytes+=len(block)
    need(uncompressed.hexdigest()==storage['uncompressed_sha256'] and uncompressed_bytes==storage['uncompressed_bytes'],
         'Gzip decoded bytes differ from raw')
    results=list(records(OUT/'results.csv'));fmm=[r for r in results if r['run_id']==RUN]
    need(len(results)==2 and len(fmm)==1 and all(r['logged_matches_unobserved_variant']=='1' for r in results),
         'Same-variant reported numeric parity failed')
    fmm=fmm[0];nodes=int(fmm['path_nodes']);dimension=3*(nodes-2)
    need(fmm['converged']=='0' and fmm['updates']=='1000','Original FMM stopping changed')
    history=[r for r in records(OUT/'history.csv') if r['run_id']==RUN]
    initial=[r for r in history if r['phase']=='initial'];final=[r for r in history if r['phase']=='final']
    accepted=[r for r in history if r['phase']=='accepted']
    need(len(initial)==len(final)==1 and len(accepted)==1000 and len(history)==1002,'FMM history inventory changed')
    need([int(r['iteration']) for r in accepted]==list(range(1000)) and final[0]['iteration']=='1000',
         'Accepted iteration inventory changed')
    pairs=list(records(OUT/'curvature_pairs.csv'));need(len(pairs)==1000,'Pair inventory incomplete')
    events=list(records(OUT/'curvature_memory_events.csv'))
    need(not events and all(r['gradient_fallback']=='0' and r['merged_nodes']=='0' for r in accepted),
         'Unexpected memory reset/topology change in unchanged B')
    memory=[];last_time=number(initial[0]['time_s']);retained=[];objective_counts=dict(decreases=0,equals=0,increases=0)
    for i,(pair,hist) in enumerate(zip(pairs,accepted)):
        same_key(pair,i);same_key(hist,i)
        need(int(pair['update'])==i+1==int(hist['updates']) and int(pair['components'])==dimension,'Pair dimensions/update mismatch')
        need(ids(pair['memory_before_ids'])==memory and ids(pair['memory_before_ages'])==[i-v for v in memory],
             'Pre-decision memory IDs/ages mismatch')
        keep=number(pair['computed_sy'])>number(pair['threshold'])
        need(number(pair['threshold'])==1e-14 and pair['retained']==str(int(keep))==hist['curvature_pair_accepted'],
             'Actual curvature decision mismatch')
        if keep:memory=(memory+[i])[-8:];retained.append(i)
        need(ids(pair['memory_after_ids'])==memory and ids(pair['memory_after_ages'])==[i-v for v in memory] and
             int(pair['memory_after_size'])==len(memory)==int(hist['memory_pairs']),'Post-decision memory IDs/ages mismatch')
        for pk,hk in [('accepted_action_s','time_s'),('step','accepted_step'),('directional_slope','directional_slope')]:
            need(number(pair[pk])==number(hist[hk]),'Pair/history scalar mismatch: '+pk)
        now=number(pair['accepted_action_s']);base=number(pair['base_action_s']);step=number(pair['step']);slope=number(pair['directional_slope'])
        need(base==last_time and number(hist['action_change_s'])==abs(base-now),'Accepted objective chain mismatch')
        rhs=base+1e-4*step*slope
        need(number(pair['armijo_rhs_s'])==rhs and now<=rhs,'Recorded binary64 Armijo mismatch')
        objective_counts['decreases' if now<base else 'equals' if now==base else 'increases']+=1
        last_time=now
    need(len(retained)==40 and retained[-1]==434 and memory==ids(pairs[-1]['memory_after_ids']),
         'Frozen B retained-memory endpoint changed')
    grid=list(records(OUT/'inputs/initial_grid.csv'));axes=[sorted({number(r[a]) for r in grid}) for a in 'xyz']
    selected=set(prepared['selected_iterations']);geometry={}
    for row in records(OUT/'curvature_selected_geometry.csv'):
        same_key(row);key=(int(row['iteration']),row['state']);path=geometry.setdefault(key,[])
        need(int(row['node'])==len(path),'Selected node order mismatch');path.append(row)
    need(set(geometry)=={(i,s) for i in selected for s in ('base','accepted')},'Selected state inventory mismatch')
    for (i,state),path in geometry.items():
        need(len(path)==nodes,'Selected topology mismatch')
        for j,row in enumerate(path):
            endpoint=j==0 or j==nodes-1
            need(row['is_endpoint']==str(int(endpoint)),'Endpoint flag mismatch')
            p=point(row);need(all(axis[0]<=p[a]<=axis[-1] for a,axis in enumerate(axes)),'Selected point outside box')
            for field in ['gradient_'+a for a in 'xyz']+['q_'+a for a in 'xyz']:
                if endpoint:need(row[field]=='','Endpoint derivative should be blank')
                else:number(row[field])
        for row,prefix in [(path[0],'source'),(path[-1],'receiver')]:
            need(point(row)==[number(context[prefix+'_'+a+'_km']) for a in 'xyz'],'Selected exact endpoint mismatch')
    exact_rows=list(records(OUT/'exact_sums/exact_sums.csv'))
    need(len(exact_rows)==1000,'Exact sum inventory mismatch')
    exact_summary=load(OUT/'exact_sums/summary.json')
    verify_map(ROOT,exact_summary['input_sha256']);verify_map(OUT/'exact_sums',exact_summary['output_sha256'])
    below=[i for i,p in enumerate(pairs) if number(p['computed_sy'])<=number(p['threshold'])]
    above=[i for i,p in enumerate(pairs) if number(p['computed_sy'])>number(p['threshold'])]
    edge_cases=dict(minimum_computed_sy=min(range(1000),key=lambda i:number(pairs[i]['computed_sy'])),
                   minimum_absolute_computed_sy=min(range(1000),key=lambda i:abs(number(pairs[i]['computed_sy']))),
                   minimum_exact_stored_sy=min(range(1000),key=lambda i:Q(exact_rows[i]['exact_stored_s_dot_y'])))
    if below:edge_cases['nearest_threshold_below_or_equal']=min(below,key=lambda i:abs(fraction(pairs[i]['computed_sy'])-fraction(pairs[i]['threshold'])))
    if above:edge_cases['nearest_threshold_above']=min(above,key=lambda i:abs(fraction(pairs[i]['computed_sy'])-fraction(pairs[i]['threshold'])))
    representative_iters=selected|{0}|set(edge_cases.values())
    component_count=0;selected_scalar_checks=0
    groups=itertools.groupby(records(OUT/'curvature_components.csv.gz'),lambda r:int(r['iteration']))
    for i,pair in enumerate(pairs):
        key,entries=next(groups,(None,None));need(key==i,'Missing/reordered component group')
        saved=[];sy=ss=yy=0.;n=0
        for n,row in enumerate(entries,1):
            same_key(row,i);need(int(row['node'])==n,'Component node order mismatch')
            for axis in 'xyz':
                s=number(row['s_'+axis]);y=number(row['y_'+axis]);movement=number(row['rounded_displacement_'+axis])
                sy+=s*y;ss+=s*s;yy+=y*y
                if i in selected:
                    before=geometry[i,'base'][n];after=geometry[i,'accepted'][n];q=number(before['q_'+axis]);step=number(pair['step'])
                    need(q==number(after['q_'+axis]) and s==step*q,'Saved s versus step*q mismatch')
                    need(y==number(after['gradient_'+axis])-number(before['gradient_'+axis]),'Saved y versus gradient change mismatch')
                    need(number(after[axis])==number(before[axis])+step*q and movement==number(after[axis])-number(before[axis]),
                         'Accepted coordinate construction/rounded movement mismatch')
                    selected_scalar_checks+=1
            if i in representative_iters:saved.append(row)
            component_count+=1
        need(n==nodes-2 and number(pair['computed_sy'])==sy and number(pair['s_squared'])==ss and number(pair['y_squared'])==yy,
             'Component count or sequential dot/norm reconstruction mismatch')
        need(number(pair['s_norm'])==math.sqrt(ss) and number(pair['y_norm'])==math.sqrt(yy),'Saved norm mismatch')
        if ss>0 and yy>0:need(number(pair['normalized_sy'])==sy/(math.sqrt(ss)*math.sqrt(yy)),'Normalized sy mismatch')
        else:need(pair['normalized_sy']=='','Undefined normalized sy must be blank')
        if i in representative_iters:representative(pair,saved,exact_rows[i])
        if (i+1)%100==0:print('Checked component groups',i+1,flush=True)
    need(next(groups,None) is None,'Trailing component group')
    # Full selected gradients and directions are read back, never reevaluated.
    for i in sorted(selected):
        before,after=geometry[i,'base'],geometry[i,'accepted'];g=[number(r['gradient_'+a]) for r in after[1:-1] for a in 'xyz']
        oldg=[number(r['gradient_'+a]) for r in before[1:-1] for a in 'xyz'];q=[number(r['q_'+a]) for r in before[1:-1] for a in 'xyz']
        need(dot(oldg,q)==number(pairs[i]['directional_slope']),'Selected directional slope mismatch')
        need(math.sqrt(dot(g,g))==number(accepted[i]['raw_gradient']),'Selected raw gradient norm mismatch')
        projected=[]
        for row in after[1:-1]:
            for a,axis in zip('xyz',axes):
                value=number(row['gradient_'+a]);coordinate=number(row[a])
                if (coordinate<=axis[0]+1e-10 and value>0) or (coordinate>=axis[-1]-1e-10 and value<0):value=0.
                projected.append(value)
        need(math.sqrt(dot(projected,projected))==number(accepted[i]['projected_gradient']),'Selected projected norm mismatch')
        move=max(abs(number(pairs[i]['step']))*norm3(q[k:k+3]) for k in range(0,len(q),3))
        need(move==number(accepted[i]['max_node_step_km']),'Selected reported step norm mismatch')
        if i+1 in selected:
            need([point(r) for r in after]==[point(r) for r in geometry[i+1,'base']],'Adjacent selected path continuity mismatch')
    last_path=[r for r in records(OUT/'paths.csv') if r['run_id']==RUN]
    need([point(r) for r in geometry[999,'accepted']]==[point(r) for r in last_path],'Final selected path differs from frozen B')
    cuts=iter(records(OUT/'curvature_selected_cuts.csv'));cut_count=0
    for i in sorted(selected):
        for state in ('base','accepted'):
            path=geometry[i,state];closest=0;worst=1;distance=math.inf;greatest=-1
            for j,row in enumerate(path[1:-1],1):
                for a,axis in zip('xyz',axes):
                    value=abs(number(row['gradient_'+a]))
                    if value>greatest:greatest=value;worst=j
                    for plane in axis[1:-1]:
                        gap=abs(number(row[a])-plane)
                        if gap<distance:distance=gap;closest=j
            for selection,j in [('closest_internal_plane',closest),('largest_gradient_component',worst)]:
                if not j:continue
                for end in (j,j+1):
                    a,b=point(path[end-1]),point(path[end])
                    for axis_index,axis in enumerate(axes):
                        for k,plane in enumerate(axis):
                            row=next(cuts);same_key(row,i);delta=b[axis_index]-a[axis_index];axis_ok=abs(delta)>1e-12
                            t=(plane-a[axis_index])/delta if axis_ok else None
                            used=axis_ok and t>1e-10 and t<1-1e-10
                            need(row['state']==state and row['selection']==selection and int(row['selected_node'])==j and
                                 int(row['edge_end_node'])==end and int(row['axis'])==axis_index and int(row['plane_index'])==k,
                                 'Cut inventory/order mismatch')
                            need(number(row['plane_value'])==plane and number(row['axis_delta'])==delta and
                                 row['axis_test_pass']==str(int(axis_ok)) and row['used']==row['parameter_test_pass']==str(int(used)),
                                 'Cut predicate mismatch')
                            need(number(row['parameter'])==t if axis_ok else row['parameter']=='','Cut parameter mismatch')
                            need([number(row['a_'+x]) for x in 'xyz']==a and [number(row['b_'+x]) for x in 'xyz']==b,'Cut edge frame mismatch')
                            cut_count+=1
    need(next(cuts,None) is None,'Trailing cut inventory')
    initialization={}
    for row in records(OUT/'curvature_initialization.csv'):
        same_key(row);path=initialization.setdefault(row['kind'],[]);need(int(row['node'])==len(path),'Seed node order mismatch');path.append(point(row))
    need(set(initialization)=={'raw_fmm_seed','post_resampling_and_merge'},'Seed kinds mismatch')
    raw_seed=initialization['raw_fmm_seed'];resampled=initialization['post_resampling_and_merge'];arc=[0.]
    for a,b in zip(raw_seed,raw_seed[1:]):arc.append(arc[-1]+norm3([y-x for x,y in zip(a,b)]))
    n=max(2,int(math.ceil(arc[-1]/prepared['path_spacing_km'])));reconstructed=[raw_seed[0]];j=1
    for i in range(1,n):
        distance=arc[-1]*i/n
        while j+1<len(arc) and arc[j]<=distance:j+=1
        weight=(distance-arc[j-1])/(arc[j]-arc[j-1])
        reconstructed.append([a+(b-a)*weight for a,b in zip(raw_seed[j-1],raw_seed[j])])
    reconstructed.append(raw_seed[-1]);j=1;merged=0
    while j<len(reconstructed) and len(reconstructed)>2:
        if norm3([b-a for a,b in zip(reconstructed[j-1],reconstructed[j])])<1e-8:
            erase=j if j+1<len(reconstructed) else j-1;del reconstructed[erase];merged+=1;j=erase-1 if erase>1 else 1
        else:j+=1
    need(reconstructed==resampled and len(resampled)==nodes,'Frozen geometric seed resampling mismatch')
    need(all(all(axis[0]<=p[a]<=axis[-1] for a,axis in enumerate(axes)) for path in initialization.values() for p in path),
         'Seed leaves original box')
    for path in initialization.values():
        need(path[0]==[number(context['source_'+a+'_km']) for a in 'xyz'] and
             path[-1]==[number(context['receiver_'+a+'_km']) for a in 'xyz'],'Seed exact native endpoints mismatch')
    seed=list(records(OUT/'curvature_seed_metadata.csv'));need(len(seed)==1,'Seed metadata inventory mismatch');same_key(seed[0])
    need(seed[0]['success']=='1' and format(number(seed[0]['field_time_s']),'.12g')==context['ray_field_time'] and
         seed[0]['fallback_steps']==context['ray_extraction_fallback_steps'],'Saved seed metadata mismatch')
    need(int(seed[0]['descent_steps'])>=0 and int(seed[0]['fallback_steps'])>=0,'Negative seed counter')
    counts=dict(pairs=0,rounded_dot_mismatches=0,computed_positive_rejected=0,exact_stored_dot_positive_rejected=0,
                exact_actual_dot_positive_rejected=0,exact_stored_dot_nonpositive_retained=0,stored_s_differs_from_actual_displacement=0,
                recorded_binary64_armijo_failures=0,exact_declared_recorded_total_armijo_failures=0)
    classification=dict(computed_positive=0,exact_stored_positive=0,exact_actual_movement_positive=0,
                        exact_stored_exceeds_threshold=0,exact_actual_movement_exceeds_threshold=0,
                        exact_stored_threshold_differs_from_recorded_retention=0,
                        exact_actual_movement_threshold_differs_from_recorded_retention=0)
    for i,(r,p) in enumerate(zip(exact_rows,pairs)):
        same_key(r,i);need(r['retained']==p['retained'] and r['update']==p['update'] and
                           int(r['components'])==dimension,'Exact sum decision mapping mismatch')
        need(number(r['computed_sy'])==number(p['computed_sy'])==number(r['rounded_dot_reconstruction']) and
             r['rounded_dot_matches_computed']=='1','Exact table sequential-dot mapping mismatch')
        need(Q(r['exact_binary64_threshold'])==fraction(p['threshold']), 'Exact table threshold mismatch')
        sy,actual=Q(r['exact_stored_s_dot_y']),Q(r['exact_actual_displacement_dot_y']);rejected=p['retained']=='0'
        need(int(r['exact_stored_s_dot_y_sign'])==(sy>0)-(sy<0) and int(r['exact_actual_displacement_dot_y_sign'])==(actual>0)-(actual<0),'Exact sign inventory mismatch')
        need(int(r['exact_dot_exceeds_binary64_threshold'])==int(sy>fraction(p['threshold'])) and
             Q(r['exact_dot_minus_computed_sy'])==sy-fraction(p['computed_sy']), 'Exact threshold/error classification mismatch')
        need(Q(r['exact_difference_of_recorded_action_totals'])==fraction(p['accepted_action_s'])-fraction(p['base_action_s']),
             'Exact recorded-total difference mismatch')
        margin=fraction(p['base_action_s'])+Q.from_float(1e-4)*fraction(p['step'])*fraction(p['directional_slope'])-fraction(p['accepted_action_s'])
        need(Q(r['exact_declared_recorded_total_armijo_margin'])==margin and int(r['exact_declared_recorded_total_armijo_pass'])==int(margin>=0),
             'Exact recorded-total Armijo algebra mismatch')
        need(Q(r['exact_rhs_rounding_error'])==fraction(p['armijo_rhs_s'])-fraction(p['accepted_action_s'])-margin and
             r['recorded_binary64_armijo_pass']=='1' and r['rhs_binary64_reconstruction_matches']=='1',
             'Recorded Armijo classification/rounding mismatch')
        counts['pairs']+=1;counts['rounded_dot_mismatches']+=not int(r['rounded_dot_matches_computed'])
        counts['computed_positive_rejected']+=rejected and number(p['computed_sy'])>0
        counts['exact_stored_dot_positive_rejected']+=rejected and sy>0
        counts['exact_actual_dot_positive_rejected']+=rejected and actual>0
        counts['exact_stored_dot_nonpositive_retained']+=not rejected and sy<=0
        counts['stored_s_differs_from_actual_displacement']+=int(r['rounded_displacement_different_components'])>0
        counts['recorded_binary64_armijo_failures']+=not int(r['recorded_binary64_armijo_pass'])
        counts['exact_declared_recorded_total_armijo_failures']+=margin<0
        threshold=fraction(p['threshold']);recorded_retained=not rejected
        classification['computed_positive']+=number(p['computed_sy'])>0
        classification['exact_stored_positive']+=sy>0
        classification['exact_actual_movement_positive']+=actual>0
        classification['exact_stored_exceeds_threshold']+=sy>threshold
        classification['exact_actual_movement_exceeds_threshold']+=actual>threshold
        classification['exact_stored_threshold_differs_from_recorded_retention']+=(sy>threshold)!=recorded_retained
        classification['exact_actual_movement_threshold_differs_from_recorded_retention']+=(actual>threshold)!=recorded_retained
    need(counts==exact_summary['counts']==summary['exact_sums'],'Reported exact-sum count inventory mismatch')
    actual_counts={}
    for name in OLD+NEW:
        if name=='curvature_components.csv.gz':actual_counts[name]=component_count;continue
        count=0
        for row in records(OUT/name):
            need(row['observation_index']==PAIR and row['run_id'] in ({r['run_id'] for r in results} if name in OLD else {RUN}),
                 'Full table native identity mismatch: '+name);count+=1
        actual_counts[name]=count
    need(actual_counts==summary['capture_counts'],'Capture count inventory mismatch')
    verify_map(ROOT,prepared['input_sha256']);verify_map(OUT,summary['output_sha256'])
    verify_map(ROOT,packaging['input_sha256']);verify_map(ROOT,packaging['output_sha256'])
    ranges={}
    for label,subset in [('all',pairs),('retained',[p for p in pairs if p['retained']=='1']),('rejected',[p for p in pairs if p['retained']=='0'])]:
        ranges[label]=dict(minimum_computed_sy=min(number(p['computed_sy']) for p in subset),
                           maximum_computed_sy=max(number(p['computed_sy']) for p in subset),count=len(subset))
    review=dict(status='passed_saved_capture_review',material_issue_found=False,summary_sha256=sha(OUT/'summary.json'),
                execution_sha256=sha(OUT/'execution.json'),prepared_sha256=sha(OUT/'prepared.json'),
                controller_completion_sha256=sha(OUT/'controller_completion.json'),packaging_receipt_sha256=sha(OUT/'packaging_receipt.json'),
                checker_sha256=sha(Path(__file__)),checker_path=str(Path(__file__).resolve().relative_to(ROOT)),
                native_context=context,verified_input_count=len(prepared['input_sha256']),verified_prepared_count=len(prepared['prepared_file_sha256']),
                verified_source_count=len(summary['source_sha256']),verified_output_count=len(summary['output_sha256']),
                old_B_tables_byte_identical=5,accepted_pair_records=1000,retained_pairs=len(retained),last_retained_iteration=retained[-1],
                final_memory_ids=memory,final_memory_ages_at_iteration_999=[999-i for i in memory],
                pair_records_after_last_retained=999-retained[-1],computed_sy_ranges=ranges,
                exact_classification_inventory=classification,
                objective_comparison_counts=objective_counts,component_records=component_count,
                selected_iterations=sorted(selected),selected_component_checks=selected_scalar_checks,cut_records=cut_count,
                initialization_nodes={k:len(v) for k,v in initialization.items()},resampling_merged_nodes=merged,
                exact_representative_iterations=sorted(representative_iters),exact_representative_edge_cases=edge_cases,
                exact_saved_count_inventory=counts,
                original_FMM_local_flag=fmm['converged'],original_FMM_updates=fmm['updates'],
                review_scope='Saved tables, geometry arithmetic, exact rational algebra of representative stored components, metadata and hashes only; no ray/field/action/optimizer evaluation.',
                limitations=['Observer/unobserved parity is the frozen in-process exact numeric comparison, not a fresh independent ray evaluation.',
                             'The 19 selected states do not recover all unexported intermediate paths or directions.',
                             'Positive exact sy does not establish useful curvature, an admissible replacement pair or a causal remedy.',
                             'Recorded-total Armijo algebra concerns approximate stored totals, not exact Fermat action.',
                             'All source/initializer/local/stopping flags remain the original frozen B results.'])
    for path,value in [(HERE/'readback.json',review),(OUT/'review.json',review)]:
        with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=review['status'],review_sha256=sha(OUT/'review.json'),counts=counts)),flush=True)


if __name__=='__main__':main()
