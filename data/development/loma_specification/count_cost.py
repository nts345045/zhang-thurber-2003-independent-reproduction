#!/usr/bin/env python3
"""Count the current generator's pairs and storage; generate no observations."""
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GEOMETRY = ROOT / "data/authoritative/loma_prieta"


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quoted_size(value):
    # Same quoting condition as src/csv.hpp; only byte counts are retained.
    return len(value.encode()) + (2 + value.count('"') if any(c in value for c in ',"\r\n') else 0)


def heap_size(value):
    # Lower bound for libstdc++ strings with 15-byte small-string storage.
    return len(value.encode()) + 1 if len(value.encode()) > 15 else 0


events = read(GEOMETRY / "selected_events.csv")
stations = read(GEOMETRY / "selected_channels.csv")
assert len({r["event_resource_id"] for r in events}) == len(events)
assert len({(r["channel_seed_id"], r["metadata_epoch_start"], r["metadata_epoch_end"])
            for r in stations}) == len(stations)
points = [tuple(float(r[k]) for k in ("x_km", "y_km", "geoid_depth_km")) for r in events]
degree = [0] * len(events)
pairs, closest = 0, float("inf")
pair_numeric_chars, pair_id_chars, pair_id_heap = 0, 0, 0
for i, point in enumerate(points):
    for j in range(i + 1, len(points)):
        distance = math.sqrt(sum((point[k] - points[j][k]) ** 2 for k in range(3)))
        closest = min(closest, abs(distance - 20))
        if distance < 20:  # Exact src/main.cpp generator condition, no neighbor cap.
            pairs += 1
            degree[i] += 1
            degree[j] += 1
            pair_numeric_chars += len(str(i)) + len(str(j))
            ids = [events[e][kind + "_resource_id"] for e in (i, j) for kind in ("event", "origin")]
            pair_id_chars += sum(quoted_size(v) for v in ids)
            pair_id_heap += sum(heap_size(v) for v in ids)

station_keys = ["network_code", "station_code", "location_code", "channel_code",
                "channel_seed_id", "channel_fdsn_source_id", "metadata_epoch_start", "metadata_epoch_end"]
common = ["1", "catalog-defined simulation truth", "zero for every truth event; no observed pick times",
          "truth_events.csv", "stations.csv"]
bases = ["synthetic noisy absolute travel time", "synthetic difference of noisy absolute travel times",
         "synthetic difference of rounded noise-free travel times"]
metadata_keys = [kind + "_" + side + "_resource_id" for side in ("i", "j") for kind in ("event", "origin")]
metadata_keys += station_keys + ["synthetic_observation", "observation_basis", "source_position_basis",
                               "simulation_origin_time_basis", "event_geometry_table", "receiver_geometry_table"]
station_chars = sum(sum(quoted_size(r[k]) for k in station_keys) for r in stations)
station_heap = sum(sum(heap_size(r[k]) for k in station_keys) for r in stations)
station_number_chars = sum(len(str(k)) for k in range(len(stations)))
abs_id_chars = sum(sum(quoted_size(r[k + "_resource_id"]) for k in ("event", "origin")) for r in events)
abs_id_heap = sum(sum(heap_size(r[k + "_resource_id"]) for k in ("event", "origin")) for r in events)
ne, ns = len(events), len(stations)
counts = [ne * ns, pairs * ns, pairs * ns]
fixed_bytes, value_heap = 0, 0
for typ, count in enumerate(counts):
    occurrences = ne if typ == 0 else pairs
    numbers = sum(len(str(i)) + 2 for i in range(ne)) if typ == 0 else pair_numeric_chars
    identities = abs_id_chars if typ == 0 else pair_id_chars
    identity_heap = abs_id_heap if typ == 0 else pair_id_heap
    # i,j,station,type,value plus 18 metadata fields: 22 commas and newline.
    fixed_bytes += ns * (numbers + identities) + occurrences * (station_number_chars + station_chars)
    fixed_bytes += count * (24 + sum(quoted_size(v) for v in common + [bases[typ]]))
    value_heap += ns * identity_heap + occurrences * station_heap
    value_heap += count * sum(heap_size(v) for v in common + [bases[typ]])
header = ",".join(["i", "j", "station", "type", "value"] + metadata_keys) + "\n"
fixed_bytes += len(header.encode())
n = sum(counts)
layout = json.loads(subprocess.check_output([str(HERE / "memory_layout")]).decode())
assert len(metadata_keys) == 18 and layout["string"] == 32
datum_lower = n * (layout["datum"] + layout["metadata_pair"] * layout["metadata_capacity"])
datum_lower += value_heap + n * sum(heap_size(k) for k in metadata_keys)
raw_table_lower = n * (layout["vector"] + 23 * layout["string"]) + value_heap
compression = []
for path in (ROOT / "data/hayward/observations.csv", ROOT / "data/synthetic/observations.csv"):
    compressed, size = 0, 0
    compressor = zlib.compressobj(6, zlib.DEFLATED, 31)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            compressed += len(compressor.compress(block))
    compressed += len(compressor.flush())
    compression.append(dict(file=str(path.relative_to(ROOT)), source_sha256=digest(path),
                            bytes=size, gzip_level6_bytes=compressed, compressed_fraction=compressed / size))
result = dict(
    created_utc=datetime.datetime.utcnow().isoformat() + "Z",
    scope="Read-only geometry/pair counting and arithmetic storage estimate; no travel times, observations, or inverse models generated",
    selection="All unordered event pairs with Euclidean 3-D distance strictly below 20 km; every selected receiver is used by the existing synthetic generator",
    sources=ne, receivers=ns, unique_rays=ne * ns, possible_event_pairs=ne * (ne - 1) // 2,
    selected_event_pairs=pairs, absolute_rows=counts[0], catalog_difference_rows=counts[1],
    precise_difference_rows=counts[2], total_observation_rows=n,
    degree_min_median_max=[min(degree), (sorted(degree)[ne // 2 - 1] + sorted(degree)[ne // 2]) / 2, max(degree)],
    closest_distance_to_threshold_km=closest,
    csv=dict(exact_bytes_excluding_value_field=fixed_bytes,
             estimates_by_mean_value_field_characters={str(m): fixed_bytes + n * m for m in (8, 12, 16)},
             interpretation="All index/identifier/epoch/label/separator bytes are counted analytically; value-field lengths remain unknown before ray/noise generation"),
    memory=dict(layout_probe=layout, loaded_datum_payload_lower_bound_bytes=datum_lower,
                raw_csv_table_payload_lower_bound_bytes=raw_table_lower,
                coexistence_payload_lower_bound_bytes=datum_lower + raw_table_lower,
                interpretation="64-bit libstdc++ lower bounds include actual repeated identity strings and metadata keys, 32-entry metadata vector capacity, and simultaneous raw CSV table plus Datum storage. Exclude allocator overhead, outer vector spare capacity, numeric-string heaps, rays, matrix/LSQR work, residuals, and other output. Not a peak RSS measurement.",
                matrix_entry_scenarios_bytes={str(k): n * k * layout["entry"] for k in (32, 64, 128)},
                matrix_scenario_interpretation="Assumes every row remains active; listed average entries per row are scenarios only, excluding row objects/capacity/allocator and solver copies"),
    existing_file_compression=compression,
    compression_interpretation="Measured existing-file ratios are analogues, not predictions for the ungenerated Loma data. Lossless gzip preserves selection but current C++ input requires plain CSV and still materializes all rows.",
    input_sha256={str(p.relative_to(ROOT)): digest(p) for p in
                  (GEOMETRY / "selected_events.csv", GEOMETRY / "selected_channels.csv", ROOT / "src/main.cpp",
                   ROOT / "src/csv.hpp", ROOT / "src/core.hpp", HERE / "count_cost.py", HERE / "memory_layout.cpp")})
(HERE / "pair_cost.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
