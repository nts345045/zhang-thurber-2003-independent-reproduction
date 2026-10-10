#!/usr/bin/env python3
"""Invented data/IO controls for the full Loma reference batch, not field results."""
import argparse
import copy
import csv
import gzip
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostics'))
import run_loma_layered_full as batch
import first_arrival_layered_reference as layered


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    checks=[]
    def check(name,ok):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok:raise AssertionError(name)
    def rejects(name,fn):
        try:fn()
        except ValueError:check(name,True)
        else:check(name,False)
    events=[dict(id=str(i),x=str(i),y='0',z='.5',t='0',event_resource_id='fixture:event:'+str(i),
        origin_resource_id='fixture:origin:'+str(i),note='Invented "quoted, source"\nline') for i in range(2)]
    stations=[dict(id=str(k),x=str(k-1),y='1',z='0',t='0',network_code='ZZ',station_code='FIX'+str(k),
        location_code='',channel_code='EHZ',channel_seed_id='ZZ.FIX{}..EHZ'.format(k),
        channel_fdsn_source_id='FDSN:ZZ_FIX{}__E_H_Z'.format(k),metadata_epoch_start='2000-01-01T00:00:00',
        metadata_epoch_end='',note='Invented receiver — "blank location"') for k in range(3)]
    grid=[dict(x=str(x),y=str(y),z=str(z),v='5') for x,y,z in itertools.product((-2,2),(-2,2),(-1,2))]
    levels,box=batch.geometry(events,stations,grid,(2,3))
    complete=out/'complete';complete.mkdir()
    report=batch.stream_references(complete,events,stations,levels,box,layered.enumerate_arrivals,lambda c:None)
    check('All Cartesian pairs and full native strings survive compression',batch.verify_outputs(complete,events,stations)==6)
    check('All homogeneous fixture references complete',report['counts']['reference_valid']==6)
    with gzip.open(str(complete/'references.csv.gz'),'rt',newline='') as f:rows=list(csv.DictReader(f))
    check('Reference time has the declared coordinate permutation',abs(float(rows[0]['time_s'])-1.5/5)<1e-15)
    check('Source gradient maps back to original x/y/z',all(abs(float(rows[0]['source_d'+axis+'_s_per_km'])-value/7.5)<1e-15
        for axis,value in zip('xyz',(1.,-1.,.5))))
    check('Quoted/newline metadata and valid blank fields preserved',rows[0]['source_note']==events[0]['note'] and
        rows[0]['receiver_location_code']=='' and rows[0]['receiver_metadata_epoch_end']=='')
    repeat=out/'repeat';repeat.mkdir()
    batch.stream_references(repeat,events,stations,levels,box,layered.enumerate_arrivals,lambda c:None)
    check('Compressed numeric and certificate files deterministic',all(batch.sha(complete/n)==batch.sha(repeat/n)
        for n in ('references.csv.gz','certificates.jsonl.gz')))
    failed=out/'unresolved';failed.mkdir()
    calls=[0]
    def controlled(*args,**kwargs):
        calls[0]+=1
        if calls[0]==2:raise ArithmeticError('Invented arithmetic failure; preserve pair')
        return layered.enumerate_arrivals(*args,**kwargs)
    result=batch.stream_references(failed,events,stations,levels,box,controlled,lambda c:None)
    check('Arithmetic failure preserves complete support',batch.verify_outputs(failed,events,stations)==6 and result['unresolved_pair_indices']==[1])
    with gzip.open(str(failed/'references.csv.gz'),'rt',newline='') as f:failed_rows=list(csv.DictReader(f))
    check('Unresolved reference has blank time and false valid flag',failed_rows[1]['time_s']=='' and failed_rows[1]['reference_valid']=='0')
    duplicate=copy.deepcopy(events);duplicate[1]['id']='0'
    rejects('Repeated native index rejected',lambda:batch.geometry(duplicate,stations,grid,(2,3)))
    outside=copy.deepcopy(events);outside[0]['x']='3'
    rejects('Endpoint beyond finite box rejected',lambda:batch.geometry(outside,stations,grid,(2,3)))
    rejects('Missing grid corner rejected',lambda:batch.geometry(events,stations,grid[:-1],(2,3)))
    varying=copy.deepcopy(grid);varying[0]['v']='6'
    rejects('Transverse velocity variation rejected',lambda:batch.geometry(events,stations,varying,(2,3)))
    # Corrupt only a copy, proving complete count alone cannot certify pair support.
    corrupt=out/'repeated_output';corrupt.mkdir()
    changed=copy.deepcopy(rows);changed[1]['station']='0'
    with batch.compressed_text(corrupt/'references.csv.gz') as f:
        writer=csv.DictWriter(f,fieldnames=list(changed[0]),lineterminator='\n');writer.writeheader();writer.writerows(changed)
    shutil.copyfile(str(complete/'certificates.jsonl.gz'),str(corrupt/'certificates.jsonl.gz'))
    rejects('Repeated output pair rejected during readback',lambda:batch.verify_outputs(corrupt,events,stations))
    wrong_gradient=out/'wrong_gradient';wrong_gradient.mkdir();changed=copy.deepcopy(rows)
    changed[0]['source_dx_s_per_km']=changed[0]['source_dy_s_per_km']
    with batch.compressed_text(wrong_gradient/'references.csv.gz') as f:
        writer=csv.DictWriter(f,fieldnames=list(changed[0]),lineterminator='\n');writer.writeheader();writer.writerows(changed)
    shutil.copyfile(str(complete/'certificates.jsonl.gz'),str(wrong_gradient/'certificates.jsonl.gz'))
    rejects('Wrong gradient permutation rejected during readback',lambda:batch.verify_outputs(wrong_gradient,events,stations))
    # Invoke the actual controller with an explicitly invented, undersized cohort.
    sandbox=out/'invented_repository';(sandbox/'diagnostics').mkdir(parents=True)
    data=sandbox/'data/loma_lom_001';data.mkdir(parents=True)
    terminal=sandbox/'data/development/loma_geometry_preflight/001';terminal.mkdir(parents=True)
    for name in ('run_loma_layered_full.py','first_arrival_layered_reference.py','first_arrival_1d_reference.py'):
        shutil.copyfile(str(ROOT/'diagnostics'/name),str(sandbox/'diagnostics'/name))
    for name,records in (('truth_events.csv',events),('stations.csv',stations),('truth_grid.csv',grid)):
        with (data/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
    (data/'authoritative_geometry').write_text('Invented fixture only; not authoritative observational data\n')
    (terminal/'summary.json').write_text(json.dumps(dict(status='completed',commands=[dict(name='geometrycheck',exit_code=0)],
        input_sha256={p.name:batch.sha(p) for p in data.iterdir()})))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
    command=[sys.executable,'diagnostics/run_loma_layered_full.py','--output','attempt']
    first=subprocess.run(command,cwd=str(sandbox),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    ledger=sandbox/'attempt/execution.json';before=ledger.read_bytes();execution=json.loads(before.decode())
    check('Controller records cohort failure before enumeration',first.returncode!=0 and execution['status']=='failed' and
        execution['error']=='Full prepared geometry counts changed' and not (sandbox/'attempt/references.csv.gz').exists())
    second=subprocess.run(command,cwd=str(sandbox),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    check('Exclusive output refuses reuse without altering failure evidence',second.returncode!=0 and ledger.read_bytes()==before)
    source=out/'source';source.mkdir()
    for name in ('check_loma_layered_batch.py','run_loma_layered_full.py','first_arrival_layered_reference.py','first_arrival_1d_reference.py'):
        shutil.copyfile(str(ROOT/'diagnostics'/name),str(source/name))
    result=dict(scope='Invented IO/domain/failure controls only; no field data or production ray execution',checks=checks,
        passed=sum(c['passed'] for c in checks),total=len(checks),
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_layered_batch.py --output '+str(out.relative_to(ROOT)),
        controller_failure_return_code=first.returncode,exclusive_repeat_return_code=second.returncode,
        source_sha256={p.name:batch.sha(p) for p in source.iterdir()})
    batch.atomic_json(out/'results.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
