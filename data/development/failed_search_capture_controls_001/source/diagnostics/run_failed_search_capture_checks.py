#!/usr/bin/env python3
"""Freeze and run invented failure-capture controls; no real ray calculation."""
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


def need(ok,message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--build',required=True,type=Path)
    args=parser.parse_args()
    out=args.output.resolve();build=args.build.resolve()
    for p in (out,build):
        p.relative_to(ROOT);need(p!=ROOT and not p.exists(),'Require fresh repository-local directory')
    need(out not in build.parents and build not in out.parents and out!=build,'Overlapping output/build')
    out.mkdir(parents=True);build.mkdir(parents=True)
    sources=['src/core.hpp','src/ray_metric.hpp','src/csv.hpp','diagnostics/failed_search_capture.hpp',
             'diagnostics/check_failed_search_capture.cpp','diagnostics/run_failed_search_capture_checks.py']
    compiler=Path(shutil.which('c++')).resolve()
    summary=dict(status='running',scope='Invented capture-interface records only; no trace(), real ray, inverse or method change.',
                 started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),commands=[],
                 compiler=str(compiler),compiler_sha256=sha(compiler),source_sha256={n:sha(ROOT/n) for n in sources})
    def save():
        temp=out/'summary.json.new';temp.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');temp.replace(out/'summary.json')
    def command(stage,argv):
        record=dict(stage=stage,command=[str(a.relative_to(ROOT)) if isinstance(a,Path) and ROOT in a.parents else str(a) for a in argv])
        summary['commands'].append(record);save()
        with (out/(stage+'_stdout.log')).open('w') as stdout,(out/(stage+'_stderr.log')).open('w') as stderr:
            r=subprocess.run(record['command'],cwd=str(ROOT),stdout=stdout,stderr=stderr,
                             env=dict(os.environ,TMPDIR=str(ROOT/'tmp'),OMP_NUM_THREADS='1'))
        record['return_code']=r.returncode;save();need(r.returncode==0,stage+' failed')
    try:
        for name,digest in summary['source_sha256'].items():
            target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(str(ROOT/name),str(target));need(sha(target)==digest,'Source freeze mismatch')
        binary=build/'check'
        command('compile',[compiler,'-std=gnu++17','-O3','-Wall','-Wextra','-Wpedantic','-fopenmp',
                           out/'source/diagnostics/check_failed_search_capture.cpp','-lstdc++fs','-o',binary])
        summary['binary_sha256']=sha(binary)
        command('controls',[binary,out/'invented'])
        with (out/'invented/checks.csv').open(newline='') as stream:checks=list(csv.DictReader(stream))
        need(checks and all(r['passed']=='1' for r in checks),'Failed recorded control')
        for name,digest in summary['source_sha256'].items():
            need(sha(ROOT/name)==sha(out/'source'/name)==digest,'Source changed during controls')
        summary.update(status='passed',checks=checks,check_count=len(checks),ray_traces=0,
                       limitations=['The declared internal run labels contain no CSV delimiter; provider metadata attach through the caller sidecars.',
                                    'Trial scalar actions/decisions are intentionally invented interface inputs. Only the invented base path is reevaluated by capture_failed.',
                                    'No numerical neutrality of the future real replay is inferred; its observed/unobserved and old-output parity remain separate requirements.'])
    except BaseException as error:
        summary.update(status='failed',failure=repr(error));raise
    finally:
        summary['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        summary['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name not in ('summary.json','summary.json.new')}
        save()
    print(json.dumps(dict(status=summary['status'],checks=summary['check_count'])))


if __name__=='__main__':
    main()
