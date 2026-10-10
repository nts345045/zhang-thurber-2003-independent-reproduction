#!/usr/bin/env python3
"""Two reviewed saved polygons: one metric direction/at most one trial each.

No compilation, tangent integration, trace, field or iterative optimizer.
The native loader uses only stdlib exact joins; numerical imports occur only
after a passed preparation review and all input/identity checks.
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
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
N=ROOT/'data/development/hayward_cmj_face_action_001'
R=ROOT/'data/development/hayward_cmj_face_action_review_001'
C=ROOT/'data/development/cmj_tangent_step_source_002'
SETTINGS=dict(terms=8,subdivisions=1,bits=128)
ROSTER={981:(1029,724,754,12568,'49639104'),987:(1031,726,757,12672,'49654119')}
USES={981:[(12568,'i'),(15081,'j'),(16943,'i'),(17559,'j'),(17871,'i'),(19525,'i'),(25283,'i'),(28675,'i'),(40595,'i')],
      987:[(12672,'i'),(14638,'j'),(14683,'j'),(14830,'j'),(15239,'j'),(16943,'j'),(21423,'i'),(30903,'j'),(37879,'i')]}


def require(ok,message):
    if not ok:raise ValueError(message)


def now():return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream:return json.load(stream)


def rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


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
    a,b=map(Q,value);require(a<=b,'Reversed saved interval');return a,b


def add(a,b):return a[0]+b[0],a[1]+b[1]
def xyz(row):return tuple(Q(float(row[k])) for k in 'xyz')


def load_inputs():
    """Attest the already saved geometry/intervals; no new integration."""
    contexts=read(N/'inputs/native_context.json')
    context={c['event']:c for c in contexts}
    require(set(context)==set(ROSTER) and len(contexts)==2,'Native context roster')
    events=rows(N/'inputs/trial_events.csv');stations=rows(N/'inputs/stations.csv')
    require(all(int(row['id'])==i for i,row in enumerate(events)) and
            all(int(row['id'])==i for i,row in enumerate(stations)),'Consecutive event/station table IDs')
    statuses=rows(N/'inputs/original_status.csv');paths=rows(N/'inputs/original_paths.csv')
    selected_rows=rows(N/'inputs/near_face_nodes.csv')
    model=read(N/'model_provenance.json');grid_rows=rows(N/'inputs/trial_grid.csv')
    require(model['native_contexts']==contexts,'Model context join')
    require(model['recorded_grid_sha256']==sha(N/'inputs/trial_grid.csv'),'Model raw-grid hash')
    sidecar=read(N/'inputs/trial_grid.csv.identifiers.json')
    require(sidecar['file_sha256']==model['recorded_grid_sha256'] and sidecar['native_context']==contexts,'Grid sidecar')
    axes=tuple(tuple(sorted({Q(float(row[k])) for row in grid_rows})) for k in 'xyz')
    require(tuple(tuple(map(Q,a)) for a in model['axes_exact_rational'])==axes,'Model axes')
    require(len(grid_rows)==len(model['nodes'])==462,'Model node inventory')
    velocity={}
    for index,(raw,saved) in enumerate(zip(grid_rows,model['nodes'])):
        require(saved['csv_row']==index,'Model CSV order')
        for k in ('x','y','z','v'):
            v=saved['values'][k]
            require(v['raw_text']==raw[k] and v['binary64_hex']==float(raw[k]).hex()
                    and Q(v['exact_rational'])==Q(float(raw[k])),'Model binary64 mapping')
        key=tuple(axes[k].index(x) for k,x in enumerate(xyz(raw)))
        require(key not in velocity,'Duplicate model node');velocity[key]=Q(float(raw['v']))
    require(len(velocity)==len(axes[0])*len(axes[1])*len(axes[2]) and all(v>0 for v in velocity.values()),'Positive Cartesian model')
    grid=dict(axes=axes,velocities=velocity)
    sparse_records=read(R/'tangent_norms.json')['cases']
    sparse={v['event']:v for v in sparse_records}
    require(set(sparse)==set(ROSTER) and len(sparse_records)==2,'Tangent case inventory')
    catalog={event:[] for event in ROSTER}
    with (ROOT/'data/hayward/observations.csv').open(newline='') as stream:
        for index,row in enumerate(csv.DictReader(stream)):
            # The preserved loader uses station_j for a declared DD second side.
            sides=[('i',int(row['i']),int(row['station']))]
            if int(row['j'])>=0:
                require(int(row['station_j'])>=0,'Explicit DD receiver epoch missing')
                sides.append(('j',int(row['j']),int(row['station_j'])))
            for side,event,station in sides:
                if event not in ROSTER or station!=160:continue
                epoch_joins={}
                for s,e,k in sides:
                    source=events[e];receiver=stations[k]
                    require(all(row[key]==receiver[key] for key in ('network_code','station_code','location_code','channel_code','channel_seed_id','channel_fdsn_source_id')),'Both-side catalog channel identity')
                    require(row['event_'+s+'_resource_id']==source['event_resource_id'] and
                            row['origin_'+s+'_resource_id']==source['origin_resource_id'],'Catalog event/origin join')
                    prefix='metadata_epoch_' if s=='i' else 'metadata_epoch_j_'
                    require(all(row[prefix+end]==receiver['metadata_epoch_'+end] for end in ('start','end')),'Catalog receiver epoch join')
                    digest='channel_source_sha256' if s=='i' else 'channel_j_source_sha256'
                    require(row[digest]==receiver['source_sha256'],'Catalog channel source hash')
                    epoch_joins[s]=dict(event_index=e,station_index=k,receiver_native=receiver)
                require(all(row[k]==stations[160][k] for k in ('network_code','station_code','location_code','channel_code','channel_seed_id','channel_fdsn_source_id')),'Catalog channel identity')
                catalog[event].append(dict(zero_based_observation_row=index,side=side,original_row=row,epoch_joins=epoch_joins))
    results=[]
    for event,(count,first,last,absolute,pick) in sorted(ROSTER.items()):
        c=context[event];status=c['original_status'];saved=read(N/('event_'+str(event)+'.json.gz'))
        require(c['station']==160 and c['native_flat_index']==event*len(stations)+160 and len(stations)==372,'Native index')
        require(c['source_native']==events[event] and c['receiver_native']==stations[160],'Full current-state native rows')
        require([s for s in statuses if int(s['event'])==event]==[status],'Original status join')
        require(int(status['event'])==event and int(status['station'])==160,'Status numeric pair identity')
        require(saved['event']==event and saved['station']==160 and saved['native_context']==c and saved['original_status']==status,'Saved context')
        require(saved['candidate_convergence_status'] is None and saved['original_convergence_flag_preserved']==status['ray_converged']=='0'
                and status['ray_derivatives_evaluated']=='0' and all(status['source_d'+k]=='' for k in 'xyz'),'Preserved flags and blank source partials')
        require(saved['settings']==SETTINGS and not saved['candidate_ineligibility'],'Starting calculation eligibility/budget')
        native=[p for p in paths if int(p['event'])==event]
        selected=list(range(first,last+1));near=[p for p in selected_rows if int(p['event'])==event]
        require(all(int(p['event'])==event and int(p['station'])==160 for p in native+near),'Path/selected numeric pair identity')
        require(len(native)==count==len(saved['coordinate_provenance']) and saved['selected_nodes']==selected,'Geometry roster')
        require([int(p['node']) for p in native]==list(range(count)) and [int(p['node']) for p in near]==selected,'Native node order')
        metadata={k:status[k] for k in native[0] if k.startswith(('source_','receiver_'))}
        require(saved['full_metadata']==metadata and all(all(p[k]==v for k,v in metadata.items()) for p in native),'Path native metadata')
        require(all(all(p[k]==v for k,v in native[int(p['node'])].items()) for p in near),'Selected raw rows')
        path=[]
        for i,(raw,p) in enumerate(zip(native,saved['coordinate_provenance'])):
            require(p['node']==i and p['x_replaced_with_exact_zero']==(i in selected),'Coordinate node/selection')
            original=xyz(raw);candidate=tuple(map(Q,p['candidate_exact_rational']))
            require(candidate==((Q(0),original[1],original[2]) if i in selected else original),'Only declared saved x-zero change')
            for k in 'xyz':
                v=p['original'][k]
                require(v['raw_text']==raw[k] and v['binary64_hex']==float(raw[k]).hex() and Q(v['exact_rational'])==Q(float(raw[k])),'Coordinate raw/binary64 mapping')
            path.append(candidate)
        require(path[0]==xyz(events[event]) and path[-1]==xyz(stations[160]),'Fixed exact failed-state endpoints')
        require(all(a!=b for a,b in zip(path,path[1:])) and all(axes[k][0]<p[k]<axes[k][-1] for p in path[1:-1] for k in range(3)),'Positive edges/interior free nodes')
        records={v['cache_id']:v for v in saved['unique_action_edge_records']}
        require(len(records)==len(saved['unique_action_edge_records']),'Unique saved action IDs')
        ids=saved['candidate_edge_record_ids'];require(len(ids)==count-1,'Complete starting edges')
        starting=[];total=(Q(0),Q(0))
        for i,identity in enumerate(ids):
            record=records[identity]
            require(tuple(map(Q,record['a_exact']))==path[i] and tuple(map(Q,record['b_exact']))==path[i+1],'Ordered starting action geometry')
            bounds=interval(record['record']['action']);require(bounds[0]>0,'Positive starting action')
            starting.append(dict(action=bounds,cache_id=identity));total=add(total,bounds)
        require(total==interval(saved['candidate_action']['exact_rational_bounds']),'Complete starting action sum')
        edges=saved['candidate_edge_tangent_records'];full=saved['candidate_free_node_tangent_components']
        require([e['edge'] for e in edges]==list(range(count-1)) and [p['node'] for p in full]==list(range(1,count-1)),'Complete tangent inventory')
        require(edges[0]['components'][0] is None and edges[-1]['components'][1] is None,'Fixed endpoint derivative omission')
        tang=sparse[event];require(tang['station']==160 and tang['native_context']==c,'Sparse tangent context')
        lookup={(p['node'],'xyz'.index(p['axis'])):p for p in tang['components']}
        require(len(lookup)==len(tang['components']),'Unique sparse tangent slots')
        components=[None];available=set();blocked=[]
        for i,p in enumerate(full,1):
            require(len(p['components'])==3,'All physical derivative axes')
            complete=[]
            for k,value in enumerate(p['components']):
                left=edges[i-1]['components'][1][k];right=edges[i]['components'][0][k]
                expect=None if left is None or right is None else add(interval(left),interval(right))
                require((value is None and expect is None) or (value is not None and interval(value)==expect),'Both adjacent derivative contributions')
                complete.append(expect)
                if expect is None:blocked.append((i,k));continue
                available.add((i,k));entry=lookup[i,k]
                require(Q(entry['coordinate_exact'])==path[i][k] and interval(entry['component_bounds'])==expect
                        and interval(entry['projected_bounds'])==expect and entry['physical_box_position']=='interior'
                        and entry['selected_near_face_node']==(i in selected),'Sparse/full tangent geometry and interval join')
            components.append(complete)
        components.append(None)
        require(set(lookup)==available and blocked==[(i,0) for i in selected]
                and len(available)==(3050 if event==981 else 3055),'Exact available/unavailable mask')
        uses=catalog[event]
        require([(r['zero_based_observation_row'],r['side']) for r in uses]==USES[event],'All nine catalog uses')
        absolute_row=next(r['original_row'] for r in uses if r['zero_based_observation_row']==absolute)
        require(absolute_row['type']=='0' and absolute_row['j']==absolute_row['station_j']=='-1','Absolute observation identity')
        for use in uses:
            row=use['original_row'];s=use['side']
            require(row['pick_'+s+'_resource_id']=='quakeml:NC.anss.org/Arrival/NC/'+pick and
                    row['arrival_'+s+'_resource_id']=='quakeml:NC.anss.org/AssocArO/NC/'+pick,'Pick/association identity')
            require(all(row[k+'_'+s+suffix]==absolute_row[k+'_i'+suffix] for k,suffix in
                        (('pick','_time_utc'),('pick','_source_sha256'))),'Repeated native pick provenance')
        results.append(dict(event=event,station=160,native_context=c,catalog_uses=uses,path=path,
            components=components,starting_edges=starting,coordinate_provenance=saved['coordinate_provenance'],
            candidate_action=saved['candidate_action'],candidate_edge_record_ids=ids,
            original_status=status,candidate_convergence_status=None,selected_near_face_nodes=selected))
    return grid,results


def group_members(pgid):
    result=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==pgid and fields[0]!='Z':result.append(int(entry.name))
        except (FileNotFoundError,ProcessLookupError):pass
    return result


def stop_group(child):
    signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
    for sig in (signal.SIGTERM,signal.SIGKILL):
        try:os.killpg(child.pid,sig)
        except ProcessLookupError:pass
        deadline=time.monotonic()+10
        while group_members(child.pid) and time.monotonic()<deadline:time.sleep(.1)
        if not group_members(child.pid):break
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:pass
    return dict(pgid=child.pid,live_members=group_members(child.pid),child_reaped=child.poll() is not None)


def main():
    prepared=read(HERE/'prepared.json');review=read(HERE/'prelaunch_review.json')
    require(review.get('status')=='passed' and review.get('prepared_sha256')==sha(HERE/'prepared.json'),'Require passed hash-bound independent prelaunch review')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed pinned file: '+name)
        for name,digest in prepared['runtime_sha256'].items():require(sha(name)==digest,'Changed runtime: '+name)
    verify()
    controls=read(C/'summary.json');control_review=read(C/'review.json')
    require(controls['status']==control_review['status']=='passed' and control_review['summary_sha256']==sha(C/'summary.json')
            and control_review['binary_sha256']==sha(C/'build/metric_step'),'Reviewed binary/controls')
    require(read(R/'review.json')['status']=='passed' and read(N/'summary.json')['status']=='completed_bounded_calculation','Reviewed starting evidence')
    for name in ('execution.json','summary.json','event_981','event_987'):
        require(not (HERE/name).exists(),'Preserve prior output: '+name)
    identifiers=read(HERE/'native_contexts.json')
    os.environ.update(prepared['environment'])
    ledger=dict(status='running',started_utc=now(),pid=os.getpid(),commands=[],native_contexts=identifiers,
                prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
                input_sha256=prepared['input_sha256'],runtime_sha256=prepared['runtime_sha256'],
                environment={key:os.environ[key] for key in prepared['environment']})
    def update():
        temp=HERE/'execution.json.new'
        temp.write_text(json.dumps(ledger,indent=2,sort_keys=True,allow_nan=False)+'\n');temp.replace(HERE/'execution.json')
    update();unsettled=[];completed=[];current=None;answer=None;code=1
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        grid,cases=load_inputs();verify()
        require([dict(event=c['event'],station=160,native_context=c['native_context'],catalog_uses=c['catalog_uses']) for c in cases]
                ==identifiers,'Prepared complete identity attachment')
        # Import only the reviewed, pinned numerical sources after native joins.
        sys.path.insert(0,str(C/'source'))
        from diagnostics import tangent_metric_step as m
        from diagnostics import trilinear_action_bounds as t
        for name in ('tangent_metric_step','trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
            module=sys.modules['diagnostics.'+name]
            require(Path(module.__file__).resolve()==C/'source/diagnostics'/(name+'.py'),'Unexpected numerical import')
        for case in cases:
            current=HERE/('event_'+str(case['event']));current.mkdir()
            identity=dict(event=case['event'],station=160,native_context=case['native_context'],catalog_uses=case['catalog_uses'],
                original_status=case['original_status'],candidate_convergence_status=None,
                coordinate_basis='Saved failed-state exact-face candidate, not provider catalog coordinates',
                node_count=len(case['path']),node_order='Source 0 through fixed receiver n-1; physical xyz',
                interior_slot_order='node 1..n-2, then x,y,z; only saved unavailable normals fixed',
                edge_order='edge e is ordered node e to e+1',selected_near_face_nodes=case['selected_near_face_nodes'],
                evidence_sha256=prepared['input_sha256'],prepared_sha256=sha(HERE/'prepared.json'))
            result_path=current/'result.json.gz'
            save(current/'result.json.gz.identifiers.json',dict(identity,expected_file=str(result_path.relative_to(ROOT)),file_sha256=None,
                 role='Complete diagnostic result or preserved failure; terminal bytes bound only after reap'))
            answer=dict(identity,coordinate_provenance=case['coordinate_provenance'],starting_candidate_action=case['candidate_action'],
                        starting_edge_record_ids=case['candidate_edge_record_ids'],settings=SETTINGS,result=None)
            calls=[]
            def helper(mode,text):
                require(mode in ('solve','round') and mode not in calls and (mode!='round' or calls==['solve']),'Single metric/round inventory')
                calls.append(mode);folder=current/('metric' if mode=='solve' else 'round');folder.mkdir()
                input_path=folder/'input.txt';input_bytes=text.encode('utf8')
                input_digest=hashlib.sha256(input_bytes).hexdigest()
                for name,role in (('input.txt','Hexadecimal binary64 helper input'),('stdout.json','Declared helper output'),('stderr.log','Declared helper diagnostics')):
                    save(folder/(name+'.identifiers.json'),dict(identity,expected_file=str((folder/name).relative_to(ROOT)),
                         role=role,mode=mode,input_file=str(input_path.relative_to(ROOT)),input_file_sha256=input_digest,
                         file_sha256=input_digest if name=='input.txt' else None))
                with input_path.open('xb') as stream:stream.write(input_bytes)
                command=[str(C/'build/metric_step'),mode,str(input_path)]
                item=dict(event=case['event'],station=160,mode=mode,command=command,started_utc=now(),
                          native_context=case['native_context'],catalog_uses=case['catalog_uses'])
                ledger['commands'].append(item);update()
                with (folder/'stdout.json').open('x') as stdout,(folder/'stderr.log').open('x') as stderr:
                    old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
                    try:child=subprocess.Popen(command,cwd=str(ROOT),env=dict(os.environ,**prepared['environment']),stdout=stdout,stderr=stderr,start_new_session=True)
                    except BaseException:
                        signal.pthread_sigmask(signal.SIG_SETMASK,old_mask);raise
                    try:
                        item['pid']=child.pid
                        signal.pthread_sigmask(signal.SIG_SETMASK,old_mask);update()
                        returned=child.wait()
                        if returned!=0 or group_members(child.pid):raise RuntimeError('Helper failed or left live writers')
                    except BaseException:
                        state=stop_group(child);item['cleanup']=state
                        if state['live_members'] or not state['child_reaped']:unsettled.append(state)
                        raise
                    finally:
                        item.update(return_code=child.returncode,child_reaped=child.poll() is not None,finished_utc=now());update()
                item['output_sha256']={name:sha(folder/name) for name in ('input.txt','stdout.json','stderr.log')};update()
                return read(folder/'stdout.json')
            answer['result']=m.single_trial(t,grid,case['path'],case['components'],case['starting_edges'],SETTINGS,
                                           lambda text:helper('solve',text),lambda text:helper('round',text))
            value=answer['result'];count=value['action_edge_evaluations']
            require(count is None or 0<=count<=len(case['path'])-1,'Per-case action budget')
            verify();save(result_path,answer)
            completed.append(dict(event=case['event'],station=160,native_context=case['native_context'],catalog_uses=case['catalog_uses'],
                result_file=str(result_path.relative_to(HERE)),result_sha256=sha(result_path),status=value['status'],
                metric_solves=value['metric_solves'],rounded_trials=value['rounded_trials'],action_edge_evaluations=count,
                original_convergence_flag='0',candidate_convergence_status=None))
            require(not value.get('error'),'Numerical eligibility/arithmetic failure preserved; stop without escalation')
            current=None;answer=None
        require(sum(v['action_edge_evaluations'] for v in completed)<=2058,'Total action budget')
        ledger['status']='completed_bounded_diagnostic';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if current is not None and answer is not None and not (current/'result.json.gz').exists():
            answer['wrapper_failure']=ledger['error'];save(current/'result.json.gz',answer)
    finally:
        stable=not unsettled and all(v.get('child_reaped') for v in ledger['commands'])
        outputs={} if not stable else {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*/*')) if p.is_file()}
        if stable:
            for p in sorted(HERE.glob('event_*/*/*')):
                if p.is_file():outputs[str(p.relative_to(HERE))]=sha(p)
        summary=dict(status=ledger['status'],error=ledger.get('error'),cases=completed,native_contexts=identifiers,settings=SETTINGS,
                     budget=dict(metric_solves_maximum=2,rounded_trials_maximum=2,new_action_edges_maximum=2058),
                     native_trace_calls=0,field_calls=0,tangent_integrals=0,optimizer_iterations=0,
                     interpretation='One diagnostic direction/trial per prescribed polygon; no original flag, endpoint/source derivative or first-arrival promotion.',
                     prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),output_sha256=outputs)
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),outputs_stable=stable,unsettled_groups=unsettled,
                      summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs)
        update()
    return code


if __name__=='__main__':sys.exit(main())
