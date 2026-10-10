#!/usr/bin/env python3
"""Freeze and test simulation gates on invented geometry; never trace real data."""
import argparse,csv,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.chdir(str(ROOT))
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',required=True);p.add_argument('--baseline',default='e097c11');a=p.parse_args()
if not a.variant.replace('_','').replace('-','').isalnum():raise ValueError('Invalid variant')
out=Path('data/development/loma_preparation')/a.variant;out.mkdir(parents=True,exist_ok=False)
cache=Path('tmp/loma_preparation_checks')/a.variant;cache.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
summary={'status':'running','scope':'Invented component geometry only; no real rays or inversions','commands':[],'source_sha256':{}}
def save():(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
def run(name,cmd):
    start=time.time()
    with (out/(name+'_stdout.log')).open('w') as stdout,(out/(name+'_stderr.log')).open('w') as stderr:
        code=subprocess.call(list(map(str,cmd)),env=dict(os.environ,TMPDIR=str(ROOT/'tmp'),OMP_NUM_THREADS='4'),stdout=stdout,stderr=stderr)
    summary['commands'].append({'name':name,'argv':list(map(str,cmd)),'exit_code':code,'seconds':time.time()-start});save()
    if code:raise RuntimeError(name+' failed')
try:
    current=sorted(str(p) for p in Path('src').glob('*') if p.suffix in ('.cpp','.hpp'))+['diagnostics/check_simulation_gate.cpp','diagnostics/run_simulation_gate_checks.py']
    for name in current:
        target=out/'current_source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,str(target));summary['source_sha256'][name]=sha(target)
    old=subprocess.check_output(['git','ls-tree','-r','--name-only',a.baseline,'src']).decode().splitlines()
    summary['baseline_commit']=subprocess.check_output(['git','rev-parse',a.baseline]).decode().strip()
    for name in old:
        target=out/'legacy_source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(subprocess.check_output(['git','show',a.baseline+':'+name]))
    flags=['g++','-std=c++17','-O2','-fopenmp']
    run('compile_current',flags+[out/'current_source/diagnostics/check_simulation_gate.cpp','-lstdc++fs','-o',cache/'current'])
    run('current',[cache/'current',out/'current_fixture'])
    run('compile_legacy',flags+[out/'legacy_source/src/main.cpp','-lstdc++fs','-o',cache/'legacy'])
    legacy=out/'legacy_fixture';legacy.mkdir()
    for name in ['truth_events.csv','stations.csv','truth_grid.csv','initial_grid.csv','fixture.cfg']:
        shutil.copyfile(str(out/'current_fixture'/name),str(legacy/name))
    run('legacy_simulate',[cache/'legacy','simulate',legacy/'fixture.cfg',legacy])
    for name in ['observations.csv','truth_events.csv','initial_events.csv']:
        assert (legacy/name).read_bytes()==(out/'current_fixture'/name).read_bytes(),name
    with (legacy/'arrivals.csv').open(newline='') as a1,(out/'current_fixture/arrivals.csv').open(newline='') as b1:
        oldrows,newrows=list(csv.reader(a1)),list(csv.reader(b1))
    assert len(oldrows)==len(newrows)
    assert all(oldrow==newrow[:len(oldrow)] for oldrow,newrow in zip(oldrows,newrows))
    summary['checks']=json.loads((out/'current_fixture/summary.json').read_text())
    summary['checks']['legacy_observations_initialization_and_arrival_values_byte_exact']=True
    shutil.copyfile(str(out/'current_fixture/preflight.cfg'),str(legacy/'preflight.cfg'))
    run('legacy_preflight',[cache/'legacy','invert',legacy/'preflight.cfg',legacy,'dd'])
    assert (legacy/'dd_matrix_preflight.csv').read_bytes()==(out/'current_fixture/dd_matrix_preflight.csv').read_bytes()
    with (legacy/'dd_preflight_ray_status.csv').open() as first,(out/'current_fixture/dd_preflight_ray_status.csv').open() as second:
        oldreader,newreader=csv.DictReader(first),csv.DictReader(second)
        oldrows,newrows=list(oldreader),list(newreader)
    assert len(oldrows)==len(newrows)==4
    assert all(old=={key:new[key] for key in old} for old,new in zip(oldrows,newrows))
    for name in ('simulation_ray_status.csv','dd_history.csv'):
        assert (legacy/name).read_bytes()==(out/'current_fixture'/name).read_bytes()
    assert not (legacy/'dd_grid.csv').exists() and not (legacy/'dd_events.csv').exists()
    summary['checks']['legacy_preflight_census_and_existing_status_fields_byte_exact']=True
    summary['checks']['legacy_simulation_status_file_byte_exact']=True
    summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'summary.json'}
    summary['status']='passed';save()
except BaseException as exc:
    summary['status']='failed';summary['failure']=str(exc);save();raise
print(str(out/'summary.json'))
