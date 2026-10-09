#!/usr/bin/env python3
"""Rebuild the analytic audit for baseline, metric-only, and current kernels."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "8f51613"
OUT = ROOT / "data/development/ray_optimizer_audit"
TMP = ROOT / "tmp/ray_optimizer_audit"
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
environment = dict(os.environ, TMPDIR=str(TMP))
baseline = subprocess.run(["git", "show", BASELINE + ":src/core.hpp"], cwd=str(ROOT),
                          check=True, stdout=subprocess.PIPE).stdout.decode()
current = (ROOT / "src/core.hpp").read_text()


def segment_bounds(source):
    return source.index("double segment("), source.index("double path_eval(")


old_start, old_end = segment_bounds(baseline)
new_start, new_end = segment_bounds(current)
metric_only = current[:new_start] + baseline[old_start:old_end] + current[new_end:]
variants = {"baseline": baseline, "metric_only": metric_only, "corrected": current}
manifest = {"baseline_commit": BASELINE,
            "scope": "Analytic component audit; no observations or inversion runs",
            "metric_only_construction": "Current kernel with baseline segment quadrature restored",
            "source_sha256": hashlib.sha256((ROOT / "diagnostics/ray_optimizer_audit.cpp").read_bytes()).hexdigest(),
            "variants": {}}
for name, source in variants.items():
    header = TMP / (name + ".hpp")
    executable = TMP / name
    header.write_text(source)
    command = ["g++", "-std=c++17", "-O3", "-Wall", "-Wextra", "-Wpedantic",
               '-DRAY_CORE_HEADER="' + str(header) + '"',
               "diagnostics/ray_optimizer_audit.cpp", "-o", str(executable)]
    subprocess.run(command, cwd=str(ROOT), env=environment, check=True)
    with (OUT / (name + ".csv")).open("w") as output:
        with (OUT / (name + "_segment.txt")).open("w") as errors:
            subprocess.run([str(executable)], cwd=str(ROOT), env=environment,
                           stdout=output, stderr=errors, check=True)
    manifest["variants"][name] = {
        "header_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "output_sha256": hashlib.sha256((OUT / (name + ".csv")).read_bytes()).hexdigest()}
    print("Completed " + name)
(OUT / "analytic_provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
