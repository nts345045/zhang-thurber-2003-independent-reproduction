#!/usr/bin/env python3
"""Invented native-ray input controls; no ray trace or field resolution."""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_table(path, rows, fields=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def fixture():
    events = [dict(id=str(i), x=str(i + .123456789012345), y="0", z="1", t="0",
                   event_resource_id="smi:invented/event/" + str(i),
                   origin_resource_id="smi:invented/origin/" + str(i),
                   note='comma, quote " and\nnewline') for i in range(3)]
    stations = []
    for i in range(2):
        stations.append(dict(id=str(i), x="12.3456789012345", y="-0.125", z="0", t="0",
            network_code="XX", station_code="MOCK", location_code="", channel_code="HHZ",
            channel_seed_id="XX.MOCK..HHZ", channel_fdsn_source_id="FDSN:XX_MOCK__H_H_Z",
            metadata_epoch_start=["2000-01-01", "2005-01-01"][i],
            metadata_epoch_end=["2005-01-01", ""][i], source_sha256="invented_metadata_document"))
    observations = [dict(i=str(i), j=str(j), station=str(k), type=str(kind), value="0",
                         station_j=str(second) if j >= 0 else "")
                    for i, j, k, kind, second in
                    [(0, -1, 0, 0, -1), (1, -1, 1, 0, -1), (0, 1, 0, 1, 1), (2, 0, 1, 1, 0)]]
    rows = [dict(i=r["i"], j=r["j"], station=r["station"], type=r["type"],
                 station_j_index=r["station_j"] or "-1", observation_row=str(i),
                 active="0" if i == 3 else "1") for i, r in enumerate(observations)]
    rays = []
    for i, k in [(0, 0), (1, 1), (2, 1)]:
        r = dict(event=str(i), station=str(k), ray_time="1", ray_projected_gradient="0",
                 ray_raw_gradient="0", ray_finite="1", ray_converged="1",
                 ray_initialization_attempted="1", ray_initialization_succeeded="1",
                 ray_direct_seed_time="1", ray_fmm_seed_time="1", ray_field_time="1")
        for prefix, native in [("source_", events[i]), ("receiver_", stations[k])]:
            for axis in "xyz": r[prefix + axis] = format(float(native[axis]), ".12g")
            r.update({prefix + name: value for name, value in native.items()
                      if name not in ("id", "x", "y", "z", "t")})
        rays.append(r)
    return dict(events=events, stations=stations, observations=observations, rows=rows,
                rays=rays, info=dict(observed_rays="3", ray_status_failures="0", observations="4"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve(); out.relative_to(ROOT)
    out.mkdir(); (out / "source").mkdir(); (out / "cases").mkdir()
    maintained = ROOT / "resolution_full_hayward.py"
    source_hash = sha(maintained)
    for source in (maintained, Path(__file__).resolve()):
        shutil.copyfile(str(source), str(out / "source" / source.name))
    spec = importlib.util.spec_from_file_location("ray_input_resolution", str(out / "source" / maintained.name))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original = fixture(); checks = []

    def case(name, mutate=None, accepted=False, csv_change=None):
        data = copy.deepcopy(original)
        if mutate: mutate(data)
        directory = out / "cases" / name; directory.mkdir()
        path = directory / "rays.csv"; save_table(path, data.pop("rays"))
        if csv_change: csv_change(path)
        (directory / "native_inputs.json").write_text(json.dumps(data, indent=2) + "\n")
        try:
            result = module.validate_exported_rays(path, **data)
        except ValueError as error:
            passed, actual, message = not accepted, "rejected", str(error)
            result = None
        else:
            passed, actual, message = accepted, "accepted", ""
        checks.append(dict(name=name, expected="accepted" if accepted else "rejected",
                           actual=actual, passed=passed, error=message, result=result))

    case("cross_epoch_blank_quoted_and_12_digit_metadata", accepted=True)
    case("ray_row_permutation", lambda d: d["rays"].reverse(), True)
    def unattempted(d):
        for r in d["rays"]:
            r.update(ray_initialization_attempted="0", ray_initialization_succeeded="0",
                     ray_direct_seed_time="nan", ray_fmm_seed_time="nan", ray_field_time="nan")
    case("unattempted_legacy_with_nonfinite_unused_seed_diagnostics", unattempted, True)
    def legacy(d):
        # An absent station_j column uses the first receiver on each DD side.
        for r in d["observations"]: r.pop("station_j")
        d["observations"] = d["observations"][:1] + [dict(i="2", j="0", station="0", type="1", value="0")]
        d["rows"] = [dict(i=r["i"], j=r["j"], station=r["station"], type=r["type"],
                           station_j_index="-1" if r["j"] == "-1" else r["station"])
                     for r in d["observations"]]
        d["rays"] = [d["rays"][0], d["rays"][2]]
        d["rays"][1]["station"] = "0"
        for key, value in d["stations"][0].items():
            if key not in ("id", "x", "y", "z", "t"): d["rays"][1]["receiver_" + key] = value
        d["info"]["observed_rays"] = "2"
    case("absent_station_j_legacy_fallback", legacy, True)
    case("missing_omitted_row_only_ray", lambda d: d["rays"].pop())
    case("duplicate_ray", lambda d: d["rays"].append(copy.deepcopy(d["rays"][0])))
    case("unexpected_pair", lambda d: d["rays"][2].update(station="0"))
    case("negative_ray_index", lambda d: d["rays"][0].update(event="-1"))
    case("out_of_range_observation", lambda d: d["observations"][0].update(i="3"))
    case("negative_observation_index", lambda d: d["observations"][0].update(i="-1"))
    case("nonconsecutive_event_id", lambda d: d["events"][0].update(id="7"))
    case("nonconsecutive_receiver_id", lambda d: d["stations"][1].update(id="0"))
    case("blank_present_station_j", lambda d: d["observations"][2].update(station_j=""))
    case("negative_present_station_j", lambda d: d["observations"][2].update(station_j="-1"))
    case("incorrect_second_epoch_index", lambda d: d["rows"][2].update(station_j_index="0"))
    case("cross_epoch_position_changed", lambda d: d["stations"][1].update(x="12.4"))
    for key in ("source_event_resource_id", "source_origin_resource_id", "source_note",
                "receiver_network_code", "receiver_station_code", "receiver_location_code",
                "receiver_channel_code", "receiver_channel_seed_id", "receiver_channel_fdsn_source_id",
                "receiver_metadata_epoch_start", "receiver_metadata_epoch_end", "receiver_source_sha256"):
        case("changed_" + key, lambda d, key=key: d["rays"][0].update({key: "changed"}))
    case("unrounded_receiver_coordinate", lambda d: d["rays"][0].update(receiver_x=d["stations"][0]["x"]))
    case("last_recorded_coordinate_digit_changed", lambda d: d["rays"][0].update(receiver_x="12.3456789013"))
    case("nonfinite_coordinate", lambda d: d["rays"][0].update(source_z="nan"))
    for key in ("ray_time", "ray_projected_gradient", "ray_raw_gradient"):
        for value in ("nan", "inf", "-1"):
            case("invalid_" + key + "_" + value, lambda d, key=key, value=value: d["rays"][0].update({key: value}))
    for key in ("ray_converged", "ray_finite", "ray_initialization_succeeded"):
        def failed(d, key=key):
            d["rays"][0][key] = "0"; d["info"]["ray_status_failures"] = "1"
        case("failed_" + key, failed)
    case("malformed_flag", lambda d: d["rays"][0].update(ray_converged="2"))
    case("stale_failure_count", lambda d: d["info"].update(ray_status_failures="1"))
    case("stale_ray_count", lambda d: d["info"].update(observed_rays="2"))
    def duplicate_header(path):
        text = path.read_text(); path.write_text(text.replace("event,station,", "event,event,", 1))
    case("duplicate_csv_header", csv_change=duplicate_header)
    def missing_field(path):
        rows = module.read(path)
        for r in rows: del r["ray_converged"]
        save_table(path, rows)
    case("missing_csv_column", csv_change=missing_field)
    def truncated_row(path):
        with path.open(newline="") as f: rows = list(csv.reader(f))
        rows[1].pop()
        with path.open("w", newline="") as f: csv.writer(f).writerows(rows)
    case("truncated_csv_row", csv_change=truncated_row)

    # Exercise the actual run entry before its column/observation or matrix work.
    d = copy.deepcopy(original); directory = out / "run_rejects_failed_ray"; directory.mkdir()
    d["rays"][0]["ray_converged"] = "0"; d["info"]["ray_status_failures"] = "1"
    for name, records in [("dd_events.csv", d["events"]), ("stations.csv", d["stations"]),
                          ("observations.csv", d["observations"]),
                          ("dd_grid.csv", [dict(x="0", y="0", z="0", v="6")]),
                          ("dd_full_linearization_rows.csv", d["rows"]),
                          ("dd_full_linearization_columns.csv", [dict(column=str(i)) for i in range(13)]),
                          ("dd_full_linearization_rays.csv", d["rays"]),
                          ("dd_full_linearization_info.csv", [dict(key=k, value=v) for k, v in d["info"].items()])]:
        save_table(directory / name, records)
    assembled = []
    def unexpected_assembly(*args, **kwargs):
        assembled.append(True); raise RuntimeError("Unexpected matrix assembly")
    module.triplet_matrix = unexpected_assembly
    try:
        module.run(directory, "dd")
    except ValueError as error:
        passed = str(error).startswith("Failed recorded local/initializer ray status:") and not assembled
    else: passed = False
    checks.append(dict(name="real_run_rejects_failed_ray_before_matrix_assembly", passed=passed))
    for suffix in (".csv", "_picks.csv", "_matrices.npz", "_manifest.json"):
        directory = out / ("existing_output_" + suffix.replace(".", "_")); directory.mkdir()
        path = directory / ("dd_full_resolution" + suffix); path.write_bytes(b"preserved invented evidence\n")
        before = sha(path)
        try: module.run(directory, "dd")
        except ValueError as error:
            passed = str(error).startswith("Preserve existing full-resolution output:") and sha(path) == before and not assembled
        else: passed = False
        checks.append(dict(name="preserve_existing_output" + suffix, passed=passed))
    directory = out / "existing_dangling_output"; directory.mkdir()
    path = directory / "dd_full_resolution.csv"; path.symlink_to("absent_invented_target")
    try: module.run(directory, "dd")
    except ValueError as error:
        passed = str(error).startswith("Preserve existing full-resolution output:") and path.is_symlink() and not assembled
    else: passed = False
    checks.append(dict(name="preserve_dangling_output_symlink", passed=passed))
    # The temporary symlink is a fixture operation, not part of the evidence inventory.
    path.unlink()
    checks.append(dict(name="maintained_source_unchanged", passed=sha(maintained) == source_hash))
    result = dict(status="passed" if all(c["passed"] for c in checks) else "failed", checks=checks,
        scope="Invented native records and malformed CSVs only; no ray trace, matrix solve or field data",
        command=sys.argv, source_sha256={p.name: sha(p) for p in (out / "source").iterdir()},
        artifacts_sha256={str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()},
        limitations=["No path/domain/exact-endpoint/source-partial fields exist in this exporter schema.",
                     "Passing recorded local flags does not certify first-arrival or final-model accuracy.",
                     "Unattempted initialization is explicitly allowed; unused seed diagnostics may be nonfinite."])
    (out / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(status=result["status"], checks=len(checks), failures=[c for c in checks if not c["passed"]]), indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
