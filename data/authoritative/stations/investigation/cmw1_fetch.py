#!/usr/bin/env python3
"""Save exact CMW1 investigation responses; never change solver metadata."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
NS = {"s": "http://www.fdsn.org/xml/station/1"}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def fetch(name, url):
    if not name.startswith("cmw1_") or Path(name).name != name:
        raise ValueError("Use a CMW1-owned filename")
    path = ROOT / name
    provenance = path.with_suffix(path.suffix + ".provenance.json")
    if path.exists():
        raw = path.read_bytes()
        meta = json.loads(provenance.read_text())
        if meta["source_url"] != url or meta["sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError("Pinned cache differs from request/hash")
    else:
        try:
            response = urlopen(Request(url, headers={"User-Agent": "IndependentTomographyReproduction/1.0"}), timeout=120)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            meta = {"source_url": url, "final_url": response.geturl(),
                    "http_status": response.status, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                    "content_type": response.headers.get("Content-Type"), "raw_file": name}
        path.write_bytes(raw)
        write_json(provenance, meta)
    identifiers = []
    if raw.lstrip().startswith(b"<?xml") or raw.lstrip().startswith(b"<FDSNStationXML"):
        root = ET.fromstring(raw)
        for network in root.findall("s:Network", NS):
            for station in network.findall("s:Station", NS):
                net, sta = network.get("code"), station.get("code")
                station_id = "FDSN:" + net + "_" + sta
                identifiers.append({"kind": "returned_station", "station_seed_id": net + "." + sta,
                                    "station_fdsn_source_id": station_id, "epoch_start": station.get("startDate"),
                                    "epoch_end": station.get("endDate"), "provider_source_id": station.get("sourceID")})
                for channel in station.findall("s:Channel", NS):
                    loc, cha = channel.get("locationCode"), channel.get("code")
                    identifiers.append({"kind": "returned_channel", "network_code": net, "station_code": sta,
                                        "location_code": loc, "channel_code": cha,
                                        "channel_seed_id": ".".join((net, sta, loc, cha)),
                                        "channel_fdsn_source_id": "FDSN:" + "_".join((net, sta, loc) + tuple(cha)),
                                        "epoch_start": channel.get("startDate"), "epoch_end": channel.get("endDate"),
                                        "provider_source_id": channel.get("sourceID"),
                                        "provider_resource_id": channel.get("resourceId")})
    sidecar = dict(meta, investigation_station_seed_id="NC.CMW1", investigation_station_fdsn_source_id="FDSN:NC_CMW1",
                   investigation_identity_basis="Derived from NC.CMW1 codes already present in provider picks; a query target does not prove metadata exists.",
                   derived_identifier_standard="https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html",
                   returned_stationxml_identities=identifiers,
                   non_xml_scope="Non-XML replies are preserved discovery evidence, not normalized channel-epoch inputs.")
    write_json(path.with_suffix(path.suffix + ".identifiers.json"), sidecar)
    print(name, meta["http_status"], len(raw), "bytes", len(identifiers), "StationXML identities", flush=True)
    if len(raw) < 1000:
        print(raw.decode("utf-8", "replace"), flush=True)
    return raw, meta


if __name__ == "__main__":
    fetch(sys.argv[1], sys.argv[2])
