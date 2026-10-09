#!/usr/bin/env python3
"""Attach station identifiers to the saved probes without network requests."""

import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STANDARD = "https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html"
PROVENANCE = json.loads((ROOT / "earthscope_probe_provenance.json").read_text())


def source(filename, endpoint):
    raw = (ROOT / filename).read_bytes()
    matches = [item for item in PROVENANCE if endpoint in item["url"]]
    assert len(matches) == 1, "Expected one provenance record for " + filename
    record = matches[0]
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == record["sha256"], "Raw response hash mismatch: " + filename
    assert len(raw) == record["bytes"], "Raw response size mismatch: " + filename
    return raw.decode("utf-8").splitlines(), {
        "raw_file": filename,
        "raw_sha256": digest,
        "source_query_url": record["url"],
        "source_final_url": record["final_url"],
        "retrieved_utc": record["retrieved_utc"],
    }


def identity(network, station):
    assert re.fullmatch(r"[A-Z0-9]{1,2}", network), "Invalid SEED network code"
    assert re.fullmatch(r"[A-Z0-9-]{1,5}", station), "Invalid SEED station code"
    return {
        "network": network,
        "station": station,
        "seed_station_code": network + "." + station,
        "resource_id": "FDSN:" + network + "_" + station,
        "resource_id_origin": "derived_from_provider_codes_using_FDSN_standard",
        "provider_resource_id": None,
    }


def time_value(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f" if "." in value else "%Y-%m-%dT%H:%M:%S")


def sidecar(filename, provenance, records, description, counts):
    result = dict(provenance)
    result.update({
        "identifier_standard": STANDARD,
        "identity_scope": "station",
        "provider_resource_ids_supplied": False,
        "description": description,
        "counts": counts,
        "records": records,
    })
    (ROOT / (filename + ".identifiers.json")).write_text(json.dumps(result, indent=2) + "\n")


station_file = "earthscope_nc_1989_station.txt"
lines, station_source = source(station_file, "/fdsnws/station/1/query?")
stations = []
epoch_keys = set()
for line_number, line in enumerate(lines, 1):
    if not line.strip() or line.startswith("#"):
        continue
    fields = line.split("|")
    assert len(fields) == 8, "Unexpected station columns on line " + str(line_number)
    network, station, latitude, longitude, elevation, site, start, end = fields
    row = identity(network, station)
    assert start and (not end or time_value(start) < time_value(end)), "Invalid station epoch"
    time_value(start)
    coordinates = [float(value) for value in (latitude, longitude, elevation)]
    assert all(math.isfinite(value) for value in coordinates), "Nonfinite station coordinates"
    assert -90 <= coordinates[0] <= 90 and -180 <= coordinates[1] <= 180
    key = (network, station, start, end)
    assert key not in epoch_keys, "Duplicate station epoch"
    epoch_keys.add(key)
    row.update({
        "epoch_start": start, "epoch_end": end,
        "latitude_degrees": latitude, "longitude_degrees": longitude,
        "elevation_m": elevation, "site_name": site, "raw_line": line_number,
    })
    row.update(station_source)
    stations.append(row)

epoch_counts = Counter(row["resource_id"] for row in stations)
epoch_indices = {}
for identifier in epoch_counts:
    epochs = sorted((row["epoch_start"], row["epoch_end"]) for row in stations if row["resource_id"] == identifier)
    epoch_indices[identifier] = {epoch: index for index, epoch in enumerate(epochs, 1)}
for row in stations:
    row["station_epoch_count"] = epoch_counts[row["resource_id"]]
    row["station_epoch_index"] = epoch_indices[row["resource_id"]][(row["epoch_start"], row["epoch_end"])]
assert len(stations) == 364 and len(epoch_counts) == 364, "Saved station probe count changed"

fed_file = "earthscope_nc_1989_fedcatalog.txt"
lines, fed_source = source(fed_file, "/irisws/fedcatalog/1/query?")
requests = []
request_keys = set()
datacenter = station_service = None
for line_number, line in enumerate(lines, 1):
    if not line.strip() or line.startswith("#"):
        continue
    if "=" in line:
        key, value = line.split("=", 1)
        if key == "DATACENTER":
            datacenter = value
        elif key == "STATIONSERVICE":
            station_service = value
        continue
    fields = line.split()
    assert len(fields) == 6, "Unexpected federated request on line " + str(line_number)
    network, station, location, channel, start, end = fields
    assert datacenter and station_service, "Request missing data-center routing"
    assert location == "*" and channel == "*", "Saved probe no longer contains only station selectors"
    assert time_value(start) < time_value(end), "Invalid request interval"
    key = tuple(fields) + (datacenter, station_service)
    assert key not in request_keys, "Duplicate federated request"
    request_keys.add(key)
    row = identity(network, station)
    row.update({
        "raw_line": line_number, "record_kind": "station_metadata_request",
        "location_selector": location, "channel_selector": channel,
        "concrete_nslc": None, "channel_resource_id": None,
        "request_start": start, "request_end": end,
        "datacenter": datacenter, "station_service": station_service,
    })
    requests.append(row)
assert len(requests) == 122, "Saved federated probe count changed"
request_station_count = len(set(row["resource_id"] for row in requests))
assert request_station_count == 122, "Saved federated station uniqueness changed"

csv_file = ROOT / "earthscope_nc_1989_stations_identified.csv"
with csv_file.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(stations[0]))
    writer.writeheader()
    writer.writerows(stations)

sidecar(station_file, station_source, stations,
        "Station resource IDs are derived by the FDSN standard, not supplied IDs. "
        "The station ID alone does not identify an epoch: preserve epoch_start/epoch_end and "
        "station_epoch_index/station_epoch_count. Blank epoch_end means open ended. "
        "No channel identity is supplied by these station-level records.",
        {"station_epochs": len(stations), "unique_stations": len(epoch_counts),
         "stations_with_multiple_epochs": sum(count > 1 for count in epoch_counts.values())})
sidecar(fed_file, fed_source, requests,
        "Rows are station-metadata requests, not observed channel identities. "
        "Location and channel wildcards remain selectors. No concrete NSLC or channel "
        "resource ID is invented. Station IDs are derived by the FDSN standard.",
        {"request_rows": len(requests), "unique_stations": request_station_count})
print("Validated and normalized 364 station epochs / 364 stations and 122 station requests.")
print("Raw files match their recorded SHA-256 hashes; no network requests made.")
