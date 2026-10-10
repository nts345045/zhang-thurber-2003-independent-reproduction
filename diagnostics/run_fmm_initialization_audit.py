#!/usr/bin/env python3
"""Measure an isolated initializer; failed gates remain recorded as failures."""
import csv
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--variant", required=True, help="New output suffix; existing evidence is never overwritten")
parser.add_argument("--refine", action="store_true")
parser.add_argument("--order", type=int, choices=(1, 2), default=1)
parser.add_argument("--closed-seed-cells", action="store_true")
parser.add_argument("--production-entry", action="store_true", help="Test production seeded/selected rays with exact prototype parity")
args = parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.variant):
    parser.error("Variant must contain only letters, digits, underscores, or hyphens")
refine = args.refine
BUILD = ROOT / "tmp/fmm_initialization_audit" / args.variant
OUT = ROOT / "data/development" / ("fmm_initialization_" + args.variant)
if OUT.exists() or BUILD.exists():
    parser.error("This variant already exists; choose a new name to preserve its evidence")
BUILD.mkdir(parents=True)
OUT.mkdir(parents=True)
os.environ["TMPDIR"] = str(ROOT / "tmp")
snapshot = BUILD / "source"
relative_sources = ["diagnostics/check_fmm_initialization.cpp", "diagnostics/first_arrival_fmm.hpp",
                    "src/first_arrival.hpp", "src/core.hpp", "src/ray_metric.hpp", "src/forward.hpp",
                    "diagnostics/production_entry_checks.hpp", "diagnostics/run_fmm_initialization_audit.py",
                    "diagnostics/seeded_bending.py"]
for relative in relative_sources:
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / relative), str(target))
header = snapshot / "diagnostics/seeded_bending.hpp"
write_header(header, snapshot / "src/core.hpp")
relative_sources.append("diagnostics/seeded_bending.hpp")
# Preserve the exact compilation inputs even if collaborators change the live tree.
def archive_metadata(info):
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    info.pax_headers = {}
    return info


with tarfile.open(str(OUT / "source_snapshot.tar.gz"), "w:gz") as archive:
    for relative in relative_sources:
        archive.add(str(snapshot / relative), arcname=relative, filter=archive_metadata)
source = snapshot / "diagnostics/check_fmm_initialization.cpp"
binary = BUILD / "check_fmm_initialization"
command = ["c++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
           str(source), "-o", str(binary)]
compiled = subprocess.run(command, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
(OUT / "compile_stdout.txt").write_text(compiled.stdout)
(OUT / "compile_stderr.txt").write_text(compiled.stderr)
if compiled.returncode:
    print(compiled.stderr, end="")
    raise SystemExit(compiled.returncode)
run_command = [str(binary), str(OUT), "refine" if refine else "baseline", str(args.order),
               "closed" if args.closed_seed_cells else "original"]
if args.production_entry:
    run_command.append("--production-entry")
result = subprocess.run(run_command, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True)
(OUT / "stdout.txt").write_text(result.stdout)
(OUT / "stderr.txt").write_text(result.stderr)
with (OUT / "results.csv").open() as f:
    rows = list(csv.DictReader(f))
with (OUT / "consistency.csv").open() as f:
    checks = list(csv.DictReader(f))
files = [binary, OUT / "source_snapshot.tar.gz"] + list(sorted(OUT.glob("*.csv")))
files += sorted(OUT.glob("*.txt"))
parity = []
if args.production_entry:
    with (OUT / "entry_parity.csv").open() as f:
        parity = list(csv.DictReader(f))
summary = {
    "purpose": "Independent FMM candidate paths followed by continuous variational bending, with optional exact production-entry parity",
    "real_observations_used": False,
    "production_solver_changed": False,
    "command": "PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py " +
               " ".join(shlex.quote(arg) for arg in sys.argv[1:]),
    "order": args.order,
    "closed_seed_cells": args.closed_seed_cells,
    "production_entry": args.production_entry,
    "entry_parity_calls": len(parity),
    "entry_parity_failures": [r for r in parity if r["passed"] != "1"],
    "return_code": result.returncode,
    "refinement": refine,
    "compile_command": [arg.replace(str(ROOT) + "/", "") for arg in command],
    "run_command": [arg.replace(str(ROOT) + "/", "") for arg in run_command],
    "source_sha256": {relative: hashlib.sha256((snapshot / relative).read_bytes()).hexdigest()
                      for relative in relative_sources},
    "cases": len(rows),
    "extraction_failures": [r for r in rows if r["extracted"] != "1"],
    "checks": len(checks),
    "failed_checks": [r for r in checks if r["passed"] != "1"],
    "selected_nonconverged": [r for r in rows if r["converged"] != "1"],
    "limitations": ["Finite seeds and auxiliary grids do not certify global first arrival.",
                    "FMM field time is not used as the reported continuous travel time.",
                    "Nondifferentiability at an exact branch crossing requires separate one-sided interpretation.",
                    "No field model has been reinverted with this prototype."],
    "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
print(json.dumps({k:summary[k] for k in ("cases","checks","failed_checks")}, indent=2))
raise SystemExit(1 if result.returncode or summary["failed_checks"] or summary["extraction_failures"] or
                summary["selected_nonconverged"] or summary["entry_parity_failures"] or
                (args.production_entry and not parity) else 0)
