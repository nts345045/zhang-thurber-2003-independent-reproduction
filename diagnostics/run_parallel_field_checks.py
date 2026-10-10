#!/usr/bin/env python3
"""Freeze and compare serial versus parallel receiver-field preparation on invented fixtures."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant',required=True)
args=parser.parse_args()
if not re.fullmatch('[A-Za-z0-9_-]+',args.variant):parser.error('Use a plain variant name')
out=Path('data/development')/('parallel_receiver_fields_'+args.variant)
build=Path('tmp')/out.name
out.mkdir(parents=True,exist_ok=False);build.mkdir(parents=True,exist_ok=False)
summary=dict(status='preparing',scope='Invented fixture parity only; no production ray job',commands=[])

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def save():
    p=out/'summary.json.new';p.write_text(json.dumps(summary,indent=2)+'\n');p.replace(out/'summary.json')
def command(label,argv):
    entry=dict(label=label,argv=list(map(str,argv)),status='running');summary['commands'].append(entry)
    start=time.time()
    with (out/(label+'_stdout.log')).open('w') as stdout,(out/(label+'_stderr.log')).open('w') as stderr:
        child=subprocess.Popen(entry['argv'],stdout=stdout,stderr=stderr,env=dict(os.environ,OMP_NUM_THREADS='4',TMPDIR=str(ROOT/'tmp')))
        entry['pid']=child.pid;save();code=child.wait()
    entry.update(status='complete',return_code=code,elapsed_seconds=time.time()-start);save()
    print(label,code,round(entry['elapsed_seconds'],3),flush=True)
    require(code==0,label+' failed; frozen evidence retained')

try:
    manifest=json.loads(Path('data/hayward_first_arrival_003/run_manifest.json').read_text())
    frozen=Path(manifest['binary']).parent.parent/'source'
    for name in ('src/core.hpp','src/first_arrival.hpp','src/ray_metric.hpp','src/csv.hpp','src/ray_checks.hpp'):
        require(sha(frozen/name)==manifest['source_sha256'][name],'Frozen dependency changed')
        require(sha(Path(name))==sha(frozen/name),'Numerical dependency changed: '+name)
    summary['frozen_serial_run_source_sha256']=manifest['source_sha256']
    for mode,root in [('serial',frozen),('parallel',Path('.'))]:
        target=out/'source'/mode
        (target/'src').mkdir(parents=True)
        for p in sorted((root/'src').glob('*')):
            if p.is_file():shutil.copyfile(str(p),str(target/'src'/p.name))
        (target/'diagnostics').mkdir()
        shutil.copyfile('diagnostics/check_parallel_fields.cpp',str(target/'diagnostics/check_parallel_fields.cpp'))
        compiled=build/mode;shutil.copytree(str(target),str(compiled))
        field=compiled/'src/first_arrival.hpp';original=field.read_text()
        require(original.count('class Field {')==1,'Diagnostic field-access location changed')
        exposed=original.replace('class Field {','class Field {\npublic: // Diagnostic-only raw-state read access.',1)
        field.write_text(exposed)
        (out/(mode+'_field_access.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),exposed.splitlines(True),fromfile='frozen/src/first_arrival.hpp',tofile='diagnostic/src/first_arrival.hpp')))
        summary[mode+'_compiled_source_sha256']={str(p.relative_to(compiled)):sha(p) for p in compiled.rglob('*') if p.is_file()}
        argv=['g++','-std=c++17','-O3','-Wall','-Wextra','-Wpedantic','-fopenmp']
        if mode=='serial':argv.append('-DSERIAL_CACHE')
        argv += [compiled/'diagnostics/check_parallel_fields.cpp','-lstdc++fs','-o',build/(mode+'_check')]
        command('compile_'+mode,argv)
        summary[mode+'_binary_sha256']=sha(build/(mode+'_check'))
    shutil.copyfile(__file__,str(out/'source/run_parallel_field_checks.py'))
    parity_files=['snapshot.bin','identified_error.bin','initial_ray_convergence.csv','initial_ray_derivatives.csv',
                  'initial_ray_identifiers.csv','initial_linearization_columns.csv','initial_linearization_matrix.csv',
                  'initial_linearization_rows.csv']
    checks={}
    for mode in ('serial','parallel'):
        for threads in (1,4):
            label=mode+'_'+str(threads);p=out/label;p.mkdir()
            command(label,[build/(mode+'_check'),p,threads])
            with (p/'checks.csv').open() as f:rows=list(csv.DictReader(f))
            require(rows and all(r['passed']=='1' for r in rows),'Fixture control failed')
            checks[label]=dict(checks=len(rows),failed=0,sha256={name:sha(p/name) for name in parity_files})
    control=checks['serial_1']['sha256']
    require(all(c['sha256']==control for c in checks.values()),'Bitwise field/candidate/ray or CLI parity failed')
    summary.update(status='passed',checks=checks,identical_artifact_groups=len(parity_files),
        source_sha256={str(p.relative_to(out)):sha(p) for p in (out/'source').rglob('*') if p.is_file()},
        limitations=['Invented component and CLI fixtures; no whole-field performance benchmark.',
                     'Only copied diagnostic Field headers expose raw private arrays; this access change does not change arithmetic.',
                     'Raw snapshots serialize explicit values and vectors, never object padding or addresses.',
                     'Parallel construction failures publish no new entries; changed model/spacing invalidation precedes construction.'])
except BaseException as error:
    summary.update(status='failed',failure=str(error));save();raise
save();print(out/'summary.json',flush=True)
