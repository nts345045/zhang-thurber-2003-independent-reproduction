#!/usr/bin/env python3
"""Isolated rotated-affine validation with immutable sources and retained failures."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
parser.add_argument('--level', choices=['baseline', 'field_refine', 'path_refine'], default='baseline')
parser.add_argument('--production-entry', action='store_true', help='Test production seeded/selected rays with exact prototype parity')
args = parser.parse_args()
if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.variant):
    parser.error('Variant must contain only letters, digits, underscores, or hyphens')
build = Path('tmp/fmm_rotated_affine') / args.variant
out = Path('data/development') / ('fmm_rotated_affine_' + args.variant)
if (ROOT / build).exists() or (ROOT / out).exists():
    parser.error('Choose a new variant to preserve existing evidence')
(ROOT / build).mkdir(parents=True)
(ROOT / out).mkdir(parents=True)
snapshot = build / 'source'
sources = ['diagnostics/check_fmm_rotated_affine.cpp', 'diagnostics/first_arrival_fmm.hpp',
           'src/first_arrival.hpp', 'src/core.hpp', 'src/ray_metric.hpp', 'src/forward.hpp',
           'diagnostics/production_entry_checks.hpp', 'diagnostics/seeded_bending.py', 'diagnostics/run_fmm_rotated_affine.py']
for relative in sources:
    destination = ROOT / snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / relative), str(destination))
write_header(ROOT / snapshot / 'diagnostics/seeded_bending.hpp', ROOT / snapshot / 'src/core.hpp')
sources.append('diagnostics/seeded_bending.hpp')
archive_path = out / 'source_snapshot.tar.gz'
# Only source bytes/paths are retained; no Unix owner, workspace path, or times.
with (ROOT / archive_path).open('wb') as raw:
    with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as archive:
            for relative in sources:
                data = (ROOT / snapshot / relative).read_bytes()
                info = tarfile.TarInfo(relative)
                info.size = len(data)
                info.mode = 0o644
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                archive.addfile(info, io.BytesIO(data))
binary = build / 'check_fmm_rotated_affine'
compile_command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
                   str(snapshot / 'diagnostics/check_fmm_rotated_affine.cpp'), '-o', str(binary)]
run_command = [str(binary), str(out), args.level]
if args.production_entry:
    run_command.append('--production-entry')
environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'))
compiled = subprocess.run(compile_command, cwd=str(ROOT), env=environment,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
(ROOT / out / 'compile_stdout.txt').write_text(compiled.stdout)
(ROOT / out / 'compile_stderr.txt').write_text(compiled.stderr)
if compiled.returncode:
    print(compiled.stderr, end='')
    raise SystemExit(compiled.returncode)
result = subprocess.run(run_command, cwd=str(ROOT), env=environment,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
(ROOT / out / 'stdout.txt').write_text(result.stdout)
(ROOT / out / 'stderr.txt').write_text(result.stderr)
rows, checks, parity = [], [], []
if (ROOT / out / 'results.csv').exists():
    with (ROOT / out / 'results.csv').open() as stream:
        rows = list(csv.DictReader(stream))
if (ROOT / out / 'checks.csv').exists():
    with (ROOT / out / 'checks.csv').open() as stream:
        checks = list(csv.DictReader(stream))
if args.production_entry and (ROOT / out / 'entry_parity.csv').exists():
    with (ROOT / out / 'entry_parity.csv').open() as stream:
        parity = list(csv.DictReader(stream))
files = [binary, archive_path] + sorted(p.relative_to(ROOT) for p in (ROOT / out).glob('*.csv'))
files += sorted(p.relative_to(ROOT) for p in (ROOT / out).glob('*.txt'))
summary = {
    'purpose': 'Invented positive 3-D affine-velocity fields, exact contained circular geodesics, and unchanged continuous bending of FMM seeds.',
    'command': 'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_rotated_affine.py ' + ' '.join(shlex.quote(a) for a in sys.argv[1:]),
    'compile_command': compile_command, 'run_command': run_command, 'TMPDIR': 'tmp',
    'level': args.level, 'order': 2, 'closed_seed_cells': True,
    'production_entry': args.production_entry,
    'entry_parity_calls': len(parity), 'entry_parity_failures': [row for row in parity if row['passed'] != '1'],
    'real_observations_used': False, 'production_solver_changed': False,
    'source_sha256': {relative: hashlib.sha256((ROOT / snapshot / relative).read_bytes()).hexdigest() for relative in sources},
    'return_code': result.returncode, 'comparisons': len(rows), 'checks': len(checks),
    'failed_checks': [row for row in checks if row['passed'] != '1'],
    'extraction_failures': [row for row in rows if row['extracted'] != '1'],
    'nonconverged_fmm_bent': [row for row in rows if row['fmm_converged'] != '1'],
    'sha256': {str(path): hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in files},
    'limitations': ['This smooth affine field has a known unconstrained first-arrival geodesic entirely inside the box; it does not test a competing direct/diving branch or heterogeneous caustic.',
                    'Both the FMM-bent candidate and selected minimum over straight/FMM seeds are tested; a correct direct seed cannot hide an inaccurate FMM-bent candidate.',
                    'The existing 2.5e-5 s time, 3e-6 s/km endpoint-derivative, and 2e-5 s reciprocity tolerances are retained.',
                    'Auxiliary and path refinement are separate variants. All numerical failures remain saved.']}
passed = (result.returncode == 0 and len(rows) == 6 and not summary['failed_checks'] and
          not summary['extraction_failures'] and not summary['nonconverged_fmm_bent'] and
          not summary['entry_parity_failures'] and (not args.production_entry or len(parity) == 6))
summary['status'] = 'passed' if passed else 'failed'
(ROOT / out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
print(json.dumps({key: summary[key] for key in ['status', 'comparisons', 'checks', 'failed_checks']}, indent=2))
raise SystemExit(0 if passed else 1)
