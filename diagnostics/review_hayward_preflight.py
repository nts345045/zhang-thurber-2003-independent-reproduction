#!/usr/bin/env python3
"""Archive and independently inspect a terminal identified Hayward preflight."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data, out = [(ROOT / name).resolve() for name in (args.data, args.output)]
    for path in (data, out): path.relative_to(ROOT)
    if out.exists(): raise ValueError("Preserve prior audit evidence")
    manifest = json.loads((data / "run_manifest.json").read_text())
    preflight = json.loads((data / "preflight.json").read_text())
    ledger = json.loads((data / "preflight_execution.json").read_text())
    if ledger["status"] not in ("failed_checks_preserved", "ready_for_accuracy_review"):
        raise ValueError("Preflight is not terminal")
    if ledger["status"] != preflight["status"]:
        raise ValueError("Terminal ledger/preflight statuses disagree")
    for stage in ("initial_linearize", "initial_raycheck"):
        matching = [c for c in ledger["completed_commands"] if c["stage"] == stage]
        if len(matching) != 1 or matching[0]["return_code"] != 0:
            raise ValueError("Incomplete numerical export stage: " + stage)
    verified = {}
    for name, digest in manifest["sha256"].items():
        path = ROOT / name
        if sha(path) != digest: raise ValueError("Changed frozen run input: " + name)
        verified[name] = digest
    for name, digest in preflight["sha256"].items():
        path = data / name
        if sha(path) != digest: raise ValueError("Changed preflight table: " + name)
        verified[str(path.relative_to(ROOT))] = digest
    with tarfile.open(str(data / "source_snapshot.tar.gz")) as archive:
        for name, digest in manifest["source_sha256"].items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest() != digest:
                raise ValueError("Changed frozen source: " + name)
    rows = read(data / "initial_linearization_rows.csv")
    events = read(data / "initial_events.csv")
    stations = read(data / "stations.csv")
    observations = read(data / "observations.csv")
    grid = read(data / "initial_grid.csv")
    expected = {str(q): r for q, r in enumerate(observations) if int(r["type"]) == 0}
    if len(rows) != len(expected) or {r["observation_row"] for r in rows} != set(expected):
        raise ValueError("Incomplete absolute support")
    pairs = {(int(r["i"]), int(r["station"])) for r in observations}
    pairs.update((int(r["j"]), int(r["station_j"])) for r in observations if int(r["j"]) >= 0)
    if pairs != {(int(r["i"]), int(r["station"])) for r in rows}:
        raise ValueError("Absolute support does not cover all differential endpoints")
    for q, row in enumerate(rows):
        if int(row["row"]) != q: raise ValueError("Nonconsecutive linearization rows")
        original = expected[row["observation_row"]]
        for key, value in original.items():
            if key not in ("j", "type", "value") and row[key] != value:
                raise ValueError("Changed native observation metadata")
        if float(row["observed"]) != float(format(float(original["value"]), ".12g")):
            raise ValueError("Changed observed value")
        for key in ("ray_time", "ray_projected_gradient", "ray_raw_gradient", "predicted", "residual"):
            if not math.isfinite(float(row[key])): raise ValueError("Nonfinite identified ray")
    columns = read(data / "initial_linearization_columns.csv")
    ns = 4 * len(events)
    if len(columns) != ns + len(grid): raise ValueError("Wrong parameter count")
    sums, origins, entries = [0.] * len(rows), collections.Counter(), 0
    seen = set()
    with (data / "initial_linearization_matrix.csv").open() as stream:
        for entry in csv.DictReader(stream):
            q, column, value = int(entry["row"]), int(entry["column"]), float(entry["value"])
            if not 0 <= q < len(rows) or not 0 <= column < len(columns) or not math.isfinite(value):
                raise ValueError("Invalid matrix entry")
            if (q, column) in seen: raise ValueError("Duplicate absolute derivative entry")
            seen.add((q, column)); entries += 1
            if column < ns:
                base = 4 * int(rows[q]["i"])
                if not base <= column < base + 4: raise ValueError("Wrong source block")
                if column == base + 3:
                    if value != 1: raise ValueError("Nonunit origin derivative")
                    origins[q] += 1
            else: sums[q] += value
    if any(origins[q] != 1 for q in range(len(rows))): raise ValueError("Missing origin derivative")
    maximum_sum_error = max(abs(sums[q] - float(r["ray_time"])) for q, r in enumerate(rows))
    if maximum_sum_error > 1e-8:
        raise ValueError("Absolute log-slowness kernel sum differs from action beyond serialization scale")
    bad = [r for r in rows if r["ray_converged"] != "1"]
    if len(preflight["failures"]) != len(bad) or any(not f.startswith("Failed initial ray at identified linearization row ") for f in preflight["failures"]):
        raise ValueError("This grouping expects only identified full-support stopping failures")
    bounds = {axis: (min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)) for axis in "xyz"}
    endpoint_counts = collections.Counter()
    identified = []
    for row in bad:
        result = dict(row)
        for prefix, records, key in (("source", events, "i"), ("receiver", stations, "station")):
            native = records[int(row[key])]
            for name, value in native.items(): result[prefix + "_" + name] = value
            for axis, limits in bounds.items():
                value = float(native[axis])
                result[prefix + "_" + axis + "_outer_bound"] = int(value in limits)
                endpoint_counts[prefix + "_" + axis + "_outer_bound"] += value in limits
                endpoint_counts[prefix + "_" + axis + "_within_1e-8_km"] += min(abs(value - b) for b in limits) <= 1e-8
        identified.append(result)
    out.mkdir(parents=True)
    write(out / "failed_rays.csv", identified)
    for key, records, filename in (("i", events, "failures_by_event.csv"),
                                   ("station", stations, "failures_by_native_epoch.csv")):
        failed = collections.Counter(r[key] for r in bad)
        total = collections.Counter(r[key] for r in rows)
        grouped = [dict(records[int(k)], failed_rays=n, total_rays=total[k])
                   for k, n in sorted(failed.items(), key=lambda x: (-x[1], int(x[0])))]
        write(out / filename, grouped)
    failed_channels = collections.Counter(stations[int(r["station"])]["channel_seed_id"] for r in bad)
    all_channels = collections.Counter(stations[int(r["station"])]["channel_seed_id"] for r in rows)
    write(out / "failures_by_channel.csv", [dict(channel_seed_id=k,
         channel_fdsn_source_id=next(s["channel_fdsn_source_id"] for s in stations if s["channel_seed_id"] == k),
         failed_rays=n, total_rays=all_channels[k]) for k, n in failed_channels.most_common()])
    for name in ("run_manifest.json", "preflight.json", "preflight_execution.json", "run.cfg", "source_snapshot.tar.gz"):
        shutil.copyfile(str(data / name), str(out / name))
    def normalize(info):
        info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ""; info.pax_headers = {}
        return info
    table_names = sorted(preflight["sha256"])
    with tarfile.open(str(out / "terminal_tables.tar.gz"), "w:gz") as archive:
        for name in table_names: archive.add(str(data / name), arcname=name, filter=normalize)
    sample = read(data / "initial_ray_convergence.csv")
    derivative = read(data / "initial_ray_derivatives.csv")
    all_sample_flags = all(r[k] == "1" for r in sample for k in
        ("production_converged", "refined_converged", "production_initialization_succeeded", "refined_initialization_succeeded"))
    all_perturbation_flags = all(r[k] == "1" for r in derivative for k in
        ("plus_converged", "minus_converged", "plus_initialization_succeeded", "minus_initialization_succeeded"))
    review = {
        "status": "terminal_preflight_failed_no_inversion_authorized", "recorded_driver_return_code": ledger["return_code"],
        "completed_child_codes": {c["stage"]: c["return_code"] for c in ledger["completed_commands"]},
        "full_rays": len(rows), "nonconverged_rays": len(bad),
        "initializers_succeeded": sum(r["ray_initialization_succeeded"] == "1" for r in rows),
        "failed_events": len(set(r["i"] for r in bad)),
        "failed_native_epochs": len(set(r["station"] for r in bad)), "failed_channels": len(failed_channels),
        "failed_iteration_counts": dict(collections.Counter(r["ray_iterations"] for r in bad)),
        "maximum_projected_gradient_s_per_km": max(float(r["ray_projected_gradient"]) for r in rows),
        "endpoint_outer_bounds": dict(endpoint_counts),
        "sample_rays": len(sample), "all_sample_local_and_initializer_flags_pass": all_sample_flags,
        "source_derivative_components": len(derivative), "all_perturbation_flags_pass": all_perturbation_flags,
        "max_sample_time_refinement_s": max(abs(float(r["difference"])) for r in sample),
        "max_source_component_vs_refined_fd_s_per_km": max(abs(float(r["production_error"])) for r in derivative),
        "absolute_matrix_entries": entries, "absolute_origin_columns_verified": len(origins),
        "maximum_absolute_kernel_sum_vs_time_s": maximum_sum_error,
        "verified_input_sha256": verified,
        "artifact_sha256": {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
        "review_source_sha256": sha(Path(__file__)),
        "limitations": ["Passing the 32-ray sample does not establish convergence on the full observation support.",
                        "No endpoint lies on an outer bound in the failed subset; saved tables do not reveal whether interior ray knots contact bounds or grid interfaces.",
                        "Local stopping failure is preserved. This review alone does not establish travel-time/derivative error or its cause.",
                        "The kernel-sum check is an implementation/serialization identity, not a first-arrival accuracy test.",
                        "Independent reference and optimizer experiments are separate evidence; no inversion was launched from this failed preflight."],
    }
    (out / "review.json").write_text(json.dumps(review, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in review.items() if k not in ("verified_input_sha256", "artifact_sha256", "limitations")}, indent=2))


if __name__ == "__main__":
    main()
