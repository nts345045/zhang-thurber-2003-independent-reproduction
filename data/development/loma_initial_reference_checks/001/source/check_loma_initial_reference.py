#!/usr/bin/env python3
"""Invented integration checks; not an additional numerical-reference test suite."""
import argparse
import copy
import csv
import gzip
import importlib.util
import itertools
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostics'))
import run_loma_initial_reference as run


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    results=[]
    def check(name,ok):
        if not ok:raise ValueError('Failed check: '+name)
        results.append(dict(name=name,passed=True))
    def rejects(name,fn):
        try:fn()
        except (ValueError,KeyError,FileNotFoundError):check(name,True)
        else:check(name,False)
    def write_csv(path,values):
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]),lineterminator='\n');writer.writeheader();writer.writerows(values)
    fixture=out/'invented_inputs';fixture.mkdir()
    events=[dict(id=str(i),x=str(x),y=str(y),z=str(z),t=str(t),event_resource_id='invented:event:'+str(i),
        origin_resource_id='invented:origin:'+str(i),note='invented, "quoted" metadata',metadata_epoch_end='')
        for i,(x,y,z,t) in enumerate([(.25,.4,.5,.125),(-.5,-.25,2.,-.4)])]
    stations=[dict(id=str(i),x=str(x),y=str(y),z=str(z),t='0',network_code='XX',station_code='S'+str(i),
        location_code='',channel_code='EHZ',channel_seed_id='XX.S'+str(i)+'..EHZ',channel_fdsn_source_id='FDSN:XX_S'+str(i)+'__E_H_Z',
        metadata_epoch_start='2000-01-01T00:00:00',metadata_epoch_end='',source_sha256='invented-not-a-provider-record')
        for i,(x,y,z) in enumerate([(1.,-1.,0.),(-2.,2.,-1.)])]
    grid=[dict(x=str(x),y=str(y),z=str(z),v='6') for x,y,z in itertools.product([-2,2],[-3,3],[-1,0,2])]
    for name,values in [('initial_events.csv',events),('stations.csv',stations),('initial_grid.csv',grid)]:write_csv(fixture/name,values)
    for name in ('run.cfg','ray_samples.csv','preparation_manifest.json','analytic_truth_manifest.json'):
        (fixture/name).write_text('{}\n' if name.endswith('.json') else 'invented fixture only\n')
    manifest=dict(expected_counts=dict(events=2,receivers=2,unique_rays=4),prepared_manifest_sha256=run.sha(fixture/'analytic_truth_manifest.json'))
    run.atomic_json(fixture/'simulation_run_manifest.json',manifest)
    ledger=dict(status='completed',return_code=0,result_status='simulation_complete_awaiting_independent_output_review',
        completed_commands=[dict(stage='simulate',return_code=0)],analytic_truth_manifest_sha256=manifest['prepared_manifest_sha256'],
        output_sha256={name:run.sha(fixture/name) for name in ('initial_events.csv','simulation_run_manifest.json')})
    run.atomic_json(fixture/'simulation_execution.json',ledger)
    review=dict(status='passed',source_count=2,receiver_count=2,arrival_count=4,
        input_sha256={p.name:run.sha(p) for p in fixture.iterdir()},
        simulation_execution_sha256=run.sha(fixture/'simulation_execution.json'),simulation_run_manifest_sha256=run.sha(fixture/'simulation_run_manifest.json'))
    run.atomic_json(fixture/'independent_simulation_review.json',review)
    plan=out/'invented_plan.json';run.atomic_json(plan,dict(input_sha256=review['input_sha256']))
    files,expected=run.checked_inputs(fixture,plan);check('terminal reviewed input gate',expected==(2,2))
    levels,box=run.geometry(events,stations,grid,expected);check('complete z-only grid eligible',levels==[(-1.,6.),(0.,6.),(2.,6.)])
    check('nonzero source corrections preserved',[r['t'] for r in events]==['0.125','-0.4'])
    bad=copy.deepcopy(grid);bad[0]['v']='5';rejects('reject horizontal velocity dependence',lambda:run.geometry(events,stations,bad,expected))
    bad=copy.deepcopy(grid)
    for row in bad:row['v']=str(6-float(row['z']))
    rejects('reject decreasing depth profile',lambda:run.geometry(events,stations,bad,expected))
    rejects('reject incomplete grid',lambda:run.geometry(events,stations,grid[:-1],expected))
    rejects('reject duplicate grid node',lambda:run.geometry(events,stations,grid+[grid[0]],expected))
    bad=copy.deepcopy(events);bad[0]['x']='2.0000000001';rejects('reject outside initial source',lambda:run.geometry(bad,stations,grid,expected))
    bad=copy.deepcopy(events);bad[0]['origin_resource_id']='';rejects('reject missing native origin',lambda:run.geometry(bad,stations,grid,expected))
    bad=copy.deepcopy(stations);bad[0]['channel_seed_id']='XX.WRONG..EHZ';rejects('reject inconsistent receiver identity',lambda:run.geometry(events,bad,grid,expected))
    rejects('reject truncated native cohort',lambda:run.geometry(events[:1],stations,grid,expected))
    bad=copy.deepcopy(events);bad[0]['t']='nan';rejects('reject nonfinite source correction',lambda:run.geometry(bad,stations,grid,expected))
    path=fixture/'initial_events.csv';before=path.read_bytes();path.write_bytes(before+b'\n')
    rejects('reject modified reviewed initial table',lambda:run.checked_inputs(fixture,plan));path.write_bytes(before)
    path=fixture/'independent_simulation_review.json';before=path.read_bytes();bad=copy.deepcopy(review);bad['status']='failed';run.atomic_json(path,bad)
    rejects('reject failed simulation review',lambda:run.checked_inputs(fixture,plan));path.write_bytes(before)
    path=fixture/'simulation_execution.json';before=path.read_bytes();bad=copy.deepcopy(ledger);bad['status']='running';run.atomic_json(path,bad)
    rejects('reject live simulation',lambda:run.checked_inputs(fixture,plan));path.write_bytes(before)
    numerical=run.load_reference(ROOT/'diagnostics/first_arrival_1d_reference.py')
    pairs=list(run.coordinate_pairs(events,stations));refs=[run.reference_for(p,levels,numerical) for p in pairs]
    altered=copy.deepcopy(events)
    for row in altered:row['t']='1234.5'
    other=[run.reference_for(p,levels,numerical) for p in run.coordinate_pairs(altered,stations)]
    check('source time excluded from complete references',refs==other)
    s,r=pairs[0];length=math.sqrt(sum((a-b)**2 for a,b in zip(s,r)));first=refs[0]['first_arrival']
    check('saved perturbed geometry used for travel time',abs(first['time_s']-length/6)<1e-15)
    check('original xyz gradient axes retained',max(abs(first['source_derivative_s_per_km'][d]-(s[d]-r[d])/(6*length)) for d in range(3))<1e-15)
    boundary=run.boundary_fields(events[1],stations[1],box)
    check('exact endpoint boundary flags',boundary['source_on_z_upper_face']==boundary['receiver_on_x_lower_face']==boundary['receiver_on_z_lower_face']==1)
    def fails(*unused):raise RuntimeError('invented root exhaustion')
    failed=run.reference_for(pairs[0],levels,fails)
    check('numerical root exhaustion retained unresolved',not failed['complete'] and not failed['reference_valid'] and failed['first_arrival'] is None and failed['unresolved'][0]['exception_type']=='RuntimeError')
    evidence=out/'unresolved';evidence.mkdir();retained=[failed]+refs[1:]
    run.write_references(evidence,events,stations,levels,box,iter(retained),lambda unused:None)
    check('unresolved native support readback',run.verify_outputs(evidence,events,stations,box)==4)
    with gzip.open(str(evidence/'references.csv.gz'),'rt') as f:firstrow=next(csv.DictReader(f))
    check('unresolved time and gradient blank',firstrow['time_s']==firstrow['source_dx_s_per_km']=='' and firstrow['source_event_resource_id']==events[0]['event_resource_id'])
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',TMPDIR=str(ROOT/'tmp'))
    command=[sys.executable,'diagnostics/run_loma_initial_reference.py','--data',str(fixture.relative_to(ROOT)),
        '--plan',str(plan.relative_to(ROOT))]
    for workers in (1,2):
        target=out/('workers'+str(workers));args=command+['--output',str(target.relative_to(ROOT)),'--workers',str(workers)]
        with (out/('workers'+str(workers)+'.log')).open('w') as log:
            proc=subprocess.run(args,cwd=str(ROOT),env=env,stdout=log,stderr=subprocess.STDOUT,universal_newlines=True)
        check('full invented wrapper workers '+str(workers),proc.returncode==0)
        summary=json.loads((target/'summary.json').read_text());terminal=json.loads((target/'execution.json').read_text())
        check('terminal ledger and all native rows workers '+str(workers),terminal['status']=='completed' and terminal['summary_sha256']==run.sha(target/'summary.json') and summary['verified_pairs']==4)
    for name in ('references.csv.gz','certificates.jsonl.gz'):
        check('deterministic ordered workers '+name,run.sha(out/'workers1'/name)==run.sha(out/'workers2'/name))
    before=run.sha(out/'workers1'/'execution.json')
    proc=subprocess.run(command+['--output',str((out/'workers1').relative_to(ROOT)),'--workers','1'],cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    check('exclusive existing-output guard',proc.returncode!=0 and run.sha(out/'workers1'/'execution.json')==before)
    source=out/'source';source.mkdir()
    paths=[Path(__file__).resolve(),ROOT/'diagnostics/run_loma_initial_reference.py',ROOT/'diagnostics/run_loma_layered_full.py',ROOT/'diagnostics/first_arrival_1d_reference.py']
    for p in paths:shutil.copyfile(str(p),str(source/p.name))
    result=dict(status='passed',scope='Invented wrapper eligibility, metadata, ordering and readiness controls only; unchanged numerical helper',
        checks=len(results),failed=0,results=results,command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_initial_reference.py --output '+str(out.relative_to(ROOT)),
        source_sha256={str(p.relative_to(ROOT)):run.sha(p) for p in paths})
    run.atomic_json(out/'summary.json',result);print(json.dumps(dict(status='passed',checks=len(results),failed=0)))

if __name__=='__main__':main()
