#!/usr/bin/env python3
"""Compare saved initial rays with the independent 1D reference, preserving IDs.

No provider requests, production ray tracing, inversion, or input edits occur.
"""
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "diagnostics"))
from first_arrival_1d_reference import enumerate_arrivals

OUT = Path(__file__).resolve().parent
DATA = ROOT / "data/hayward"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    with (DATA / name).open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Duplicate CSV headers: " + name)
    return reader.fieldnames, rows


def unique(rows, field):
    result = {r[field]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError("Nonunique explicit index: " + field)
    return result


def stats(values):
    return dict(count=len(values), minimum=min(values), maximum=max(values),
                median=statistics.median(values), mean=sum(values) / len(values),
                rms=math.sqrt(sum(v * v for v in values) / len(values)),
                maximum_absolute=max(abs(v) for v in values)) if values else None


def main():
    names = ["initial_events.csv", "stations.csv", "initial_grid.csv", "initial_ray_convergence.csv",
             "initial_ray_identifiers.csv", "initial_ray_derivatives.csv", "run_manifest.json"]
    files = [DATA / name for name in names] + [ROOT / "data/development/hayward_initial_ray_summary.json",
             ROOT / "diagnostics/first_arrival_1d_reference.py", Path(__file__).resolve(), OUT / "checks.json"]
    hashes = {str(p.relative_to(ROOT)):digest(p) for p in files}
    manifest = json.loads((DATA / "run_manifest.json").read_text())
    prior = json.loads((ROOT / "data/development/hayward_initial_ray_summary.json").read_text())
    for name in ["initial_events.csv", "stations.csv", "initial_grid.csv"]:
        key = str((DATA / name).relative_to(ROOT))
        if hashes[key] != manifest["sha256"][key]:
            raise ValueError("Saved geometry differs from run manifest: " + key)
    for item in prior["source_files"]:
        if item["path"] in hashes and hashes[item["path"]] != item["sha256"]:
            raise ValueError("Saved initial diagnostic changed: " + item["path"])
    _, event_rows = read("initial_events.csv")
    _, station_rows = read("stations.csv")
    _, grid = read("initial_grid.csv")
    conv_fields, convergence = read("initial_ray_convergence.csv")
    identity_fields, identities = read("initial_ray_identifiers.csv")
    derivative_fields, derivatives = read("initial_ray_derivatives.csv")
    events, stations = unique(event_rows, "id"), unique(station_rows, "id")
    rays = unique(convergence, "diagnostic_row")
    levels = sorted(set((float(r["z"]), float(r["v"])) for r in grid))
    if len(levels) != len(set(z for z, v in levels)):
        raise ValueError("Saved initial grid is not one dimensional")
    depths, speeds = map(list, zip(*levels))
    associations = {key: [] for key in rays}
    for row in identities:
        ray = rays[row["diagnostic_row"]]
        if any(row[key] != ray[key] for key in ("event", "station")):
            raise ValueError("Explicit diagnostic/ray indices disagree")
        source, receiver = events[row["event"]], stations[row["station"]]
        for prefix, native in [("source_", source), ("receiver_", receiver)]:
            for key, value in native.items():
                if key not in ("id", "x", "y", "z", "t") and row[prefix + key] != value:
                    raise ValueError("Native identity/metadata mismatch: " + prefix + key)
        side = row["observation_event_side"]
        if side not in ("i", "j"):
            raise ValueError("Unknown observation event side")
        for kind in ("event", "origin"):
            if row["observation_" + kind + "_" + side + "_resource_id"] != source[kind + "_resource_id"]:
                raise ValueError("Observation side does not identify the source")
        for key in ("channel_seed_id", "channel_fdsn_source_id"):
            if row["observation_" + key] != receiver[key]:
                raise ValueError("Observation and native receiver channel differ")
        for bound in ("start", "end"):
            key = "metadata_epoch_" + ("j_" if side == "j" else "") + bound
            if row["observation_" + key] != receiver["metadata_epoch_" + bound]:
                raise ValueError("Observation side and native receiver epoch differ")
        if side == "j" and int(row["observation_station_j"]) >= 0 and row["observation_station_j"] != row["station"]:
            raise ValueError("Explicit second receiver index differs")
        associations[row["diagnostic_row"]].append(row)
    if not all(associations.values()):
        raise ValueError("A saved ray has no identity association")
    derivative_map = {}
    for row in derivatives:
        ray = rays[row["diagnostic_row"]]
        if any(row[key] != ray[key] for key in ("event", "station")) or row["axis"] not in ("0", "1", "2"):
            raise ValueError("Derivative indices disagree with explicit ray mapping")
        key = row["diagnostic_row"], row["axis"]
        if key in derivative_map:
            raise ValueError("Duplicate derivative component")
        derivative_map[key] = row
    records, extra = [], {}
    time_errors, refined_errors, gradient_errors = [], [], []
    for key, ray in rays.items():
        event, station = events[ray["event"]], stations[ray["station"]]
        source = [float(event[k]) for k in ("x", "y", "z")]
        receiver = [float(station[k]) for k in ("x", "y", "z")]
        reference = enumerate_arrivals(depths, speeds, source, receiver)
        first = reference.get("first_arrival")
        item = {name: ray[name] for name in conv_fields if name not in identity_fields}
        item.update(reference_complete=int(reference["complete"]), reference_valid=int(reference["reference_valid"]),
                    reference_unresolved_json=json.dumps(reference["unresolved"], separators=(",", ":")),
                    reference_candidate_count=len(reference["candidates"]),
                    reference_time_s=first["time_s"] if first else "",
                    reference_branch=first["kind"] if first else "",
                    reference_turning_depth_km=first["turning_depth_km"] if first and first["turning_depth_km"] is not None else "",
                    reference_near_tie_count=len(reference.get("near_ties", [])),
                    production_minus_reference_s=float(ray["production_time"]) - first["time_s"] if first else "",
                    refined_minus_reference_s=float(ray["refined_time"]) - first["time_s"] if first else "",
                    preserved_metadata_path_base="data/hayward")
        if first:
            time_errors.append(item["production_minus_reference_s"])
            refined_errors.append(item["refined_minus_reference_s"])
        for axis, letter in enumerate("xyz"):
            item["source_" + letter + "_km"] = source[axis]
            item["receiver_" + letter + "_km"] = receiver[axis]
            item["reference_source_d" + letter] = first["source_derivative_s_per_km"][axis] if first else ""
            saved = derivative_map.get((key, str(axis)))
            for column in derivative_fields:
                if column not in ("diagnostic_row", "event", "station", "axis"):
                    item["saved_initial_" + letter + "_" + column] = saved[column] if saved else ""
            for mode in ("production", "refined"):
                error = float(saved[mode + "_derivative"]) - first["source_derivative_s_per_km"][axis] if saved and first else ""
                item[mode + "_source_d" + letter + "_minus_reference"] = error
                if mode == "production" and error != "":
                    gradient_errors.append(error)
        extra[key] = item
        identity = associations[key][0]
        records.append(dict(diagnostic_row=key, event=ray["event"], station=ray["station"],
                            identities={k: identity[k] for k in identity_fields if k.startswith("source_") or k.startswith("receiver_")},
                            source_xyz_km=source, receiver_xyz_km=receiver,
                            saved_convergence=ray, saved_derivatives=[r for (d, a), r in derivative_map.items() if d == key],
                            reference=reference, comparison=item))
    combined = [dict(row, **extra[row["diagnostic_row"]]) for row in identities]
    output = OUT / "hayward_initial_comparison.csv"
    fields = identity_fields + list(extra[next(iter(extra))])
    if len(fields) != len(set(fields)):
        raise ValueError("Derived columns overwrite identity fields")
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(combined)
    with output.open() as f:
        saved = list(csv.DictReader(f))
    if len(saved) != len(identities) or any(any(a[k] != b[k] for k in identity_fields) for a, b in zip(identities, saved)):
        raise ValueError("Saved output altered original identity columns")
    for p in files:
        if digest(p) != hashes[str(p.relative_to(ROOT))]:
            raise ValueError("Input changed during comparison: " + str(p.relative_to(ROOT)))
    summary = dict(created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   command="PYTHONDONTWRITEBYTECODE=1 python3 data/development/first_arrival_1d_enumeration/compare_hayward_initial.py",
                   scope="Saved authoritative initial geometry and previously computed ray samples; no production rays rerun and no new observations retrieved",
                   explicit_join_keys=["diagnostic_row", "event", "station"],
                   native_source_receiver_metadata_verified=True, original_identity_columns_preserved=identity_fields,
                   input_files_unchanged=True, sha256=hashes, comparison_sha256=digest(output),
                   rays=len(rays), identity_associations=len(identities), saved_derivative_components=len(derivatives),
                   reference_complete=sum(r["reference"]["complete"] for r in records),
                   reference_valid=sum(r["reference"]["reference_valid"] for r in records),
                   production_minus_reference_s=stats(time_errors), refined_minus_reference_s=stats(refined_errors),
                   production_source_derivative_minus_reference_s_per_km=stats(gradient_errors),
                   production_later_over_1ms=sum(e > .001 for e in time_errors),
                   refined_later_over_1ms=sum(e > .001 for e in refined_errors),
                   production_later_over_25us=sum(e > .000025 for e in time_errors),
                   threshold_interpretation="Descriptive error counts, not a new field-data pass threshold or proof of a particular error mechanism",
                   limitations=["Only the existing 32-ray sample is compared, not all 14262 native source/receiver pairs.",
                                "A complete branch enumeration does not supply interval-certified ordering of nearly tied floating-point travel times; all near ties remain recorded.",
                                "Positive differences establish late numerical travel times relative to this continuous 1D reference; by themselves they do not separate branch selection, path discretization, and local optimization errors.",
                                "This comparison concerns the initial model only, not updated 3D inversion models.",
                                "Preserved provider-relative file paths retain their original data/hayward base; no metadata path is reinterpreted relative to this output directory."],
                   records=records)
    (OUT / "hayward_initial_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: summary[k] for k in ("rays", "identity_associations", "reference_complete", "reference_valid",
          "production_minus_reference_s", "refined_minus_reference_s", "production_later_over_1ms")}, indent=2))


if __name__ == "__main__":
    main()
