#!/usr/bin/env python3
"""Summarize the preserved, controlled FMM experiments without changing them."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/development"
NAMES = ["audit", "order1_control", "order2_baseline", "order1_closed", "order2_closed",
         "refinement", "order2_refinement", "order1_closed_refinement", "order2_closed_refinement"]


def read_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    comparisons = []
    input_hashes = {}
    all_rows = {}
    for name in NAMES:
        folder = DATA / ("fmm_initialization_" + name)
        summary = json.loads((folder / "summary.json").read_text())
        rows = read_rows(folder / "results.csv")
        checks = read_rows(folder / "consistency.csv")
        all_rows[name] = rows
        assert len(rows) == summary["cases"] and len(checks) == summary["checks"]
        assert [r for r in checks if r["passed"] != "1"] == summary["failed_checks"]
        aux = min(float(r["auxiliary_spacing_km"]) for r in rows)
        path = min(float(r["path_spacing_km"]) for r in rows)
        finest = [r for r in rows if r["case"] == "constant_top_gradient" and
                  float(r["auxiliary_spacing_km"]) == aux and float(r["path_spacing_km"]) == path]
        # In this specified flat-top test, a selected path staying at z=-0.5
        # is the direct branch. This is not a classifier for arbitrary models.
        missed = [float(r["distance_km"]) for r in finest if r["reference_branch"] == "diving" and
                  float(r["maximum_depth_km"]) == -0.5]
        comparisons.append({
            "variant": name,
            "order": summary.get("order", 1),
            "closed_seed_cells": summary.get("closed_seed_cells", False),
            "cases": len(rows), "checks": len(checks), "failed_checks": len(summary["failed_checks"]),
            "extraction_failures": len(summary["extraction_failures"]),
            "selected_nonconverged": len(summary["selected_nonconverged"]),
            "finest_auxiliary_spacing_km": aux, "finest_path_spacing_km": path,
            "finest_missed_diving_branch_offsets_km": missed,
            "strict_nonzero_endpoint_errors": sum(float(r["endpoint_error_km"]) != 0 for r in rows),
            "maximum_endpoint_error_km": max(float(r["endpoint_error_km"]) for r in rows),
            "paths_with_outside_nodes": sum(float(r["outside_nodes"]) != 0 for r in rows),
            "finest_flat_layer_results": [{key: r[key] for key in (
                "distance_km", "selected", "time_error_s", "source_error_s_per_km", "maximum_depth_km")}
                for r in finest],
        })
        for basename in ("summary.json", "results.csv", "consistency.csv", "paths.csv"):
            p = folder / basename
            input_hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    original, control = all_rows["audit"], all_rows["order1_control"]
    same_results = len(original) == len(control) and all(
        a[k] == b[k] for a, b in zip(original, control) for k in a if k not in ("field_seconds", "ray_seconds"))
    same_checks = read_rows(DATA / "fmm_initialization_audit/consistency.csv") == read_rows(
        DATA / "fmm_initialization_order1_control/consistency.csv")
    same_paths = read_rows(DATA / "fmm_initialization_audit/paths.csv") == read_rows(
        DATA / "fmm_initialization_order1_control/paths.csv")
    result = {
        "purpose": "Separate switched stencil order, exact-grid source seeding, and field/path refinement.",
        "real_observations_used": False,
        "production_solver_changed": False,
        "command": "PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/compare_fmm_orders.py",
        "variants": comparisons,
        "historical_control": {"equal_non_timing_results": same_results,
                               "equal_gate_rows": same_checks, "equal_path_rows": same_paths},
        "limitations": [
            "The retained accuracy gates do not include strict bitwise endpoint equality; discrepancies are reported separately.",
            "Coarse experiments have 61 gates; refinement has 37 because homogeneous checks were not repeated.",
            "Only listed offsets were tested; these are finite-case checks, not a general first-arrival certificate.",
            "Second-order stencils and source initialization do not establish a globally second-order convergence rate.",
            "No field inversion uses this prototype."],
        "input_sha256": input_hashes,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    target = DATA / "fmm_order_comparison.json"
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for row in comparisons:
        print(row["variant"], "failed gates", row["failed_checks"], "of", row["checks"],
              "missed offsets", row["finest_missed_diving_branch_offsets_km"],
              "nonzero endpoint errors", row["strict_nonzero_endpoint_errors"])
    assert same_results and same_checks and same_paths


if __name__ == "__main__":
    main()
