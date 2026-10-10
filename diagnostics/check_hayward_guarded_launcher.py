#!/usr/bin/env python3
"""Invented end-to-end eligibility, native-output and interruption controls."""
import argparse
import copy
import csv
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import run_hayward_guarded_inversion as launcher
from run_loma_initial_preflight import live_group_members


def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def table(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def write(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--variant',required=True);args=parser.parse_args()
    if not args.variant.replace('_','').isalnum():raise ValueError('Use a simple variant')
    out=ROOT/'data/development/hayward_guarded_launcher_checks'/args.variant
    build=ROOT/'tmp/hayward_guarded_launcher_checks'/args.variant
    out.mkdir(parents=True);build.mkdir(parents=True)
    summary=dict(status='running',scope='Invented geometry and review-schema fixtures; no real inversion or scientific acceptance',checks=[],commands=[])
    parity_original=ROOT/'data/development/hayward_guard_adoption_checks/001'
    parity_original_hash=launcher.sha(parity_original/'summary.json')
    # Rejection fixtures mutate only this owned copy, never frozen controls.
    shutil.copytree(str(parity_original),str(out/'copied_adoption_controls'))
    parity=out/'copied_adoption_controls/summary.json'
    baseline=ROOT/'tmp/hayward_guard_adoption_checks/001/baseline/dd'
    fixture=ROOT/'data/development/hayward_guard_adoption_checks/001/guarded_external_t1'
    data=out/'invented_preflight';data.mkdir();reference=out/'invented_reference';reference.mkdir()
    accuracy=out/'invented_accuracy_review.json'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(ROOT/'tmp'),OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1')
    def save():dump(out/'summary.json',summary)
    def run(name,command,expected=0):
        with (out/(name+'_stdout.log')).open('x') as a,(out/(name+'_stderr.log')).open('x') as b:
            code=subprocess.call(list(map(str,command)),cwd=str(ROOT),env=env,stdout=a,stderr=b)
        summary['commands'].append(dict(name=name,command=list(map(str,command)),return_code=code));save()
        assert (code==0)==(expected==0),name
    def check(name,ok):
        summary['checks'].append(dict(name=name,passed=bool(ok)));assert ok,name
    def reject(name,path,update):
        saved=path.read_bytes()
        try:
            value=json.loads(saved.decode());update(value);dump(path,value)
            try:launcher.reviewed_inputs(data,reference,accuracy,parity)
            except (ValueError,KeyError,FileNotFoundError):check(name,True)
            else:raise AssertionError('Accepted '+name)
        finally:path.write_bytes(saved)
    try:
        sources=['run_hayward_guarded_inversion.py','run_loma_initial_preflight.py','run_loma_analytic_simulation.py',
                 'diagnostics/review_loma_analytic_simulation.py','diagnostics/check_hayward_guarded_launcher.py']
        for name in sources:
            target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(ROOT/name),str(target))
        summary['source_sha256']={n:launcher.sha(ROOT/n)for n in sources}
        events=table(fixture/'initial_events.csv')[:2]
        stations=table(fixture/'cross_epoch/stations.csv');stations=[stations[0],stations[2]];stations[1]['id']='1'
        write(data/'initial_events.csv',events);write(data/'stations.csv',stations)
        grid=[dict(x=x,y=y,z=z,v=6)for z in(-1,3)for y in(-1,1)for x in(-1,2)]
        write(data/'initial_grid.csv',grid)
        old=table(fixture/'cross_epoch/observations.csv');observations=[]
        def arrival(i,k):
            return math.sqrt(sum((float(events[i][a])-float(stations[k][a]))**2 for a in 'xyz'))/6
        for i,k in [(0,0),(1,0),(0,1)]:
            row=dict(old[0]);row.update(i=str(i),station=str(k),value=format(arrival(i,k),'.17g'),
                event_i_resource_id=events[i]['event_resource_id'],origin_i_resource_id=events[i]['origin_resource_id'],
                pick_i_resource_id='smi:fixture/pick{}_{}'.format(i,k),arrival_i_resource_id='smi:fixture/arrival{}_{}'.format(i,k),
                metadata_epoch_start=stations[k]['metadata_epoch_start'],metadata_epoch_end=stations[k]['metadata_epoch_end'],
                channel_source_sha256=stations[k]['source_sha256'])
            observations.append(row)
        row=dict(old[1]);row.update(station_j='1',value=format(arrival(1,0)-arrival(0,1),'.17g'),
            pick_i_resource_id='smi:fixture/pick1_0',pick_j_resource_id='smi:fixture/pick0_1',
            arrival_i_resource_id='smi:fixture/arrival1_0',arrival_j_resource_id='smi:fixture/arrival0_1')
        observations.append(row);write(data/'observations.csv',observations)
        (data/'run.cfg').write_text('authoritative_ids_required 1\ncatalog_only_dd 1\nray_initializer 1\nray_spacing 0.03125\nfmm_spacing 0.125\nray_iterations 1000\niterations 1\nstage_length 6\ndamping 0.1\nsmoothing 1\npair_distance 20\n')
        for name in launcher.COPIED:
            if not (data/name).exists():(data/name).write_text('{"scope":"invented launcher fixture"}\n'if name.endswith('.json') else 'invented fixture only\n')
        run('initial_linearize',[baseline,'linearize',data/'run.cfg',data,'initial'])
        run('initial_raycheck',[baseline,'raycheck',data/'run.cfg',data,'initial'])
        initial=table(data/'initial_linearization_rows.csv');mat=table(data/'initial_linearization_matrix.csv')
        by_row={int(r['row']):{}for r in initial}
        for r in mat:by_row[int(r['row'])][int(r['column'])]=float(r['value'])
        errors=[]
        for n,row in enumerate(initial):
            i,k=int(row['i']),int(row['station']);a=[float(events[i][v])-float(stations[k][v])for v in 'xyz'];length=math.sqrt(sum(v*v for v in a))
            derivative=[v/(6*length)for v in a]
            errors.append(dict(event=i,station=k,event_resource_id=events[i]['event_resource_id'],origin_resource_id=events[i]['origin_resource_id'],
                channel_seed_id=stations[k]['channel_seed_id'],channel_fdsn_source_id=stations[k]['channel_fdsn_source_id'],
                metadata_epoch_start=stations[k]['metadata_epoch_start'],metadata_epoch_end=stations[k]['metadata_epoch_end'],
                time_error_s=abs(float(row['ray_time'])-length/6),source_error_s_per_km=math.sqrt(sum((by_row[n].get(4*i+j,0)-derivative[j])**2 for j in range(3)))))
        write(reference/'analytic_comparison.csv',errors)
        check('actual_invented_reference_limits',all(r['time_error_s']<=2.5e-5 and r['source_error_s_per_km']<=3e-6 for r in errors))
        actual_manifest=json.loads((ROOT/'data/hayward_first_arrival_004/run_manifest.json').read_text())
        manifest=dict(threads=4,binary=str(baseline.relative_to(ROOT)),source_sha256=actual_manifest['source_sha256'],
                      sha256={str((data/n).relative_to(ROOT)):launcher.sha(data/n)for n in launcher.COPIED})
        manifest['sha256'][manifest['binary']]=launcher.sha(baseline);dump(data/'run_manifest.json',manifest)
        preflight=dict(status='ready_for_accuracy_review',failures=[],absolute_rays=3,sample_rays=3,
            derivative_components=len(table(data/'initial_ray_derivatives.csv')),
            sha256={p.name:launcher.sha(p)for p in data.glob('initial_*csv')})
        dump(data/'preflight.json',preflight)
        ledger=dict(status='ready_for_accuracy_review',return_code=0,current_command_return_code=0,
                    completed_commands=[dict(stage=n,return_code=0)for n in('initial_linearize','initial_raycheck')])
        dump(data/'preflight_execution.json',ledger)
        full=dict(status='complete',rays=3,unique_native_pairs=3,accuracy_control_limits=launcher.LIMITS,
            accuracy={'all':{'both_limits_pass':3}},original_reverified_sha256=dict(manifest['sha256']))
        full['original_reverified_sha256'].update({str((data/n).relative_to(ROOT)):v for n,v in preflight['sha256'].items()})
        dump(reference/'summary.json',full)
        with tarfile.open(str(reference/'frozen_tables.tar.gz'),'w:gz')as archive:archive.add(str(reference/'analytic_comparison.csv'),arcname='analytic_comparison.csv')
        package=dict(status='verified_lossless',archive='frozen_tables.tar.gz',archive_info={'sha256':launcher.sha(reference/'frozen_tables.tar.gz')})
        dump(reference/'packaging.json',package)
        review=dict(status='passed',scope='Invented homogeneous analytic fixture calculated by test helper; not a real independent publication review',material_issue_found=False,
            summary_sha256=launcher.sha(reference/'summary.json'),packaging_sha256=launcher.sha(reference/'packaging.json'),verified_pairs=3,both_limits_pass=3,
            saved_local_convergence_pass=3,saved_initialization_pass=3,maximum_absolute_time_error_s=max(r['time_error_s']for r in errors),
            maximum_source_error_euclidean_norm_s_per_km=max(r['source_error_s_per_km']for r in errors))
        for key in('native_metadata_fields_all_match','source_column_metadata_all_match','complete_original_absolute_support','source_derivatives_reconstructed_from_sparse_triplets'):review[key]=True
        dump(reference/'independent_review.json',review)
        final_review=dict(status='passed',decision='eligible_for_guarded_dd_attempt',preflight_directory=str(data.relative_to(ROOT)),
            checks={k:True for k in launcher.REVIEW_CHECKS},interpretation='Invented homogeneous fixture; exact reference errors pass and finite differences are only schema controls.',
            limitations=['Fixture reviews exercise lifecycle gates, not a claim of independent validation of real data.'],
            sha256={key:launcher.sha(path)for key,path in {'preflight_manifest':data/'run_manifest.json','preflight_ledger':data/'preflight_execution.json',
                'preflight_checks':data/'preflight.json','full_reference_summary':reference/'summary.json','full_reference_review':reference/'independent_review.json'}.items()},
            sampled_tables_sha256={n:launcher.sha(data/n)for n in launcher.SAMPLE_FILES})
        dump(accuracy,final_review)
        launcher.reviewed_inputs(data,reference,accuracy,parity);check('complete_invented_eligibility_contract',True)
        original={str(p.relative_to(data)):launcher.sha(p)for p in data.rglob('*')if p.is_file()}
        for name,status in [('running_ledger_rejected','running'),('failed_ledger_rejected','failed')]:
            reject(name,data/'preflight_execution.json',lambda d,status=status:d.update(status=status))
        reject('missing_successful_child_rejected',data/'preflight_execution.json',lambda d:d.update(completed_commands=[]))
        reject('preflight_failure_rejected',data/'preflight.json',lambda d:d.update(failures=['local failure']))
        reject('unaccepted_accuracy_review_rejected',accuracy,lambda d:d.update(decision='awaiting_review'))
        reject('stale_accuracy_review_rejected',accuracy,lambda d:d['sha256'].update(preflight_ledger='stale'))
        reject('unassessed_fd_rejected',accuracy,lambda d:d['checks'].update(finite_difference_truncation_assessed=False))
        reject('stale_sample_review_rejected',accuracy,lambda d:d['sampled_tables_sha256'].update(initial_ray_derivatives='stale'))
        reject('full_reference_failure_rejected',reference/'independent_review.json',lambda d:d.update(both_limits_pass=2))
        reject('wrong_source_limit_rejected',reference/'summary.json',lambda d:d['accuracy_control_limits'].update(source_euclidean_norm_s_per_km=1e-5))
        reject('failed_guard_parity_rejected',parity,lambda d:d.update(status='failed'))
        for name in('observations.csv','initial_events.csv','stations.csv','run.cfg'):
            p=data/name;saved=p.read_bytes()
            try:
                p.write_bytes(saved+b'changed\n')
                try:launcher.reviewed_inputs(data,reference,accuracy,parity)
                except ValueError:check('changed_'+name+'_rejected',True)
                else:raise AssertionError(name)
            finally:p.write_bytes(saved)
        command=[sys.executable,ROOT/'run_hayward_guarded_inversion.py','--preflight',data,'--reference',reference,
                 '--accuracy-review',accuracy,'--parity-review',parity,'--output',out/'run','--build',build/'run']
        run('launcher',command)
        result=json.loads((out/'run/dd_inversion_execution.json').read_text())
        check('completed_without_scientific_success',result['status']=='completed_pending_final_diagnostics' and result['scientific_success']is False)
        check('one_DD_command_only',[c['stage']for c in result['completed_commands']if c['stage'].endswith('_invert')]==['dd_invert'])
        output_expected=json.loads((out/'run/dd_inversion_run_manifest.json').read_text())['expected_counts']
        for name,key,value in [('dd_coverage.csv','path_length','nan'),
                               ('dd_residuals.csv','i_initialization_succeeded','0'),
                               ('dd_history.csv','ray_initialization_succeeded_count','0'),
                               ('dd_matrix_preflight.csv','columns','0')]:
            target=out/'run'/name;saved=target.read_bytes()
            try:
                invalid=table(target);invalid[0][key]=value;write(target,invalid)
                try:launcher.check_inverse(out/'run',output_expected)
                except ValueError:check('invalid_output_'+key+'_rejected',True)
                else:raise AssertionError('Invalid output accepted: '+key)
            finally:target.write_bytes(saved)
        launcher.verify_hashes(out/'run',json.loads((out/'run/dd_inversion_run_manifest.json').read_text())['input_sha256'])
        launcher.verify_hashes(out/'run',result['output_sha256']);check('all_output_and_copied_input_hashes',True)
        launcher.verify_hashes(data,original);check('original_fixture_unchanged',True)
        run('duplicate_run_rejected',command,1)
        # Actual new-driver SIGTERM while a compiler descendant is writing.
        stopped=out/'interrupted';interrupted_build=build/'interrupted'
        interrupt_command=command[:-4]+['--output',stopped,'--build',interrupted_build]
        with (out/'interrupt_stdout.log').open('x')as a,(out/'interrupt_stderr.log').open('x')as b:
            process=subprocess.Popen(list(map(str,interrupt_command)),cwd=str(ROOT),env=env,stdout=a,stderr=b,start_new_session=True)
            deadline=time.monotonic()+90;group=None
            while time.monotonic()<deadline and process.poll()is None:
                try:d=json.loads((stopped/'dd_inversion_execution.json').read_text())
                except(FileNotFoundError,json.JSONDecodeError):time.sleep(.05);continue
                if d.get('current_stage')=='compile'and d.get('current_child_pid'):
                    group=d['current_child_pid']
                    compiler_live=False
                    for pid in live_group_members(group):
                        try:compiler_live |= 'cc1plus' in (Path('/proc')/str(pid)/'stat').read_text()
                        except FileNotFoundError:pass
                    if compiler_live:break
                time.sleep(.05)
            assert group is not None and process.poll()is None,'Compiler interruption point missing'
            process.send_signal(signal.SIGTERM);code=process.wait(timeout=30)
        ledger=json.loads((stopped/'dd_inversion_execution.json').read_text())
        check('interrupted_terminal_driver',code==143 and ledger['status']=='interrupted')
        check('actual_descendants_terminated',ledger['exception_child']['remaining_live_group_members']==[] and live_group_members(group)==[])
        launcher.verify_hashes(stopped,ledger['partial_output_sha256']);check('interruption_hashes_stable_after_descendants',True)
        launcher.verify_hashes(data,original);check('original_inputs_unchanged_after_interrupt',True)
        for name,digest in summary['source_sha256'].items():assert launcher.sha(ROOT/name)==digest,name
        check('original_adoption_controls_unchanged',launcher.sha(parity_original/'summary.json')==parity_original_hash)
        summary.update(status='passed',real_inversions_run=False)
    except BaseException as error:
        summary.update(status='failed',error_type=type(error).__name__,error=str(error));raise
    finally:
        summary['artifact_sha256']={str(p.relative_to(out)):launcher.sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'summary.json'}
        save()
    print(json.dumps({'status':summary['status'],'checks':len(summary['checks'])},indent=2))


if __name__=='__main__':main()
