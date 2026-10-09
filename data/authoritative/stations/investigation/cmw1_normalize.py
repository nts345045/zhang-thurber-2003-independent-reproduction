#!/usr/bin/env python3
"""Attach identifiers and test CMW1 historical identities, without solver edits."""
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STANDARD = "https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identities(net, sta, loc, cha):
    return dict(network_code=net, station_code=sta, location_code=loc,
                channel_code=cha, station_seed_id=net + "." + sta,
                station_fdsn_source_id="FDSN:" + net + "_" + sta,
                channel_seed_id=".".join((net, sta, loc, cha)),
                channel_fdsn_source_id="FDSN:" + "_".join((net, sta, loc) + tuple(cha)))


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def attach_text_identities(name, columns, rows, description):
    path = ROOT / name
    sidecar = path.with_suffix(path.suffix + ".identifiers.json")
    data = json.loads(sidecar.read_text())
    assert sha256(path) == data["sha256"]
    data["record_identity_columns"] = columns
    data["record_identities"] = rows
    data["record_count"] = len(rows)
    data["identifier_basis"] = "SEED codes preserved; FDSN identifiers derived by the cited standard, not supplied provider resource IDs."
    data["record_interpretation"] = description
    data["non_xml_scope"] = "Historical metadata/discovery evidence; the parent acquisition normalizer uses the exact CMW1 operation epochs and ELEV under its separately declared sensor-elevation assumption."
    write_json(sidecar, data)


def historical_rows():
    history_path = ROOT / "cmw1_ncsn_historical_stations.txt"
    meta = json.loads(history_path.with_suffix(".txt.provenance.json").read_text())
    format_path = ROOT / "cmw1_ncsn_station_format.txt"
    assert sha256(history_path) == meta["sha256"]
    history_ids, selected = [], []
    for number, line in enumerate(history_path.read_text().splitlines(), 1):
        sta, net = line[:5].strip(), line[5:7].strip()
        cha, provider_loc = line[126:129].strip(), line[130:132].strip()
        assert len(cha) == 3 and net and sta
        loc = "" if provider_loc in ("-", "--") else provider_loc
        ids = identities(net, sta, loc, cha)
        start_date, end_date = line[89:97], line[98:106]
        start_hm, end_hm = line[133:137], line[138:142]
        history_ids.append([number, ids["station_seed_id"], ids["station_fdsn_source_id"],
                            ids["channel_seed_id"], ids["channel_fdsn_source_id"],
                            start_date, start_hm, end_date, end_hm])
        if (net, sta) != ("NC", "CMW1"):
            continue
        epoch_start = datetime.strptime(start_date + start_hm, "%Y%m%d%H%M").strftime("%Y-%m-%dT%H:%M:%SZ")
        epoch_end = datetime.strptime(end_date + end_hm, "%Y%m%d%H%M").strftime("%Y-%m-%dT%H:%M:%SZ")
        row = dict(ids)
        row.update(metadata_epoch_start=epoch_start, metadata_epoch_end=epoch_end,
                   epoch_basis="Provider instrument operation dates/times, GMT; endpoint inclusion unspecified.",
                   provider_start_date=start_date, provider_start_hm=start_hm,
                   provider_end_date=end_date, provider_end_hm=end_hm,
                   provider_data_use_start_date=line[108:116],
                   provider_data_use_end_date=line[117:125],
                   latitude=float(line[30:32]) + float(line[33:40]) / 60.0,
                   longitude=-(float(line[41:44]) + float(line[45:52]) / 60.0),
                   provider_elevation_m=line[54:58].strip(),
                   provider_location_status=line[60],
                   location_status_definition="WGS84 GPS external antenna; self-reported GPS of telemetry antenna.",
                   provider_usgs_channel_code=line[8:11],
                   provider_location_code=provider_loc,
                   sensor_z_geoid_km="",
                   vertical_coordinate_status="unresolved_historical_sensor_elevation",
                   provider_resource_id="",
                   identifier_basis="FDSN source IDs derived from provider SEED codes; provider supplies no resource IDs.",
                   source_file=history_path.name, source_line=number,
                   source_sha256=meta["sha256"], source_url=meta["source_url"],
                   retrieved_utc=meta["retrieved_utc"],
                   format_source_file=format_path.name, format_source_sha256=sha256(format_path))
        selected.append(row)
    return meta, history_ids, selected


def main():
    history_path = ROOT / "cmw1_ncsn_historical_stations.txt"
    meta, history_ids, selected = historical_rows()
    attach_text_identities(history_path.name,
        ["source_line", "station_seed_id", "station_fdsn_source_id", "channel_seed_id", "channel_fdsn_source_id",
         "provider_operation_start_yyyymmdd", "provider_operation_start_hhmm_gmt",
         "provider_operation_end_yyyymmdd", "provider_operation_end_hhmm_gmt"], history_ids,
        "All 14,595 provider channel-history rows. '--' or '-' locations mean empty location. Dates/times remain exact provider text, including far-future sentinels.")
    assert len(selected) == 10
    assert len(set((r["channel_seed_id"], r["metadata_epoch_start"], r["metadata_epoch_end"]) for r in selected)) == 10
    write_csv(ROOT / "cmw1_historical_channel_epochs.csv", selected)

    summary_path = ROOT / "cmw1_ncedc_channel_summary_day.txt"
    summary_ids = []
    for number, line in enumerate(summary_path.read_text().splitlines(), 1):
        if number <= 2:
            continue
        parts = line.split()
        sta, net, cha, loc = parts[:4]
        loc = "" if loc == "--" else loc
        ids = identities(net, sta, loc, cha)
        summary_ids.append([number, ids["station_seed_id"], ids["station_fdsn_source_id"],
                            ids["channel_seed_id"], ids["channel_fdsn_source_id"], parts[5], parts[6]])
    attach_text_identities(summary_path.name,
        ["source_line", "station_seed_id", "station_fdsn_source_id", "channel_seed_id", "channel_fdsn_source_id",
         "provider_epoch_start", "provider_epoch_end"], summary_ids,
        "All channel epochs in the raw NCEDC channel summary, with '--' normalized to the empty location only in identifiers.")

    fed_path = ROOT / "cmw1_earthscope_fedcatalog_all_epochs.txt"
    fed_ids = []
    for number, line in enumerate(fed_path.read_text().splitlines(), 1):
        parts = line.split()
        if len(parts) != 6 or parts[:2] != ["NC", "CMW1"]:
            continue
        net, sta, loc, cha, start, end = parts
        assert not any(c in "".join(parts[:4]) for c in "*?")
        ids = identities(net, sta, "" if loc == "--" else loc, cha)
        fed_ids.append([number, ids["station_seed_id"], ids["station_fdsn_source_id"],
                        ids["channel_seed_id"], ids["channel_fdsn_source_id"], start, end])
    attach_text_identities(fed_path.name,
        ["source_line", "station_seed_id", "station_fdsn_source_id", "channel_seed_id", "channel_fdsn_source_id",
         "routed_request_start", "routed_request_end"], fed_ids,
        "Concrete NSLCs in routed channel requests, not independent epoch verification. No wildcard channels occur in this response.")

    dart_path = ROOT / "cmw1_ncedc_dart_directory.html"
    dart_ids = []
    for number, line in enumerate(dart_path.read_text().splitlines(), 1):
        match = re.search(r'href="([A-Z0-9]{3})\.\.D/"', line)
        if match:
            ids = identities("NC", "CMW1", "", match.group(1))
            dart_ids.append([number, ids["station_seed_id"], ids["station_fdsn_source_id"],
                             ids["channel_seed_id"], ids["channel_fdsn_source_id"]])
    attach_text_identities(dart_path.name,
        ["source_line", "station_seed_id", "station_fdsn_source_id", "channel_seed_id", "channel_fdsn_source_id"],
        dart_ids, "Current DART directory channel names; directory entries do not establish historical epoch coverage.")

    picks_path = ROOT.parent.parent / "hayward" / "picks_selected.csv"
    picks_sha = sha256(picks_path)
    with picks_path.open() as handle:
        picks = [p for p in csv.DictReader(handle) if (p["network_code"], p["station_code"]) == ("NC", "CMW1")]
    matches = []
    for pick in picks:
        found = [r for r in selected if r["channel_seed_id"] == pick["channel_seed_id"]
                 and r["metadata_epoch_start"] <= pick["pick_time_utc"] < r["metadata_epoch_end"]]
        row = dict((key, pick[key]) for key in ("event_resource_id", "origin_resource_id", "arrival_resource_id",
                   "pick_resource_id", "network_code", "station_code", "location_code", "channel_code",
                   "channel_seed_id", "channel_fdsn_source_id", "pick_time_utc", "arrival_time_weight"))
        row.update(match_count=len(found), matched_history_source_lines=";".join(str(r["source_line"]) for r in found),
                   history_source_file=history_path.name, history_source_sha256=meta["sha256"],
                   history_source_url=meta["source_url"], picks_source_file="../../hayward/picks_selected.csv",
                   picks_source_sha256=picks_sha)
        matches.append(row)
    assert len(matches) == 142 and all(r["match_count"] == 1 for r in matches)
    assert len(set(r["pick_resource_id"] for r in matches)) == len(matches)
    write_csv(ROOT / "cmw1_historical_pick_matches.csv", matches)
    counts = Counter(r["channel_seed_id"] for r in matches)
    result = dict(station_seed_id="NC.CMW1", station_fdsn_source_id="FDSN:NC_CMW1",
                  channel_fdsn_source_ids=sorted(set(r["channel_fdsn_source_id"] for r in matches)),
                  historical_identity_rows=len(history_ids), channel_summary_identity_rows=len(summary_ids),
                  fedcatalog_request_identity_rows=len(fed_ids), cmw1_historical_channel_epochs=len(selected),
                  cmw1_picks=len(matches), unique_matches=len(matches), missing_matches=0, overlapping_matches=0,
                  picks_per_channel=dict(sorted(counts.items())),
                  positive_association_weight_picks=sum(float(r["arrival_time_weight"]) > 0 for r in matches),
                  minimum_pick_time_utc=min(r["pick_time_utc"] for r in matches),
                  maximum_pick_time_utc=max(r["pick_time_utc"] for r in matches),
                  historical_source_sha256=meta["sha256"], picks_source_sha256=picks_sha,
                  derived_identifier_standard=STANDARD,
                  original_investigation_state=dict(
                      vertical_coordinate_status="Historical master does not separately identify sensor elevation or burial depth.",
                      historical_epoch_csv="cmw1_historical_channel_epochs.csv",
                      description="Investigation CSV preserves source ambiguity with sensor_z blank; adopted model coordinates are recorded separately."),
                  current_adopted_metadata=dict(
                      metadata_file="../channel_epochs.csv", metadata_readme="../README.md",
                      matching_summary_file="../matching_summary.json",
                      vertical_coordinate_status="historical_elevation_interpreted_as_sensor_explicit_assumption",
                      provider_elevation_m=214, sensor_z_geoid_km=-0.214,
                      historical_sensor_burial_depth_m=None,
                      assumption="Historical ELEV used unchanged as receiver elevation; its sensor interpretation is consistent with later Channel/Elevation=214m, not independently survey verified.",
                      location_status_preserved="E: external GPS antenna",
                      vertical_datum_basis="Historical format describes GPS-site elevations as geoid referenced; no numerical datum conversion imposed.",
                      later_stationxml_depth_backfilled=False,
                      operation_epochs_distinct_from_response_epochs=True,
                      inversion_execution_status="Not established by metadata review; consult inversion run records."))
    write_json(ROOT / "cmw1_historical_match_summary.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
