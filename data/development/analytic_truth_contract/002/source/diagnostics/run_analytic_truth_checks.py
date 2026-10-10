#!/usr/bin/env python3
"""Freeze and test the explicit analytic-truth contract with invented geometry."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',required=True)
    args=parser.parse_args()
    if not args.variant.replace('_','').replace('-','').isalnum():parser.error('Plain variant required')
    os.chdir(str(ROOT))
    out=Path('data/development/analytic_truth_contract')/args.variant;out.mkdir(parents=True,exist_ok=False)
    build=Path('tmp/analytic_truth_contract')/args.variant;build.mkdir(parents=True,exist_ok=False)
    baseline=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
    summary=dict(status='preparing',scope='Invented homogeneous truth, depth-varying initial grid and exact native/noise contract checks; no actual Loma simulation',baseline_commit=baseline,commands=[])
    def save():(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def run(name,command):
        start=time.time();record=dict(stage=name,command=list(map(str,command)),status='running');summary['commands'].append(record);save()
        with (out/(name+'_stdout.log')).open('w') as stdout,(out/(name+'_stderr.log')).open('w') as stderr:
            code=subprocess.call(record['command'],stdout=stdout,stderr=stderr,env=dict(os.environ,OMP_NUM_THREADS='2'))
        record.update(return_code=code,seconds=time.time()-start,status='complete');save()
        if code:raise RuntimeError(name+' failed: '+str(code))
    try:
        for path in list(Path('src').glob('*'))+[Path('diagnostics/check_analytic_truth.cpp'),Path(__file__).resolve().relative_to(ROOT)]:
            if path.is_file():
                target=out/'source'/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(path),str(target))
        names=subprocess.check_output(['git','ls-tree','-r','--name-only',baseline,'src']).decode().splitlines()
        for name in names:
            target=out/'baseline_source'/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(subprocess.check_output(['git','show',baseline+':'+name]))
        summary['source_sha256']={str(p.relative_to(out)):sha(p) for folder in ['source','baseline_source'] for p in (out/folder).rglob('*') if p.is_file()};save()
        flags=['g++','-std=c++17','-O2','-fopenmp','-Wall','-Wextra','-Wpedantic']
        run('compile_checks',flags+[out/'source/diagnostics/check_analytic_truth.cpp','-lstdc++fs','-o',build/'check'])
        run('contract_checks',[build/'check',out/'fixtures'])
        run('compile_baseline',flags+[out/'baseline_source/src/main.cpp','-lstdc++fs','-o',build/'baseline'])
        run('baseline_simulation',[build/'baseline','simulate',out/'fixtures/run.cfg',out/'fixtures/baseline'])
        names=['arrivals.csv','observations.csv','initial_events.csv','truth_events.csv','simulation_ray_status.csv','authoritative_geometry']
        for name in names:
            if (out/'fixtures/ordinary'/name).read_bytes()!=(out/'fixtures/baseline'/name).read_bytes():raise ValueError('Legacy numerical/identity output changed: '+name)
        with (out/'fixtures/checks.csv').open() as stream:checks=list(csv.DictReader(stream))
        if any(r['passed']!='1' for r in checks):raise ValueError('Failed contract check')
        summary.update(status='complete',checks_passed=len(checks),legacy_byte_identical_files=names)
        summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='summary.json'}
    except BaseException as error:
        summary.update(status='failed',error_type=type(error).__name__,error=str(error));save();raise
    save();print(json.dumps({k:summary[k] for k in ['status','checks_passed','legacy_byte_identical_files']},indent=2))

if __name__=='__main__':main()
