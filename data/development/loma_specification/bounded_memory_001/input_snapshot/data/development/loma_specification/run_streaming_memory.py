#!/usr/bin/env python3
"""Freeze identified geometry and measure all Loma structural slots, no times."""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
args = parser.parse_args()
if Path(args.variant).name != args.variant or args.variant in ('', '.', '..'):
    parser.error('Use one new directory name')
OUT = HERE / args.variant
if OUT.exists():
    parser.error('Existing evidence is immutable; choose another variant')
OUT.mkdir()
snapshot = OUT / 'input_snapshot'
inputs = ['data/authoritative/loma_prieta/selected_events.csv',
          'data/authoritative/loma_prieta/selected_channels.csv',
          'src/csv.hpp', 'src/main.cpp', 'src/core.hpp',
          'data/development/loma_specification/streaming_memory.cpp',
          'data/development/loma_specification/run_streaming_memory.py']
for name in inputs:
    target = snapshot / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / name), str(target))
binary = OUT / 'streaming_memory'
def relative(path): return str(path.relative_to(ROOT))
command = ['c++', '-O2', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
           '-I', relative(snapshot / 'src'),
           relative(snapshot / 'data/development/loma_specification/streaming_memory.cpp'), '-o', relative(binary)]
environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'))
compiled = subprocess.run(command, cwd=str(ROOT), env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
(OUT / 'compile_stdout.txt').write_text(compiled.stdout)
(OUT / 'compile_stderr.txt').write_text(compiled.stderr)
if compiled.returncode:
    raise SystemExit(compiled.returncode)
run_command = [relative(binary)] + [relative(snapshot / name) for name in inputs[:2]]
result = subprocess.run(run_command, cwd=str(ROOT), env=environment, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, universal_newlines=True)
(OUT / 'stdout.txt').write_text(result.stdout)
(OUT / 'stderr.txt').write_text(result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
counts = json.loads(result.stdout)
assert counts['row_slots'] == 15932384 and counts['strict_below_20km_pairs'] == 152834
assert counts['absolute_slots'] == counts['unique_ray_slots'] == 37648
assert counts['catalog_slots'] == counts['precise_slots'] == 7947368
assert counts['numeric_datum_bytes'] == 40
fields = []
for spacing in (.5, .25, .125, .0625):
    nodes = math.prod([int(math.ceil(length / spacing)) + 1 for length in (70, 100, 17)]) if hasattr(math, 'prod') else 1
    if not hasattr(math, 'prod'):
        for length in (70, 100, 17): nodes *= int(math.ceil(length / spacing)) + 1
    fields.append(dict(spacing_km=spacing,auxiliary_nodes=nodes,
                       one_field_persistent_array_bytes=12 * nodes,
                       all_52_fields_persistent_array_bytes=52 * 12 * nodes,
                       build_arrays_excluding_heap_bytes=9 * nodes))
summary = dict(scope='Structural memory probe only; every slot has NaN instead of a travel time; no observation file, ray, noise draw or inversion generated',
               geometry_status='Exact copies of authoritative selected geometry with all native identifiers and provenance columns retained',
               snapshot_path_base='Original provider-relative source_file paths retain their data/authoritative/loma_prieta base',
               compile_command=command,run_command=run_command,counts=counts,
               csv_streaming_parser_used_for='Only the small input geometry tables; this probe does not benchmark parsing a full observations CSV',
               fmm_component_memory_scenarios=fields,
               memory_limits='Measured peak includes numeric slots and geometry/identity lookup, not rays, matrices, LSQR, FMM fields or generated CSV parsing. FMM scenarios count time/parent arrays and temporary slowness/accepted arrays only; heap and allocation overhead are additional.',
               input_sha256={name:hashlib.sha256((snapshot / name).read_bytes()).hexdigest() for name in inputs},
               output_sha256={relative(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [binary,OUT/'stdout.txt',OUT/'stderr.txt',OUT/'compile_stdout.txt',OUT/'compile_stderr.txt']})
(OUT / 'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
print(json.dumps(counts,indent=2))
