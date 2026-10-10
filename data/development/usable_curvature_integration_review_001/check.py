#!/usr/bin/env python3
"""Read the frozen candidate/check outputs without compiling or tracing."""
import csv
import difflib
import hashlib
import json
import math
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'data/development/usable_curvature_integration_checks_001'
CANDIDATE=ROOT/'data/development/usable_curvature_integration_prepared_001'
cache={}


def sha(path):
    path=path.resolve()
    if path not in cache:
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        cache[path]=h.hexdigest()
    return cache[path]


def read(folder,name): return json.loads((folder/name).read_text())
def rows(folder,name):
    with (folder/name).open(newline='') as stream:return list(csv.DictReader(stream))
def need(ok,label):
    if not ok:raise ValueError(label)
def verify(base,mapping):
    for name,digest in mapping.items():need(sha(base/name)==digest,'Hash mismatch: '+str(base/name))

def main():
    s=read(OUT,'summary.json'); e=read(OUT,'execution.json'); c=read(OUT,'controller_completion.json'); launch=read(OUT,'launch.json')
    need(s['status']=='passed' and e['status']==c['status']=='completed' and e['return_code']==c['driver_return_code']==0 and c['child_reaped'],'Terminal gate')
    need(e['summary_sha256']==c['summary_sha256']==sha(OUT/'summary.json') and c['execution_sha256']==sha(OUT/'execution.json'),'Terminal binding')
    need(c['launch_sha256']==sha(OUT/'launch.json') and c['controller_sha256']==launch['controller_sha256']==sha(OUT/'controller.py'),'Controller binding')
    need(launch['launcher_sha256']==sha(OUT/'runner.py')==sha(ROOT/'diagnostics/run_usable_curvature_integration_checks.py'),'Executed wrapper source')
    verify(OUT,c['log_sha256'])
    need(not s['partial_hashes_withheld_live_descendants'] and s['maintained_sources_unchanged'] and s['executed_sources_unchanged'],'Frozen terminal outputs')
    p=read(CANDIDATE,'prepared.json')
    need(s['candidate_prepared_sha256']==launch['candidate_prepared_sha256']==sha(CANDIDATE/'prepared.json'),'Candidate binding')
    verify(ROOT,p['input_sha256']); verify(CANDIDATE,p['prepared_file_sha256'])
    verify(ROOT,p['baseline_source_sha256']); verify(CANDIDATE/'before',p['baseline_source_sha256'])
    verify(CANDIDATE/'after',p['candidate_source_sha256'])
    verify(ROOT,s['input_sha256']); verify(OUT/'source',s['source_sha256']); verify(OUT,s['output_sha256'])
    workspace=ROOT/s['workspace']; build=workspace.parent
    verify(workspace,s['source_sha256'])
    for name in p['candidate_source_sha256']:
        need(sha(CANDIDATE/'after'/name)==sha(OUT/'source'/name),'Executed candidate roster')
    changed=[name for name in p['baseline_source_sha256'] if p['baseline_source_sha256'][name]!=p['candidate_source_sha256'][name]]
    added=set(p['candidate_source_sha256'])-set(p['baseline_source_sha256'])
    need(changed==['src/core.hpp'] and added=={'src/usable_ray_curvature.hpp'},'Candidate scope')
    native=ROOT/'data/development/loma_usable_curvature_native_001'
    core=(native/'source/src/core.hpp').read_text().replace('#include "../diagnostics/usable_ray_curvature.hpp"','#include "usable_ray_curvature.hpp"',1)
    helper=(native/'source/diagnostics/usable_ray_curvature.hpp').read_text().replace('// Diagnostic copy only. Include after Vec, dot and inverse_ray_metric.','// Include after Vec, dot and inverse_ray_metric; checked L-BFGS arithmetic.',1)
    need(core==(CANDIDATE/'after/src/core.hpp').read_text() and helper==(CANDIDATE/'after/src/usable_ray_curvature.hpp').read_text(),'Reviewed D numerical mapping')
    need(p['native_review_sha256']==sha(native/'review.json') and p['native_summary_sha256']==sha(native/'summary.json'),'Native D lineage')
    # Reconstruct both packaging edits without executing the copied runners.
    for name in ('run_fmm_initialization_audit.py','run_fmm_rotated_affine.py'):
        before=(OUT/'runner_before'/name).read_text()
        need(before==(ROOT/'diagnostics'/name).read_text(),'Original runner unchanged')
        token='"src/ray_metric.hpp",' if 'initialization' in name else "'src/ray_metric.hpp',"
        addition=' "src/usable_ray_curvature.hpp",' if token[0]=='"' else " 'src/usable_ray_curvature.hpp',"
        need(before.count(token)==1,'Unique packaging insertion')
        after=before.replace(token,token+addition,1)
        need(after==(OUT/'source/diagnostics'/name).read_text(),'Packaging-only runner edit')
        diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original/'+name,tofile='copied/'+name))
        need(diff==(OUT/(name+'.packaging.diff')).read_text(),'Saved packaging diff')
    for name,digest in s['source_sha256'].items():
        if name.startswith('diagnostics/') and not Path(name).name.startswith('run_fmm_'):
            need(sha(ROOT/name)==digest,'Unchanged diagnostic source')
    need('-O3' in s['flags'] and '-fopenmp' in s['flags'] and '-DNDEBUG' not in s['flags'],'Recorded compiler flags')
    need(sha(Path(s['compiler']))==s['compiler_sha256'],'Compiler pin')
    verify(Path('/'),s['runtime_library_sha256'])
    binary_paths=dict(dd=build/'cmake/dd',inversion_gate=build/'inversion_gate',external_input=build/'external_input')
    for name,digest in s['binary_sha256'].items():need(sha(binary_paths[name])==digest,'Binary pin')
    need(len(s['commands'])==11 and all(r['status']=='completed' and r['return_code']==0 for r in s['commands']),'All commands completed')
    need([(r['label'],r['threads']) for r in s['commands'] if r['threads']!=1]==[('inversion_gate',4),('external_input',4)],'Thread roster')
    core_rows=rows(OUT,'results/core/validation.csv')
    need(len(core_rows)==s['core_checks']==48 and all(r['passed']=='1' and math.isfinite(float(r['error'])) and float(r['error'])<=float(r['tolerance']) for r in core_rows),'Core controls')
    for name,path in [('inversion_gate','results/inversion_gate/summary.json'),('external_input','results/external_input.json')]:
        need(read(OUT,path)==s[name] and s[name]['status']=='passed','Saved component summary')
    need(s['inversion_gate']['altered_ray_causes']==9 and s['inversion_gate']['current_trial_final_rejections']==3 and not s['inversion_gate']['real_inversions_run'],'Guard scope')
    need(len(s['external_input']['checks'])==11 and not s['external_input']['inversions_run'],'External input scope')
    stats={}; archive_members=0
    for label,dirname,expected_rows,expected_checks,expected_parity in [('layered','fmm_initialization_usable_curvature_001',44,37,58),('oblique','fmm_rotated_affine_usable_curvature_001',6,72,6)]:
        folder=OUT/'analytic_results'/dirname
        child=read(folder,'summary.json');need(child==s[label],'Child summary binding')
        verify(workspace,child['sha256'])
        child_source=workspace/('tmp/fmm_initialization_audit/usable_curvature_001/source' if label=='layered' else 'tmp/fmm_rotated_affine/usable_curvature_001/source')
        verify(child_source,child['source_sha256'])
        with tarfile.open(str(folder/'source_snapshot.tar.gz'),'r:gz') as archive:
            members=archive.getmembers()
            need({m.name for m in members}==set(child['source_sha256']) and len(members)==len(child['source_sha256']),'Archive source roster')
            for member in members:
                need(member.isfile() and member.uid==member.gid==member.mtime==0 and not member.uname and not member.gname,'Sanitized source archive')
                need(hashlib.sha256(archive.extractfile(member).read()).hexdigest()==child['source_sha256'][member.name],'Archived source bytes')
                if member.name!='diagnostics/seeded_bending.hpp':need(child['source_sha256'][member.name]==sha(OUT/'source'/member.name),'Child snapshot equals candidate')
            archive_members+=len(members)
        # The copied optimizer body remains byte-identical, independently of the
        # reported entry comparisons. Do not execute its source generator.
        body=core[core.index('  int merged = merge_close_nodes(p), updates = 0;'):core.index('\nstruct Entry {')]
        header=(child_source/'diagnostics/seeded_bending.hpp').read_text()
        need(header.endswith(body+'\n'),'Generated optimizer body mapping')
        result=rows(folder,'results.csv'); checks=rows(folder,'consistency.csv' if label=='layered' else 'checks.csv'); parity=rows(folder,'entry_parity.csv')
        need(len(result)==expected_rows and len(checks)==expected_checks and len(parity)==expected_parity,'Analytic support')
        need(all(r['passed']=='1' and math.isfinite(float(r['value'])) and float(r['value'])<=float(r['tolerance']) for r in checks),'Declared analytic gates')
        need([int(r['call']) for r in parity]==list(range(expected_parity)),'Parity call ordering')
        for row in parity:
            need(all(value=='1' for key,value in row.items() if key.endswith('_equal') or key in ('passed','seeded_entry_checked')),'Exact numeric entry comparisons')
            need(row['prototype_selected_time_s']==row['production_selected_time_s'],'Saved selected time parity')
        need(child['production_entry'] and child['order']==2 and child['closed_seed_cells'] and not child['real_observations_used'],'Analytic settings')
        time_error=[]; source_error=[]
        for r in result:
            require_flag='converged' if label=='layered' else 'best_converged'
            need(r['extracted']==r[require_flag]=='1' and int(r['outside_nodes'])==0 and float(r['endpoint_error_km'])==0,'Selected flags/endpoints/domain')
            dt=abs(float(r['best_time_s'])-float(r['reference_time_s']))
            key='time_error_s' if label=='layered' else 'best_time_error_s'
            need(abs(dt-abs(float(r[key])))<2e-13,'Saved time error serialization')
            if label=='layered':
                norm=math.sqrt(sum((float(r['source_d'+axis])-float(r['reference_d'+axis]))**2 for axis in 'xyz'))
                need(abs(norm-float(r['source_error_s_per_km']))<2e-15,'Saved source norm serialization')
                source_error.append(float(r['source_error_s_per_km']))
            else:
                norm=math.sqrt(sum((float(r['fmm_source_d'+axis])-float(r['reference_source_d'+axis]))**2 for axis in 'xyz'))
                need(abs(norm-float(r['fmm_source_error_s_per_km']))<2e-15 and r['fmm_converged']=='1','FMM norm/local flag')
                source_error.append(float(r['best_source_error_s_per_km']))
            time_error.append(abs(float(r[key])))
        stats[label]=dict(rows=len(result),declared_checks=len(checks),production_entry_numeric_comparisons=len(parity),maximum_saved_time_error_s=max(time_error),maximum_saved_source_norm_error_s_per_km=max(source_error))
        if label=='layered':
            fine=[r for r in result if float(r['auxiliary_spacing_km'])==float(r['path_spacing_km'])==.0625]
            coarse_exceedances=[r for r in result if abs(float(r['time_error_s']))>25e-6 or float(r['source_error_s_per_km'])>3e-6]
            need(len(fine)==11 and len(coarse_exceedances)==1,'Fine-grid scope and retained coarse failure')
            bad=coarse_exceedances[0]
            need(bad['case']=='constant_top_gradient' and float(bad['distance_km'])==14.68 and float(bad['auxiliary_spacing_km'])==float(bad['path_spacing_km'])==.125,'Known coarse case')
            stats[label].update(finest_grid_rows=len(fine),finest_grid_maximum_time_error_s=max(abs(float(r['time_error_s'])) for r in fine),finest_grid_maximum_source_norm_error_s_per_km=max(float(r['source_error_s_per_km']) for r in fine),coarse_exceedances=coarse_exceedances)
    pins={str(p.relative_to(ROOT)):d for p,d in cache.items() if ROOT in p.parents}
    old_cache=dict(cache);cache.clear()
    for path,digest in old_cache.items():need(sha(path)==digest,'Post-read hash: '+str(path))
    result=dict(status='passed',reviewer='/root/scientific_audit/ray_math_review',summary_sha256=sha(OUT/'summary.json'),execution_sha256=sha(OUT/'execution.json'),controller_completion_sha256=sha(OUT/'controller_completion.json'),prepared_sha256=sha(CANDIDATE/'prepared.json'),checker_sha256=sha(Path(__file__)),
        method='Source/packaging diff review and saved-output/hash/arithmetic reconstruction only; no build, native trace or control rerun.',
        material_issue_found=False,counts=dict(prepared_ancestry_pins=len(p['input_sha256']),launch_input_pins=len(s['input_sha256']),frozen_sources=len(s['source_sha256']),terminal_output_pins=len(s['output_sha256']),archive_members=archive_members,core_checks=48,successful_commands=11,unchanged_original_source_and_CMake_members=len(p['baseline_source_sha256'])-1),
        source_mapping=dict(core_matches_reviewed_D_except_include=True,helper_matches_reviewed_D_except_comment=True,runner_changes_only_helper_inventory=True,other_diagnostics_unchanged=True,maintained_production_sources_unchanged=True),
        results=stats,source_and_output_sha256=pins,
        limitations=['Only declared invented integration controls and already reviewed single-ray D mapping are assessed.',
          'The layered analytic accuracy gates use the finest grid. One saved coarse source error exceeds 3e-6 and is retained explicitly.',
          'Entry comparisons are exact numeric equality, not representation-bit equality of signed zeros.',
          'Local flags preserve both original stopping alternatives; they do not all imply strict 1e-7 gradient convergence.',
          'No historical full-cohort equivalence, general first-arrival, nonsmooth or endpoint-discretization certificate, production adoption or new inverse acceptance.'])
    with (HERE/'review.json').open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='passed',review_sha256=sha(HERE/'review.json'),counts=result['counts'],results=stats),indent=2))


if __name__=='__main__':main()
