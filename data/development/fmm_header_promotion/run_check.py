#!/usr/bin/env python3
"""Compile a frozen shared-header component fixture, retaining all outputs."""
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAPSHOT = OUT / 'source_snapshot'
BUILD = ROOT / 'tmp/fmm_header_promotion'
if SNAPSHOT.exists() or BUILD.exists():
    raise SystemExit('Existing evidence is immutable; use another output folder')
SNAPSHOT.mkdir()
BUILD.mkdir(parents=True)
sources = ['diagnostics/check_fmm_field.cpp', 'diagnostics/first_arrival_fmm.hpp',
           'src/first_arrival.hpp', 'src/core.hpp']
for name in sources:
    target = SNAPSHOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / name), str(target))

def relative(path):
    return str(path.relative_to(ROOT))

binary = BUILD / 'check_fmm_field'
compile_command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
                   relative(SNAPSHOT / sources[0]), '-o', relative(binary)]
run_command = [relative(binary), relative(OUT / 'results.csv'), '2']
environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'))
compile_result = subprocess.run(compile_command, cwd=str(ROOT), env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
(OUT / 'compile_stdout.txt').write_text(compile_result.stdout)
(OUT / 'compile_stderr.txt').write_text(compile_result.stderr)
run_result = None
if compile_result.returncode == 0:
    run_result = subprocess.run(run_command, cwd=str(ROOT), env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
    (OUT / 'stdout.txt').write_text(run_result.stdout)
    (OUT / 'stderr.txt').write_text(run_result.stderr)
rows = []
if (OUT / 'results.csv').exists():
    with (OUT / 'results.csv').open() as stream:
        rows = list(csv.DictReader(stream))
old_header = subprocess.check_output(['git', 'show', 'HEAD:diagnostics/first_arrival_fmm.hpp'],
                                     cwd=str(ROOT)).decode()
expected = old_header.replace(
    '// Diagnostic initializer only. Returned field times are not production actions.',
    '// Auxiliary eikonal initializer. Field times do not replace continuous ray actions.', 1
    ).replace('#include "../src/core.hpp"', '#include "core.hpp"', 1)
same_implementation = expected == (SNAPSHOT / 'src/first_arrival.hpp').read_text()
passed = (compile_result.returncode == 0 and run_result is not None and
          run_result.returncode == 0 and len(rows) == 39 and same_implementation)
files = list(sorted(p for p in OUT.glob('*.txt'))) + [Path(__file__).resolve()]
if binary.exists():
    files.append(binary)
if (OUT / 'results.csv').exists():
    files.append(OUT / 'results.csv')
summary = dict(status='passed' if passed else 'failed',
               scope='Header relocation and invented FMM components only; no field inversion or forward-cache validation',
               real_observations_used=False, fmm_order=2, path_cases=len(rows),
               compile_command=compile_command, run_command=run_command, TMPDIR='tmp',
               compile_return_code=compile_result.returncode,
               run_return_code=run_result.returncode if run_result is not None else None,
               implementation_unchanged_except_include_and_comment=same_implementation,
               previous_header_sha256=hashlib.sha256(old_header.encode()).hexdigest(),
               source_sha256={name:hashlib.sha256((SNAPSHOT / name).read_bytes()).hexdigest() for name in sources},
               output_sha256={relative(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
               source_snapshot_base=relative(SNAPSHOT),
               limitations=['Passing finite component cases does not certify global first arrivals.',
                            'The snapshotted core includes the separate integration branch changes; this check does not validate its new seeded entry point.'])
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
print(json.dumps({k: summary[k] for k in ('status', 'path_cases', 'implementation_unchanged_except_include_and_comment')}, indent=2))
raise SystemExit(0 if passed else 1)
