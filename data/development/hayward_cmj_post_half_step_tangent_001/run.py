#!/usr/bin/env python3
"""One tangent pass and exact zero-support signs on the accepted half steps."""
import csv
import datetime
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STEP=ROOT/'data/development/hayward_cmj_tangent_half_step_001'
REVIEW=ROOT/'data/development/hayward_cmj_tangent_half_step_review_001'
START=ROOT/'data/development/hayward_cmj_face_action_001'
PRE=ROOT/'data/development/hayward_cmj_post_step_tangent_001'
PRE_REVIEW=ROOT/'data/development/hayward_cmj_post_step_tangent_review_001'
ZERO=ROOT/'data/development/hayward_cmj_post_step_zero_support_001'
ZERO_REVIEW=ROOT/'data/development/hayward_cmj_post_step_zero_support_review_002'
SOURCE=ROOT/'data/development/cmj_tangent_step_source_002/source'
SETTINGS=dict(terms=8,subdivisions=1,bits=128)


def require(ok,message):
    if not ok:raise ValueError(message)


def now():return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path,**kwargs):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream:return json.load(stream,**kwargs)


def encoded(value):
    if isinstance(value,Q):return str(value)
    if isinstance(value,dict):return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encoded(v) for v in value]
    return value


def save(path,value):
    data=(json.dumps(encoded(value),indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf8')
    with path.open('xb') as stream:
        if path.suffix=='.gz':
            with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as compressed:compressed.write(data)
        else:stream.write(data)


def interval(value):
    a,b=map(Q,value);require(a<=b,'Reversed saved bounds');return a,b


def add(a,b):return a[0]+b[0],a[1]+b[1]


def projected_norm(path,components,axes):
    """Exact physical-box projection and sums; no square-root approximation."""
    total=(Q(0),Q(0));records=[];blocked=[];boundary=0
    for node in range(1,len(path)-1):
        require(len(components[node])==3,'Missing physical component')
        for axis,saved in enumerate(components[node]):
            if saved is None:blocked.append((node,axis));continue
            lo,hi=interval(saved);position=path[node][axis];where='interior';projected=(lo,hi)
            require(axes[axis][0]<=position<=axes[axis][-1],'Outside physical box')
            if position==axes[axis][0]:where='exact_lower';projected=(min(lo,Q(0)),min(hi,Q(0)))
            elif position==axes[axis][-1]:where='exact_upper';projected=(max(lo,Q(0)),max(hi,Q(0)))
            a,b=projected;square=(Q(0) if a<=0<=b else min(a*a,b*b),max(a*a,b*b))
            total=add(total,square);boundary+=int(where!='interior')
            records.append(dict(node=node,axis=axis,coordinate_exact=position,component_bounds=(lo,hi),
                                physical_box_position=where,projected_bounds=projected,squared_bounds=square))
    scales={}
    for name,scale in (('strict_gradient_scale',Q(1,10**7)),('combined_gradient_scale',Q(1,10**5))):
        squared=scale*scale
        scales[name]=dict(scale_squared=squared,classification='strictly_above' if total[0]>squared else
                         ('strictly_below' if total[1]<squared else 'overlapping'),diagnostic_only=True)
    return dict(lower_squared=total[0],upper_squared=total[1],units='s^2/km^2',
                available_component_count=len(records),unavailable_component_count=len(blocked),
                exact_physical_boundary_component_count=boundary,threshold_scales=scales,
                activity_rule='Exact physical box only; no 1e-10 activity band.'),records,blocked


def load_model():
    model=read(START/'model_provenance.json');axes=tuple(tuple(map(Q,v)) for v in model['axes_exact_rational'])
    require(len(axes)==3 and all(len(a)>=2 and all(x<y for x,y in zip(a,a[1:])) for a in axes),'Increasing physical axes')
    require(model['recorded_grid_sha256']==sha(START/'inputs/trial_grid.csv'),'Model raw-grid pin')
    with (START/'inputs/trial_grid.csv').open(newline='') as stream:raw=list(csv.DictReader(stream))
    require(len(raw)==len(model['nodes'])==462,'Complete model inventory');velocity={}
    for index,(row,saved) in enumerate(zip(raw,model['nodes'])):
        require(saved['csv_row']==index,'Model row order')
        for key in ('x','y','z','v'):
            value=saved['values'][key]
            require(value['raw_text']==row[key] and value['binary64_hex']==float(row[key]).hex()
                    and Q(value['exact_rational'])==Q(float(row[key])),'Model raw/binary64 mapping')
        position=tuple(Q(float(row[k])) for k in 'xyz');key=tuple(axes[k].index(x) for k,x in enumerate(position))
        require(key not in velocity,'Duplicate grid node');velocity[key]=Q(float(row['v']))
    require(len(velocity)==len(axes[0])*len(axes[1])*len(axes[2]) and all(v>0 for v in velocity.values()),'Positive Cartesian model')
    return dict(axes=axes,velocities=velocity),model


def load_case(event,identity,pre):
    folder=STEP/('event_'+str(event));result=read(folder/'result.json.gz');value=result['result']
    rounded=read(folder/'round/stdout.json');tokens=read(folder/'round/stdout.json',parse_float=str,parse_int=str)
    for path in (folder/'result.json.gz',folder/'round/stdout.json'):
        attached=read(Path(str(path)+'.identifiers.json'))
        require(attached['native_context']==identity['native_context'] and attached['catalog_uses']==identity['catalog_uses']
                and attached['expected_file']==str(path.relative_to(ROOT)),'Inherited numeric-file sidecar')
    require(result['event']==event and result['station']==160 and result['native_context']==identity['native_context']
            and result['catalog_uses']==identity['catalog_uses'],'Full native/catalog identity')
    require(len(identity['catalog_uses'])==9 and value['status']=='diagnostic_trial_accepted','Reviewed single-trial outcome')
    require(result['candidate_convergence_status'] is None and value['new_convergence_status'] is None and not value['original_status_changed'],'No status promotion')
    status=identity['native_context']['original_status']
    require(status==result['original_status'] and status['ray_converged']==status['ray_derivatives_evaluated']=='0'
            and all(status['source_d'+k]=='' for k in 'xyz'),'Original flags/blank partials')
    require(rounded==value['rounded_record'] and len(rounded['trial'])==len(rounded['trial_hex']),'Saved rounded-output join')
    path=[tuple(map(Q,p)) for p in value['trial']];require(len(path)==(1029 if event==981 else 1031),'Fixed node roster')
    require(len(rounded['trial'])==3*len(path),'Rounded coordinate inventory');provenance=[]
    for node,p in enumerate(path):
        for axis,x in enumerate(p):
            slot=3*node+axis;a=float(rounded['trial'][slot]);b=float.fromhex(rounded['trial_hex'][slot])
            require(a.hex()==b.hex() and Q(a)==x and float(tokens['trial'][slot]).hex()==a.hex(),'Rounded decimal/hex/exact join')
        provenance.append(dict(node=node,exact_rational=p,decimal_tokens=tokens['trial'][3*node:3*node+3],
                               binary64_hex=rounded['trial_hex'][3*node:3*node+3]))
    before=[tuple(map(Q,p['exact_rational'])) for p in result['coordinate_provenance']]
    require(path[0]==before[0] and path[-1]==before[-1],'Fixed endpoints')
    require(all(pre[k]==identity[k] for k in ('event','station','native_context','catalog_uses')),'Pre-step full native join')
    require(pre['status']=='completed_available_tangent_bounds' and not pre['ineligibility']
            and pre['original_convergence_flag']=='0' and pre['candidate_convergence_status'] is None,'Reviewed pre-step status')
    require(pre['coordinate_provenance']==result['coordinate_provenance']
            and [v['node'] for v in pre['coordinate_provenance']]==list(range(len(before))),'Retained first-step geometry')
    require(len(pre['free_node_components'])==len(before)-2
            and [v['node'] for v in pre['free_node_components']]==list(range(1,len(before)-1)),'Complete pre-step raw vector')
    components=[None]+[[None if v is None else interval(v) for v in row['components']]
                      for row in pre['free_node_components']]+[None]
    require(Q(value['alpha'])==Q(1,2) and value['metric_solves']==0 and value['rounded_trials']==1,'Accepted fixed half step')
    require(result['rejected_full_step']['status']=='diagnostic_trial_not_accepted','Preserved rejected full step')
    return path,before,components,provenance,result


def reviewed_terminal(folder,review_folder,identities,expected_status):
    review=read(review_folder/'review.json');summary=read(folder/'summary.json');outer=read(folder/'outer_reaping.json')
    require(review['status']=='passed','Passed independent terminal review')
    for key,name in (('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),
                     ('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
        require(review[key]==sha(folder/name),'Independent terminal input binding')
    require(summary['status']==expected_status and outer['status']=='completed_and_reaped'
            and outer['tool_exit_code']==0,'Reaped prior calculation')
    require(summary['native_contexts']==identities==read(folder/'native_contexts.json'),'Prior full native roster')
    require(len(review['cases'])==2 and [v['event'] for v in review['cases']]==[981,987],'Reviewed case roster')
    for identity,case in zip(identities,review['cases']):
        require(all(case[k]==identity[k] for k in ('event','station','native_context','catalog_uses'))
                and case['original_convergence_flag']=='0' and case['candidate_convergence_status'] is None,'Reviewed identities/statuses')
    for name,digest in summary['output_sha256'].items():require(sha(folder/name)==digest,'Changed prior output: '+name)
    return review


def main():
    prepared=read(HERE/'prepared.json');approval=read(HERE/'prelaunch_review.json')
    require(approval.get('status')=='passed' and approval.get('prepared_sha256')==sha(HERE/'prepared.json'),'Independent prelaunch review required')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed pinned file: '+name)
        for name,digest in prepared['runtime_sha256'].items():require(sha(Path(name))==digest,'Changed runtime: '+name)
    verify()
    identities=read(HERE/'native_contexts.json')
    require([v['event'] for v in identities]==[981,987],'Exact two-case native roster')
    reviewed_terminal(STEP,REVIEW,identities,'completed_bounded_half_step_diagnostic')
    pre_review=reviewed_terminal(PRE,PRE_REVIEW,identities,'completed_bounded_tangent_diagnostic')
    reviewed_terminal(ZERO,ZERO_REVIEW,identities,'completed_bounded_saved_support')
    for name in ('execution.json','summary.json','event_981.json.gz','event_987.json.gz'):
        require(not (HERE/name).exists(),'Preserve prior output: '+name)
    os.environ.update(prepared['environment'])
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),native_contexts=identities,
                attempted_tangent_edges=0,completed_tangent_edges=0,sign_edges_completed=0,sign_patches_completed=0,
                prepared_sha256=sha(HERE/'prepared.json'),
                prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),input_sha256=prepared['input_sha256'],
                environment={k:os.environ[k] for k in prepared['environment']})
    def update():
        tmp=HERE/'execution.json.new';tmp.write_text(json.dumps(ledger,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(HERE/'execution.json')
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    update();code=1;reports=[];active=None;destination=None
    try:
        grid,model=load_model();pre={event:read(PRE/('event_'+str(event)+'.json.gz')) for event in (981,987)}
        require(model['native_contexts']==[v['native_context'] for v in identities],'Model full native context')
        sys.path.insert(0,str(SOURCE))
        from diagnostics import trilinear_action_bounds as t
        for name in ('trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
            require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==SOURCE/'diagnostics'/(name+'.py'),'Frozen numerical import')
        spec=importlib.util.spec_from_file_location('frozen_zero_support',str(ZERO/'run.py'))
        z=importlib.util.module_from_spec(spec);spec.loader.exec_module(z)
        require(Path(z.__file__).resolve()==ZERO/'run.py','Frozen pure sign/support module')
        for identity in identities:
            event=identity['event'];destination=HERE/('event_'+str(event)+'.json.gz')
            active=dict(identity,status='loading_identified_trial',original_convergence_flag='0',candidate_convergence_status=None,
                        settings=SETTINGS,tangent_edge_records=[],zero_normal_support_proofs=[],
                        source_partials_evaluated=False,attempted_tangent_edges=0,completed_tangent_edges=0)
            save(HERE/(destination.name+'.identifiers.json'),dict(identity,expected_file=str(destination.relative_to(ROOT)),file_sha256=None,
                 evidence_sha256=prepared['input_sha256'],prepared_sha256=sha(HERE/'prepared.json'),
                 coordinate_basis='Exact accepted half-step rounded path; retained first-step comparison, rejected full step and original failed-state/catalog identities remain distinct',
                 node_order='Original order; fixed source node0, fixed receiver n-1; physical xyz',edge_order='edge e joins nodes e,e+1',
                 role='One tangent pass plus exact face signs and feasible support assembly; no new convergence flag'))
            path,before,pre_components,coordinates,prior=load_case(event,identity,pre[event])
            active.update(coordinate_provenance=coordinates,prior_result_sha256=sha(STEP/('event_'+str(event))/'result.json.gz'),
                          saved_trial_action=prior['result']['action']['trial_action'],chain_provenance=prior['chain_provenance'],
                          rejected_full_step=prior['rejected_full_step'],pre_components_sha256=sha(PRE/('event_'+str(event)+'.json.gz')),
                          interpretation='Saved half-step action copied for geometry identity; not reevaluated.')
            axes=grid['axes'];aligned=[];blocked=set();reasons=[]
            for node,p in enumerate(path):
                if any(not axes[k][0]<=p[k]<=axes[k][-1] for k in range(3)):reasons.append(dict(reason='outside_physical_box',node=node))
            for edge,(a,b) in enumerate(zip(path,path[1:])):
                faces=[(k,axis.index(a[k])) for k,axis in enumerate(axes) if a[k]==b[k] and a[k] in axis[1:-1]]
                aligned.append(dict(edge=edge,aligned_internal_faces=faces))
                if a==b:reasons.append(dict(reason='zero_length_edge',edge=edge))
                if len(faces)>1:reasons.append(dict(reason='unsupported_multiple_aligned_faces',edge=edge,faces=faces))
                for k,unused in faces:
                    blocked.update((node,k) for node in (edge,edge+1) if 0<node<len(path)-1)
            active.update(aligned_edge_inventory=aligned,geometric_blocked_slots=sorted(blocked),ineligibility=reasons)
            if reasons:
                active['status']='ineligible_saved_trial';save(destination,active)
                reports.append(dict(identity,status=active['status'],ineligibility=reasons,tangent_edge_evaluations=0,
                                    result_file=destination.name,result_sha256=sha(destination),
                                    original_convergence_flag='0',candidate_convergence_status=None))
                active=None;destination=None;continue
            pre_norm,unused,pre_blocked=projected_norm(before,pre_components,axes)
            require(encoded(pre_norm)==pre[event]['post_step_norm'],
                    'Pre-step norm saved arithmetic')
            audit=next(v for v in pre_review['cases'] if v['event']==event)
            require(interval(audit['post_squared_bounds'])==(pre_norm['lower_squared'],pre_norm['upper_squared']),
                    'Independent pre-step norm binding')
            active['pre_step_norm']=pre_norm;active['status']='evaluating_available_tangents'
            components=[[(Q(0),Q(0)) for k in range(3)] for p in path];components[0]=components[-1]=None
            for edge,(a,b) in enumerate(zip(path,path[1:])):
                require(ledger['attempted_tangent_edges']<2058,'Fixed total edge budget')
                active['attempted_tangent_edges']+=1;ledger['attempted_tangent_edges']+=1;ledger['current_event']=event;ledger['current_edge']=edge
                if edge%64==0:update()
                record=t.edge_tangent_components(grid,a,b,SETTINGS)
                # Retain every returned record before subsequent assertions;
                # fixed endpoint values are omitted even in a failed case.
                for side in (0,1):
                    if edge+side in (0,len(path)-1):record['components'][side]=None
                active['tangent_edge_records'].append(dict(record,edge=edge,endpoint_nodes=[edge,edge+1]))
                active['completed_tangent_edges']+=1;ledger['completed_tangent_edges']+=1
                require(record['blocked_axes']==[k for k,index in aligned[edge]['aligned_internal_faces']],'Actual aligned-face mask')
                for side in (0,1):
                    node=edge+side
                    if node in (0,len(path)-1):continue
                    for k,bounds in enumerate(record['components'][side]):
                        require((bounds is None)==(k in record['blocked_axes']),'Edge component availability')
                        if bounds is not None:components[node][k]=add(components[node][k],interval(bounds))
            for node,k in blocked:components[node][k]=None
            post_norm,vector,post_blocked=projected_norm(path,components,axes)
            require(post_blocked==sorted(blocked),'Complete incident-edge blocked mask')
            comparison=dict(same_available_mask=set(pre_blocked)==blocked,newly_unavailable_slots=sorted(blocked-set(pre_blocked)),
                            newly_available_slots=sorted(set(pre_blocked)-blocked),pre=pre_norm,post=post_norm,
                            diagnostic_only=True,interpretation='Available components only; differing masks change the compared coordinate subset. No stopping decision.')
            if comparison['same_available_mask'] and pre_norm['lower_squared']>0:
                comparison['squared_norm_ratio_bounds']=(post_norm['lower_squared']/pre_norm['upper_squared'],post_norm['upper_squared']/pre_norm['lower_squared'])
            active.update(status='completed_available_tangent_bounds',free_node_components=[dict(node=i,components=components[i]) for i in range(1,len(path)-1)],
                          available_projected_components=vector,post_step_norm=post_norm,comparison=comparison)
            active['status']='checking_exact_zero_normal_support'
            for edge,(a,b,record) in enumerate(zip(path,path[1:],active['tangent_edge_records'])):
                if not record['blocked_axes']:continue
                proof=dict(z.zero_normal_support(grid,a,b,t),edge=edge,endpoint_nodes=[edge,edge+1])
                active['zero_normal_support_proofs'].append(proof)
                ledger['sign_edges_completed']+=1;ledger['sign_patches_completed']+=len(proof['patches']);update()
            support=z.supporting_vector(path,active['tangent_edge_records'],active['zero_normal_support_proofs'],axes)
            active.update(status='completed_tangent_and_support_bounds',full_support=support,
                          support_interpretation='One feasible full-vector upper bound, not a minimum; failed signs remain inconclusive. No stopping decision.')
            verify();save(destination,active)
            reports.append(dict(identity,status=active['status'],result_file=destination.name,result_sha256=sha(destination),
                                tangent_edge_evaluations=active['completed_tangent_edges'],comparison=comparison,
                                support_status=support['status'],feasible_full_support_norm=support['norm'],
                                original_convergence_flag='0',candidate_convergence_status=None))
            active=None;destination=None
        verify();ledger['status']='completed_bounded_post_half_tangent_and_support';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if active is not None and destination is not None and not destination.exists():
            active.update(status='failed_preserved',error=ledger['error']);save(destination,active)
    finally:
        outputs={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*')) if p.is_file()}
        summary=dict(status=ledger['status'],error=ledger.get('error'),native_contexts=identities,cases=reports,settings=SETTINGS,
                     attempted_tangent_edges=ledger['attempted_tangent_edges'],completed_tangent_edges=ledger['completed_tangent_edges'],
                     sign_edges_completed=ledger['sign_edges_completed'],sign_patches_completed=ledger['sign_patches_completed'],
                     aligned_normal_integrations=0,support_searches=0,
                     tangent_edge_budget=2058,action_integrations=0,metric_solves=0,rounded_trials=0,trace_calls=0,field_calls=0,optimizer_iterations=0,
                     prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),output_sha256=outputs,
                     scope='One tangent pass and zero-aligned-normal support on both accepted half steps. No source/model partial, stopping decision, minimum or first-arrival certificate.')
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs,
                      subprocess_calls=0,outer_reaping_owner='root; separate terminal receipt after this process exits')
        update()
    return code


if __name__=='__main__':sys.exit(main())
