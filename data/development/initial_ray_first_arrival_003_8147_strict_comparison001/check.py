#!/usr/bin/env python3
"""Compare declared stopping controls and fixed path refinements for native row8147."""
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def require(ok,message):
    if not ok: raise ValueError(message)

def table(p):
    with p.open() as f: return list(csv.DictReader(f))

def main():
    runs={k:HERE.parent/('initial_ray_first_arrival_003_8147_'+v) for k,v in
          [('control','strict_control001'),('strict','strict_gradient001')]}
    summaries={k:json.loads((p/'summary.json').read_text()) for k,p in runs.items()}
    verified={}
    for k,p in runs.items():
        s=summaries[k]
        require(s['status']=='completed_with_declared_stopping_control','Incomplete diagnostic')
        for name,expected in s['output_sha256'].items():
            require(sha(p/name)==expected,'Diagnostic artifact changed: '+name)
        require(sha(p/'control_core.hpp')==s['frozen_source_sha256']['src/core.hpp'], 'Frozen core differs')
        require(all(c['exit_code']==0 for c in s['commands']),'Diagnostic process failed')
        verified[k]=dict(summary_sha256=sha(p/'summary.json'),artifact_sha256=s['output_sha256'])
    require((runs['control']/'identified_ray.csv').read_bytes()==(runs['strict']/'identified_ray.csv').read_bytes(),
            'Native ray differs')
    require((runs['control']/'initial_grid.csv').read_bytes()==(runs['strict']/'initial_grid.csv').read_bytes(),
            'Model differs')
    for rel,h in summaries['control']['source_sha256'].items():
        if rel not in ('src/core.hpp','diagnostics/observed_optimizer.hpp'):
            require(summaries['strict']['source_sha256'][rel]==h,'Unexpected source change: '+rel)
    original=(runs['control']/'source/src/core.hpp').read_text()
    expected=original.replace('if (change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {',
                             'if (false) { // Diagnostic only: disable the combined action-change stop.',1)
    require((runs['strict']/'source/src/core.hpp').read_text()==expected,'Unexpected strict patch')
    native=table(runs['control']/'identified_ray.csv')[0]
    require(native['observation_row']=='8147','Unexpected native ray')
    source=[float(native['source_'+a+'_km']) for a in 'xyz']
    receiver=[float(native['receiver_'+a+'_km']) for a in 'xyz']
    grid=table(runs['control']/'initial_grid.csv')
    profile=sorted(set((float(r['z']),float(r['v'])) for r in grid))
    require(len(profile)==len(set(z for z,v in profile)),'Model is not horizontally uniform')
    spec=importlib.util.spec_from_file_location('reference',str(HERE/'source/first_arrival_1d_reference.py'))
    reference=importlib.util.module_from_spec(spec); spec.loader.exec_module(reference)
    result=reference.enumerate_arrivals([z for z,v in profile],[v for z,v in profile],source,receiver)
    require(result['complete'] and result['reference_valid'] and len(result['near_ties'])==1,'Reference is not unique/valid/complete')
    exact=result['first_arrival']; compared=[]
    for condition,p in runs.items():
        for r in summaries[condition]['results']:
            require(r['logged_matches_unobserved_variant']=='1','Observation hook changed optimizer result')
            row=dict(r,condition=condition)
            row['time_error_s']=float(r['time_s'])-exact['time_s']
            errors=[float(r['source_d'+a])-exact['source_derivative_s_per_km'][d] for d,a in enumerate('xyz')]
            for a,e in zip('xyz',errors): row['source_error_d'+a]=e
            row['source_error_norm_s_per_km']=math.sqrt(sum(e*e for e in errors))
            row['time_limit_pass']=abs(row['time_error_s'])<=2.5e-5
            row['source_vector_limit_pass']=row['source_error_norm_s_per_km']<=3e-6
            label='spacing'+format(float(r['path_spacing_km']),'.6f').replace('.','_')
            history=[h for h in table(p/label/'history.csv') if h['run_id']==r['run_id']]
            require(history[-1]['phase']=='final','Missing final observation hook')
            row['termination']='strict_gradient' if float(r['projected_gradient'])<1e-7 else (
                'combined_stop' if r['converged']=='1' else (
                'iteration_limit' if r['updates']==r['max_updates'] else 'line_search_no_acceptable_trial'))
            if row['termination']=='line_search_no_acceptable_trial':
                require(history[-2]['phase']=='line_search_failed' and
                        history[-2]['line_search_evaluations']=='24', 'Missing line-search failure evidence')
            for k in ('event_i_resource_id','origin_i_resource_id','pick_i_resource_id','arrival_i_resource_id',
                      'channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end'):
                row[k]=native[k]
            row['full_native_metadata_mapping']='../'+runs[condition].name+'/identified_ray.csv: observation_index = observation_row'
            compared.append(row)
    require(len(compared)==16,'Expected all 16 controls')
    parity=[]
    for saved in json.loads((HERE/'prior_controls.json').read_text()):
        candidates=[r for r in compared if r['condition']=='control' and float(r['path_spacing_km'])==saved['path_spacing_km'] and r['max_updates']=='1000']
        best=min(candidates,key=lambda r:float(r['time_s']))
        old=saved['row']
        for a,b in [('time_s','ray_time'),('projected_gradient','ray_projected_gradient')]+[('source_d'+a,'production_source_d'+a) for a in 'xyz']:
            require(float(format(float(best[a]),'.12g'))==float(old[b]),'Frozen original control changed: '+a)
        require(best['updates']==old['ray_iterations'] and best['converged']==old['ray_converged'],'Original stop changed')
        require((best['initialization']=='fmm')==(old['ray_selected_fmm_seed']=='1'),'Original selected start changed')
        parity.append(dict(path_spacing_km=saved['path_spacing_km'],selected_run=best['run_id'],matches_saved_frozen_control=True))
    with (HERE/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(compared[0]),lineterminator='\n');w.writeheader();w.writerows(compared)
    report=dict(scope='One native initial ray; isolated stop-rule diagnostic; no production change or inversion',
        native=native,profile=profile,reference=result,thresholds=dict(time_s=2.5e-5,source_vector_norm_s_per_km=3e-6),
        frozen_original_parity=parity,observer_parity_count=len(compared),strict_stopping_successes=sum(
            r['converged']=='1' for r in compared if r['condition']=='strict'),
        comparisons=compared,verified=verified,review_source_sha256=sha(Path(__file__)),
        reference_source_sha256=sha(HERE/'source/first_arrival_1d_reference.py'),
        comparison_sha256=sha(HERE/'comparison.csv'),prior_controls_sha256=sha(HERE/'prior_controls.json'),
        conclusions=['Extra optimization lowers the polyline actions but does not repair the source derivatives in this case.',
                     'No strict run reaches 1e-7; six exhaust their budgets and two repeats of the 0.0625 km FMM start fail the line search after 597 accepted updates.',
                     'Halving path spacing decreases time error, consistent with a discretization contribution; lack of strict stationarity prevents isolating pure optimized-polyline error.',
                     'This one-ray experiment does not explain all 16 earlier source-vector failures or updated three-dimensional models.'])
    (HERE/'review.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps([dict((k,r[k]) for k in ('condition','run_id','termination','time_error_s','source_error_norm_s_per_km')) for r in compared],indent=2))

if __name__=='__main__': main()
