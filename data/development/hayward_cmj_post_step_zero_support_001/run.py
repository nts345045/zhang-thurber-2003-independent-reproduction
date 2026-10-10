#!/usr/bin/env python3
"""Saved accepted post001 components plus exact one-sided polynomial signs.

No tangent/action integration, metric, rounding, ray, field or optimizer call.
"""
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
POST=ROOT/'data/development/hayward_cmj_post_step_tangent_001'
REVIEW=ROOT/'data/development/hayward_cmj_post_step_tangent_review_001'
STEP=ROOT/'data/development/hayward_cmj_tangent_step_001'
START=ROOT/'data/development/hayward_cmj_face_action_001'
SOURCE=ROOT/'data/development/cmj_tangent_step_source_002/source'


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


def zero_normal_support(grid,a,b,t):
    """Exact whole-patch signs only: no reciprocal or normal integration."""
    a,b,e,aligned,pieces=t.partition(grid,a,b)
    require(len(aligned)==1,'Zero-normal proof requires one aligned face')
    axis,index=aligned[0];records=[]
    for left,right,cell in pieces:
        minus=list(cell);minus[axis]=index-1
        plus=list(cell);plus[axis]=index
        vm,gm,bm=t.cell_polynomials(grid,a,e,left,right,tuple(minus))
        vp,gp,bp=t.cell_polynomials(grid,a,e,left,right,tuple(plus))
        require(vm==vp and min(bm[0],bp[0])>0,'Continuous positive face velocity')
        pm,pp=gm[axis],gp[axis]
        require(len(pm)<=3 and len(pp)<=3,'One-sided normal is not quadratic')
        lower=t.quadratic_bounds(pm);upper=t.quadratic_bounds(pp)
        passed=lower[0]>=0 and upper[1]<=0
        records.append(dict(u=(left,right),normal_axis=axis,normal_coordinate=grid['axes'][axis][index],
                            minus_cell=minus,plus_cell=plus,velocity_polynomial=vm,
                            velocity_vertex_bounds=(min(bm[0],bp[0]),max(bm[1],bp[1])),
                            minus_velocity_normal_polynomial=pm,plus_velocity_normal_polynomial=pp,
                            minus_exact_range=lower,plus_exact_range=upper,zero_normal_supported=passed,
                            both_polynomials_zero=all(x==0 for x in pm+pp),
                            theta_numerator=pm,theta_denominator=t.padd(pm,t.scale(pp,-1))))
    return dict(status='proved_zero_normal_support' if all(r['zero_normal_supported'] for r in records)
                else 'inconclusive_sign_condition_failed',patches=records,
                parameter='Local patch parameter t in [0,1]; global edge interval u recorded separately.',
                units='Velocity normal derivatives: (km/s)/km = 1/s.',
                extrema_rule='Exact rational endpoint values and every interior stationary point of the quadratic.',
                selection='Where gm-gp>0, theta=gm/(gm-gp) in [0,1] and centered lambda=2theta-1. '
                          'At gm-gp=0, the proved signs imply gm=gp=0; choose theta=1/2, lambda=0.',
                first_variation='Positive continuous v gives s_minus,n=-gm/v^2<=0<=-gp/v^2=s_plus,n. '
                                'The same pointwise mixture makes both weighted endpoint normal moments zero.')


def supporting_vector(path,edge_records,proofs,axes):
    """One feasible vector, retaining ordinary entry/exit normal terms."""
    failed=[v['edge'] for v in proofs if v['status']!='proved_zero_normal_support']
    if failed:
        return dict(status='inconclusive_sign_condition_failed',failed_edges=failed,
                    vector=None,projected_components=None,norm=None,
                    interpretation='The zero-normal choice was not proved; no alternative support search or integration.')
    proved={v['edge'] for v in proofs}
    normal_slots={(record['edge']+side,k) for record in edge_records for side in (0,1)
                  for k in record['blocked_axes'] if 0<record['edge']+side<len(path)-1}
    components=[[(Q(0),Q(0)) for k in range(3)] for p in path]
    components[0]=components[-1]=None;ordinary=[];zero=[]
    for record in edge_records:
        edge=record['edge'];blocked=record['blocked_axes']
        require(not blocked or edge in proved,'Missing aligned-edge proof')
        for side in (0,1):
            node=edge+side
            if node in (0,len(path)-1):continue
            for k,value in enumerate(record['components'][side]):
                require((value is None)==(k in blocked),'Support edge availability')
                if value is None:zero.append(dict(edge=edge,side=side,node=node,axis=k,contribution=(Q(0),Q(0))))
                else:
                    term=interval(value);components[node][k]=add(components[node][k],term)
                    if (node,k) in normal_slots:ordinary.append(dict(edge=edge,side=side,node=node,axis=k,contribution=term))
    norm,projected,blocked=projected_norm(path,components,axes)
    require(not blocked,'Feasible full vector must cover every free coordinate')
    return dict(status='feasible_zero_aligned_normal_support',
                vector=[dict(node=i,components=components[i]) for i in range(1,len(path)-1)],
                zero_aligned_contributions=zero,ordinary_contributions_in_blocked_slots=ordinary,
                projected_components=projected,norm=norm,
                interpretation='Upper squared norm bounds one feasible full supporting vector, not the minimum. '
                               'Ordinary unaligned-edge contributions remain, including every face entry/exit normal. '
                               'A large upper bound is inconclusive; no convergence flag or global/source accuracy claim.')


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


def load_case(identity,grid,review):
    event=identity['event'];file=POST/('event_'+str(event)+'.json.gz');post=read(file)
    trial=read(STEP/('event_'+str(event))/'result.json.gz');path=[tuple(map(Q,p)) for p in trial['result']['trial']]
    require(len(path)==(1029 if event==981 else 1031),'Fixed native node roster')
    require(post['status']=='completed_available_tangent_bounds' and post['ineligibility']==[],'Eligible saved post001 components')
    require(trial['result']['status']=='diagnostic_trial_accepted','Use retained accepted first trial only')
    for record in (post,trial):
        require(all(record[k]==identity[k] for k in ('event','station','native_context','catalog_uses')),'Full native/catalog identities')
        require(record['candidate_convergence_status'] is None,'No candidate flag')
    status=identity['native_context']['original_status']
    require(status['ray_converged']==status['ray_derivatives_evaluated']=='0'
            and all(status['source_d'+k]=='' for k in 'xyz'),'Original false flags and blank partials')
    require(post['original_convergence_flag']=='0' and len(identity['catalog_uses'])==9,'Original flag/catalog roster')
    require(post['prior_result_sha256']==sha(STEP/('event_'+str(event))/'result.json.gz'),'Accepted path byte binding')
    coordinates=post['coordinate_provenance']
    require([tuple(map(Q,v['exact_rational'])) for v in coordinates]==path
            and [v['node'] for v in coordinates]==list(range(len(path))),'Full exact saved coordinates')
    before=[tuple(map(Q,p['candidate_exact_rational'])) for p in trial['coordinate_provenance']]
    require(path[0]==before[0] and path[-1]==before[-1] and all(a!=b for a,b in zip(path,path[1:])),'Fixed endpoints and positive edges')
    axes=grid['axes'];require(all(axes[k][0]<=p[k]<=axes[k][-1] for p in path for k in range(3)),'Physical box')
    edge_records=post['tangent_edge_records'];require(len(edge_records)==len(path)-1,'Complete saved edges')
    require(post['attempted_tangent_edges']==post['completed_tangent_edges']==len(path)-1,'Complete prior component pass')
    alignment=[];blocked=set();components=[None]+[[(Q(0),Q(0)) for k in range(3)] for p in path[1:-1]]+[None]
    for edge,(a,b,row) in enumerate(zip(path,path[1:],edge_records)):
        faces=[(k,axis.index(a[k])) for k,axis in enumerate(axes) if a[k]==b[k] and a[k] in axis[1:-1]]
        require(len(faces)<=1 and row['edge']==edge and row['endpoint_nodes']==[edge,edge+1]
                and row['blocked_axes']==[k for k,index in faces],'Actual saved alignment')
        alignment.append(dict(edge=edge,aligned_internal_faces=faces))
        for side in (0,1):
            node=edge+side
            if node in (0,len(path)-1):require(row['components'][side] is None,'Fixed endpoint omission');continue
            require(len(row['components'][side])==3,'Complete edge axes')
            for k,value in enumerate(row['components'][side]):
                require((value is None)==(k in row['blocked_axes']),'Saved edge availability')
                if value is None:blocked.add((node,k))
                else:components[node][k]=add(components[node][k],interval(value))
    for node,k in blocked:components[node][k]=None
    require(encoded(alignment)==post['aligned_edge_inventory'] and encoded(sorted(blocked))==post['geometric_blocked_slots'],'Geometric mask join')
    require(encoded([dict(node=i,components=components[i]) for i in range(1,len(path)-1)])==post['free_node_components'],'Saved adjacent component sums')
    norm,vector,unused=projected_norm(path,components,axes)
    require(encoded(norm)==post['post_step_norm'] and encoded(vector)==post['available_projected_components'],'Reviewed available norm algebra')
    audit=next(v for v in review['cases'] if v['event']==event)
    require(all(audit[k]==identity[k] for k in ('event','station','native_context','catalog_uses'))
            and interval(audit['post_squared_bounds'])==(norm['lower_squared'],norm['upper_squared']),'Independent saved norm review')
    return path,post,norm


def main():
    prepared=read(HERE/'prepared.json');approval=read(HERE/'prelaunch_review.json')
    require(approval.get('status')=='passed' and approval.get('prepared_sha256')==sha(HERE/'prepared.json'),'Independent source/prelaunch review required')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed pin: '+name)
        for name,digest in prepared['runtime_sha256'].items():require(sha(Path(name))==digest,'Changed runtime: '+name)
    verify();review=read(REVIEW/'review.json');summary=read(POST/'summary.json')
    require(review['status']=='passed','Passed post001 review')
    for key,name in [('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),
                     ('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')]:
        require(review[key]==sha(POST/name),'Post001 terminal review binding')
    require(summary['status']=='completed_bounded_tangent_diagnostic','Terminal accepted-geometry components')
    for name,digest in summary['output_sha256'].items():require(sha(POST/name)==digest,'Changed saved output')
    identities=read(HERE/'native_contexts.json')
    require(identities==read(POST/'native_contexts.json')==summary['native_contexts']
            and [v['event'] for v in identities]==[981,987],'Native roster')
    for name in ('execution.json','summary.json','event_981.json.gz','event_987.json.gz'):
        require(not (HERE/name).exists(),'Preserve output: '+name)
    os.environ.update(prepared['environment'])
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),native_contexts=identities,
                prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
                input_sha256=prepared['input_sha256'],environment={k:os.environ[k] for k in prepared['environment']},
                sign_edges_completed=0,sign_patches_completed=0)
    def update():
        tmp=HERE/'execution.json.new';tmp.write_text(json.dumps(ledger,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(HERE/'execution.json')
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    update();code=1;reports=[];active=None;destination=None
    try:
        grid,model=load_model();require(model['native_contexts']==[v['native_context'] for v in identities],'Model native join')
        sys.path.insert(0,str(SOURCE))
        from diagnostics import trilinear_action_bounds as t
        for name in ('trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
            require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==SOURCE/'diagnostics'/(name+'.py'),'Frozen polynomial source')
        for identity in identities:
            event=identity['event'];destination=HERE/('event_'+str(event)+'.json.gz')
            active=dict(identity,status='loading_saved_components',original_convergence_flag='0',candidate_convergence_status=None,
                        zero_normal_support_proofs=[],source_partials_evaluated=False)
            save(HERE/(destination.name+'.identifiers.json'),dict(identity,expected_file=str(destination.relative_to(ROOT)),file_sha256=None,
                 evidence_sha256=prepared['input_sha256'],prepared_sha256=sha(HERE/'prepared.json'),
                 coordinate_basis='Retained accepted first trial, distinct from rejected second trial and provider catalog coordinates',
                 role='Saved component assembly and exact whole-patch polynomial signs; no new integration or convergence flag'))
            path,post,available=load_case(identity,grid,review)
            active.update(coordinate_provenance=post['coordinate_provenance'],saved_components_sha256=sha(POST/('event_'+str(event)+'.json.gz')),
                          available_tangent_norm=available,status='checking_exact_one_sided_signs')
            for edge,(a,b,row) in enumerate(zip(path,path[1:],post['tangent_edge_records'])):
                if not row['blocked_axes']:continue
                proof=dict(zero_normal_support(grid,a,b,t),edge=edge,endpoint_nodes=[edge,edge+1])
                active['zero_normal_support_proofs'].append(proof)
                ledger['sign_edges_completed']+=1;ledger['sign_patches_completed']+=len(proof['patches']);update()
            support=supporting_vector(path,post['tangent_edge_records'],active['zero_normal_support_proofs'],grid['axes'])
            active.update(status='completed_saved_support_assessment',full_support=support,
                          interpretation='Available tangent lower norm is a residual obstruction; full feasible-vector upper norm is a witness, not the minimum.')
            verify();save(destination,active)
            reports.append(dict(identity,status=active['status'],support_status=support['status'],available_tangent_norm=available,
                                feasible_full_support_norm=support['norm'],result_file=destination.name,result_sha256=sha(destination),
                                original_convergence_flag='0',candidate_convergence_status=None))
            active=None;destination=None
        verify();ledger['status']='completed_bounded_saved_support';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if active is not None and destination is not None and not destination.exists():
            active.update(status='failed_preserved',error=ledger['error']);save(destination,active)
    finally:
        outputs={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*')) if p.is_file()}
        result=dict(status=ledger['status'],error=ledger.get('error'),native_contexts=identities,cases=reports,
                    sign_edges_completed=ledger['sign_edges_completed'],sign_patches_completed=ledger['sign_patches_completed'],
                    tangent_integrations=0,normal_integrations=0,action_integrations=0,metric_solves=0,rounded_trials=0,
                    trace_calls=0,field_calls=0,optimizer_iterations=0,subprocess_calls=0,
                    prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),output_sha256=outputs,
                    scope='One zero-aligned-normal feasible support on the retained accepted first trial; no support minimization or stopping decision.')
        save(HERE/'summary.json',result)
        ledger.update(return_code=code,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs,
                      outer_reaping_owner='root; separate terminal receipt after this process exits');update()
    return code


if __name__=='__main__':sys.exit(main())
