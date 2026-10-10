#!/usr/bin/env python3
"""One final-polygon interval pass and a coupled feasible support proposal."""
import csv
import datetime
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATA=ROOT/'data/development'
ITER=DATA/'hayward_cmj_tangent_iteration_001'
ITER_REVIEW=DATA/'hayward_cmj_tangent_iteration_review_001'
BENCH=DATA/'hayward_cmj_fixed_polygon_kernel_001'
POST=DATA/'hayward_cmj_post_half_step_tangent_001'
SOURCE=HERE/'source'
SETTINGS=dict(terms=8,subdivisions=1,bits=128)


def require(ok,message):
    if not ok:raise ValueError(message)


def now():return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream:return json.load(stream)


def encoded(value):
    if isinstance(value,Q):return str(value)
    if isinstance(value,dict):return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encoded(v) for v in value]
    return value


def save(path,value):
    data=(json.dumps(encoded(value),indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf8')
    with path.open('xb') as stream:
        if path.suffix=='.gz':
            with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as packed:packed.write(data)
        else:stream.write(data)


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path));result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def table(path):
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream);require(len(reader.fieldnames)==len(set(reader.fieldnames)),'Unique CSV header')
        rows=list(reader);require(all(None not in r and None not in r.values() for r in rows),'Complete CSV rows');return rows


def interval(pair):
    lo,hi=map(Q,pair);require(lo<=hi,'Ordered interval');return lo,hi


def add(a,b):return a[0]+b[0],a[1]+b[1]


def terminal_gate(identities):
    review=read(ITER_REVIEW/'review.json');receipt=read(ITER_REVIEW/'execution_receipt.json')
    summary=read(ITER/'summary.json');execution=read(ITER/'execution.json');outer=read(ITER/'outer_reaping.json')
    require(review['status']=='passed' and summary['status']==execution['status']=='completed_bounded_tangent_iteration'
            and execution['return_code']==0 and execution['outputs_stable'],'Completed reviewed iterator')
    for key,name in (('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),
                     ('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
        require(review[key]==sha(ITER/name),'Iterator review binding')
    require(outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_process_absent']
            and outer['summary_sha256']==sha(ITER/'summary.json') and outer['execution_sha256']==sha(ITER/'execution.json'),'Iterator outer reaping')
    require(receipt['status']=='passed' and receipt['return_code']==0 and receipt['child_reaped'],'Iterator saved-review reaping')
    for name,digest in receipt['output_sha256'].items():require(sha(ITER_REVIEW/name)==digest,'Iterator review receipt output')
    require(summary['native_contexts']==execution['native_contexts']==outer['native_contexts']==review['native_contexts']==identities,'Full terminal native joins')
    require(summary['original_convergence_flag']=='0' and summary['candidate_convergence_status'] is None,'No promoted iterator status')
    controls=read(HERE/'controls/summary.json');checked=read(HERE/'controls/review.json');closed=read(HERE/'controls/execution_receipt.json')
    require(controls['status']==checked['status']=='passed' and checked['summary_sha256']==sha(HERE/'controls/summary.json'),'Reviewed compact controls')
    for key,name in (('helper_sha256','aligned_face_support.py'),('primitive_sha256','source/diagnostics/trilinear_action_bounds.py')):
        require(controls[key]==checked[key]==sha(HERE/name),'Controlled helper source')
    require(closed['status']=='passed' and closed['return_code']==0 and closed['child_reaped'],'Compact controls reaped')
    for name,digest in closed['output_sha256'].items():require(sha(HERE/'controls'/name)==digest,'Control receipt output')
    return review


def load_case(identity,grid,oracle,review,rows):
    event=identity['event'];n=1029 if event==981 else 1031
    expected=next(v for v in review['cases'] if v['event']==event)
    require(all(expected[k]==identity[k] for k in ('event','station','native_context','catalog_uses')),'Reviewed final native case')
    require(identity['station']==160 and len(identity['catalog_uses'])==9,'Exact native receiver and catalog use roster')
    original=identity['native_context']['original_status']
    require(original['ray_converged']==original['ray_derivatives_evaluated']=='0' and all(original['source_d'+k]=='' for k in 'xyz'),'Original failed flags and blank source partials')
    side=read(ITER/'results/paths.csv.identifiers.json')
    require(side['native_contexts']==read(ITER/'native_contexts.json') and side['prepared_sha256']==sha(ITER/'prepared.json')
            and side['expected_file']==str((ITER/'results/paths.csv').relative_to(ROOT)),'Final numeric path sidecar')
    states={};provenance=[]
    for state in ('initial','final'):
        selected=[r for r in rows if int(r['event'])==event and r['state']==state]
        require([int(r['node']) for r in selected]==list(range(n)) and all(r['station']=='160' for r in selected),'Ordered fixed topology')
        path=[]
        for row in selected:
            point=[]
            for key in 'xyz':
                a=float(row[key]);b=float.fromhex(row[key+'_hex'])
                require(math.isfinite(a) and a.hex()==b.hex(),'Exact binary64 coordinate tokens');point.append(Q(b))
            path.append(tuple(point))
            if state=='final':provenance.append(dict(node=int(row['node']),exact_rational=point,decimal_tokens=[row[k] for k in 'xyz'],binary64_hex=[row[k+'_hex'] for k in 'xyz']))
        states[state]=path
    path=states['final'];start=states['initial'];axes=grid['axes']
    require(path[0]==start[0] and path[-1]==start[-1],'Fixed native source/receiver coordinates')
    require(all(axes[k][0]<=p[k]<=axes[k][-1] for p in path for k in range(3)),'Physical model box')
    polygon=next(v for v in oracle['polygons'] if v['event']==event and v['stage_integer']==3)
    require(all(polygon[k]==identity[k] for k in ('event','station','native_context','catalog_uses'))
            and [tuple(map(Q,p)) for p in polygon['coordinates_exact_rational']]==start,'Reviewed starting half-polygon join')
    require([v['edge'] for v in polygon['action']['edges']]==list(range(n-1)),'Complete cached starting edge actions')
    inventory=[];blocked=set();patches=0
    for edge,(a,b) in enumerate(zip(path,path[1:])):
        require(a!=b,'No zero-length final edge')
        faces=[(k,axis.index(a[k])) for k,axis in enumerate(axes) if a[k]==b[k] and a[k] in axis[1:-1]]
        require(len(faces)<=1,'No multiple-aligned-face edge')
        cuts={Q(0),Q(1)}
        if faces:
            for k,axis in enumerate(axes):
                if a[k]!=b[k]:cuts.update((x-a[k])/(b[k]-a[k]) for x in axis[1:-1] if 0<(x-a[k])/(b[k]-a[k])<1)
            patches+=len(cuts)-1
            for k,unused in faces:blocked.update((i,k) for i in (edge,edge+1) if 0<i<n-1)
        inventory.append(dict(edge=edge,aligned_internal_faces=faces,normal_patch_count=len(cuts)-1 if faces else 0))
    saved_gradient=[r for r in table(ITER/'results/gradients.csv') if int(r['event'])==event and r['state']=='final']
    require([(int(r['node']),int(r['axis'])) for r in saved_gradient]==[(i,k) for i in range(1,n-1) for k in range(3)],'Complete final ordinary component output')
    require(blocked=={(int(r['node']),int(r['axis'])) for r in saved_gradient if r['available']=='0'},'Same geometric search mask')
    require(patches==(32 if event==981 else 33),'Exact final aligned patch inventory')
    return path,start,provenance,polygon,inventory,blocked,saved_gradient


def action_account(path,start,records,polygon,cpp_row):
    final=(Q(0),Q(0));difference=(Q(0),Q(0));comparisons=[]
    for record,cached in zip(records,polygon['action']['edges']):
        edge=record['edge'];after=interval(record['action']);before=interval(cached['bounds'])
        same=path[edge]==start[edge] and path[edge+1]==start[edge+1]
        change=(Q(0),Q(0)) if same else (after[0]-before[1],after[1]-before[0])
        final=add(final,after);difference=add(difference,change)
        comparisons.append(dict(edge=edge,identical_endpoint_pair=same,starting_action=before,final_action=after,difference=change,
                                starting_cache=cached))
    value=Q(float.fromhex(cpp_row['action_hex']))
    require(float(cpp_row['action']).hex()==float.fromhex(cpp_row['action_hex']).hex(),'Final C++ action decimal/hex')
    classification='resolved_decrease' if difference[1]<0 else ('resolved_increase' if difference[0]>0 else 'inconclusive')
    return dict(final_action=final,starting_half_action=interval(polygon['action']['full_bounds']),paired_net_change=difference,
                classification=classification,edges=comparisons,cpp_final_action_exact=value,
                cpp_final_action_error=(value-final[1],value-final[0]),
                scope='Net change from reviewed accepted half geometry; no certification of every intermediate approximate decision.')


def available_comparison(components,rows):
    records=[];squared_lower=Q(0);squared_upper=Q(0)
    for row in rows:
        node,axis=int(row['node']),int(row['axis']);value=float(row['component']);hex_value=float.fromhex(row['component_hex'])
        require(math.isfinite(value) and value.hex()==hex_value.hex(),'Final C++ gradient decimal/hex')
        bound=components[node][axis]
        if bound is None:continue
        lo,hi=interval(bound);lower,upper=Q(value)-hi,Q(value)-lo
        distance=Q(0) if lower<=0<=upper else min(abs(lower),abs(upper));maximum=max(abs(lower),abs(upper))
        squared_lower+=distance*distance;squared_upper+=maximum*maximum
        records.append(dict(node=node,axis=axis,cpp_hex=row['component_hex'],component_bounds=(lo,hi),error_bounds=(lower,upper)))
    return dict(component_errors=records,error_norm_squared_bounds=(squared_lower,squared_upper),
                scope='Available internal components only; ordinary aligned normals are not compared to a chosen supporting vector.')


def main():
    prepared=read(HERE/'prepared.json');approval=read(HERE/'prelaunch_review.json')
    require(approval['status']=='passed' and approval['prepared_sha256']==sha(HERE/'prepared.json'),'Root prelaunch review required')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed pinned input/source: '+name)
        for name,digest in prepared['runtime_sha256'].items():require(sha(Path(name))==digest,'Changed runtime: '+name)
        require(sha(Path(sys.executable))==prepared['python']['sha256'],'Changed Python executable')
    verify();os.environ.update(prepared['environment']);identities=read(HERE/'native_contexts.json')
    require([r['event'] for r in identities]==[981,987],'Exact two-case roster');review=terminal_gate(identities)
    for name in ('execution.json','summary.json','event_981.json.gz','event_987.json.gz'):
        require(not (HERE/name).exists(),'Fresh native output required')
    prior=module(POST/'run.py','reviewed_model_and_norm');helper=module(HERE/'aligned_face_support.py','coupled_support')
    sys.path.insert(0,str(SOURCE))
    from diagnostics import trilinear_action_bounds as t
    for name in ('trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
        require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==SOURCE/'diagnostics'/(name+'.py'),'Isolated interval source import')
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),native_contexts=identities,
                attempted_edges=0,completed_edges=0,attempted_normal_patches=0,completed_normal_patches=0,proposal_calls=0,
                prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
                environment={k:os.environ[k] for k in prepared['environment']})
    def update():
        temp=HERE/'execution.json.new';temp.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n');temp.replace(HERE/'execution.json')
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    update();code=1;active=None;destination=None;reports=[]
    try:
        grid,model=prior.load_model();require(model['native_contexts']==[v['native_context'] for v in identities],'Same failed-trial model native contexts')
        oracle=read(BENCH/'oracle.json.gz');require(oracle['native_contexts']==identities,'Same reviewed action-cache identities')
        rows=table(ITER/'results/paths.csv');cpp=table(ITER/'results/summary.csv')
        require(all(r['event'] in ('981','987') and r['station']=='160' and r['state'] in ('initial','final') for r in rows),'Complete final path-table native inventory')
        for identity in identities:
            event=identity['event'];destination=HERE/('event_%d.json.gz'%event)
            active=dict(identity,status='loading_final_polygon',original_convergence_flag='0',candidate_convergence_status=None,
                        settings=SETTINGS,edge_records=[],patch_moment_records=[],patches=[],normal_ineligibility=[])
            save(HERE/(destination.name+'.identifiers.json'),dict(identity,expected_file=str(destination.relative_to(ROOT)),file_sha256=None,
                 prepared_sha256=sha(HERE/'prepared.json'),input_sha256=prepared['input_sha256'],
                 coordinate_basis='Exact final binary64 iterator polygon, unchanged native endpoints and topology',
                 role='Final available components, net action and one coupled feasible support vector; no new Ray flag or source-accuracy claim'))
            path,start,coordinates,polygon,inventory,blocked,gradient=load_case(identity,grid,oracle,review,rows)
            active.update(coordinate_provenance=coordinates,aligned_edge_inventory=inventory,geometric_blocked_slots=sorted(blocked),
                          iterator_paths_sha256=sha(ITER/'results/paths.csv'),iterator_review_sha256=sha(ITER_REVIEW/'review.json'),
                          starting_oracle_sha256=sha(BENCH/'oracle.json.gz'),status='evaluating_final_edges')
            for edge,(a,b) in enumerate(zip(path,path[1:])):
                require(ledger['attempted_edges']<2058,'Fixed combined edge-call budget')
                ledger['attempted_edges']+=1;ledger['current_event']=event;ledger['current_edge']=edge
                if edge%64==0:update()
                record=t.edge_tangent_components(grid,a,b,SETTINGS)
                for side in (0,1):
                    if edge+side in (0,len(path)-1):record['components'][side]=None
                active['edge_records'].append(dict(record,edge=edge,endpoint_nodes=[edge,edge+1]))
                ledger['completed_edges']+=1
                require(record['blocked_axes']==[k for k,index in inventory[edge]['aligned_internal_faces']],'Actual final edge component mask')
            base=helper.ordinary_base(path,active['edge_records']);require({tuple(v) for v in base['blocked_slots']}==blocked,'Full incident-edge blocked roster')
            components=[list(v) if v is not None else None for v in base['components']]
            for node,axis in blocked:components[node][axis]=None
            norm,projected,actual_blocked=prior.projected_norm(path,components,grid['axes']);require(actual_blocked==sorted(blocked),'Final available projection')
            active.update(ordinary_base=base,available_components=[dict(node=i,components=components[i]) for i in range(1,len(path)-1)],
                          available_projected_components=projected,available_norm=norm,
                          cpp_available_comparison=available_comparison(components,gradient),
                          action=action_account(path,start,active['edge_records'],polygon,next(v for v in cpp if int(v['event'])==event)),
                          status='evaluating_coupled_normal_moments')
            for edge,(a,b) in enumerate(zip(path,path[1:])):
                count=inventory[edge]['normal_patch_count']
                if not count:continue
                require(ledger['attempted_normal_patches']+count<=65,'Fixed four-moment patch budget')
                ledger['attempted_normal_patches']+=count;update()
                moment=helper.aligned_patch_moments(grid,a,b,SETTINGS,t)
                active['patch_moment_records'].append(dict(moment,edge=edge,endpoint_nodes=[edge,edge+1]))
                require(len(moment['patches'])==count,'Complete predeclared patch partition')
                ledger['completed_normal_patches']+=moment.get('normal_patch_integrations',0)
                if moment['status']!='bounded_convex_patch_moments':
                    active['normal_ineligibility'].append(dict(edge=edge,status=moment['status']));continue
                for patch in moment['patches']:
                    active['patches'].append(dict(patch,edge=edge,endpoint_nodes=[edge,edge+1],length=moment['length']))
            if active['normal_ineligibility']:
                active.update(proposal=None,full_support=dict(status='inconclusive_unproved_patch_convexity'),status='completed_ineligible_support_assessment')
            else:
                require(ledger['proposal_calls']<2,'Two bounded proposal fits only');ledger['proposal_calls']+=1;update()
                proposal=helper.propose_theta(path,base,active['patches'],max_sweeps=10000);active['proposal']=proposal
                if proposal['status']=='bounded_midpoint_proposal':
                    require(all(float.fromhex(h).hex()==float(v).hex() and Q(float(v))==q for h,v,q in zip(proposal['theta_hex'],proposal['theta'],proposal['theta_exact'])),'Exact emitted binary64 proposal')
                    active['full_support']=helper.assemble_support(path,base,active['patches'],proposal['theta_exact'],grid['axes'],prior.projected_norm)
                else:active['full_support']=dict(status='inconclusive_unusable_proposal',reason=proposal['reason'])
                active['status']='completed_final_action_support_assessment'
            verify();save(destination,active)
            reports.append(dict(identity,status=active['status'],result_file=destination.name,result_sha256=sha(destination),
                 available_norm=active['available_norm'],net_action=active['action']['paired_net_change'],net_action_classification=active['action']['classification'],
                 proposal_status=active['proposal']['status'] if active['proposal'] else None,full_support_status=active['full_support']['status'],
                 full_support_norm=active['full_support'].get('norm'),original_convergence_flag='0',candidate_convergence_status=None))
            active=None;destination=None
        verify();ledger['status']='completed_bounded_final_tangent_support_audit';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if active is not None and destination is not None and not destination.exists():
            active.update(status='failed_preserved',error=ledger['error']);save(destination,active)
    finally:
        outputs={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*')) if p.is_file()}
        counts={k:ledger[k] for k in ('attempted_edges','completed_edges','attempted_normal_patches','completed_normal_patches','proposal_calls')}
        summary=dict(status=ledger['status'],error=ledger.get('error'),native_contexts=identities,cases=reports,settings=SETTINGS,
                     counts=counts,budget=dict(combined_edges=2058,normal_patches=65,proposal_fits=2,sweeps_per_fit=10000),
                     trace_calls=0,field_calls=0,optimizer_iterations=0,metric_solves=0,rounded_trials=0,
                     fixed_endpoint_partials_reported=False,source_model_accuracy_assessed=False,
                     prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),output_sha256=outputs,
                     scope='One final interval audit and restricted feasible support proposal. No minimum-support, first-arrival or Ray-convergence claim.')
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs,
                      subprocess_calls=0,outer_reaping_owner='root; separate terminal receipt after process exit');update()
    return code


if __name__=='__main__':sys.exit(main())
