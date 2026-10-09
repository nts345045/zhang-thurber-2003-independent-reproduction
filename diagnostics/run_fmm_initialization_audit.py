#!/usr/bin/env python3
"""Measure an isolated initializer; failed gates remain recorded as failures."""
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tmp/fmm_initialization_audit"
OUT = ROOT / "data/development/fmm_initialization_audit"
BUILD.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(ROOT / "tmp")
header = BUILD / "seeded_bending.hpp"
write_header(header)
source = ROOT / "diagnostics/check_fmm_initialization.cpp"
binary = BUILD / "check_fmm_initialization"
command = ["c++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
           "-I", str(BUILD), str(source), "-o", str(binary)]
subprocess.check_call(command, cwd=str(ROOT))
subprocess.check_call([str(binary), str(OUT)], cwd=str(ROOT))
with (OUT / "results.csv").open() as f:
    rows = list(csv.DictReader(f))
with (OUT / "consistency.csv").open() as f:
    checks = list(csv.DictReader(f))
files = [source, ROOT / "diagnostics/first_arrival_fmm.hpp", ROOT / "src/core.hpp",
         Path(__file__).resolve(), ROOT / "diagnostics/seeded_bending.py", header, binary]
files += list(sorted(OUT.glob("*.csv")))
summary = {
    "purpose": "Independent FMM candidate paths followed by unchanged continuous variational bending; prototype only",
    "real_observations_used": False,
    "production_solver_changed": False,
    "command": "python3 diagnostics/run_fmm_initialization_audit.py",
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
raise SystemExit(1 if summary["failed_checks"] or summary["extraction_failures"] else 0)
