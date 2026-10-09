#!/usr/bin/env python3
"""Record an analytic first-arrival counterexample without changing the solver."""
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tmp/first_arrival_audit"
OUT = ROOT / "data/development/first_arrival_audit"
BUILD.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(ROOT / "tmp")
source = ROOT / "diagnostics/check_layered_first_arrival.cpp"
binary = BUILD / "check_layered_first_arrival"
command = ["c++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
           str(source), "-o", str(binary)]
subprocess.check_call(command, cwd=str(ROOT))
subprocess.check_call([str(binary), str(OUT / "results.csv")], cwd=str(ROOT))
with (OUT / "results.csv").open() as f:
    rows = list(csv.DictReader(f))
for row in rows:
    if float(row["distance_km"]) >= 20:
        error = abs(float(row["diving_polyline_time_s"]) - float(row["diving_time_s"]))
        if error > 1e-5:
            raise ValueError("Analytic ray and independently integrated polyline disagree")
summary = {
    "purpose": "An invented analytic velocity field diagnoses a branch-selection failure; no real observations are used.",
    "model": "v=4 km/s for -1<=z<=0 km; v=4+0.2*z km/s for 0<=z<=20 km; source and receiver z=-0.5 km",
    "geometry": "horizontal separations 4,20,40 km; infinite horizontal layer interpreted within a box containing every tested ray",
    "method": "Snell-law integration of direct and both turning branches; independent fine-polyline quadrature checks the analytic diving time",
    "current_solver": "Production trace() initialized at a straight path; spacing0.5km/max1000updates; stopping criteria unchanged",
    "maximum_first_arrival_error_s": max(float(r["returned_first_arrival_error_s"]) for r in rows),
    "stationary_but_late_cases": [float(r["distance_km"]) for r in rows
                                  if int(r["returned_converged"]) and float(r["returned_first_arrival_error_s"]) > 1e-5],
    "interpretation": "Optimizer stationarity and finite differences of the selected branch do not establish a first arrival. This counterexample does not quantify the error of each field ray.",
    "command": "python3 diagnostics/run_first_arrival_audit.py",
    "compiler_command": ["c++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
                         "diagnostics/check_layered_first_arrival.cpp", "-o", "tmp/first_arrival_audit/check_layered_first_arrival"],
    "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (source, ROOT / "src/core.hpp", Path(__file__).resolve(), binary, OUT / "results.csv")},
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
print(json.dumps(summary, indent=2))
