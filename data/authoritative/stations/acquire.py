#!/usr/bin/env python3
"""Acquire authoritative channel epochs for the independently selected picks."""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
HAYWARD = ROOT.parent / "hayward"
NS = {"s": "http://www.fdsn.org/xml/station/1"}
FDSN_STANDARD = "https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html"
XML_STANDARD = "https://docs.fdsn.org/projects/stationxml/en/latest/reference.html"
DATUM_SOURCE = "https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html"
FEDCATALOG = "https://service.earthscope.org/irisws/fedcatalog/1/query"
OFFLINE = False


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_time(value):
    value = value.rstrip("Z")
    if value.endswith("+00:00"):
        value = value[:-6]
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f" if "." in value else "%Y-%m-%dT%H:%M:%S")


def csv_read(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def csv_write(path, rows, fields=None):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fetch(endpoint, params, prefix, extension):
    url = endpoint + "?" + urlencode(params)
    name = prefix + "_" + hashlib.sha256(url.encode()).hexdigest()[:12] + extension
    path = ROOT / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path = path.with_suffix(path.suffix + ".provenance.json")
    if path.exists():
        raw = path.read_bytes()
        meta = json.loads(provenance_path.read_text())
        if meta["source_url"] != url or meta["source_sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError("Existing raw response/provenance mismatch: " + name)
    else:
        if OFFLINE:
            raise RuntimeError("Offline mode forbids retrieving missing cache: " + name)
        request = Request(url, headers={"User-Agent": "IndependentTomographyReproduction/1.0", "Accept-Encoding": "identity"})
        started = utc_now()
        try:
            response = urlopen(request, timeout=120)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            meta = {"source_url": url, "final_url": response.geturl(), "http_status": response.status,
                    "request_method": "GET", "request_parameters": params,
                    "request_started_utc": started, "retrieved_utc": utc_now(),
                    "bytes": len(raw), "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "source_file": "raw/" + name,
                    "response_headers": {key: value for key, value in response.headers.items()
                                         if key.lower() in ("date", "content-type", "last-modified", "etag")}}
        path.write_bytes(raw)
        json_write(provenance_path, meta)
    if meta["http_status"] != 200 or not raw:
        json_write(path.with_suffix(path.suffix + ".identifiers.json"), dict(meta, records=[],
                   response_kind="HTTP error or empty response, not station metadata"))
        raise RuntimeError("No usable metadata in " + url + ": " + raw.decode("utf-8", "replace")[:1200])
    return raw, meta, path


def identifiers(network, station, location=None, channel=None):
    if not re.fullmatch(r"[A-Z0-9]{1,2}", network) or not re.fullmatch(r"[A-Z0-9-]{1,5}", station):
        raise ValueError("Nonconcrete SEED station identity: " + network + "." + station)
    result = {"network_code": network, "station_code": station,
              "station_seed_id": network + "." + station,
              "station_fdsn_source_id": "FDSN:" + network + "_" + station}
    if channel is not None:
        if location == "--" or not re.fullmatch(r"[A-Z0-9-]{0,2}", location) or not re.fullmatch(r"[A-Z0-9]{3}", channel):
            raise ValueError("Nonconcrete SEED channel identity")
        result.update(location_code=location, channel_code=channel,
                      channel_seed_id=".".join((network, station, location, channel)),
                      channel_fdsn_source_id="FDSN:" + "_".join((network, station, location) + tuple(channel)))
    result["identifier_basis"] = "derived from provider SEED codes using FDSN Source Identifiers v1.0"
    return result


def route(network, stations, channels, locations, start, end):
    params = {"network": network, "station": ",".join(stations),
              "channel": ",".join(channels), "location": ",".join(locations),
              "starttime": start, "endtime": end, "targetservice": "station",
              "level": "channel", "format": "request"}
    raw, meta, path = fetch(FEDCATALOG, params, "earthscope_routes_" + network, ".txt")
    service = datacenter = None
    records, services = [], set()
    for line_number, line in enumerate(raw.decode().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if key == "STATIONSERVICE":
                service = value
            elif key == "DATACENTER":
                datacenter = value
            continue
        fields = line.split()
        if len(fields) != 6 or service is None:
            raise ValueError("Unexpected federated routing record: " + line)
        net, sta, loc, cha, first, last = fields
        loc = "" if loc == "--" else loc
        concrete = not any(character in loc + cha for character in "*?,")
        row = identifiers(net, sta, loc, cha) if concrete else identifiers(net, sta)
        row.update(raw_line=line_number, location_selector=loc, channel_selector=cha,
                   request_start=first, request_end=last, station_service=service,
                   datacenter=datacenter, record_kind="metadata request",
                   provider_resource_id=None)
        records.append(row)
        services.add(service)
    json_write(path.with_suffix(path.suffix + ".identifiers.json"), dict(meta, records=records,
               identifier_standard=FDSN_STANDARD, wildcard_policy="Wildcards are selectors, not concrete channel identities."))
    # The earlier EarthScope discovery established NCEDC routing for NC. This
    # selection follows the authoritative NCEDC route also for archived BK data.
    matches = [service for service in services if service.startswith("https://service.ncedc.org/fdsnws/station/1")]
    if len(matches) != 1:
        raise RuntimeError("Cannot identify one NCEDC metadata route for " + network + ": " + repr(services))
    return matches[0].rstrip("/") + "/query"


def text(node, name):
    child = node.find("s:" + name, NS)
    return "" if child is None or child.text is None else child.text.strip()


def provider_ids(node):
    values = [{"field": key, "value": value} for key, value in node.attrib.items()
              if key.rsplit("}", 1)[-1] in ("sourceID", "resourceId", "resourceID", "publicID")]
    values.extend({"field": "Identifier", "type": item.get("type", ""), "value": item.text or ""}
                  for item in node.findall("s:Identifier", NS))
    return json.dumps(values, separators=(",", ":"))


def stationxml(raw, meta, path):
    tree = ET.fromstring(raw)
    rows = []
    for network in tree.findall("s:Network", NS):
        for station in network.findall("s:Station", NS):
            for channel in station.findall("s:Channel", NS):
                row = identifiers(network.attrib["code"], station.attrib["code"],
                                  channel.attrib["locationCode"], channel.attrib["code"])
                starts = [node.get("startDate") for node in (network, station, channel) if node.get("startDate")]
                ends = [node.get("endDate") for node in (network, station, channel) if node.get("endDate")]
                if not starts:
                    raise ValueError("No metadata epoch start: " + row["channel_seed_id"])
                start = max(starts, key=parse_time)
                end = min(ends, key=parse_time) if ends else ""
                if end and parse_time(start) >= parse_time(end):
                    raise ValueError("Empty/inverted metadata epoch: " + row["channel_seed_id"])
                numbers = {"latitude_deg": float(text(channel, "Latitude")),
                           "longitude_deg": float(text(channel, "Longitude")),
                           "channel_sensor_elevation_m": float(text(channel, "Elevation")),
                           "sensor_depth_below_ground_m": float(text(channel, "Depth")),
                           "station_elevation_m": float(text(station, "Elevation"))}
                if not all(math.isfinite(value) for value in numbers.values()):
                    raise ValueError("Nonfinite metadata coordinate")
                if not (-90 <= numbers["latitude_deg"] <= 90 and -180 <= numbers["longitude_deg"] <= 180):
                    raise ValueError("Invalid geographic coordinate")
                ambiguous = (numbers["sensor_depth_below_ground_m"] != 0 and
                             numbers["channel_sensor_elevation_m"] == numbers["station_elevation_m"])
                z_sensor = -numbers["channel_sensor_elevation_m"] / 1000
                z_ground = (numbers["sensor_depth_below_ground_m"] - numbers["channel_sensor_elevation_m"]) / 1000
                row.update(numbers)
                row.update(metadata_epoch_start=start, metadata_epoch_end=end,
                           channel_epoch_start=channel.get("startDate", ""), channel_epoch_end=channel.get("endDate", ""),
                           station_epoch_start=station.get("startDate", ""), station_epoch_end=station.get("endDate", ""),
                           provider_channel_source_id=channel.get("sourceID", ""),
                           provider_channel_resource_ids_json=provider_ids(channel),
                           provider_station_resource_ids_json=provider_ids(station),
                           provider_network_resource_ids_json=provider_ids(network),
                           latitude_datum=channel.find("s:Latitude", NS).get("datum", "WGS84 (StationXML default)"),
                           longitude_datum=channel.find("s:Longitude", NS).get("datum", "WGS84 (StationXML default)"),
                           sensor_z_geoid_km="" if ambiguous else z_sensor,
                           z_if_sensor_elevation_km=z_sensor,
                           z_if_ground_elevation_km=z_ground,
                           vertical_coordinate_status="ambiguous_provider_borehole_elevation_convention" if ambiguous else "stationxml_sensor_elevation_convention_applied",
                           vertical_datum_basis="NCEDC documents station elevations and catalog geoid depth on the same datum; StationXML supplies no explicit vertical-datum field",
                           elevation_semantics="Nonzero burial depth and equal channel/station elevations require provider-convention clarification" if ambiguous else "Channel/Elevation interpreted as sensor elevation per StationXML; no separate burial correction",
                           stationxml_schema_version=tree.get("schemaVersion", ""),
                           source_document_metadata_index=len(rows),
                           source_file=meta["source_file"], source_url=meta["source_url"],
                           source_sha256=meta["source_sha256"], retrieved_utc=meta["retrieved_utc"])
                rows.append(row)
    json_write(path.with_suffix(path.suffix + ".identifiers.json"), dict(meta, channel_epochs=rows,
               identifier_standard=FDSN_STANDARD, stationxml_standard=XML_STANDARD,
               vertical_datum_documentation=DATUM_SOURCE))
    return rows


def acquire():
    if not json.loads((HAYWARD / "pick_selection_manifest.json").read_text())["acquisition_complete"]:
        raise RuntimeError("Wait for the complete pick acquisition before requesting channel metadata")
    requests = csv_read(HAYWARD / "channel_requests.csv")
    by_network = defaultdict(list)
    for row in requests:
        identifiers(row["network_code"], row["station_code"], row["location_code"], row["channel_code"])
        by_network[row["network_code"]].append(row)
    metadata = []
    for network, rows in sorted(by_network.items()):
        stations = sorted(set(row["station_code"] for row in rows))
        for offset in range(0, len(stations), 25):
            batch = stations[offset:offset + 25]
            wanted = [row for row in rows if row["station_code"] in batch]
            start = (min(parse_time(row["first_pick_time_utc"]) for row in wanted) - timedelta(seconds=1)).isoformat()
            end = (max(parse_time(row["last_pick_time_utc"]) for row in wanted) + timedelta(seconds=1)).isoformat()
            channels = sorted(set(row["channel_code"] for row in wanted))
            locations = sorted(set(row["location_code"] or "--" for row in wanted))
            endpoint = route(network, batch, channels, locations, start, end)
            # NCEDC rejects comma lists beginning with the blank-location token
            # "--" as an option. Retrieve all locations for these channels and
            # keep the exact NSLC selection in the subsequent epoch join.
            params = {"net": network, "sta": ",".join(batch), "start": start, "end": end,
                      "cha": ",".join(channels),
                      "level": "channel", "format": "xml"}
            raw, meta, path = fetch(endpoint, params, "ncedc_channels_" + network, ".xml")
            metadata.extend(stationxml(raw, meta, path))
            print(network, offset, "station batch retrieved", flush=True)
    keys = [(row["channel_seed_id"], row["metadata_epoch_start"], row["metadata_epoch_end"]) for row in metadata]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate NSLC/epoch keys in returned metadata; do not collapse them silently")
    csv_write(ROOT / "channel_epochs.csv", metadata)
    match()


def match():
    if not json.loads((HAYWARD / "pick_selection_manifest.json").read_text())["acquisition_complete"]:
        raise RuntimeError("Cannot match an incomplete pick export")
    metadata = csv_read(ROOT / "channel_epochs.csv")
    picks = csv_read(HAYWARD / "picks_selected.csv")
    by_channel = defaultdict(list)
    for row in metadata:
        by_channel[row["channel_seed_id"]].append(row)
    matches, failures = [], []
    for pick in picks:
        seed_id = pick["channel_seed_id"]
        timestamp = pick["pick_time_utc"]
        if not seed_id or not timestamp:
            raise ValueError("Pick lacks an explicit channel identity or pick time")
        t = parse_time(timestamp)
        candidates = [row for row in by_channel.get(seed_id, [])
                      if parse_time(row["metadata_epoch_start"]) <= t and
                      (not row["metadata_epoch_end"] or t < parse_time(row["metadata_epoch_end"]))]
        expected = identifiers(pick["network_code"], pick["station_code"], pick["location_code"], pick["channel_code"])
        if seed_id != expected["channel_seed_id"] or pick["channel_fdsn_source_id"] != expected["channel_fdsn_source_id"]:
            raise ValueError("Pick channel identifiers disagree: " + pick["pick_resource_id"])
        row = {"event_resource_id": pick["event_resource_id"],
               "origin_resource_id": pick["origin_resource_id"], "arrival_resource_id": pick["arrival_resource_id"],
               "pick_resource_id": pick["pick_resource_id"],
               "pick_time_utc": timestamp, "channel_seed_id": seed_id,
               "channel_fdsn_source_id": pick["channel_fdsn_source_id"],
               "network_code": pick["network_code"], "station_code": pick["station_code"],
               "location_code": pick["location_code"], "channel_code": pick["channel_code"],
               "match_count": len(candidates), "match_status": "unique" if len(candidates) == 1 else "missing" if not candidates else "overlapping",
               "metadata_epoch_start": candidates[0]["metadata_epoch_start"] if len(candidates) == 1 else "",
               "metadata_epoch_end": candidates[0]["metadata_epoch_end"] if len(candidates) == 1 else "",
               "metadata_source_file": candidates[0]["source_file"] if len(candidates) == 1 else "",
               "metadata_source_sha256": candidates[0]["source_sha256"] if len(candidates) == 1 else ""}
        matches.append(row)
        if len(candidates) != 1:
            failures.append(dict(row, candidate_epochs=candidates))
    csv_write(ROOT / "pick_epoch_matches.csv", matches)
    summary = {"created_utc": utc_now(), "metadata_epochs": len(metadata),
               "metadata_channels": len(by_channel), "pick_rows": len(picks),
               "matches": dict(Counter(row["match_status"] for row in matches)),
               "epoch_membership": "start inclusive; end exclusive; empty end unbounded",
               "channel_requests_sha256": hashlib.sha256((HAYWARD / "channel_requests.csv").read_bytes()).hexdigest(),
               "picks_sha256": hashlib.sha256((HAYWARD / "picks_selected.csv").read_bytes()).hexdigest(),
               "failures": failures}
    json_write(ROOT / "matching_summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "failures"}, indent=2))
    if failures:
        raise RuntimeError("Missing or overlapping metadata epochs: report for clarification before inversion")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("acquire", "match"))
    parser.add_argument("--offline", action="store_true", help="Require all raw responses to exist; forbid network retrieval")
    args = parser.parse_args()
    OFFLINE = args.offline
    acquire() if args.stage == "acquire" else match()
