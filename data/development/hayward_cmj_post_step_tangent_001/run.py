#!/usr/bin/env python3
"""Available tangent bounds on two saved rounded trials; no search or action."""
import csv
import datetime
from fractions import Fraction as Q
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STEP=ROOT/'data/development/hayward_cmj_tangent_step_001'
REVIEW=ROOT/'data/development/hayward_cmj_tangent_step_review_001'
START=ROOT/'data/development/hayward_cmj_face_action_001'
PRE=ROOT/'data/development/hayward_cmj_face_action_review_001'
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
    before=[tuple(map(Q,p['candidate_exact_rational'])) for p in result['coordinate_provenance']]
    require(path[0]==before[0] and path[-1]==before[-1],'Fixed endpoints')
    require(pre['event']==event and pre['station']==160 and pre['native_context']==identity['native_context'],'Pre-step norm native join')
    components=[[None]*3 for p in before];components[0]=components[-1]=None;seen=set()
    for row in pre['components']:
        node=row['node'];axis='xyz'.index(row['axis']);require((node,axis) not in seen and 0<node<len(before)-1,'Pre-step sparse inventory')
        require(Q(row['coordinate_exact'])==before[node][axis],'Pre-step coordinate join')
        seen.add((node,axis));components[node][axis]=interval(row['component_bounds'])
    return path,before,components,provenance,result


def main():
    prepared=read(HERE/'prepared.json');approval=read(HERE/'prelaunch_review.json')
    require(approval.get('status')=='passed' and approval.get('prepared_sha256')==sha(HERE/'prepared.json'),'Independent prelaunch review required')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed pinned file: '+name)
        for name,digest in prepared['runtime_sha256'].items():require(sha(Path(name))==digest,'Changed runtime: '+name)
    verify()
    review=read(REVIEW/'review.json');step_summary=read(STEP/'summary.json');outer=read(STEP/'outer_reaping.json')
    require(review['status']=='passed' and review['native_summary_sha256']==sha(STEP/'summary.json')
            and review['native_execution_sha256']==sha(STEP/'execution.json') and review['outer_reaping_sha256']==sha(STEP/'outer_reaping.json')
            and review['native_prepared_sha256']==sha(STEP/'prepared.json'),'Reviewed terminal input bindings')
    require(step_summary['status']=='completed_bounded_diagnostic' and outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0,'Terminal prior calculation')
    for name,digest in step_summary['output_sha256'].items():require(sha(STEP/name)==digest,'Changed reviewed terminal output: '+name)
    identities=read(HERE/'native_contexts.json')
    require(identities==read(STEP/'native_contexts.json')==step_summary['native_contexts'] and [v['event'] for v in identities]==[981,987],'Exact two-case native roster')
    for name in ('execution.json','summary.json','event_981.json.gz','event_987.json.gz'):
        require(not (HERE/name).exists(),'Preserve prior output: '+name)
    os.environ.update(prepared['environment'])
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),native_contexts=identities,
                attempted_tangent_edges=0,completed_tangent_edges=0,prepared_sha256=sha(HERE/'prepared.json'),
                prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),input_sha256=prepared['input_sha256'],
                environment={k:os.environ[k] for k in prepared['environment']})
    def update():
        tmp=HERE/'execution.json.new';tmp.write_text(json.dumps(ledger,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(HERE/'execution.json')
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    update();code=1;reports=[];active=None;destination=None
    try:
        grid,model=load_model();pre_records=read(PRE/'tangent_norms.json')['cases'];pre={v['event']:v for v in pre_records}
        require(len(pre_records)==2 and set(pre)=={981,987},'Pre-step norm roster')
        require(model['native_contexts']==[v['native_context'] for v in identities],'Model full native context')
        sys.path.insert(0,str(SOURCE))
        from diagnostics import trilinear_action_bounds as t
        for name in ('trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
            require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==SOURCE/'diagnostics'/(name+'.py'),'Frozen numerical import')
        for identity in identities:
            event=identity['event'];destination=HERE/('event_'+str(event)+'.json.gz')
            active=dict(identity,status='loading_identified_trial',original_convergence_flag='0',candidate_convergence_status=None,
                        settings=SETTINGS,tangent_edge_records=[],attempted_tangent_edges=0,completed_tangent_edges=0)
            save(HERE/(destination.name+'.identifiers.json'),dict(identity,expected_file=str(destination.relative_to(ROOT)),file_sha256=None,
                 evidence_sha256=prepared['input_sha256'],prepared_sha256=sha(HERE/'prepared.json'),
                 coordinate_basis='Exact saved rounded diagnostic trial; failed-state/catalog identities retained',
                 node_order='Original order; fixed source node0, fixed receiver n-1; physical xyz',edge_order='edge e joins nodes e,e+1',
                 role='Available tangent bounds and exact norm algebra only; no new convergence flag'))
            path,before,pre_components,coordinates,prior=load_case(event,identity,pre[event])
            active.update(coordinate_provenance=coordinates,prior_result_sha256=sha(STEP/('event_'+str(event))/'result.json.gz'),
                          saved_trial_action=prior['result']['action']['trial_action'],interpretation='Saved action copied for geometry identity; not reevaluated.')
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
            require(pre_norm['lower_squared']==Q(pre[event]['summary']['lower_squared']) and pre_norm['upper_squared']==Q(pre[event]['summary']['upper_squared']),
                    'Pre-step norm saved arithmetic')
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
            verify();save(destination,active)
            reports.append(dict(identity,status=active['status'],result_file=destination.name,result_sha256=sha(destination),
                                tangent_edge_evaluations=active['completed_tangent_edges'],comparison=comparison,
                                original_convergence_flag='0',candidate_convergence_status=None))
            active=None;destination=None
        verify();ledger['status']='completed_bounded_tangent_diagnostic';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if active is not None and destination is not None and not destination.exists():
            active.update(status='failed_preserved',error=ledger['error']);save(destination,active)
    finally:
        outputs={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*')) if p.is_file()}
        summary=dict(status=ledger['status'],error=ledger.get('error'),native_contexts=identities,cases=reports,settings=SETTINGS,
                     attempted_tangent_edges=ledger['attempted_tangent_edges'],completed_tangent_edges=ledger['completed_tangent_edges'],
                     tangent_edge_budget=2058,action_integrations=0,metric_solves=0,rounded_trials=0,trace_calls=0,field_calls=0,optimizer_iterations=0,
                     prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),output_sha256=outputs,
                     scope='Available tangent vector of the two already saved trials. No source/model partial or convergence/first-arrival certificate.')
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs,
                      subprocess_calls=0,outer_reaping_owner='root; separate terminal receipt after this process exits')
        update()
    return code


if __name__=='__main__':sys.exit(main())
