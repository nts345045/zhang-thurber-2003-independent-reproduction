#!/usr/bin/env python3
"""Freeze and run invented active-set quadratic checks; no field inputs."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant',required=True)
args=parser.parse_args()
if not re.fullmatch('[a-zA-Z0-9_-]+',args.variant):parser.error('Use a simple variant name')
out=Path('data/development/cone_ray_metric_checks')/args.variant
build=Path('tmp/cone_ray_metric_checks')/args.variant
if (ROOT/out).exists() or (ROOT/build).exists():parser.error('Choose a fresh variant; results are not overwritten')
(ROOT/out).mkdir(parents=True);(ROOT/build).mkdir(parents=True)
snapshot=build/'source'
sources=['diagnostics/check_cone_ray_metric.cpp','diagnostics/cone_ray_metric.hpp',
         'diagnostics/reduced_ray_metric.hpp','diagnostics/run_cone_ray_metric_checks.py','src/core.hpp', 'src/ray_metric.hpp']
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
for name in sources:
    target=ROOT/snapshot/name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(str(ROOT/name),str(target))
archive=out/'source_snapshot.tar.gz'
with (ROOT/archive).open('wb') as raw:
    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w') as package:
            for name in sources:
                data=(ROOT/snapshot/name).read_bytes();info=tarfile.TarInfo(name)
                info.size=len(data);info.mode=0o644;info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
                package.addfile(info,io.BytesIO(data))
binary=build/'check_cone_ray_metric'
command=['c++','-O3','-std=c++17','-Wall','-Wextra','-Wpedantic',str(snapshot/'diagnostics/check_cone_ray_metric.cpp'),'-o',str(binary)]
env=dict(os.environ,TMPDIR=str(ROOT/'tmp'))
compiled=subprocess.run(command,cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
(ROOT/out/'compile_stderr.txt').write_text(compiled.stderr)
if compiled.returncode:raise RuntimeError(compiled.stderr)
with (ROOT/out/'results.csv').open('w') as stdout,(ROOT/out/'stderr.txt').open('w') as stderr:
    run=subprocess.run([str(binary)],cwd=str(ROOT),env=env,stdout=stdout,stderr=stderr)
with (ROOT/out/'results.csv').open() as stream:checks=list(csv.DictReader(stream))
groups={}
for row in checks:
    group=groups.setdefault(row['check'],{'checks':0,'failures':0,'maximum_error':0.})
    group['checks']+=1;group['failures']+=row['passed']!='1';group['maximum_error']=max(group['maximum_error'],float(row['error']))
summary={'status':'passed' if run.returncode==0 and all(r['passed']=='1' for r in checks) else 'failed',
         'command':'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_cone_ray_metric_checks.py --variant '+args.variant,
         'compile_command':command,'run_command':[str(binary)],'TMPDIR':'tmp','return_code':run.returncode,
         'checks':len(checks),'groups':groups,'failures':[r for r in checks if r['passed']!='1'],
         'solver_work':(ROOT/out/'stderr.txt').read_text().strip(),
         'source_sha256':{name:sha(snapshot/name) for name in sources},
         'sha256':{str(p):sha(p) for p in [binary,archive,out/'results.csv',out/'stderr.txt',out/'compile_stderr.txt']},
         'scope':'Invented quadratic controls only: exhaustive small-face reference, randomized larger KKT residuals, explicit release/guard/overflow cases. Algebra tolerances do not change any ray stopping threshold.'}
(ROOT/out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':summary['status'],'checks':summary['checks'],'failures':summary['failures'],'solver_work':summary['solver_work']},indent=2))
raise SystemExit(0 if summary['status']=='passed' else 1)
