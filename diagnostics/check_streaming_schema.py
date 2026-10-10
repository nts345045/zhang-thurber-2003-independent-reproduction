#!/usr/bin/env python3
"""Reject reordered/missing/duplicate synthetic fields before any ray or solve."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--fixture',required=True)
p.add_argument('--executable',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
fixture,exe,out=Path(a.fixture),Path(a.executable),Path(a.output)
out.mkdir(parents=True,exist_ok=False)
with (fixture/'observations.csv').open(newline='') as stream:
    source=list(csv.reader(stream))
checks=[]
for case in ['reordered','missing','duplicate']:
    dest=out/case;dest.mkdir()
    for name in ['initial_events.csv','stations.csv','fixture.cfg']:
        shutil.copyfile(str(fixture/name),str(dest/name))
    rows=[row[:] for row in source]
    for row in rows:
        if case=='reordered': row[5],row[6]=row[6],row[5]
        elif case=='missing': del row[5]
        else: row.append(row[5])
    with (dest/'observations.csv').open('w',newline='') as stream:
        csv.writer(stream,lineterminator='\n').writerows(rows)
    command=[str(exe),'--solver','invert',str(dest/'fixture.cfg'),str(dest),'dd']
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    (dest/'stdout.log').write_text(result.stdout);(dest/'stderr.log').write_text(result.stderr)
    expected={'reordered':'Unexpected shared synthetic metadata column','missing':'Unexpected shared synthetic metadata schema','duplicate':'Duplicate CSV column'}[case]
    assert result.returncode==1 and expected in result.stderr
    assert not (dest/'dd_history.csv').exists() and not (dest/'dd_matrix_preflight.csv').exists()
    checks.append({'case':case,'argv':command,'exit_code':result.returncode,'error':result.stderr.strip(),'before_rays_or_solve':True})
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
summary={'status':'passed','scope':'Malformed invented metadata fixtures only; no rays or inversions run','checks':checks,
         'driver_sha256':sha(Path(__file__)),'executable_sha256':sha(exe),
         'input_sha256':{name:sha(fixture/name) for name in ['initial_events.csv','stations.csv','observations.csv','fixture.cfg']},
         'output_sha256':{str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file()}}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
