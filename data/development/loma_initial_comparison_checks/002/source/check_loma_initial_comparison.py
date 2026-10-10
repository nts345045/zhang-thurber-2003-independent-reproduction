#!/usr/bin/env python3
"""Invented saved-table controls; no new solver or reference calculation."""
import argparse
import copy
import csv
import gzip
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostics'))
import compare_loma_initial_rays as cmp


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    checks=[]
    def check(name,ok):
        if not ok:raise ValueError('Failed control: '+name)
        checks.append(dict(name=name,passed=True))
    def rejects(name,fn):
        try:fn()
        except (ValueError,KeyError,FileNotFoundError):check(name,True)
        else:check(name,False)
    def write_csv(path,values):
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]),lineterminator='\n');writer.writeheader();writer.writerows(values)
    reference=out/'invented_reference'
    shutil.copytree(str(ROOT/'data/development/loma_initial_reference_checks/002/workers1'),str(reference))
    for name in ('review.json','independent_review.json'):
        cmp.atomic_json(reference/name,dict(status='passed',scope='Invented review-link fixture only; no field-data claim',
            summary_sha256=cmp.sha(reference/'summary.json'),execution_sha256=cmp.sha(reference/'execution.json')))
    refsummary,_=cmp.checked_reference(reference)
    with gzip.open(str(reference/'references.csv.gz'),'rt') as f:refs=list(csv.DictReader(f))
    with gzip.open(str(reference/'certificates.jsonl.gz'),'rt') as f:certs=[json.loads(line) for line in f]
    _,events=cmp.table(reference/'inputs/initial_events.csv');_,stations=cmp.table(reference/'inputs/stations.csv')
    statuses=[]
    for r in refs:
        i,k=int(r['event']),int(r['station']);row=dict(event=str(i),station=str(k))
        for prefix,native in [('source_',events[i]),('receiver_',stations[k])]:
            for a in 'xyz':row[prefix+a]=format(float(native[a]),'.12g')
        row.update(ray_time=r['time_s'],source_t=events[i]['t'],source_dx=r['source_dx_s_per_km'],
            source_dy=r['source_dy_s_per_km'],source_dz=r['source_dz_s_per_km'],ray_projected_gradient='1e-8',ray_raw_gradient='2e-8',
            ray_path_points='2',ray_converged='1',ray_finite='1',ray_path_in_domain='1',ray_exact_source_endpoint='1',
            ray_exact_receiver_endpoint='1',ray_initialization_attempted='1',ray_initialization_succeeded='1',ray_iterations='0')
        for prefix,native in [('source_',events[i]),('receiver_',stations[k])]:
            row.update({prefix+key:value for key,value in native.items() if key not in ('id','x','y','z','t')})
        statuses.append(row)
    def preflight(path,values):
        path.mkdir();(path/'simulation_provenance').mkdir()
        for name in ('initial_events.csv','stations.csv','initial_grid.csv'):
            shutil.copyfile(str(reference/'inputs'/name),str(path/name))
        for name in ('simulation_execution.json','simulation_run_manifest.json','independent_simulation_review.json','analytic_truth_manifest.json'):
            shutil.copyfile(str(reference/'inputs'/name),str(path/'simulation_provenance'/name))
        (path/'run.cfg').write_text('iterations 1\nmatrix_preflight_only 1\nstage_length 6\nray_spacing .03125\nfmm_spacing .125\n')
        (path/'invented_binary').write_bytes(b'Invented binary-hash fixture, never executed\n')
        (path/'preflight_source.tar.gz').write_bytes(b'Invented source-hash fixture, no executable code\n')
        write_csv(path/'dd_preflight_ray_status.csv',values)
        matrix=dict(iteration='0',observation_rows='8',columns='20',active_data_rows='8',smoothing_rows='0',damped_rows='28')
        write_csv(path/'dd_matrix_preflight.csv',[matrix])
        full=dict(full_rays=4,local_converged=sum(r['ray_converged']=='1' for r in values),matrix_stage=0,matrix_census=matrix,
            maximum_projected_gradient=max(float(r['ray_projected_gradient']) for r in values),maximum_raw_gradient=max(float(r['ray_raw_gradient']) for r in values))
        cmp.atomic_json(path/'full_initial_checks.json',full)
        names=['initial_events.csv','stations.csv','initial_grid.csv','run.cfg']+['simulation_provenance/'+n for n in ('simulation_execution.json','simulation_run_manifest.json','independent_simulation_review.json','analytic_truth_manifest.json')]
        manifest=dict(binary=cmp.relative(path/'invented_binary'),binary_sha256=cmp.sha(path/'invented_binary'),threads=4,
            matrix_preflight_only=True,matrix_mode='dd',matrix_iteration=0,matrix_stage=0,
            input_sha256={name:cmp.sha(path/name) for name in names},source_archive_sha256=cmp.sha(path/'preflight_source.tar.gz'),
            expected_counts=dict(events=2,receivers=2,unique_rays=4,total_rows=8),
            simulation_review_sha256=cmp.sha(reference/'inputs/independent_simulation_review.json'))
        cmp.atomic_json(path/'preflight_run_manifest.json',manifest)
        command=[str(path/'invented_binary'),'invert',str(path/'run.cfg'),str(path),'dd']
        ledger=dict(status='running',current_stage='initial_geometrycheck',threads=4,
            completed_commands=[dict(stage='initial_matrix_preflight',return_code=0,command=command)])
        cmp.atomic_json(path/'preflight_execution.json',ledger)
        return manifest,full,ledger
    data=out/'invented_preflight';manifest,full,ledger=preflight(data,statuses)
    cmp.checked_preflight(data,reference,refsummary);check('completed matrix with live independent geometry stage accepted',True)
    check('assessment config intentionally differs',cmp.sha(data/'run.cfg')!=cmp.sha(reference/'inputs/run.cfg'))
    cmp.native_join(statuses[0],refs[0],events[0],stations[0]);check('native quoted and empty metadata accepted',True)
    row,reasons=cmp.compare_row(statuses[0],refs[0],certs[0]['reference'],refsummary['original_box_km'])
    check('nonzero source_t excluded from pure propagation time',row['scientific_pass']==1 and row['time_error_s']==0 and row['source_t']!='0')
    check('original xyz source derivatives and norm zero',row['source_error_euclidean_norm_s_per_km']==0)
    bad=copy.deepcopy(statuses[0]);bad['ray_time']=str(float(bad['ray_time'])+float(bad['source_t']))
    row,reasons=cmp.compare_row(bad,refs[0],certs[0]['reference'],refsummary['original_box_km'])
    check('adding source_t to propagation time fails unchanged limit',row['time_limit_pass']==0)
    bad=copy.deepcopy(statuses[0])
    for a in 'xyz':bad['source_d'+a]=str(float(bad['source_d'+a])+2.5e-6)
    row,reasons=cmp.compare_row(bad,refs[0],certs[0]['reference'],refsummary['original_box_km'])
    check('Euclidean gate not maximum component gate',max(abs(row['source_d'+a+'_error_s_per_km']) for a in 'xyz')<3e-6 and row['source_vector_limit_pass']==0)
    bad=copy.deepcopy(statuses[0]);bad['source_dx'],bad['source_dz']=bad['source_dz'],bad['source_dx']
    row,_=cmp.compare_row(bad,refs[0],certs[0]['reference'],refsummary['original_box_km']);check('wrong axis permutation detected numerically',row['source_vector_limit_pass']==0)
    for key in ('ray_converged','ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint','ray_initialization_attempted','ray_initialization_succeeded'):
        bad=copy.deepcopy(statuses[0]);bad[key]='0';row,reasons=cmp.compare_row(bad,refs[0],certs[0]['reference'],refsummary['original_box_km'])
        check('preserve failed '+key,row[key]=='0' and row['scientific_pass']==0 and key+'_false' in reasons and row['time_limit_pass']==1)
    bad=copy.deepcopy(statuses[0]);bad['source_dx']='nan';row,reasons=cmp.compare_row(bad,refs[0],certs[0]['reference'],refsummary['original_box_km'])
    check('nonfinite modeled values retained but cannot pass',row['modeled_values_finite']==row['scientific_pass']==0 and row['source_dx']=='nan')
    for key in ('source_event_resource_id','receiver_channel_seed_id','receiver_metadata_epoch_end','source_t'):
        bad=copy.deepcopy(statuses[0]);bad[key]='1' if key=='source_t' else 'wrong'
        rejects('reject changed '+key,lambda bad=bad:cmp.native_join(bad,refs[0],events[0],stations[0]))
    rr=copy.deepcopy(refs[0]);ref=copy.deepcopy(certs[0]['reference']);ref['near_ties']=[0,1];rr['near_tie_count']='2'
    row,reasons=cmp.compare_row(statuses[0],rr,ref,refsummary['original_box_km']);check('near tie preserved and ineligible',row['reference_eligible']==row['scientific_pass']==0)
    rr=copy.deepcopy(refs[0]);ref=copy.deepcopy(certs[0]['reference']);ref['reference_valid']=False;ref['first_arrival']=None
    rr.update(reference_valid='0',time_s='',branch='')
    for a in 'xyz':rr['source_d'+a+'_s_per_km']=''
    row,reasons=cmp.compare_row(statuses[0],rr,ref,refsummary['original_box_km']);check('invalid reference retained without arithmetic comparison',row['numerically_compared']==row['scientific_pass']==0)
    for key,value in [('reference_valid','0'),('time_s',str(float(refs[0]['time_s'])+.01)),
                      ('source_dx_s_per_km',str(float(refs[0]['source_dx_s_per_km'])+.01)),
                      ('source_on_z_upper_face','1')]:
        bad=copy.deepcopy(refs[0]);bad[key]=value
        rejects('reject corrupted reference '+key,lambda bad=bad:cmp.compare_row(statuses[0],bad,certs[0]['reference'],refsummary['original_box_km']))
    def mutate_json(name,change,label):
        path=data/name;before=path.read_bytes();value=json.loads(before.decode('utf-8'));change(value);cmp.atomic_json(path,value)
        rejects(label,lambda:cmp.checked_preflight(data,reference,refsummary));path.write_bytes(before)
    mutate_json('preflight_execution.json',lambda d:d.update(completed_commands=[]),'reject unfinished matrix stage')
    mutate_json('preflight_execution.json',lambda d:d['completed_commands'][0].update(return_code=1),'reject failed matrix stage')
    mutate_json('preflight_execution.json',lambda d:d['completed_commands'][0]['command'].__setitem__(3,str(out/'other')),'reject foreign completed command')
    mutate_json('preflight_execution.json',lambda d:d.update(threads=3),'reject thread provenance mismatch')
    mutate_json('preflight_run_manifest.json',lambda d:d.update(matrix_stage=1),'reject noninitial matrix stage')
    for name in ('initial_events.csv','stations.csv','initial_grid.csv','simulation_provenance/independent_simulation_review.json'):
        path=data/name;before=path.read_bytes();path.write_bytes(before+b'\n')
        rejects('reject changed pinned '+name,lambda:cmp.checked_preflight(data,reference,refsummary));path.write_bytes(before)
    rejects('reject output nested in data',lambda:cmp.disjoint(data/'new',data,reference))
    rejects('reject ancestor output',lambda:cmp.disjoint(out,data,reference))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
    command=[sys.executable,'diagnostics/compare_loma_initial_rays.py','--reference',cmp.relative(reference)]
    def execute(source,target):
        with (out/(target.name+'.log')).open('w') as log:
            p=subprocess.run(command+['--data',cmp.relative(source),'--output',cmp.relative(target)],cwd=str(ROOT),env=env,stdout=log,stderr=subprocess.STDOUT,universal_newlines=True)
        return p.returncode
    target=out/'comparison_pass';check('full invented comparison executes without numerical rerun',execute(data,target)==0)
    summary=json.loads((target/'summary.json').read_text());check('all four identified rows pass',summary['rows']==4 and summary['scientific_pass'] and summary['overall_preflight_assessed'] is False)
    with gzip.open(str(target/'comparison.csv.gz'),'rt') as f:saved=list(csv.DictReader(f))
    check('every original status and native field preserved',all(all(r[key]==value for key,value in native.items()) for r,native in zip(saved,statuses)))
    captured=json.loads((target/'inputs/preflight/preflight_execution_at_capture.json').read_text());check('live controller ledger snapshot retained',captured['current_stage']=='initial_geometrycheck')
    failed_status=copy.deepcopy(statuses);failed_status[0]['ray_converged']='0'
    for a in 'xyz':failed_status[1]['source_d'+a]=str(float(failed_status[1]['source_d'+a])+2.5e-6)
    failed_data=out/'invented_failures';preflight(failed_data,failed_status);failed_target=out/'comparison_failures'
    check('scientific failures do not abort completed comparison',execute(failed_data,failed_target)==0)
    summary=json.loads((failed_target/'summary.json').read_text());check('completion separate from scientific failure',summary['status']=='comparison_complete' and not summary['scientific_pass'] and len(summary['failures'])==2)
    check('all failures retain event origin channel epoch identifiers',all(all(key in r for key in ('comparison_row','event_resource_id','origin_resource_id','channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end')) for r in summary['failures']))
    before=cmp.sha(target/'execution.json');check('existing output cannot be overwritten',execute(data,target)!=0 and cmp.sha(target/'execution.json')==before)
    source=out/'source';source.mkdir();paths=[Path(__file__).resolve(),ROOT/'diagnostics/compare_loma_initial_rays.py',ROOT/'diagnostics/run_loma_layered_full.py']
    for p in paths:shutil.copyfile(str(p),str(source/p.name))
    result=dict(status='passed',scope='Invented saved tables and artificial stage/review ledgers only; no actual Loma comparator or ray/reference computation',
        checks=len(checks),failed=0,results=checks,source_sha256={cmp.relative(p):cmp.sha(p) for p in paths},
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_initial_comparison.py --output '+cmp.relative(out))
    cmp.atomic_json(out/'summary.json',result);print(json.dumps(dict(status='passed',checks=len(checks),failed=0)))

if __name__=='__main__':main()
