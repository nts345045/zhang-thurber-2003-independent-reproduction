#!/usr/bin/env python3
"""Retrieve the authorized independent Loma Prieta source/receiver geometry."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent


def helper(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, str(ROOT.parent / relative_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse this project's time, provenance, identifier, and StationXML parsers.
# Each module is loaded independently; output paths are assigned explicitly.
event_api = helper("hayward_acquisition_helpers", "hayward/acquire.py")
station_api = helper("station_acquisition_helpers", "stations/acquire.py")
event_api.ROOT = ROOT
station_api.ROOT = ROOT
CRITERIA = {
    "status": "independent authoritative geometry; not the manuscript's exact cohort",
    "start_utc_inclusive": "1989-10-18T00:00:00Z",
    "end_utc_exclusive": "1989-11-18T00:00:00Z",
    "magnitude_inclusive": [2.0, 5.5],
    "query_latitude_inclusive": [36.5, 37.6],
    "query_longitude_inclusive": [-122.6, -121.2],
    "event_type": "earthquake",
    "geoid_depth_km_inclusive": [0, 16],
    "origin_latitude_deg": 37.0361667,
    "origin_longitude_deg": -121.8798333,
    "origin_coordinate_source": "../discovery/usgs_nc216859.geojson",
    "origin_event_resource_id": "quakeml:nc.anss.org/Event/NC/216859",
    "origin_origin_resource_id": "quakeml:nc.anss.org/Origin/NC/2642104",
    "axis_rotation_anticlockwise_deg": 45,
    "x_km_inclusive": [-15, 20],
    "y_km_inclusive": [-45, 25],
    "horizontal_coordinates": "WGS84 zero-ellipsoid-height ECEF difference projected onto origin east/north tangent basis; x=E*cos(45)+N*sin(45), y=-E*sin(45)+N*cos(45)",
    "catalog": "NCSS preferred origins and magnitudes as retrieved",
    "summary_page_limit": 10000,
    "selection_cap": None,
    "event_service_documentation": "https://service.ncedc.org/fdsnws/event/1/",
    "depth_datum_documentation": "https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html",
}
event_api.CRITERIA = CRITERIA
SNAPSHOT = "1989-11-01T00:00:00Z"
STATION_CRITERIA = {
    "status": CRITERIA["status"],
    "snapshot_utc": SNAPSHOT,
    "snapshot_interval_convention": "effective metadata start <= snapshot < effective metadata end; no end means open epoch",
    "network_code": "NC", "channel_code": "EHZ", "location_selection": "all valid locations",
    "x_km_inclusive": [-35, 35], "y_km_inclusive": [-60, 40],
    "horizontal_coordinates": CRITERIA["horizontal_coordinates"],
    "origin_latitude_deg": CRITERIA["origin_latitude_deg"],
    "origin_longitude_deg": CRITERIA["origin_longitude_deg"],
    "grid_top_km": "min(-1, floor(minimum selected sensor z in km)); all horizontally selected sensors retained",
    "maximum_sensor_z_km": 16,
    "sensor_z_definition": "minus Channel/Elevation in metres divided by 1000; do not subtract burial depth twice",
    "selection_cap": None,
}


def event_row(event, meta):
    origin = event_api.preferred(event, "origin", "preferredOriginID")
    magnitude = event_api.preferred(event, "magnitude", "preferredMagnitudeID")
    values = [float(value) for value in
              (event_api.qtext(origin, "latitude/value"), event_api.qtext(origin, "longitude/value"),
               event_api.qtext(origin, "depth/value"), event_api.qtext(magnitude, "mag/value"))]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Nonfinite catalog coordinate or magnitude")
    latitude, longitude, depth_m, mag = values
    depth_km = depth_m / 1000
    east, north, x, y = event_api.horizontal_coordinates(latitude, longitude)
    timestamp = event_api.qtext(origin, "time/value")
    reasons = []
    if not event_api.parse_time(CRITERIA["start_utc_inclusive"]) <= event_api.parse_time(timestamp) < event_api.parse_time(CRITERIA["end_utc_exclusive"]):
        reasons.append("outside_half_open_time_interval")
    for name, value, bounds in (
            ("magnitude", mag, CRITERIA["magnitude_inclusive"]),
            ("latitude", latitude, CRITERIA["query_latitude_inclusive"]),
            ("longitude", longitude, CRITERIA["query_longitude_inclusive"]),
            ("geoid_depth", depth_km, CRITERIA["geoid_depth_km_inclusive"]),
            ("x", x, CRITERIA["x_km_inclusive"]), ("y", y, CRITERIA["y_km_inclusive"])):
        if not bounds[0] <= value <= bounds[1]:
            reasons.append("outside_" + name + "_range")
    event_type = event_api.qtext(event, "type")
    if event_type != "earthquake":
        reasons.append("non_earthquake_event_type" if event_type else "unknown_event_type")
    return {
        "event_resource_id": event.attrib["publicID"],
        "provider_event_dataid": event.get(event_api.CAT + "dataid", ""),
        "provider_event_datasource": event.get(event_api.CAT + "datasource", ""),
        "provider_event_eventid": event.get(event_api.CAT + "eventid", ""),
        "origin_resource_id": origin.attrib["publicID"],
        "magnitude_resource_id": magnitude.attrib["publicID"],
        "origin_time_utc": event_api.normalize_time(timestamp), "origin_time_provider_text": timestamp,
        "latitude_deg": latitude, "longitude_deg": longitude, "geoid_depth_km": depth_km,
        "magnitude": mag, "magnitude_type": event_api.qtext(magnitude, "type"), "event_type": event_type,
        "origin_evaluation_status": event_api.qtext(origin, "evaluationStatus"),
        "origin_method_resource_id": event_api.qtext(origin, "methodID"),
        "earth_model_resource_id": event_api.qtext(origin, "earthModelID"),
        "east_km": east, "north_km": north, "x_km": x, "y_km": y,
        "selected": int(not reasons), "exclusion_reasons": ";".join(reasons),
        "source_file": meta["raw_file"], "source_sha256": meta["sha256"],
        "source_url": meta["requested_url"], "retrieved_utc": meta["retrieved_utc"],
    }


def events():
    rows, queries = [], []
    offset = 1
    while True:
        params = {"start": CRITERIA["start_utc_inclusive"].rstrip("Z"),
                  "end": CRITERIA["end_utc_exclusive"].rstrip("Z"),
                  "minmag": 2.0, "maxmag": 5.5, "minlat": 36.5, "maxlat": 37.6,
                  "minlon": -122.6, "maxlon": -121.2, "catalog": "NCSS", "format": "xml",
                  "includearrivals": "false", "orderby": "time-asc", "limit": 10000, "offset": offset}
        returned, meta = event_api.fetch_xml("events_{:05d}".format(offset), params)
        rows.extend(event_row(event, meta) for event in returned)
        queries.append({"offset": offset, "count": len(returned), "raw_file": meta["raw_file"]})
        if len(returned) < 10000:
            break
        offset += 10000
    ids = [row["event_resource_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate native event identities across catalog pages")
    rows.sort(key=lambda row: (row["origin_time_utc"], row["event_resource_id"]))
    selected = [row for row in rows if row["selected"]]
    event_api.write_csv(ROOT / "catalog_candidates.csv", rows)
    event_api.write_csv(ROOT / "selected_events.csv", selected, list(rows[0]))
    manifest = {"created_utc": event_api.utc_now(), "criteria": CRITERIA, "summary_queries": queries,
                "candidate_events": len(rows), "selected_events": len(selected),
                "excluded_events": len(rows) - len(selected),
                "exclusion_reason_counts_nonexclusive": dict(Counter(reason for row in rows for reason in row["exclusion_reasons"].split(";") if reason)),
                "candidate_event_types": dict(Counter(row["event_type"] for row in rows)),
                "unknown_event_type_count": sum(not row["event_type"] for row in rows),
                "selected_by_day": dict(Counter(row["origin_time_utc"][:10] for row in selected)),
                "selection_manifest_complete": True,
                "observational_pick_acquisition": "not requested; these catalog locations define synthetic source geometry"}
    event_api.write_json(ROOT / "event_selection_manifest.json", manifest)
    print(json.dumps({key: value for key, value in manifest.items() if key != "criteria"}, indent=2), flush=True)


def fetch_station(endpoint, params, stem, suffix):
    path = ROOT / "raw" / (stem + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    provenance = path.with_suffix(suffix + ".provenance.json")
    url = requests.Request("GET", endpoint, params=params).prepare().url
    if path.exists():
        raw = path.read_bytes()
        meta = json.loads(provenance.read_text())
        if meta["source_url"] != url or hashlib.sha256(raw).hexdigest() != meta["source_sha256"]:
            raise ValueError("Saved station response URL/hash mismatch: " + str(path))
    else:
        if event_api.OFFLINE:
            raise RuntimeError("Offline rebuild requires saved station response: " + str(path))
        started = event_api.utc_now()
        response = requests.get(endpoint, params=params, timeout=(20, 180),
                                headers={"Accept-Encoding": "identity", "User-Agent": "IndependentTomographyReproduction/1.0"})
        raw = response.content
        meta = {"source_url": url, "final_url": response.url, "request_method": "GET", "request_parameters": params,
                "request_started_utc": started, "retrieved_utc": event_api.utc_now(), "http_status": response.status_code,
                "bytes": len(raw), "source_sha256": hashlib.sha256(raw).hexdigest(), "source_file": str(path.relative_to(ROOT)),
                "response_headers": {key: value for key, value in response.headers.items() if key.lower() in
                                     ("date", "content-type", "last-modified", "etag", "content-length")}}
        path.write_bytes(raw)
        event_api.write_json(provenance, meta)
    if meta["http_status"] != 200 or not raw:
        event_api.write_json(path.with_suffix(suffix + ".identifiers.json"), dict(meta, records=[], response_kind="error or empty response"))
        raise RuntimeError("No usable station reply; preserved response requires review: " + str(path))
    return raw, meta, path


def stations():
    # Query the snapshot instant. Explicit effective-epoch checks follow below.
    params = {"network": "NC", "channel": "EHZ", "starttime": SNAPSHOT, "endtime": SNAPSHOT,
              "targetservice": "station", "level": "channel", "format": "request"}
    raw, meta, path = fetch_station(station_api.FEDCATALOG, params, "earthscope_routes", ".txt")
    service = datacenter = None
    routes, services = [], set()
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
        if len(fields) != 6 or not service:
            raise ValueError("Unrecognized EarthScope route record: " + line)
        net, sta, loc, cha, start, end = fields
        loc = "" if loc == "--" else loc
        identity = station_api.identifiers(net, sta, loc, cha)
        identity.update(raw_line=line_number, request_start=start, request_end=end,
                        station_service=service, datacenter=datacenter, provider_resource_id=None,
                        record_kind="metadata request, not a channel epoch")
        routes.append(identity)
        services.add(service)
    event_api.write_json(path.with_suffix(".txt.identifiers.json"), dict(meta, records=routes))
    ncedc = [value for value in services if value.startswith("https://service.ncedc.org/fdsnws/station/1")]
    if len(ncedc) != 1:
        raise RuntimeError("Could not identify a unique authoritative NCEDC station route")
    endpoint = ncedc[0].rstrip("/") + "/query"
    params = {"net": "NC", "cha": "EHZ", "start": SNAPSHOT, "end": SNAPSHOT, "level": "channel", "format": "xml"}
    raw, meta, path = fetch_station(endpoint, params, "ncedc_channel_epochs", ".xml")
    rows = station_api.stationxml(raw, meta, path)
    snapshot = event_api.parse_time(SNAPSHOT)
    selected_ids = set()
    for row in rows:
        east, north, x, y = event_api.horizontal_coordinates(row["latitude_deg"], row["longitude_deg"])
        reasons = []
        if row["network_code"] != "NC" or row["channel_code"] != "EHZ":
            reasons.append("outside_NC_EHZ_selection")
        if not event_api.parse_time(row["metadata_epoch_start"]) <= snapshot or (
                row["metadata_epoch_end"] and not snapshot < event_api.parse_time(row["metadata_epoch_end"])):
            reasons.append("metadata_epoch_not_active_at_snapshot")
        if not -35 <= x <= 35:
            reasons.append("outside_x_range")
        if not -60 <= y <= 40:
            reasons.append("outside_y_range")
        if row["sensor_z_geoid_km"] > 16 and not reasons:
            raise RuntimeError("Selected sensor lies below 16 km: review before choosing any vertical exclusion")
        if not reasons:
            if row["channel_seed_id"] in selected_ids:
                raise RuntimeError("Ambiguous overlapping metadata epochs at snapshot: " + row["channel_seed_id"])
            selected_ids.add(row["channel_seed_id"])
        row.update(east_km=east, north_km=north, x_km=x, y_km=y,
                   snapshot_utc=SNAPSHOT, selected=int(not reasons), exclusion_reasons=";".join(reasons))
    selected = [row for row in rows if row["selected"]]
    if not selected:
        raise RuntimeError("No channels selected; selection/access requires review")
    event_api.write_csv(ROOT / "channel_candidates.csv", rows)
    event_api.write_csv(ROOT / "selected_channels.csv", selected, list(rows[0]))
    z_min = min(row["sensor_z_geoid_km"] for row in selected)
    z_max = max(row["sensor_z_geoid_km"] for row in selected)
    manifest = {"created_utc": event_api.utc_now(), "criteria": STATION_CRITERIA,
                "earthscope_routing_records": len(routes), "earthscope_routing_services": sorted(services),
                "candidate_channel_epochs": len(rows), "selected_channels": len(selected),
                "selected_stations": len(set((row["network_code"], row["station_code"]) for row in selected)),
                "excluded_channel_epochs": len(rows) - len(selected),
                "exclusion_reason_counts_nonexclusive": dict(Counter(reason for row in rows for reason in row["exclusion_reasons"].split(";") if reason)),
                "minimum_selected_sensor_z_km": z_min, "maximum_selected_sensor_z_km": z_max,
                "suggested_grid_top_km": min(-1, math.floor(z_min)),
                "overlapping_selected_channel_epochs": 0, "selection_manifest_complete": True}
    event_api.write_json(ROOT / "station_selection_manifest.json", manifest)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("events", "stations"))
    parser.add_argument("--offline", action="store_true", help="Verify/rebuild only pinned responses; fail if any is missing")
    args = parser.parse_args()
    event_api.OFFLINE = args.offline
    {"events": events, "stations": stations}[args.stage]()
