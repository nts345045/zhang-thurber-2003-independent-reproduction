#!/usr/bin/env python3
"""Audit the saved B seed-load replay without constructing fields or rays."""
import csv
import difflib
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/development/loma_seed_loaded_b_native_001'
BASE=ROOT/'data/development/loma_outer_accumulation_native_001'
CAPTURE=ROOT/'data/development/loma_curvature_capture_native_001'
TABLES=('results.csv','history.csv','paths.csv','path_gradient_checks.csv','cone_metric.csv')


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def load(path):return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def verify(base,mapping):
    for name,digest in mapping.items():need(sha(base/name)==digest,'Hash mismatch: '+str(base/name))


def number(value):
    x=float(value);need(math.isfinite(x),'Nonfinite saved modeled value');return x


def check():
    for name,digest in [('summary.json','7e0f2b7cf435794af124f35e55d1c6faa2faa0d850150ecb631be0d818bfcc59'),
                        ('execution.json','e05512836570c4dd05f00c1308e76893c5c22b9aab89f4c9de45f7b56da1504b'),
                        ('controller_completion.json','2b777340d4881c65a428360bd96e2bae29daa7e87aa31dde809c4c6447f4f78d')]:
        need(sha(OUT/name)==digest,'Unexpected terminal pin '+name)
    summary,execution,controller,prepared,prelaunch=[load(OUT/name) for name in
        ('summary.json','execution.json','controller_completion.json','prepared.json','prelaunch_review.json')]
    need(summary['status']=='completed_seed_loaded_B_neutrality' and execution['status']=='completed' and
         execution['return_code']==0 and execution['summary_sha256']==sha(OUT/'summary.json'),'Native stage not terminal')
    need(controller['status']=='completed' and controller['child_reaped'] is True and controller['driver_return_code']==0 and
         controller['summary_sha256']==sha(OUT/'summary.json') and controller['execution_sha256']==sha(OUT/'execution.json') and
         controller['launch_sha256']==sha(OUT/'launch.json') and controller['controller_sha256']==sha(OUT/'controller.py'),
         'Controller lifecycle/link mismatch')
    verify(OUT,controller['log_sha256'])
    need(summary['prepared_sha256']==sha(OUT/'prepared.json') and prelaunch['prepared_sha256']==sha(OUT/'prepared.json') and
         prelaunch['status']=='passed' and summary['prelaunch_review_sha256']==sha(OUT/'prelaunch_review.json') and
         prelaunch['launcher_sha256']==sha(OUT/'launcher.py')==prepared['launcher_sha256'], 'Prelaunch/source pin mismatch')
    verify(ROOT,prepared['input_sha256']);verify(OUT,prepared['prepared_file_sha256'])
    verify(OUT/'source',summary['source_sha256']);verify(OUT,summary['output_sha256'])
    need(summary['source_sha256']==prepared['source_sha256'] and
         summary['original_retention_predicate']=='sy > 1e-14' and not summary['positive_variant_allowed'],
         'Retention experiment unexpectedly changed')
    need((summary['path_spacing_km'],summary['field_spacing_km'],summary['maximum_updates'],summary['threads'])==
         (.03125,.125,1000,1),'Frozen B settings changed')
    need(sha(Path(summary['compiler']))==summary['compiler_sha256'] and
         sha(ROOT/summary['build']/'observe')==summary['binary_sha256'],'Compiler/binary pin mismatch')
    verify(Path('/'),summary['runtime_library_sha256'])
    need([c['stage'] for c in summary['commands']]==['compile','runtime_libraries','observe'] and
         all(c['status']=='completed' and c['return_code']==0 for c in summary['commands']), 'Recorded child stage mismatch')
    controls,control_review=[load(OUT/'inputs'/name) for name in ('controls_summary.json','controls_review.json')]
    need(controls['status']==control_review['status']=='passed' and
         control_review['summary_sha256']==sha(OUT/'inputs/controls_summary.json') and
         control_review['execution_sha256']==sha(OUT/'inputs/controls_execution.json') and
         controls['variants']['seed_loaded_B']['checks_passed']==100, 'Control review link mismatch')
    context=summary['native_context']
    need(context==prepared['native_context']==load(CAPTURE/'summary.json')['native_context'] and
         rows(OUT/'identified_ray.csv')==[context] and len(context)==199 and context['observation_index']=='3426',
         'Complete native context mismatch')
    for file in (BASE/'source/src').iterdir():
        if file.is_file():need(sha(file)==sha(OUT/'source/src'/file.name),'Frozen B numerical source changed')
    need((BASE/'source/diagnostics/observed_optimizer.hpp').read_bytes()==
         (OUT/'source/diagnostics/observed_optimizer.hpp').read_bytes(),'Frozen observer mathematics changed')
    original=(BASE/'source/diagnostics/check_ray_stopping.cpp').read_text()
    modified=(OUT/'source/diagnostics/check_ray_stopping.cpp').read_text()
    diff=''.join(difflib.unified_diff(original.splitlines(True),modified.splitlines(True),
                fromfile='frozen_B/check_ray_stopping.cpp',tofile='seed_loaded_B/check_ray_stopping.cpp'))
    need(diff==(OUT/'seed_loader_driver.diff').read_text() and 'first_arrival::Field field' not in modified and
         'read_saved_candidate(g,a,b,saved_run,audit_observation,argv[7],argv[8])' in modified,
         'Driver change differs from reviewed seed loader')
    for name in ('curvature_initialization.csv','curvature_seed_metadata.csv'):
        need((OUT/'inputs'/name).read_bytes()==(CAPTURE/name).read_bytes(),'Captured seed changed')
        side=load(OUT/'inputs'/(name+'.identifiers.json'))
        need(side['file_sha256']==sha(OUT/'inputs'/name) and side['native_context']==context and
             side['join_key']=='observation_index' and side['join_value']=='3426','Seed native sidecar mismatch')
    seed_metadata=rows(OUT/'inputs/curvature_seed_metadata.csv');need(len(seed_metadata)==1,'Candidate metadata inventory mismatch')
    metadata=seed_metadata[0];run='fmm_0.031250_1000'
    need(metadata['run_id']==run and metadata['observation_index']=='3426' and metadata['success']=='1',
         'Candidate identity/success mismatch')
    number(metadata['field_time_s']);need(int(metadata['descent_steps'])>=0 and int(metadata['fallback_steps'])>=0,
                                        'Invalid candidate counters')
    grid=rows(OUT/'inputs/initial_grid.csv');bounds={a:(min(number(r[a]) for r in grid),max(number(r[a]) for r in grid)) for a in 'xyz'}
    frames={}
    for row in rows(OUT/'inputs/curvature_initialization.csv'):
        need(row['run_id']==run and row['observation_index']=='3426','Candidate frame identity mismatch')
        frame=frames.setdefault(row['kind'],[]);need(int(row['node'])==len(frame),'Candidate frame order mismatch');frame.append(row)
        need(all(bounds[a][0]<=number(row[a])<=bounds[a][1] for a in 'xyz'),'Candidate frame outside box')
    need({k:len(v) for k,v in frames.items()}=={'raw_fmm_seed':568,'post_resampling_and_merge':1134},'Candidate frame inventory mismatch')
    for frame in frames.values():
        for row,prefix in [(frame[0],'source'),(frame[-1],'receiver')]:
            need(all(number(row[a])==number(context[prefix+'_'+a+'_km']) for a in 'xyz'),'Candidate endpoint changed')
    table_hashes={};counts={}
    for name in TABLES:
        digest=sha(OUT/name);need(digest==sha(BASE/name)==sha(CAPTURE/name)==prepared['expected_old_table_sha256'][name],
                                'One of five B tables changed: '+name)
        table_hashes[name]=digest;table=rows(OUT/name);counts[name]=len(table)
        need(all(r['observation_index']=='3426' and r['run_id'] in ('fmm_0.031250_1000','straight_0.031250_1000') for r in table),
             'Native output join mismatch')
        side=load(OUT/(name+'.identifiers.json'))
        need(side['file_sha256']==digest and side['native_context']==context and side['join_key']=='observation_index' and
             side['join_value']=='3426' and side['context_sha256']==sha(OUT/'identified_ray.csv'),'Output sidecar mismatch')
    results=rows(OUT/'results.csv');need(results==summary['results'] and len(results)==2 and
        all(r['logged_matches_unobserved_variant']=='1' for r in results),'Saved same-variant numeric parity failed')
    reference=load(OUT/'inputs/reference_row.json');history=rows(OUT/'history.csv');comparisons=[]
    for r in results:
        run_history=[h for h in history if h['run_id']==r['run_id']];accepted=[h for h in run_history if h['phase']=='accepted']
        need(len(accepted)==int(r['updates']) and run_history[-1]['phase']=='final','History termination/count mismatch')
        time_error=number(r['time_s'])-number(reference['reference_time_s'])
        norm=math.sqrt(sum((number(r['source_d'+a])-number(reference['reference_source_d'+a+'_s_per_km']))**2 for a in 'xyz'))
        saved=[c for c in summary['continuous_reference_comparison'] if c['run_id']==r['run_id']]
        need(len(saved)==1 and saved[0]['time_error_s']==time_error and
             saved[0]['source_error_euclidean_norm_s_per_km']==norm and saved[0]['native_context']==context and
             saved[0]['original_local_convergence_flag']==r['converged'] and saved[0]['final_history']==run_history[-1],
             'Reference/history comparison mismatch')
        need(saved[0]['time_limit_pass']==(abs(time_error)<=2.5e-5) and saved[0]['source_limit_pass']==(norm<=3e-6),
             'Original accuracy-limit classification changed')
        pairs=sum(int(h['curvature_pair_accepted']) for h in accepted)
        need(pairs==saved[0]['accepted_curvature_pairs'],'Curvature count changed')
        comparisons.append(dict(run_id=r['run_id'],updates=int(r['updates']),local_flag=r['converged'],
            accepted_curvature_pairs=pairs,time_error_s=time_error,source_error_euclidean_norm_s_per_km=norm))
    need([(r['updates'],r['local_flag'],r['accepted_curvature_pairs']) for r in comparisons]==[(54,'1',54),(1000,'0',40)],
         'Original B stopping/retention changed')
    need(summary['selected_run_id']==run and summary['original_five_tables_byte_identical'] and
         summary['observed_paths_and_arrays_match_unobserved_variant'],'Original selection or parity changed')
    verify(ROOT,prepared['input_sha256']);verify(OUT,summary['output_sha256'])
    return dict(status='passed',material_issue_found=False,summary_sha256=sha(OUT/'summary.json'),
                execution_sha256=sha(OUT/'execution.json'),controller_completion_sha256=sha(OUT/'controller_completion.json'),
                prepared_sha256=sha(OUT/'prepared.json'),prelaunch_review_sha256=sha(OUT/'prelaunch_review.json'),
                checker_sha256=sha(Path(__file__)),verified_input_pins=len(prepared['input_sha256']),
                verified_prepared_pins=len(prepared['prepared_file_sha256']),verified_source_pins=len(summary['source_sha256']),
                verified_output_pins=len(summary['output_sha256']),five_tables_byte_identical_sha256=table_hashes,
                output_row_counts=counts,full_native_context=context,full_candidate_metadata_and_frames_match=True,
                source_change_only_reviewed_driver_seed_loading=True,original_B_core_observer_byte_identical=True,
                original_retention_predicate='sy > 1e-14',positive_variant_executed=False,
                same_variant_observer_numeric_parity_recorded=True,reference_comparisons=comparisons,
                scope='Saved files, exact table/source/hash equality, native joins, recorded lifecycle and reference-error arithmetic only.',
                limitations=['No field, ray, action, optimizer or reference was reexecuted for this review.',
                    'The replay validates loading this captured Candidate; it does not validate a changed curvature-retention rule.',
                    'Same-variant path/array comparison is the frozen driver numeric check, not a new bit-pattern ray rerun.',
                    'The selected FMM ray retains its false local flag after1000 updates despite passing existing reference limits.'])


if __name__=='__main__':print(json.dumps(check(),indent=2,allow_nan=False))
