#!/usr/bin/env python3
"""Invented homogeneous I/O fixtures; no real data or solver calls."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BUILD = ROOT / 'tmp/hayward_1d_support_checks'
if BUILD.exists():
    raise ValueError('Preserve prior checks; use a clean separate checkout for reproduction')
BUILD.mkdir(parents=True)
HELPER = ROOT / 'diagnostics/compare_hayward_1d_support.py'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, records):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(records)
def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))
def f12(value):
    return format(value, '.12g')
base = BUILD / 'invented_valid'
base.mkdir()
events = [dict(id=str(i), x=x, y=y, z=z, t=0,
               event_resource_id='smi:invented/event/{}'.format(i),
               origin_resource_id='smi:invented/origin/{}'.format(i))
          for i,(x,y,z) in enumerate([(.2,.3,.4),(.9,.6,.8)])]
station = dict(id='0',x=.9,y=.9,z=.9,t=0, network_code='XX',station_code='MOCK',location_code='',channel_code='HHZ',
               channel_seed_id='XX.MOCK..HHZ',channel_fdsn_source_id='FDSN:XX_MOCK__H_H_Z',
               metadata_epoch_start='2000-01-01T00:00:00Z',metadata_epoch_end='')
grid = [dict(x=x,y=y,z=z,v=5) for z in [0,1] for y in [0,1] for x in [0,1]]
obs=[]; rays=[]; matrix=[]; columns=[]
for i,e in enumerate(events):
    delta=[float(e[k])-float(station[k]) for k in 'xyz']
    length=math.sqrt(sum(v*v for v in delta));time=length/5
    o=dict(i=str(i),j='-1',station='0',type='0',value=str(time+.1),station_j='-1',
           event_i_resource_id=e['event_resource_id'],origin_i_resource_id=e['origin_resource_id'],
           pick_i_resource_id='smi:invented/pick/{}'.format(i),arrival_i_resource_id='smi:invented/arrival/{}'.format(i))
    o.update({k:v for k,v in station.items() if k not in ['id','x','y','z','t']});obs.append(o)
    ray=dict(row=str(i),observation_row=str(i),i=str(i),station='0',observed=f12(time+.1),predicted=f12(time),residual=f12(.1),
             ray_time=f12(time),ray_converged='1',ray_projected_gradient='0',ray_raw_gradient='0')
    ray.update({k:v for k,v in o.items() if k not in ['i','j','station','type','value']});rays.append(ray)
    for axis,key in enumerate('xyzt'):
        c=dict(column=str(4*i+axis),parameter=key,event=str(i),node='-1',x=e['x'],y=e['y'],z=e['z'],
               reference_value=e[key],parameter_unit='s' if key=='t' else 'km')
        c.update({'source_'+k:v for k,v in e.items() if k not in ['id','x','y','z','t']});columns.append(c)
        value=1 if axis==3 else delta[axis]/(5*length)
        if value:matrix.append(dict(row=i,column=4*i+axis,value=f12(value)))
    # The exact nodal q kernel along a homogeneous straight ray: trilinear
    # weights become cubic in t, so two-point Gauss integrates them exactly.
    for n,node in enumerate(grid):
        weight=0
        for sign in [-1,1]:
            t=.5+sign*.5/math.sqrt(3)
            point=[float(e[k])+(float(station[k])-float(e[k]))*t for k in 'xyz']
            w=.5
            for axis,key in enumerate('xyz'):w*=point[axis] if node[key] else 1-point[axis]
            weight+=w
        matrix.append(dict(row=i,column=8+n,value=f12(time*weight)))
for n,node in enumerate(grid):
    c=dict(column=str(8+n),parameter='q',event='-1',node=str(n),x=node['x'],y=node['y'],z=node['z'],reference_value=0,parameter_unit='dimensionless')
    c.update(source_event_resource_id='',source_origin_resource_id='');columns.append(c)
for name,records in [('initial_events.csv',events),('stations.csv',[station]),('initial_grid.csv',grid),('observations.csv',obs),
                     ('initial_linearization_rows.csv',rays),('initial_linearization_columns.csv',columns),('initial_linearization_matrix.csv',matrix)]:
    write(base/name,records)
def manifests(folder):
    names=['initial_events.csv','stations.csv','initial_grid.csv','observations.csv']
    (folder/'run_manifest.json').write_text(json.dumps({'sha256':{str((folder/n).relative_to(ROOT)):sha(folder/n) for n in names},'fixture':'invented homogeneous source/receiver geometry'}))
    (folder/'preflight.json').write_text(json.dumps({'status':'invented_fixture','sha256':{p.name:sha(p) for p in folder.glob('initial_*.csv')}}))
checks=[]
for name in ['valid','changed_identity','missing_origin_column']:
    folder=base if name=='valid' else BUILD/name
    if name!='valid':shutil.copytree(str(base),str(folder))
    if name=='changed_identity':
        altered=read(folder/'initial_linearization_rows.csv');altered[0]['event_i_resource_id']='smi:invented/wrong';write(folder/'initial_linearization_rows.csv',altered)
    if name=='missing_origin_column':
        altered=[r for r in read(folder/'initial_linearization_matrix.csv') if not(r['row']=='0' and r['column']=='3')];write(folder/'initial_linearization_matrix.csv',altered)
    manifests(folder)
    command=['python3',str(HELPER.relative_to(ROOT)),'--data',str(folder.relative_to(ROOT)),'--output',str((BUILD/(name+'_output')).relative_to(ROOT))]
    result=subprocess.run(command,cwd=str(ROOT),env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    passed=result.returncode==0 if name=='valid' else result.returncode!=0
    if name=='valid':
        summary=json.loads((BUILD/'valid_output/summary.json').read_text())
        passed=passed and summary['reference_counts']['reference_valid']==2 and summary['rays']==2
        # Serialization is the only expected source/time discrepancy here.
        passed=passed and summary['production_minus_reference_s']['maximum_absolute']<5e-13
        passed=passed and summary['production_source_derivative_minus_reference_s_per_km']['maximum_absolute']<5e-13
    else:
        expected='Original observation metadata changed' if name=='changed_identity' else 'Missing absolute origin-time columns'
        passed=passed and expected in result.stderr and not(BUILD/(name+'_output')).exists()
    checks.append(dict(name=name,passed=bool(passed),command=command,return_code=result.returncode,
                       stdout=result.stdout,stderr=result.stderr.replace(str(ROOT)+'/','')))
report=dict(scope='Invented two-ray homogeneous fixture and malformed identity/matrix controls; no real rays or inversion',
            command='PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_1d_support_checks/check.py',
            helper_sha256=sha(HELPER),fixture_source_sha256=sha(Path(__file__).resolve()),
            reference_sha256=sha(ROOT/'diagnostics/first_arrival_1d_reference.py'),checks=checks,passed=all(c['passed'] for c in checks))
(HERE/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'passed':report['passed'],'checks':[(c['name'],c['passed']) for c in checks]}))
raise SystemExit(0 if report['passed'] else 1)
