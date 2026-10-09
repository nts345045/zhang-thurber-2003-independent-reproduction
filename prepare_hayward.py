#!/usr/bin/env python3
"""Prepare identified catalog observations; no network calls or invented picks."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from data.authoritative.hayward.acquire import horizontal_coordinates, parse_time

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "data/authoritative/hayward"
STATIONS = ROOT / "data/authoritative/stations"
OUT = ROOT / "data/hayward"


def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0])
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def epoch_key(row):
    return (row["channel_seed_id"], row["metadata_epoch_start"],
            row["metadata_epoch_end"])


def matches_epoch(pick, channel):
    t = parse_time(pick["pick_time_utc"])
    return (parse_time(channel["metadata_epoch_start"]) <= t and
            (not channel["metadata_epoch_end"] or
             t < parse_time(channel["metadata_epoch_end"])))


def prepare():
    if not json.loads((CATALOG / "pick_selection_manifest.json").read_text())["acquisition_complete"]:
        raise ValueError("Refusing an incomplete catalog pick acquisition")
    events = read(CATALOG / "selected_events.csv")
    picks = read(CATALOG / "picks_selected.csv")
    channels = read(STATIONS / "channel_epochs.csv")
    by_id = {r["event_resource_id"]: r for r in events}
    if len(by_id) != len(events):
        raise ValueError("Duplicate selected event resource ID")
    epochs = defaultdict(list)
    for row in channels:
        codes = [row[k] for k in ("network_code", "station_code", "location_code", "channel_code")]
        expected_seed = ".".join(codes)
        expected_fdsn = "FDSN:" + "_".join(codes[:3] + list(codes[3]))
        if row["channel_seed_id"] != expected_seed or row["channel_fdsn_source_id"] != expected_fdsn:
            raise ValueError("Channel SEED/FDSN identifiers disagree with provider naming codes")
        epochs[row["channel_seed_id"]].append(row)
    selected, excluded = [], []
    missing = []
    for pick in picks:
        channel_matches = [r for r in epochs[pick["channel_seed_id"]]
                           if matches_epoch(pick, r)]
        if len(channel_matches) != 1:
            missing.append(dict(pick, metadata_match_count=len(channel_matches),
                                metadata_issue="nonunique_or_missing_channel_epoch"))
            continue
        channel = channel_matches[0]
        if not channel["sensor_z_geoid_km"] or channel.get("vertical_coordinate_status", "").startswith("ambiguous"):
            missing.append(dict(pick, metadata_match_count=1,
                                metadata_issue="unresolved_receiver_vertical_coordinate"))
            continue
        if pick["channel_fdsn_source_id"] != channel["channel_fdsn_source_id"]:
            raise ValueError("Pick/channel FDSN source identifiers disagree")
        east, north, x, y = horizontal_coordinates(float(channel["latitude_deg"]),
                                                   float(channel["longitude_deg"]))
        z = float(channel["sensor_z_geoid_km"])
        origin = by_id[pick["event_resource_id"]]
        if origin["origin_resource_id"] != pick["origin_resource_id"]:
            raise ValueError("Selected origin changed between catalog and picks")
        travel = (parse_time(pick["pick_time_utc"]) -
                  parse_time(origin["origin_time_utc"])).total_seconds()
        sigma = float(pick["pick_uncertainty_s"])
        reasons = []
        if not (-35 <= x <= 35 and -30 <= y <= 30 and z <= 20):
            reasons.append("receiver_outside_horizontal_or_lower_model_boundary")
        if not math.isfinite(sigma) or sigma <= 0:
            reasons.append("nonpositive_or_nonfinite_uncertainty")
        if not math.isfinite(travel) or travel <= 0:
            reasons.append("nonpositive_or_nonfinite_pick_minus_origin")
        provider_weight = pick["arrival_time_weight"]
        if provider_weight and float(provider_weight) <= 0:
            reasons.append("provider_preferred_origin_association_has_nonpositive_weight")
        if reasons:
            excluded.append(dict(pick, exclusion_reasons=";".join(reasons)))
            continue
        selected.append(dict(pick=pick, channel=channel, x=x, y=y, z=z,
                             travel=travel, sigma=sigma))
    OUT.mkdir(parents=True, exist_ok=True)
    if missing:
        write(OUT / "unresolved_metadata.csv", missing)
        raise RuntimeError("Required channel metadata is missing or ambiguous; "
                           "stop for clarification, see unresolved_metadata.csv")

    # A preferred origin may associate multiple P picks with a single channel.
    # Keep the smallest reported uncertainty; break ties by provider pick ID.
    unique = {}
    for row in sorted(selected, key=lambda r: (r["sigma"], r["pick"]["pick_resource_id"])):
        key = (row["pick"]["event_resource_id"], epoch_key(row["channel"]))
        if key in unique:
            excluded.append(dict(row["pick"], exclusion_reasons="duplicate_event_channel_epoch"))
        else:
            unique[key] = row
    count = Counter(key[0] for key in unique)
    retained = {eid for eid, n in count.items() if n >= 8}
    for key, row in unique.items():
        if key[0] not in retained:
            excluded.append(dict(row["pick"], exclusion_reasons="event_has_fewer_than_eight_domain_picks"))
    kept = [r for key, r in unique.items() if key[0] in retained]
    if not kept:
        raise ValueError("No observations satisfy the declared selection")
    event_rows, receiver_rows = [], []
    indices = {}
    for event in sorted((by_id[e] for e in retained),
                        key=lambda r: (r["origin_time_utc"], r["event_resource_id"])):
        i = len(event_rows)
        indices[event["event_resource_id"]] = i
        row = dict(id=i, x=event["x_km"], y=event["y_km"],
                   z=event["geoid_depth_km"], t=0)
        row.update({"event_resource_id": event["event_resource_id"],
                    "origin_resource_id": event["origin_resource_id"],
                    "reference_origin_time_utc": event["origin_time_utc"],
                    "catalog_latitude_deg": event["latitude_deg"],
                    "catalog_longitude_deg": event["longitude_deg"],
                    "catalog_geoid_depth_km": event["geoid_depth_km"],
                    "magnitude_resource_id": event["magnitude_resource_id"],
                    "catalog_magnitude": event["magnitude"],
                    "catalog_magnitude_type": event["magnitude_type"],
                    "origin_resource_id_basis": "provider reference origin; t is a correction in seconds",
                    "source_file": "../authoritative/hayward/" + event["source_file"],
                    "source_sha256": event["source_sha256"]})
        event_rows.append(row)
    receivers = {epoch_key(r["channel"]): r for r in kept}
    receiver_index = {}
    for key in sorted(receivers):
        source = receivers[key]
        k = len(receiver_rows)
        receiver_index[key] = k
        row = dict(id=k, x=source["x"], y=source["y"], z=source["z"], t=0)
        row.update(source["channel"])
        row["source_file"] = "../authoritative/stations/" + source["channel"]["source_file"]
        receiver_rows.append(row)
    by_event = defaultdict(dict)
    for row in kept:
        i = indices[row["pick"]["event_resource_id"]]
        k = receiver_index[epoch_key(row["channel"])]
        by_event[i][k] = row

    def datum(i, j, k):
        a = by_event[i][k]
        b = by_event[j][k] if j >= 0 else None
        sigma = math.hypot(a["sigma"], b["sigma"]) if b else a["sigma"]
        row = dict(i=i, j=j, station=k, type=int(j >= 0),
                   value=a["travel"] - (b["travel"] if b else 0))
        for side, item in (("i", a), ("j", b)):
            for kind in ("event", "origin", "arrival", "pick"):
                row[kind + "_" + side + "_resource_id"] = item["pick"][kind + "_resource_id"] if item else ""
            row["pick_" + side + "_time_utc"] = item["pick"]["pick_time_utc"] if item else ""
            row["pick_" + side + "_uncertainty_s"] = item["sigma"] if item else ""
            row["pick_" + side + "_uncertainty_confidence_level"] = item["pick"]["pick_uncertainty_confidence_level"] if item else ""
            row["pick_" + side + "_source_sha256"] = item["pick"]["source_sha256"] if item else ""
        for key in ("network_code", "station_code", "location_code", "channel_code",
                    "channel_seed_id", "channel_fdsn_source_id", "metadata_epoch_start",
                    "metadata_epoch_end"):
            row[key] = a["channel"][key]
        row["channel_source_sha256"] = a["channel"]["source_sha256"]
        row["uncertainty_s"] = sigma
        row["a_priori_weight"] = 0.05 / sigma
        row["observation_basis"] = "catalog P pick difference" if b else "catalog P pick minus reference origin"
        return row

    observations = [datum(i, -1, k) for i in range(len(event_rows))
                    for k in sorted(by_event[i])]
    positions = np.array([[float(e[key]) for key in ("x", "y", "z")] for e in event_rows])
    candidates = []
    for i in range(len(event_rows)):
        distances = np.linalg.norm(positions[i + 1:] - positions[i], axis=1)
        for offset in np.flatnonzero(distances < 10):
            j = i + 1 + int(offset)
            common = sorted(set(by_event[i]).intersection(by_event[j]))
            if len(common) >= 8:
                candidates.append((float(distances[offset]), i, j, common))
    # An undirected greedy degree cap is explicit and deterministic. It does
    # not guarantee one connected component or duplicate the authors' pairing.
    degree = Counter()
    pairs = []
    for distance, i, j, common in sorted(candidates):
        if degree[i] >= 10 or degree[j] >= 10:
            continue
        degree[i] += 1
        degree[j] += 1
        for k in common:
            observations.append(datum(i, j, k))
        pairs.append(dict(i=i, j=j, distance_km=distance, common_channels=len(common),
                          event_i_resource_id=event_rows[i]["event_resource_id"],
                          event_j_resource_id=event_rows[j]["event_resource_id"],
                          origin_i_resource_id=event_rows[i]["origin_resource_id"],
                          origin_j_resource_id=event_rows[j]["origin_resource_id"]))
    parent = list(range(len(event_rows)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for p in pairs:
        parent[find(p["i"])] = find(p["j"])
    components = Counter(find(i) for i in range(len(event_rows)))
    top = min(-1., math.floor(min(float(r["z"]) for r in receiver_rows)))
    xaxis = [-35, -20, -10, -5, -4, -3, 0, 5, 10, 20, 35]
    yaxis = [-30, -20, -10, 0, 10, 20, 30]
    zaxis = [top, 0, 4, 8, 12, 20]
    # Continuous-gradient adaptation of the written W&E2002 Table1 layers,
    # sampled on the target grid. This is not the original layered ray model.
    profile_z = [0, 1, 3, 6, 14, 25]
    profile_v = [3.77, 4.64, 5.34, 5.75, 6.22, 7.98]
    grid = [dict(x=x, y=y, z=z, v=float(np.interp(z, profile_z, profile_v)))
            for z in zaxis for y in yaxis for x in xaxis]
    write(OUT / "initial_events.csv", event_rows)
    write(OUT / "stations.csv", receiver_rows)
    write(OUT / "observations.csv", observations)
    write(OUT / "initial_grid.csv", grid)
    write(OUT / "event_pairs.csv", pairs,
          ["i", "j", "distance_km", "common_channels", "event_i_resource_id",
           "event_j_resource_id", "origin_i_resource_id", "origin_j_resource_id"])
    fields = list(picks[0]) + (["exclusion_reasons"] if "exclusion_reasons" not in picks[0] else [])
    write(OUT / "excluded_picks.csv", excluded, fields)
    event_audit = [dict(event_resource_id=e["event_resource_id"],
                        origin_resource_id=e["origin_resource_id"],
                        retained_domain_pick_count=count[e["event_resource_id"]],
                        selected=int(e["event_resource_id"] in retained)) for e in events]
    write(OUT / "event_selection.csv", event_audit)
    (OUT / "authoritative_ids_required").write_text("Provider IDs and SEED/FDSN channel epochs are mandatory.\n")
    manifest = {
        "dataset_status": "independently selected authoritative observations; manuscript cohort unidentified",
        "events_before_domain_pick_selection": len(events), "events": len(event_rows),
        "physical_station_codes": len(set(r["station_seed_id"] for r in receiver_rows)),
        "channels": len(set(r["channel_seed_id"] for r in receiver_rows)),
        "channel_epochs": len(receiver_rows),
        "observations_by_type": dict(Counter(r["type"] for r in observations)),
        "excluded_picks": len(excluded),
        "pick_exclusions_nonexclusive": dict(Counter(reason for r in excluded for reason in r["exclusion_reasons"].split(";"))),
        "pair_candidate_count": len(candidates), "event_pairs": len(pairs),
        "maximum_event_degree": max(degree.values()) if degree else 0,
        "unlinked_events": sum(degree[i] == 0 for i in range(len(event_rows))),
        "pair_graph_component_sizes": sorted(components.values(), reverse=True),
        "pairing": "ascending 3D catalog distance <10km; >=8 common channel epochs; undirected degree <=10",
        "epoch_interval": "start inclusive, end exclusive",
        "minimum_absolute_picks_per_event": 8,
        "provider_association_weight_policy": "exclude known nonpositive weights; positive provider weights are retained as provenance, not multiplied again into inverse-uncertainty weights",
        "uncertainty_weight": "0.05s/sigma; difference sigma=sqrt(sigma_i^2+sigma_j^2); correlations among differences are not whitened",
        "uncertainty_interpretation": "reported symmetric uncertainty is interpreted as independent one-standard-deviation picking noise for conditional propagation; the selected provider records do not supply confidence levels or establish this calibration",
        "grid_km": {"x": xaxis, "y": yaxis, "z": zaxis},
        "starting_model": {
            "source": "https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2000JB000084",
            "table": 1, "layer_top_depth_km": profile_z, "vp_km_s": profile_v,
            "adaptation": "linear interpolation of table values then sampling at grid depths; constant above z=0; geoid depth used without undocumented datum conversion",
        },
        "manuscript_counts": {"events": 1489, "stations": 52,
                              "absolute_p": 20257, "catalog_differences": 767127,
                              "waveform_differences": 17955},
        "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (CATALOG / "selected_events.csv", CATALOG / "picks_selected.csv",
                             STATIONS / "channel_epochs.csv")},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (OUT / "selection_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: manifest[k] for k in ("events", "physical_station_codes",
                     "channel_epochs", "observations_by_type", "event_pairs",
                     "unlinked_events", "pair_graph_component_sizes")}, indent=2))


if __name__ == "__main__":
    prepare()
