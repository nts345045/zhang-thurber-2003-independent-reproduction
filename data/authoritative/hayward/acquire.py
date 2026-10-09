#!/usr/bin/env python3
"""Acquire the explicitly independent Hayward subset, retaining source identities."""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import requests


ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://service.ncedc.org/fdsnws/event/1/query"
NS = {"q": "http://quakeml.org/xmlns/bed/1.2"}
CAT = "{http://anss.org/xmlns/catalog/0.1}"
OFFLINE = False
CRITERIA = {
    "status": "independent authoritative subset; not the manuscript's exact cohort",
    "start_utc_inclusive": "1984-01-01T00:00:00Z",
    "end_utc_exclusive": "1999-01-01T00:00:00Z",
    "magnitude_inclusive": [0.2, 4.5],
    "query_latitude_inclusive": [37.2, 38.3],
    "query_longitude_inclusive": [-122.7, -121.4],
    "geoid_depth_km_inclusive": [0, 20],
    "origin_latitude_deg": 37.72,
    "origin_longitude_deg": -122.06,
    "axis_rotation_anticlockwise_deg": 35,
    "x_km_inclusive": [-10, 10],
    "y_km_inclusive": [-30, 30],
    "horizontal_coordinates": "WGS84 zero-ellipsoid-height ECEF difference projected onto origin east/north tangent basis; x=E*cos(35)+N*sin(35), y=-E*sin(35)+N*cos(35)",
    "catalog": "NCSS preferred origins and magnitudes as retrieved",
    "event_type_filter": "earthquake only; other and unknown types explicitly excluded",
    "summary_page_limit": 10000,
    "event_service_documentation": "https://service.ncedc.org/fdsnws/event/1/",
    "depth_datum_documentation": "https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html",
    "prior_discovery": "../discovery/README.md; USGS and EarthScope service discovery preceded NCEDC acquisition",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value):
    # FDSN QuakeML values are UTC even when the provider omits the trailing Z.
    offset = timedelta(0)
    match = re.search(r"([+-])(\d\d):(\d\d)$", value)
    if match:
        offset = timedelta(hours=int(match.group(2)), minutes=int(match.group(3)))
        if match.group(1) == "-":
            offset = -offset
        value = value[:match.start()]
    value = value.rstrip("Z")
    fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in value else "%Y-%m-%dT%H:%M:%S"
    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc) - offset


def normalize_time(value):
    return parse_time(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows, fields=None):
    if fields is None:
        if not rows:
            raise ValueError("No rows/fields for " + str(path))
        fields = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def qtext(node, path):
    found = node.find("/".join("q:" + p for p in path.split("/")), NS)
    return "" if found is None or found.text is None else found.text.strip()


def resources(tree):
    """Attach provider public IDs to each unchanged XML reply."""
    result = []
    def visit(node, parent_id=None):
        public_id = node.get("publicID")
        if public_id:
            result.append({"element_type": node.tag.rsplit("}", 1)[-1],
                           "resource_id": public_id, "parent_resource_id": parent_id,
                           "identifier_basis": "provider QuakeML publicID"})
            parent_id = public_id
        for child in node:
            visit(child, parent_id)
    visit(tree)
    ids = [row["resource_id"] for row in result]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate public IDs within a provider reply")
    return result


def fetch_xml(stem, params):
    raw_dir = ROOT / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / (stem + ".xml")
    meta_path = path.with_suffix(".provenance.json")
    requested_url = requests.Request("GET", ENDPOINT, params=params).prepare().url
    if path.exists():
        meta = json.loads(meta_path.read_text())
        data = path.read_bytes()
        if meta["requested_url"] != requested_url or hashlib.sha256(data).hexdigest() != meta["sha256"]:
            raise ValueError("Saved response does not match this request/hash: " + stem)
    else:
        if OFFLINE:
            raise RuntimeError("Offline acquisition rebuild requires saved response: " + str(path))
        started = utc_now()
        response = requests.get(ENDPOINT, params=params, timeout=(20, 180),
                                headers={"Accept-Encoding": "identity", "User-Agent": "IndependentTomographyReproduction/1.0"})
        data = response.content
        meta = {
            "requested_url": requested_url, "final_url": response.url,
            "request_method": "GET", "request_parameters": params,
            "request_started_utc": started, "retrieved_utc": utc_now(),
            "http_status": response.status_code, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "response_headers": {k: v for k, v in response.headers.items()
                                 if k.lower() in {"content-type", "content-length", "date", "last-modified", "etag", "content-encoding"}},
            "raw_file": str(path.relative_to(ROOT)),
            "selection_status": CRITERIA["status"],
        }
        path.write_bytes(data)
        write_json(meta_path, meta)
    if meta["http_status"] not in (200, 204):
        raise RuntimeError("Provider HTTP {} for {}; raw response saved; stop for review".format(meta["http_status"], requested_url))
    if meta["http_status"] == 204:
        write_json(path.with_suffix(".identifiers.json"), dict(meta, resources=[]))
        return [], meta
    tree = ET.fromstring(data)
    events = tree.findall(".//q:event", NS)
    write_json(path.with_suffix(".identifiers.json"), dict(meta, resources=resources(tree)))
    return events, meta


def horizontal_coordinates(latitude, longitude):
    # WGS84 ellipsoid, a=6378.137 km, inverse flattening=298.257223563.
    a = 6378.137
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    def ecef(lat, lon):
        phi, lam = math.radians(lat), math.radians(lon)
        radius = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
        return (radius * math.cos(phi) * math.cos(lam),
                radius * math.cos(phi) * math.sin(lam),
                radius * (1 - e2) * math.sin(phi))
    lat0, lon0 = CRITERIA["origin_latitude_deg"], CRITERIA["origin_longitude_deg"]
    p, p0 = ecef(latitude, longitude), ecef(lat0, lon0)
    dx, dy, dz = [p[i] - p0[i] for i in range(3)]
    phi, lam = math.radians(lat0), math.radians(lon0)
    east = -math.sin(lam) * dx + math.cos(lam) * dy
    north = -math.sin(phi) * math.cos(lam) * dx - math.sin(phi) * math.sin(lam) * dy + math.cos(phi) * dz
    theta = math.radians(CRITERIA["axis_rotation_anticlockwise_deg"])
    return east, north, east * math.cos(theta) + north * math.sin(theta), -east * math.sin(theta) + north * math.cos(theta)


def preferred(event, tag, id_tag):
    identifier = qtext(event, id_tag)
    matches = [node for node in event.findall("q:" + tag, NS) if node.get("publicID") == identifier]
    if not identifier or len(matches) != 1:
        raise ValueError("Cannot identify unique preferred " + tag + ": " + str(event.get("publicID")))
    return matches[0]


def event_row(event, meta):
    origin = preferred(event, "origin", "preferredOriginID")
    magnitude = preferred(event, "magnitude", "preferredMagnitudeID")
    resource_id = event.attrib["publicID"]
    origin_id = origin.attrib["publicID"]
    magnitude_id = magnitude.attrib["publicID"]
    lat, lon, depth, mag = [float(value) for value in
                          (qtext(origin, "latitude/value"), qtext(origin, "longitude/value"),
                           qtext(origin, "depth/value"), qtext(magnitude, "mag/value"))]
    if not all(math.isfinite(value) for value in (lat, lon, depth, mag)):
        raise ValueError("Nonfinite catalog value in " + resource_id)
    depth /= 1000
    east, north, x, y = horizontal_coordinates(lat, lon)
    timestamp = qtext(origin, "time/value")
    reasons = []
    if not parse_time(CRITERIA["start_utc_inclusive"]) <= parse_time(timestamp) < parse_time(CRITERIA["end_utc_exclusive"]):
        reasons.append("outside_half_open_time_interval")
    if not 0.2 <= mag <= 4.5:
        reasons.append("outside_magnitude_range")
    if not 37.2 <= lat <= 38.3 or not -122.7 <= lon <= -121.4:
        reasons.append("outside_broad_query_bounds")
    if not 0 <= depth <= 20:
        reasons.append("outside_geoid_depth_range")
    if abs(x) > 10:
        reasons.append("outside_across_strike_corridor")
    if abs(y) > 30:
        reasons.append("outside_along_strike_corridor")
    event_type = qtext(event, "type")
    if event_type != "earthquake":
        reasons.append("unknown_event_type" if not event_type else "non_earthquake_event_type")
    return {
        "event_resource_id": resource_id,
        "provider_event_dataid": event.get(CAT + "dataid", ""),
        "provider_event_datasource": event.get(CAT + "datasource", ""),
        "provider_event_eventid": event.get(CAT + "eventid", ""),
        "origin_resource_id": origin_id, "magnitude_resource_id": magnitude_id,
        "origin_time_utc": normalize_time(timestamp), "origin_time_provider_text": timestamp,
        "latitude_deg": lat, "longitude_deg": lon,
        "geoid_depth_km": depth, "magnitude": mag,
        "magnitude_type": qtext(magnitude, "type"), "event_type": event_type,
        "origin_evaluation_status": qtext(origin, "evaluationStatus"),
        "origin_method_resource_id": qtext(origin, "methodID"),
        "earth_model_resource_id": qtext(origin, "earthModelID"),
        "east_km": east, "north_km": north, "x_km": x, "y_km": y,
        "selected": int(not reasons), "exclusion_reasons": ";".join(reasons),
        "source_file": meta["raw_file"], "source_sha256": meta["sha256"],
        "source_url": meta["requested_url"], "retrieved_utc": meta["retrieved_utc"],
    }


def summaries():
    rows = []
    seen = {}
    query_counts = []
    for year in range(1984, 1999):
        offset = 1
        while True:
            params = {"start": str(year) + "-01-01T00:00:00", "end": str(year + 1) + "-01-01T00:00:00",
                      "minmag": 0.2, "maxmag": 4.5,
                      "minlat": 37.2, "maxlat": 38.3,
                      "minlon": -122.7, "maxlon": -121.4,
                      "catalog": "NCSS", "format": "xml", "includearrivals": "false",
                      "orderby": "time-asc", "limit": 10000, "offset": offset}
            events, meta = fetch_xml("summaries_{}_{:05d}".format(year, offset), params)
            query_counts.append({"year": year, "offset": offset, "count": len(events), "raw_file": meta["raw_file"]})
            for event in events:
                row = event_row(event, meta)
                # Provider end-bound inclusivity is neutralized explicitly.
                if parse_time(row["origin_time_utc"]) >= parse_time(str(year + 1) + "-01-01T00:00:00Z"):
                    continue
                identifier = row["event_resource_id"]
                if identifier in seen:
                    raise ValueError("Duplicate event within half-open summary partitions: " + identifier)
                seen[identifier] = True
                rows.append(row)
            print("summary year={} offset={} returned={} accumulated={}".format(year, offset, len(events), len(rows)), flush=True)
            if len(events) < 10000:
                break
            offset += 10000
    rows.sort(key=lambda row: (row["origin_time_utc"], row["event_resource_id"]))
    selected = [row for row in rows if row["selected"]]
    write_csv(ROOT / "catalog_candidates.csv", rows)
    write_csv(ROOT / "selected_events.csv", selected, list(rows[0]))
    counts = Counter(reason for row in rows for reason in row["exclusion_reasons"].split(";") if reason)
    manifest = {
        "created_utc": utc_now(), "criteria": CRITERIA,
        "summary_queries": query_counts, "candidate_events": len(rows), "selected_events": len(selected),
        "excluded_events": len(rows) - len(selected), "exclusion_reason_counts_nonexclusive": dict(counts),
        "candidate_event_types": dict(Counter(row["event_type"] for row in rows)),
        "unknown_event_type_count": sum(not row["event_type"] for row in rows),
        "selected_event_types": dict(Counter(row["event_type"] for row in selected)),
        "selected_by_year": dict(Counter(row["origin_time_utc"][:4] for row in selected)),
        "selection_manifest_complete": True,
        "pick_acquisition_status": "not started; report candidate counts before fetching",
    }
    write_json(ROOT / "event_selection_manifest.json", manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("criteria", "summary_queries")}, indent=2))


PICK_CRITERIA = {
    "origin": "provider preferred origin matching the retrieved summary",
    "phase": "exact arrival phase P; other phase labels retained as excluded",
    "network": "NC",
    "time_uncertainty_s_inclusive": [0, 0.15],
    "uncertainty_policy": "provider symmetric time/uncertainty required; unknown/nonfinite/negative excluded; no uncertainty imputed",
    "identity_policy": "known network, station, location (empty is valid), three-character channel, event/origin/pick/arrival provider public IDs required",
    "station_epoch_status": "channel metadata matching is a separate stage; no unverified epoch is invented",
    "arrival_time_weight_policy": "retained without additional cutoff; reported explicitly",
    "duplicate_policy": "no phase/channel averaging or silent deduplication; preferred-origin pick associations must be unique",
    "batch_size": 25,
    "fdsn_standard": "https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html",
}


def finite_number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def pick_row(event_id, origin_id, arrival, pick, preferred_origin_id, meta):
    arrival_id = "" if arrival is None else arrival.get("publicID", "")
    pick_id = pick.get("publicID", "")
    waveform = pick.find("q:waveformID", NS)
    attrs = {} if waveform is None else waveform.attrib
    net, sta, loc, cha = [attrs.get(key) for key in
                         ("networkCode", "stationCode", "locationCode", "channelCode")]
    known_codes = bool(net and sta and loc is not None and cha and
                       re.fullmatch(r"[A-Z0-9]{1,2}", net) and
                       re.fullmatch(r"[A-Z0-9]{1,5}", sta) and
                       re.fullmatch(r"[A-Z0-9-]{0,2}", loc) and
                       re.fullmatch(r"[A-Z0-9]{3}", cha))
    phase = "" if arrival is None else qtext(arrival, "phase")
    timestamp = qtext(pick, "time/value")
    uncertainty_text = qtext(pick, "time/uncertainty")
    uncertainty = finite_number(uncertainty_text)
    reasons = []
    if origin_id != preferred_origin_id:
        reasons.append("not_associated_with_preferred_origin")
    if phase != "P":
        reasons.append("not_exact_P_phase" if phase else "unknown_arrival_phase")
    if net != "NC":
        reasons.append("not_NC_network" if net else "unknown_network")
    if uncertainty is None:
        reasons.append("unknown_or_nonfinite_time_uncertainty")
    elif uncertainty < 0 or uncertainty > 0.15:
        reasons.append("outside_time_uncertainty_range")
    if not known_codes:
        reasons.append("missing_or_unsupported_SEED_identity")
    if not all((event_id, origin_id, arrival_id, pick_id)):
        reasons.append("missing_event_origin_arrival_or_pick_resource_id")
    if not timestamp:
        reasons.append("missing_pick_time")
    return {
        "event_resource_id": event_id, "origin_resource_id": origin_id,
        "arrival_resource_id": arrival_id, "pick_resource_id": pick_id,
        "network_code": net or "", "station_code": sta or "",
        "location_code": "" if loc is None else loc, "location_code_present": int(loc is not None),
        "channel_code": cha or "",
        "channel_seed_id": ".".join((net, sta, loc, cha)) if known_codes else "",
        "channel_fdsn_source_id": "FDSN:" + "_".join((net, sta, loc) + tuple(cha)) if known_codes else "",
        "station_fdsn_source_id": "FDSN:" + net + "_" + sta if known_codes else "",
        "channel_identifier_basis": "derived from provider SEED codes using FDSN standard" if known_codes else "",
        "waveform_provider_resource_uri": "" if waveform is None else (waveform.text or "").strip(),
        "phase": phase, "pick_phase_hint": qtext(pick, "phaseHint"),
        "pick_time_utc": normalize_time(timestamp) if timestamp else "", "pick_time_provider_text": timestamp,
        "pick_uncertainty_s": uncertainty_text,
        "pick_lower_uncertainty_s": qtext(pick, "time/lowerUncertainty"),
        "pick_upper_uncertainty_s": qtext(pick, "time/upperUncertainty"),
        "pick_uncertainty_confidence_level": qtext(pick, "time/confidenceLevel"),
        "arrival_time_weight": "" if arrival is None else qtext(arrival, "timeWeight"),
        "arrival_time_residual_s": "" if arrival is None else qtext(arrival, "timeResidual"),
        "arrival_distance_provider_value": "" if arrival is None else qtext(arrival, "distance"),
        "distance_unit_status": "QuakeML schema expects degrees; provider convention not independently verified; unused in selection/inversion",
        "arrival_azimuth_deg": "" if arrival is None else qtext(arrival, "azimuth"),
        "pick_evaluation_mode": qtext(pick, "evaluationMode"),
        "pick_evaluation_status": qtext(pick, "evaluationStatus"),
        "selected": int(not reasons), "exclusion_reasons": ";".join(reasons),
        "source_file": meta["raw_file"], "source_sha256": meta["sha256"],
        "source_url": meta["requested_url"], "retrieved_utc": meta["retrieved_utc"],
    }


def export_picks(rows, events, batches, complete):
    selected = [row for row in rows if row["selected"]]
    selected_pick_ids = [(row["event_resource_id"], row["pick_resource_id"]) for row in selected]
    if len(selected_pick_ids) != len(set(selected_pick_ids)):
        raise ValueError("Duplicate preferred-origin selected pick association; stop for review")
    write_csv(ROOT / "picks_all.csv", rows)
    write_csv(ROOT / "picks_selected.csv", selected, list(rows[0]))
    channels = {}
    for row in selected:
        key = row["channel_seed_id"]
        if key not in channels:
            channels[key] = {field: row[field] for field in
                             ("network_code", "station_code", "location_code", "channel_code",
                              "channel_seed_id", "channel_fdsn_source_id", "station_fdsn_source_id",
                              "channel_identifier_basis")}
            channels[key].update({"first_pick_time_utc": row["pick_time_utc"], "last_pick_time_utc": row["pick_time_utc"], "pick_count": 0})
        channel = channels[key]
        channel["first_pick_time_utc"] = min(channel["first_pick_time_utc"], row["pick_time_utc"])
        channel["last_pick_time_utc"] = max(channel["last_pick_time_utc"], row["pick_time_utc"])
        channel["pick_count"] += 1
    channel_rows = [channels[key] for key in sorted(channels)]
    if channel_rows:
        write_csv(ROOT / "channel_requests.csv", channel_rows)
    all_counts = Counter(row["event_resource_id"] for row in rows)
    selected_counts = Counter(row["event_resource_id"] for row in selected)
    acquired_ids = {event["event_resource_id"] for event in events[:sum(batch["returned_events"] for batch in batches)]}
    write_csv(ROOT / "event_pick_counts.csv", [
        {"event_resource_id": event["event_resource_id"], "origin_resource_id": event["origin_resource_id"],
         "all_arrival_or_unassociated_pick_rows": all_counts[event["event_resource_id"]],
         "selected_P_picks": selected_counts[event["event_resource_id"]],
         "acquired": int(event["event_resource_id"] in acquired_ids)} for event in events])
    manifest = {
        "created_utc": utc_now(), "selection_status": CRITERIA["status"], "criteria": PICK_CRITERIA,
        "acquisition_complete": complete, "selected_catalog_events": len(events), "batch_requests": batches,
        "events_acquired": len(acquired_ids),
        "events_represented_by_pick_rows": len(all_counts), "events_with_selected_picks": len(selected_counts),
        "all_arrival_or_unassociated_pick_rows": len(rows), "selected_P_pick_rows": len(selected),
        "excluded_rows": len(rows) - len(selected),
        "exclusion_reason_counts_nonexclusive": dict(Counter(reason for row in rows for reason in row["exclusion_reasons"].split(";") if reason)),
        "all_phase_counts": dict(Counter(row["phase"] for row in rows)),
        "all_network_counts": dict(Counter(row["network_code"] for row in rows)),
        "all_uncertainty_counts": dict(Counter(row["pick_uncertainty_s"] for row in rows)),
        "unknown_or_nonfinite_uncertainty_rows": sum(finite_number(row["pick_uncertainty_s"]) is None for row in rows),
        "missing_or_unsupported_SEED_identity_rows": sum("missing_or_unsupported_SEED_identity" in row["exclusion_reasons"] for row in rows),
        "selected_zero_uncertainty_count": sum(float(row["pick_uncertainty_s"]) == 0 for row in selected),
        "selected_arrival_time_weight_counts": dict(Counter(row["arrival_time_weight"] for row in selected)),
        "selected_channels": len(channels), "selected_stations": len(set(row["station_fdsn_source_id"] for row in selected)),
        "missing_channel_metadata": "not assessed in this acquisition stage; station/channel epoch join required before inversion",
    }
    write_json(ROOT / "pick_selection_manifest.json", manifest)
    event_manifest = json.loads((ROOT / "event_selection_manifest.json").read_text())
    event_manifest["pick_acquisition_status"] = "complete" if complete else "explicit partial acquisition"
    event_manifest["pick_manifest"] = "pick_selection_manifest.json"
    write_json(ROOT / "event_selection_manifest.json", event_manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("criteria", "batch_requests", "all_uncertainty_counts", "selected_arrival_time_weight_counts")}, indent=2), flush=True)


def picks(max_batches=None):
    events = list(csv.DictReader((ROOT / "selected_events.csv").open()))
    rows, batches = [], []
    size = PICK_CRITERIA["batch_size"]
    for offset in range(0, len(events), size):
        if max_batches is not None and len(batches) >= max_batches:
            break
        batch = events[offset:offset + size]
        identifiers = [row["provider_event_eventid"] for row in batch]
        if any(not value for value in identifiers):
            raise ValueError("Provider event query identity is missing; stop for review")
        params = {"eventid": ",".join(identifiers), "catalog": "NCSS", "format": "xml", "includearrivals": "true"}
        acquired, meta = fetch_xml("picks_{:05d}".format(offset), params)
        expected = {row["event_resource_id"]: row for row in batch}
        if {event.get("publicID") for event in acquired} != set(expected):
            raise ValueError("Requested/returned event identity sets differ in " + meta["raw_file"])
        for event in acquired:
            event_id = event.attrib["publicID"]
            preferred_origin_id = qtext(event, "preferredOriginID")
            if preferred_origin_id != expected[event_id]["origin_resource_id"]:
                raise ValueError("Preferred origin changed between summary and picks: " + event_id)
            current = event_row(event, meta)
            for field in ("latitude_deg", "longitude_deg", "geoid_depth_km", "magnitude"):
                if current[field] != float(expected[event_id][field]):
                    raise ValueError("Catalog value changed between summary and picks: " + event_id + " " + field)
            if parse_time(current["origin_time_utc"]) != parse_time(expected[event_id]["origin_time_utc"]):
                raise ValueError("Origin time changed between summary and picks: " + event_id)
            by_id = {pick.attrib["publicID"]: pick for pick in event.findall("q:pick", NS)}
            associated = set()
            for origin in event.findall("q:origin", NS):
                origin_id = origin.get("publicID", "")
                for arrival in origin.findall("q:arrival", NS):
                    pick_id = qtext(arrival, "pickID")
                    if pick_id not in by_id:
                        raise ValueError("Arrival references an absent pick: " + pick_id)
                    associated.add(pick_id)
                    rows.append(pick_row(event_id, origin_id, arrival, by_id[pick_id], preferred_origin_id, meta))
            for pick_id in sorted(set(by_id) - associated):
                rows.append(pick_row(event_id, "", None, by_id[pick_id], preferred_origin_id, meta))
        batches.append({"offset": offset, "requested_events": len(batch), "returned_events": len(acquired), "raw_file": meta["raw_file"]})
        print("pick batch={} events={}/{} cumulative_rows={}".format(len(batches), offset + len(batch), len(events), len(rows)), flush=True)
    export_picks(rows, events, batches, sum(batch["returned_events"] for batch in batches) == len(events))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["summaries", "picks"])
    parser.add_argument("--max-batches", type=int, help="Explicit diagnostic partial acquisition; manifest remains incomplete")
    parser.add_argument("--offline", action="store_true", help="Rebuild normalized outputs from hash-verified pinned replies; fail if any reply is missing")
    args = parser.parse_args()
    OFFLINE = args.offline
    if args.stage == "summaries":
        summaries()
    else:
        picks(args.max_batches)
