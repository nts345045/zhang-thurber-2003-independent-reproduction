#!/usr/bin/env python3
"""One independent component pass on two unchanged original failed polygons."""
import csv
import datetime
from fractions import Fraction as Q
import importlib.util
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FACE=ROOT/'data/development/hayward_cmj_face_action_001'
CUT=ROOT/'data/development/hayward_cmj_original_cut_inventory_001'
SAVED=ROOT/'data/development/hayward_cmj_saved_gradient_001'
BASE=ROOT/'data/development/hayward_cmj_post_step_tangent_001/run.py'
SOURCE=HERE/'source'
SETTINGS=dict(terms=8,subdivisions=1,bits=128)


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path));result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream:return json.load(stream)


def utilities():
    # The reviewed utility module imports only stdlib definitions. Verify its
    # exact bytes before loading; no primitive or prior calculation is invoked.
    prepared=read(HERE/'prepared.json')
    require(sha(BASE)==prepared['input_sha256'][str(BASE.relative_to(ROOT))],'Changed utility source')
    name='original_component_utilities'
    if name not in sys.modules:sys.modules[name]=module(BASE,name)
    return sys.modules[name]


def save(path,value):return utilities().save(path,value)
def now():return datetime.datetime.utcnow().isoformat()+'Z'


def table(path):
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream);require(len(reader.fieldnames)==len(set(reader.fieldnames)),'Unique CSV headers')
        rows=list(reader)
    require(all(None not in r and None not in r.values() for r in rows),'Complete CSV rows')
    return rows


def load_inputs():
    """Saved tables/identities only; callable without importing a primitive."""
    u=utilities()
    identities=read(HERE/'native_contexts.json')
    require(identities==read(CUT/'native_contexts.json') and [r['event'] for r in identities]==[981,987],'Exact native roster')
    review=read(SAVED/'review.json');summary=read(SAVED/'summary.json');execution=read(SAVED/'execution.json');outer=read(SAVED/'command_completion.json')
    require(review['status']=='passed' and review['summary_sha256']==sha(SAVED/'summary.json')
            and review['execution_sha256']==sha(SAVED/'execution.json'),'Reviewed saved gradients')
    require(summary['status']=='completed_fixed_saved_path_decomposition' and execution['status']=='completed'
            and execution['return_code']==0 and execution['summary_sha256']==sha(SAVED/'summary.json')
            and execution['prepared_sha256']==sha(SAVED/'prepared.json'),'Terminal saved-gradient binding')
    require(outer['status']=='completed' and outer['observed_command_exit_code']==0 and outer['no_live_recorded_process_group_members']
            and outer['summary_sha256']==sha(SAVED/'summary.json') and outer['execution_sha256']==sha(SAVED/'execution.json'),'Closed prior gradient controller')
    cut_review=read(CUT/'review.json');cut_summary=read(CUT/'summary.json')
    require(cut_review['status']=='passed' and cut_review['summary_sha256']==sha(CUT/'summary.json')
            and cut_summary['status']=='completed_saved_original_cut_inventory','Reviewed original cut inventory')
    grid,model=u.load_model()
    require(model['native_contexts']==read(FACE/'inputs/native_context.json')==[r['native_context'] for r in identities],'Original model/native join')
    events={int(r['id']):r for r in table(FACE/'inputs/trial_events.csv')}
    stations={int(r['id']):r for r in table(FACE/'inputs/stations.csv')}
    paths=table(FACE/'inputs/original_paths.csv');statuses=table(FACE/'inputs/original_status.csv')
    gradients=table(SAVED/'results/old/node_gradients.csv');norms=table(SAVED/'results/old/norms.csv')
    require(len(paths)==len(gradients)==2060 and len(statuses)==len(norms)==2,'Only original old-kernel polygons')
    cases=[]
    for identity in identities:
        event=identity['event'];context=identity['native_context'];n=1029 if event==981 else 1031
        require(context['source_native']==events[event] and context['receiver_native']==stations[160],'Complete indexed source/receiver metadata')
        status=next(r for r in statuses if int(r['event'])==event)
        require(status==context['original_status'] and status['ray_converged']==status['ray_derivatives_evaluated']=='0'
                and all(status['source_d'+k]=='' for k in 'xyz'),'Unchanged false flag and blank source partials')
        rows=[r for r in paths if int(r['event'])==event];observed=[r for r in gradients if int(r['event'])==event]
        require([int(r['node']) for r in rows]==list(range(n)) and len(observed)==n,'Original ordered node inventory')
        polygon=[];raw=[];legacy_projected=[]
        for i,(row,old) in enumerate(zip(rows,observed)):
            require(all(old[k]==v for k,v in row.items()) and old['variant']=='old' and row['station']=='160','Every original coordinate/native field retained')
            for key,value in status.items():
                if key.startswith(('source_','receiver_')) and key in row:require(row[key]==value,'Path native status association')
            point=tuple(Q(float(row[k])) for k in 'xyz');polygon.append(point)
            require(all(math.isfinite(float(row[k])) and grid['axes'][j][0]<=point[j]<=grid['axes'][j][-1] for j,k in enumerate('xyz')),'Finite unchanged original polygon')
            fixed=i in (0,n-1);require(old['is_free']==('0' if fixed else '1'),'Fixed/free roster')
            if fixed:
                require(all(old[prefix+k]=='' for prefix in ('raw_g','projected_g') for k in 'xyz'),'Fixed endpoint partials omitted')
                raw.append(None);legacy_projected.append(None)
            else:
                require(all(math.isfinite(float(old[prefix+k])) for prefix in ('raw_g','projected_g') for k in 'xyz'),'Finite saved internal components')
                raw.append(tuple(Q(float(old['raw_g'+k])) for k in 'xyz'))
                legacy_projected.append(tuple(Q(float(old['projected_g'+k])) for k in 'xyz'))
        require(polygon[0]==tuple(Q(float(context['source_native'][k])) for k in 'xyz')
                and polygon[-1]==tuple(Q(float(context['receiver_native'][k])) for k in 'xyz'),'Exact fixed native endpoints')
        norm=next(r for r in norms if int(r['event'])==event)
        require(norm['variant']=='old' and all(norm[k]==v for k,v in status.items()),'Original status/norm identity')
        require(len(identity['catalog_uses'])==9,'Nine native catalog uses')
        for use in identity['catalog_uses']:
            side,row=use['side'],use['original_row'];receiver='station' if side=='i' else 'station_j'
            require(int(row[side])==event and int(row[receiver])==160,'Catalog pair association')
            require(set(use['epoch_joins'])==({'i'} if row['type']=='0' else {'i','j'}),'Both-side epoch inventory')
            for which,joined in use['epoch_joins'].items():
                event_id=int(row[which]);station_id=int(row['station' if which=='i' else 'station_j']);station=stations[station_id]
                require(joined['event_index']==event_id and joined['station_index']==station_id and joined['receiver_native']==station
                        and row['event_'+which+'_resource_id']==events[event_id]['event_resource_id']
                        and row['origin_'+which+'_resource_id']==events[event_id]['origin_resource_id'],'Both native event/origin/receiver joins')
                require(all(row[k]==station[k] for k in ('channel_seed_id','channel_fdsn_source_id','location_code')),'Channel and valid empty location')
                for end in ('start','end'):
                    require(row['metadata_epoch_'+('' if which=='i' else 'j_')+end]==station['metadata_epoch_'+end],'Both channel epochs')
        cut=read(CUT/('event_%d.json.gz'%event))
        require(cut['native_context']==context and cut['catalog_uses']==identity['catalog_uses'] and len(cut['edge_records'])==n-1,'Original cut native geometry')
        for edge,r in enumerate(cut['edge_records']):
            require(r['edge']==edge and tuple(map(Q,r['a_exact']))==polygon[edge]
                    and tuple(map(Q,r['b_exact']))==polygon[edge+1],'Exact unchanged edge geometry')
        cases.append(dict(identity,path=polygon,original_rows=rows,saved_raw=raw,legacy_projected=legacy_projected,
                          saved_norm=norm,cut_inventory_sha256=sha(CUT/('event_%d.json.gz'%event))))
    return grid,identities,cases


def square(bounds):
    lo,hi=bounds
    return (Q(0) if lo<=0<=hi else min(lo*lo,hi*hi),max(lo*lo,hi*hi))


def main():
    prepared=read(HERE/'prepared.json');approval=read(HERE/'prelaunch_review.json')
    require(approval['status']=='passed' and approval['prepared_sha256']==sha(HERE/'prepared.json'),'Root prelaunch gate')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed source/input: '+name)
        require(sha(Path(sys.executable))==prepared['python']['sha256'],'Changed Python')
        for name,digest in prepared['runtime_sha256'].items():require(sha(Path(name))==digest,'Changed runtime')
    verify();os.environ.update(prepared['environment']);grid,identities,cases=load_inputs();u=utilities()
    for name in ('execution.json','summary.json','event_981.json.gz','event_987.json.gz'):
        require(not (HERE/name).exists(),'Preserve prior output: '+name)
    for identity in identities:
        name='event_%d.json.gz'%identity['event']
        save(HERE/(name+'.identifiers.json'),dict(identity,expected_file=str((HERE/name).relative_to(ROOT)),
             prepared_sha256=sha(HERE/'prepared.json'),coordinate_basis='Unchanged original old-kernel failed polygon',
             original_convergence_flag='0',candidate_convergence_status=None,
             role='Internal fixed-polygon component bounds only; fixed endpoint partials omitted'))
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),native_contexts=identities,
                attempted_component_edges=0,completed_component_edges=0,prepared_sha256=sha(HERE/'prepared.json'),
                prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),environment=prepared['environment'])
    def update():
        temporary=HERE/'execution.json.new';temporary.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n');temporary.replace(HERE/'execution.json')
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    update();code=1;reports=[];active=None;destination=None
    try:
        sys.path.insert(0,str(SOURCE))
        from diagnostics import trilinear_action_bounds as t
        for name in ('trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
            require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==SOURCE/'diagnostics'/(name+'.py'),'Frozen primitive import')
        for case in cases:
            event=case['event'];path=case['path'];n=len(path);destination=HERE/('event_%d.json.gz'%event)
            active=dict(case,status='evaluating_original_components',settings=SETTINGS,tangent_edge_records=[],
                        original_convergence_flag='0',candidate_convergence_status=None)
            components=[[(Q(0),Q(0)) for k in range(3)] for p in path];components[0]=components[-1]=None
            blocked=set();aligned=[]
            for edge,(a,b) in enumerate(zip(path,path[1:])):
                require(a!=b and ledger['attempted_component_edges']<2058,'Nonzero edge and fixed total budget')
                faces=[(k,axis.index(a[k])) for k,axis in enumerate(grid['axes']) if a[k]==b[k] and a[k] in axis[1:-1]]
                require(len(faces)<=1,'Unsupported multiple aligned faces')
                aligned.append(dict(edge=edge,aligned_internal_faces=faces))
                ledger.update(current_event=event,current_edge=edge);ledger['attempted_component_edges']+=1
                if edge%64==0:update()
                r=t.edge_tangent_components(grid,a,b,SETTINGS)
                for side in (0,1):
                    if edge+side in (0,n-1):r['components'][side]=None
                active['tangent_edge_records'].append(dict(r,edge=edge,endpoint_nodes=[edge,edge+1]))
                ledger['completed_component_edges']+=1
                require(r['blocked_axes']==[k for k,index in faces],'Actual geometric availability')
                for side in (0,1):
                    node=edge+side
                    if node in (0,n-1):continue
                    for k,bounds in enumerate(r['components'][side]):
                        require((bounds is None)==(k in r['blocked_axes']),'Component availability')
                        if bounds is None:blocked.add((node,k))
                        else:components[node][k]=u.add(components[node][k],u.interval(bounds))
            for node,k in blocked:components[node][k]=None
            norm,projected,unavailable=u.projected_norm(path,components,grid['axes'])
            require(set(unavailable)==blocked,'Full incident-edge mask')
            errors=[];squared=(Q(0),Q(0));raw_norm=(Q(0),Q(0));saved_true_box=[[None]*3 for p in path]
            for node in range(1,n-1):
                for k in range(3):
                    observed=case['saved_raw'][node][k];saved_true_box[node][k]=(observed,observed)
                    bounds=components[node][k]
                    if bounds is None:continue
                    error=(observed-bounds[1],observed-bounds[0]);squared=u.add(squared,square(error));raw_norm=u.add(raw_norm,square(bounds))
                    errors.append(dict(node=node,axis=k,coordinate_exact=path[node][k],saved_raw_exact=observed,
                         saved_raw_hex=float(observed).hex(),reference_bounds=bounds,error_bounds=error,
                         legacy_projected_exact=case['legacy_projected'][node][k]))
            saved_box_norm,saved_box_components,unused=u.projected_norm(path,saved_true_box,grid['axes'])
            active.update(status='completed_original_component_bounds',free_node_components=[dict(node=i,components=components[i]) for i in range(1,n-1)],
                 aligned_edge_inventory=aligned,geometric_blocked_slots=sorted(blocked),raw_available_squared_norm=raw_norm,
                 projected_norm=norm,available_projected_components=projected,saved_raw_under_true_box=saved_box_norm,
                 saved_true_box_components=saved_box_components,component_comparison=errors,error_squared_norm=squared,
                 interpretation='Error compares the saved raw free-knot vector with independent ordinary bounds. Legacy band-projected values remain separately labeled; only exact physical-box projection is used here.')
            verify();save(destination,active)
            reports.append({**{k:case[k] for k in ('event','station','native_context','catalog_uses')},
                'status':active['status'],'result_file':destination.name,'result_sha256':sha(destination),'component_edges':n-1,
                'available_components':len(errors),'unavailable_components':len(blocked),'error_squared_norm':squared,
                'projected_norm':norm,'original_convergence_flag':'0','candidate_convergence_status':None})
            active=None;destination=None
        require(ledger['completed_component_edges']==2058,'Complete original-edge roster')
        verify();ledger['status']='completed_original_fixed_polygon_component_audit';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if active is not None and destination is not None and not destination.exists():
            active.update(status='failed_preserved',error=ledger['error']);save(destination,active)
    finally:
        outputs={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*')) if p.is_file()}
        summary=dict(status=ledger['status'],error=ledger.get('error'),native_contexts=identities,cases=reports,
             attempted_component_edges=ledger['attempted_component_edges'],completed_component_edges=ledger['completed_component_edges'],
             edge_budget=2058,settings=SETTINGS,prepared_sha256=sha(HERE/'prepared.json'),output_sha256=outputs,
             subprocess_calls=0,trace_calls=0,field_calls=0,metric_solves=0,rounded_trials=0,optimizer_iterations=0,
             source_model_partials=0,original_convergence_flag='0',candidate_convergence_status=None,
             scope='Unchanged original old-kernel polygons; no cut repair, path change, native solve, accuracy acceptance or flag promotion.')
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs,
                      subprocess_calls=0,outer_reaping_owner='root after this process exits')
        update()
    return code


if __name__=='__main__':sys.exit(main())
