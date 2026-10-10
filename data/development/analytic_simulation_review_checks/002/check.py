#!/usr/bin/env python3
"""Invented-output controls for the streaming audit; no simulator or rays run."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists())
SOURCE=HERE/'source/review_loma_analytic_simulation.py'
FIXTURE=ROOT/'data/development/analytic_simulation_launcher_001/invented_simulation'
spec=importlib.util.spec_from_file_location('review',str(SOURCE))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
checks=[]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def mutate_csv(path,column,value,row=0):
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream);header=reader.fieldnames;rows=list(reader)
    rows[row][column]=value
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=header);writer.writeheader();writer.writerows(rows)

def check(name,mutate=None,terminal=False):
    with tempfile.TemporaryDirectory(prefix='analytic_audit_',dir=str(ROOT/'tmp')) as temporary:
        case=Path(temporary)/'case';shutil.copytree(str(FIXTURE),str(case))
        if mutate:mutate(case)
        try:
            if terminal: module.terminal_inputs(case)
            else: module.audit_payload(case)
        except (ValueError,KeyError) as error:
            if mutate is None:raise
            checks.append(dict(name=name,passed=True,rejected=True,message=str(error)))
        else:
            if mutate is not None:raise ValueError('Mutation accepted: '+name)
            checks.append(dict(name=name,passed=True,rejected=False))

def ledger(path,**values):
    p=path/'simulation_execution.json';x=json.loads(p.read_text());x.update(values);p.write_text(json.dumps(x))

check('invented_terminal_manifest',terminal=True)
check('invented_all_native_noise_and_ordered_rows')
check('live_ledger_rejected',lambda p:ledger(p,status='running'),True)
check('failed_exit_rejected',lambda p:ledger(p,return_code=1),True)
check('changed_output_hash_rejected',lambda p:mutate_csv(p/'arrivals.csv','true_time','1'),True)
check('altered_absolute_value',lambda p:mutate_csv(p/'observations.csv','value','123'))
check('wrong_DD_value',lambda p:mutate_csv(p/'observations.csv','value','123',4))
check('wrong_precise_value',lambda p:mutate_csv(p/'observations.csv','value','123',5))
check('wrong_observation_type',lambda p:mutate_csv(p/'observations.csv','type','2',4))
check('wrong_native_j_ID',lambda p:mutate_csv(p/'observations.csv','event_j_resource_id','wrong',4))
check('empty_location_changed',lambda p:mutate_csv(p/'observations.csv','location_code','99'))
check('wrong_epoch',lambda p:mutate_csv(p/'observations.csv','metadata_epoch_start','changed'))
check('fabricated_ray_flag',lambda p:mutate_csv(p/'arrivals.csv','ray_converged','1'))
check('wrong_quantization',lambda p:mutate_csv(p/'arrivals.csv','rounded_time','100'))
check('changed_full_precision_status_coordinate',lambda p:mutate_csv(p/'simulation_truth_status.csv','source_x','0.00000000001'))
check('bias_outside_uniform_support',lambda p:mutate_csv(p/'arrivals.csv','station_bias','1'))
check('changed_saved_source_ID',lambda p:mutate_csv(p/'truth_events.csv','event_resource_id','changed'))
check('missing_observation',lambda p:(p/'observations.csv').write_text('\n'.join((p/'observations.csv').read_text().splitlines()[:-1])+'\n'))
for value,expected in [(0.5,1.),(-.5,-1.),(1.5,2.),(-1.5,-2.),(.49999999999999994,0.),(-.49999999999999994,0.),(1.4999999999999998,1.)]:
    if module.round_away(value)!=expected:raise ValueError('Wrong ties-away rounding')
    checks.append(dict(name='round_away_'+repr(value),passed=True,expected=expected))
result=dict(scope='Invented terminal simulation output audit controls only; no real output audit or simulator execution',
    passed=True,check_count=len(checks),checks=checks,source_sha256=sha(SOURCE),check_source_sha256=sha(Path(__file__)),
    fixture_execution_sha256=sha(FIXTURE/'simulation_execution.json'),fixture_run_manifest_sha256=sha(FIXTURE/'simulation_run_manifest.json'),
    command='PYTHONDONTWRITEBYTECODE=1 python3 '+str(Path(__file__).resolve().relative_to(ROOT)))
(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('Passed {} streaming-audit controls'.format(len(checks)))
