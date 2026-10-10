#!/usr/bin/env python3
"""Preserve every native identity while testing feasible alternative field rays."""
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tmp/fmm_hayward_audit"
OUT = ROOT / "data/development/fmm_hayward_audit"
BUILD.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(ROOT / "tmp")
os.environ["OMP_NUM_THREADS"] = "1"
header = BUILD / "seeded_bending.hpp"
write_header(header)
source = ROOT / "diagnostics/check_fmm_hayward.cpp"
binary = BUILD / "check_fmm_hayward"
input_path = ROOT / "data/development/hayward_dd_top_layer_rays.csv"
grid_path = ROOT / "data/hayward/dd_grid.csv"
events_path = ROOT / "data/hayward/dd_events.csv"
stations_path = ROOT / "data/hayward/stations.csv"
def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))
inputs = read(input_path)
events = {r["id"]:r for r in read(events_path)}
stations = {r["id"]:r for r in read(stations_path)}
for r in inputs:
    event, station = events[r["i"]], stations[r["station"]]
    for axis in "xyz":
        if float(event[axis]) != float(r["dd_source_"+axis+"_km"]) or float(station[axis]) != float(r["receiver_"+axis+"_km"]):
            raise ValueError("Ray geometry differs from saved model")
    for key in ("event_resource_id","origin_resource_id"):
        if event[key] != r[key.replace("_resource_id","_i_resource_id")]:
            raise ValueError("Event identity differs from saved model")
    for key in ("channel_seed_id","channel_fdsn_source_id","metadata_epoch_start","metadata_epoch_end"):
        if station[key] != r[key]:
            raise ValueError("Receiver identity differs from saved model: "+key)
    if station["source_sha256"] != r["channel_source_sha256"]:
        raise ValueError("Receiver metadata source hash differs from saved model")

command = ["c++","-O3","-std=c++17","-Wall","-Wextra","-Wpedantic","-fopenmp",
           "-I",str(BUILD),str(source),"-o",str(binary),"-lstdc++fs"]
subprocess.check_call(command,cwd=str(ROOT))
output_path = OUT / "results.csv"
subprocess.check_call([str(binary),str(grid_path),str(input_path),str(output_path),"0.5"],cwd=str(ROOT))
outputs = read(output_path)
by_index = {r["observation_index"]:r for r in outputs}
if len(outputs) != len(inputs) or len(by_index) != len(inputs):
    raise ValueError("Ray count or unique observation mapping changed")
for before in inputs:
    after = by_index[before["observation_index"]]
    if any(after[k] != v for k,v in before.items()):
        raise ValueError("Original ray metadata changed")
    if float(after["selected_outside_nodes"]):
        raise ValueError("Selected ray violates the model domain")
    if float(after["action_reduction_s"]) < 0:
        raise ValueError("Candidate selection increased the action")
files = [source,ROOT/"diagnostics/first_arrival_fmm.hpp",ROOT/"src/first_arrival.hpp",
         ROOT/"src/forward.hpp",ROOT/"diagnostics/seeded_bending.py",
         ROOT/"src/main.cpp",ROOT/"src/core.hpp",ROOT/"src/ray_checks.hpp",ROOT/"src/csv.hpp",
         Path(__file__).resolve(),header,binary,input_path,grid_path,events_path,stations_path,output_path]
summary = {
    "purpose":"Feasible path comparison at the saved DD model; no reinversion and no first-arrival certificate",
    "command":"python3 diagnostics/run_fmm_hayward_audit.py",
    "selection":"Every saved absolute ray whose final-DD source and receiver depths are both within [-1,0] km",
    "ray_count":len(outputs),
    "all_input_columns_and_native_identities_preserved":True,
    "auxiliary_spacing_km":0.5,"path_spacing_km":0.5,
    "extraction_failures":sum(r["extracted"]!="1" for r in outputs),
    "selected_nonconverged":sum(r["selected_converged"]!="1" for r in outputs),
    "exact_endpoint_check_failures":sum(float(r["selected_endpoint_error_km"])!=0 for r in outputs),
    "maximum_endpoint_error_km":max(float(r["selected_endpoint_error_km"]) for r in outputs),
    "maximum_action_reduction_s":max(float(r["action_reduction_s"]) for r in outputs),
    "rays_with_action_reduction_over_1_ms":sum(float(r["action_reduction_s"])>0.001 for r in outputs),
    "limitations":["First-order FMM missed known near-crossover branches in the independent analytic audit.",
                   "A smaller feasible action disproves optimality of a prior path; agreement does not prove a first arrival.",
                   "Source derivative comparisons require stationarity and path refinement.",
                   "Nonzero endpoint discrepancies from the original direct-path arithmetic remain recorded failures, even when at roundoff scale.",
                   "This targeted shallow-endpoint set is not representative of all field rays."],
    "sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
}
(OUT/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
print(json.dumps(summary,indent=2))
raise SystemExit(1 if summary["selected_nonconverged"] or summary["extraction_failures"]
                 or summary["exact_endpoint_check_failures"] else 0)
