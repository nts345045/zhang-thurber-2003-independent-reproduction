#!/usr/bin/env python3
"""Re-extract the identified failures of the frozen Hayward candidate audit."""
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/development/fmm_field_checks/closed_cell_hayward"
TMP = ROOT / "tmp/fmm_closed_cell_hayward"
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(ROOT / "tmp")
os.environ["OMP_NUM_THREADS"] = "1"
baseline = ROOT / "data/development/fmm_hayward_audit/results.csv"
inputs = ROOT / "data/development/hayward_dd_top_layer_rays.csv"
grid = ROOT / "data/hayward/dd_grid.csv"
with baseline.open() as f:
    failed = {r["observation_index"]:r for r in csv.DictReader(f) if r["extracted"] != "1"}
with inputs.open() as f:
    reader = csv.DictReader(f)
    names = reader.fieldnames
    selected = [r for r in reader if r["observation_index"] in failed]
if not failed or len(failed) != len(selected):
    raise ValueError("Frozen failure rows are absent or unmatched")
subset = OUT / "identified_inputs.csv"
with subset.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    writer.writerows(selected)
header = TMP / "seeded_bending.hpp"
binary = TMP / "check_fmm_hayward"
write_header(header)
source = ROOT / "diagnostics/check_fmm_hayward.cpp"
command = ["c++","-O3","-std=c++17","-Wall","-Wextra","-Wpedantic","-fopenmp",
           "-I",str(TMP),str(source),"-o",str(binary),"-lstdc++fs"]
subprocess.check_call(command,cwd=str(ROOT))
output = OUT / "results.csv"
subprocess.check_call([str(binary),str(grid),str(subset),str(output),"0.5"],cwd=str(ROOT))
with output.open() as f:
    rows = {r["observation_index"]:r for r in csv.DictReader(f)}
assert len(rows) == len(selected)
for old in selected:
    new = rows[old["observation_index"]]
    assert all(new[k] == v for k,v in old.items())
    assert new["extracted"] == "1"
    assert float(new["selected_outside_nodes"]) == 0
    assert float(new["selected_endpoint_error_km"]) == 0
    assert new["field_time_s"] == failed[old["observation_index"]]["field_time_s"]
files = [Path(__file__).resolve(),source,ROOT/"diagnostics/first_arrival_fmm.hpp",
         ROOT/"src/first_arrival.hpp",ROOT/"src/forward.hpp",
         ROOT/"diagnostics/seeded_bending.py",ROOT/"src/main.cpp",ROOT/"src/core.hpp",
         ROOT/"src/csv.hpp",ROOT/"src/ray_checks.hpp",baseline,inputs,grid,subset,output,header,binary]
summary = {
    "command":"python3 diagnostics/check_fmm_failed_extraction.py",
    "purpose":"Re-extract every previously failed identified ray with the closed receiver-cell correction",
    "ray_count":len(rows),"all_native_input_columns_preserved":True,
    "all_previously_failed_extractions_now_succeed":True,
    "reported_auxiliary_field_times_unchanged":True,
    "maximum_action_reduction_s":max(float(r["action_reduction_s"]) for r in rows.values()),
    "selected_nonconverged":sum(r["selected_converged"]!="1" for r in rows.values()),
    "limitations":["This tests receiver-cell extraction only, not global first-arrival selection.",
                   "The original 186-ray audit and its failed flags remain unchanged.",
                   "No production solver or inversion is modified."],
    "sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
}
(OUT/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({k:summary[k] for k in ("ray_count","all_previously_failed_extractions_now_succeed",
                                       "maximum_action_reduction_s","selected_nonconverged")},indent=2))
