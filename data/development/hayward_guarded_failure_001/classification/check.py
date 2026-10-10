#!/usr/bin/env python3
"""Classify preserved guarded failure; no ray, matrix solve or data retrieval."""
import collections
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = ROOT/'data/hayward_first_arrival_guarded_001'
BUILD = ROOT/'tmp/hayward_guarded_runs/001'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def read(name):
    with (RUN/name).open() as f: return list(csv.DictReader(f))

def stats(values):
    return dict(minimum=min(values),median=statistics.median(values),maximum=max(values),mean=sum(values)/len(values))

def magnitude(values): return math.sqrt(sum(x*x for x in values))

def main():
    ledger=json.loads((RUN/'dd_inversion_execution.json').read_text())
    manifest=json.loads((RUN/'dd_inversion_run_manifest.json').read_text())
    controller=json.loads((RUN/'controller_provenance/completion.json').read_text())
    assert ledger['status']=='failed' and ledger['return_code']==1 and not ledger['scientific_success']
    assert controller['status']=='failed' and controller['driver_return_code']==1 and controller['child_reaped']
    assert controller['dd_inversion_execution.json_sha256']==sha(RUN/'dd_inversion_execution.json')
    assert controller['dd_inversion_run_manifest.json_sha256']==sha(RUN/'dd_inversion_run_manifest.json')
    pins={}
    for key in ('input_sha256','copied_provenance_sha256','build_provenance_sha256'):
        for name,digest in manifest[key].items():
            assert sha(RUN/name)==digest,name; pins[str((RUN/name).relative_to(ROOT))]=digest
    for name,digest in ledger['partial_output_sha256'].items():
        assert sha(RUN/name)==digest,name; pins[str((RUN/name).relative_to(ROOT))]=digest
    for name,digest in manifest['source_sha256'].items():
        assert sha(BUILD/'source'/name)==digest,name; pins[str((BUILD/'source'/name).relative_to(ROOT))]=digest
    assert sha(ROOT/manifest['binary'])==manifest['binary_sha256']
    pins[manifest['binary']]=manifest['binary_sha256']
    for name in ('dd_inversion_execution.json','dd_inversion_run_manifest.json','controller_provenance/completion.json'):
        pins[str((RUN/name).relative_to(ROOT))]=sha(RUN/name)
    for command in ledger['completed_commands']:
        assert not Path('/proc/{}/stat'.format(command['pid'])).exists()
    assert [x['return_code'] for x in ledger['completed_commands']]==[0,0,0,0,0,1]
    context=read('dd_failed_forward_context.csv'); assert len(context)==1
    context=context[0]
    assert (context['iteration'],context['phase'],context['line_search_trial'],context['derivatives_requested'])==('0','line_search_trial','0','0')
    assert not read('dd_history.csv')
    assert not any((RUN/('dd_'+x+'.csv')).exists() for x in ('events','grid','residuals','coverage'))
    initial,accepted,trial=(read(name) for name in ('initial_events.csv','dd_last_accepted_events.csv','dd_failed_forward_events.csv'))
    stations=read('stations.csv')
    original_grid,accepted_grid,trial_grid=(read(name) for name in ('initial_grid.csv','dd_last_accepted_grid.csv','dd_failed_forward_grid.csv'))
    assert len(initial)==len(accepted)==len(trial)==1092 and len(stations)==372
    assert len(original_grid)==len(accepted_grid)==len(trial_grid)==462
    bounds={a:(min(float(r[a]) for r in trial_grid),max(float(r[a]) for r in trial_grid)) for a in 'xyz'}
    depths=sorted(set(float(r['z']) for r in trial_grid))[1:-1]
    event_shifts=[]; time_shifts=[]; source_boundary_counts=collections.Counter()
    for i,(start,last,candidate) in enumerate(zip(initial,accepted,trial)):
        assert int(start['id'])==int(last['id'])==int(candidate['id'])==i
        for key,value in start.items():
            if key in ('x','y','z','t'): assert float(last[key])==float(value)
            else: assert last[key]==candidate[key]==value
        assert all(math.isfinite(float(candidate[a])) for a in ('x','y','z','t'))
        assert all(bounds[a][0]<=float(candidate[a])<=bounds[a][1] for a in 'xyz')
        event_shifts.append(magnitude([float(candidate[a])-float(start[a]) for a in 'xyz']))
        time_shifts.append(float(candidate['t'])-float(start['t']))
        for a in 'xyz':
            for j,label in enumerate(('lower','upper')):
                source_boundary_counts[a+'_'+label]+=float(candidate[a])==bounds[a][j]
    velocity_delta=[]; log_delta=[]
    for start,last,candidate in zip(original_grid,accepted_grid,trial_grid):
        for key in ('x','y','z','v'): assert float(last[key])==float(start[key])
        for a in 'xyz': assert float(candidate[a])==float(start[a])
        assert math.isfinite(float(candidate['v'])) and float(candidate['v'])>0
        velocity_delta.append(float(candidate['v'])-float(start['v']))
        log_delta.append(-math.log(float(candidate['v'])/float(start['v'])))
    used=set(); observation_count=0
    with (RUN/'observations.csv').open() as f:
        for row in csv.DictReader(f):
            i,j,k=int(row['i']),int(row['j']),int(row['station']);used.add((i,k));observation_count+=1
            if j>=0:used.add((j,int(row['station_j']) if row.get('station_j') else k))
    status=read('dd_failed_forward_ray_status.csv')
    bypair={(int(r['event']),int(r['station'])):r for r in status}
    assert len(status)==len(bypair)==len(used)==14262 and set(bypair)==used
    assert [(int(r['event']),int(r['station'])) for r in status]==sorted(used)
    native_fields=0
    for pair,row in bypair.items():
        i,k=pair
        for prefix,fields in [('source_',initial[i]),('receiver_',stations[k])]:
            for key,value in fields.items():
                if key not in ('id','x','y','z','t'):
                    assert row[prefix+key]==value,(pair,prefix+key);native_fields+=1
        for a in 'xyz':
            assert float(row['source_'+a])==float(trial[i][a])
            assert float(row['receiver_'+a])==float(stations[k][a])
        assert float(row['source_t'])==float(trial[i]['t'])
        assert row['ray_derivatives_evaluated']=='0' and all(row['source_d'+a]=='' for a in 'xyz')
        assert all(row[key]=='1' for key in ('ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint','ray_initialization_attempted','ray_initialization_succeeded'))
        assert all(math.isfinite(float(row[key])) and float(row[key])>=0 for key in ('ray_time','ray_projected_gradient','ray_raw_gradient'))
    failures=read('dd_failed_forward_ray_failures.csv')
    failed={(int(r['event']),int(r['station'])):r for r in failures}
    assert len(failed)==len(failures)==181
    assert set(failed)=={pair for pair,r in bypair.items() if r['ray_converged']=='0'}
    for pair,row in failed.items():
        assert row['reasons']=='local_stopping_failed' and row['derivatives_requested']=='0'
        assert row['velocity_derivatives']==row['path_lengths']=='0' and row['expected_velocity_nodes']=='462'
        for key,value in row.items():
            if key.startswith(('source_','receiver_')):assert value==bypair[pair][key];native_fields+=1
    path_checks={pair:dict(count=0,last=None,exact_domain_face_nodes=0,minimum_internal_depth_plane_distance_km=None) for pair in failed}
    path_rows=0
    with (RUN/'dd_failed_forward_ray_paths.csv').open() as f:
        for row in csv.DictReader(f):
            pair=(int(row['event']),int(row['station']));assert pair in failed
            record=path_checks[pair];assert int(row['node'])==record['count']
            p=[float(row[a]) for a in 'xyz']
            assert all(math.isfinite(v) and bounds[a][0]<=v<=bounds[a][1] for a,v in zip('xyz',p))
            assert record['last'] is None or p!=record['last']
            if record['count']==0:assert p==[float(trial[pair[0]][a]) for a in 'xyz']
            for key,value in row.items():
                if key.startswith(('source_','receiver_')):assert value==bypair[pair][key];native_fields+=1
            record['exact_domain_face_nodes']+=any(v in bounds[a] for a,v in zip('xyz',p))
            distance=min(abs(p[2]-z) for z in depths)
            old=record['minimum_internal_depth_plane_distance_km']
            record['minimum_internal_depth_plane_distance_km']=distance if old is None else min(distance,old)
            record['count']+=1;record['last']=p;path_rows+=1
    identified=[]
    for pair in sorted(failed):
        row=dict(bypair[pair]);p=path_checks[pair]
        assert p['count']==int(row['ray_path_points']) and p['last']==[float(stations[pair[1]][a]) for a in 'xyz']
        assert row['ray_selected_fmm_seed']=='1' and 0<=int(row['ray_iterations'])<=1000
        row.update(failure_reasons=failed[pair]['reasons'],derived_selected_ray_termination='update_budget_exhausted' if int(row['ray_iterations'])==1000 else 'line_search_exhausted',
            trial_source_shift_3d_km=event_shifts[pair[0]],trial_source_time_shift_s=time_shifts[pair[0]],
            saved_path_nodes_checked=p['count'],exact_domain_face_nodes=p['exact_domain_face_nodes'],minimum_internal_depth_plane_distance_km=p['minimum_internal_depth_plane_distance_km'])
        identified.append(row)
    out=HERE/'identified_failures.csv'
    with out.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(identified[0]));writer.writeheader();writer.writerows(identified)
    channels=[]
    for seed in sorted(set(r['receiver_channel_seed_id'] for r in identified)):
        rows=[r for r in identified if r['receiver_channel_seed_id']==seed]
        channels.append(dict(channel_seed_id=seed,channel_fdsn_source_id=rows[0]['receiver_channel_fdsn_source_id'],count=len(rows),
            native_epochs=[dict(native_receiver_index=k,metadata_epoch_start=stations[k]['metadata_epoch_start'],metadata_epoch_end=stations[k]['metadata_epoch_end']) for k in sorted(set(int(r['station']) for r in rows))]))
    source_axis_range={a:stats([float(r['source_'+a]) for r in identified]) for a in 'xyz'}
    for name,digest in pins.items():assert sha(ROOT/name)==digest,name
    result={'status':'passed_saved_failure_audit','created_utc':datetime.datetime.utcnow().isoformat()+'Z','reviewer':'scientific_audit',
        'source_sha256':sha(Path(__file__)),'input_sha256':pins,'output_sha256':{'identified_failures.csv':sha(out)},
        'scope':'Saved failure/native/state/hash census only; no solver, ray, matrix, reference, objective or observational query.',
        'terminal_context':context,'controller_reaped':True,'native_observations':observation_count,'native_rays':len(status),'native_failed_rays':len(failed),
        'accepted_updates':0,'history_rows':0,'last_accepted_state_numerically_equals_initial':True,
        'failure_reasons':dict(collections.Counter(r['failure_reasons'] for r in identified)),
        'derived_selected_termination_counts':dict(collections.Counter(r['derived_selected_ray_termination'] for r in identified)),
        'derivation_limit':'Loop exit is inferred from the frozen original optimizer and accepted-update count; no iteration history or final rejected direction was saved.',
        'failure_events':len(set(r['event'] for r in identified)),'failure_native_receiver_epochs':len(set(r['station'] for r in identified)),
        'failure_channels':channels,'failed_projected_gradient_s_per_km':stats([float(r['ray_projected_gradient']) for r in identified]),
        'failed_raw_gradient_s_per_km':stats([float(r['ray_raw_gradient']) for r in identified]),
        'failed_iterations':stats([int(r['ray_iterations']) for r in identified]),'failed_merged_nodes':dict(collections.Counter(r['ray_merged_nodes'] for r in identified)),
        'failed_source_coordinates_km':source_axis_range,'all_failed_selected_fmm':True,'all_initializers_succeeded':True,
        'full_status_all_finite_domain_exact_endpoints':True,'path_rows_checked':path_rows,'native_metadata_cells_checked':native_fields,
        'trial_change':{'source_displacement_3d_km':stats(event_shifts),'source_time_correction_s':stats(time_shifts),
            'source_exact_boundary_counts':dict(source_boundary_counts),'velocity_difference_km_per_s':stats(velocity_delta),
            'absolute_velocity_difference_km_per_s':stats([abs(x) for x in velocity_delta]),'delta_log_slowness':stats(log_delta),
            'initial_velocity_range_km_per_s':stats([float(r['v']) for r in original_grid]),'candidate_velocity_range_km_per_s':stats([float(r['v']) for r in trial_grid])},
        'maximum_projected_gradient_record':max(identified,key=lambda r:float(r['ray_projected_gradient'])),
        'interpretation':['The initial state passed the current-model gate and reached matrix assembly/solve; the first full-step candidate was rejected before its objective could be evaluated.',
            'No proposed update was accepted. Failed candidate and last accepted state are distinct, with original resource IDs retained.',
            'All181 selected-ray failures are local stopping failures; there is no saved evidence of initializer/domain/endpoint/nonfinite failure.',
            'This run used the frozen original kernel7111f67c, not the later adopted D kernel.',
            'No candidate source derivatives were evaluated, no LSQR diagnostics or candidate objective were flushed before the exception, and no continuous3D accuracy reference exists for this trial.',
            'The census does not establish a common mechanism or that D would fix the rays. A bounded identified old/D replay is a proposal, not an executed remedy.']}
    with (HERE/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'status':result['status'],'summary_sha256':sha(HERE/'summary.json'),'path_rows':path_rows,'native_cells':native_fields,'trial_change':result['trial_change']}))

if __name__=='__main__':main()
