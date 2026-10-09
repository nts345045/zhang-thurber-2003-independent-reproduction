#!/usr/bin/env python3
"""Index saved USGS discovery records without changing their source bytes."""
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
NS = {"q": "http://quakeml.org/xmlns/bed/1.2"}
CATALOG = "{http://anss.org/xmlns/catalog/0.1}"


def read_json(name):
    return json.loads((ROOT / name).read_text())


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")


def text(element, path):
    node = element.find("/".join("q:" + part for part in path.split("/")), NS)
    return node.text if node is not None and node.text is not None else ""


def waveform_ids(element):
    node = element.find("q:waveformID", NS)
    if node is None:
        return {}
    net, sta, loc, cha = (node.get(key) for key in
                          ("networkCode", "stationCode", "locationCode", "channelCode"))
    if not net or not sta or loc is None or not cha or len(cha) != 3:
        raise ValueError("Incomplete SEED identity: " + repr(node.attrib))
    return {"network_code": net, "station_code": sta, "location_code": loc,
            "channel_code": cha, "seed_id": ".".join((net, sta, loc, cha)),
            "station_resource_id": "FDSN:" + net + "_" + sta,
            "channel_resource_id": "FDSN:" + "_".join((net, sta, loc) + tuple(cha)),
            "channel_identifier_basis": "FDSN standard mapping of provider SEED codes"}


def source_record(name, provenance_name):
    raw = (ROOT / name).read_bytes()
    provenance = read_json(provenance_name)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != provenance["sha256"]:
        raise ValueError("Source hash changed: " + name)
    return {"raw_file": name, "raw_sha256": digest,
            "source_url": provenance["requested_url"],
            "retrieved_utc": provenance["retrieved_utc"]}


def main():
    xml_name = "usgs_nc216859_phases.xml"
    source = source_record(xml_name, "usgs_nc216859_phases.provenance.json")
    tree = ET.parse(str(ROOT / xml_name)).getroot()
    event = tree.find(".//q:event", NS)
    event_id = event.attrib["publicID"]
    parents = {child: parent for parent in tree.iter() for child in parent}
    resources = []
    for node in tree.iter():
        if "publicID" not in node.attrib:
            continue
        parent = parents.get(node)
        while parent is not None and "publicID" not in parent.attrib:
            parent = parents.get(parent)
        row = {"element_type": node.tag.rsplit("}", 1)[-1],
               "resource_id": node.attrib["publicID"],
               "resource_id_basis": "provider QuakeML publicID",
               "parent_resource_id": parent.get("publicID") if parent is not None else None}
        row.update(waveform_ids(node))
        resources.append(row)
    ids = [row["resource_id"] for row in resources]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("Empty or duplicate provider resource IDs")
    id_set = set(ids)
    # Check object references, excluding method/model URIs referring to external resources.
    object_refs = {"pickID", "originID", "magnitudeID", "amplitudeID",
                   "stationMagnitudeID", "preferredOriginID", "preferredMagnitudeID"}
    for node in tree.iter():
        if node.tag.rsplit("}", 1)[-1] in object_refs and node.text not in id_set:
            raise ValueError("Unresolved QuakeML object reference: " + str(node.text))
    write_json(xml_name + ".identifiers.json", dict(source, resources=resources,
               event_resource_id=event_id, scope="Service discovery; not manuscript input selection"))

    picks = {node.attrib["publicID"]: node for node in event.findall("q:pick", NS)}
    observations = []
    for origin in event.findall("q:origin", NS):
        for arrival in origin.findall("q:arrival", NS):
            pick_id = text(arrival, "pickID")
            pick = picks[pick_id]
            row = {"event_resource_id": event_id,
                   "origin_resource_id": origin.attrib["publicID"],
                   "arrival_resource_id": arrival.attrib["publicID"],
                   "pick_resource_id": pick_id}
            row.update(waveform_ids(pick))
            row.update({"phase": text(arrival, "phase"),
                        "pick_time_utc": text(pick, "time/value"),
                        "pick_uncertainty_s": text(pick, "time/uncertainty"),
                        "source_file": xml_name, "source_url": source["source_url"]})
            observations.append(row)
    if not observations or len({row["pick_resource_id"] for row in observations}) != len(picks):
        raise ValueError("Missing or unassociated picks in discovery sample")
    with (ROOT / "usgs_nc216859_picks.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(observations)

    geo_name = "usgs_nc216859.geojson"
    geo_source = source_record(geo_name, "usgs_nc216859.provenance.json")
    geo = read_json(geo_name)
    if geo["id"] != event.attrib[CATALOG + "dataid"]:
        raise ValueError("GeoJSON and QuakeML event identities disagree")
    write_json(geo_name + ".identifiers.json", dict(geo_source,
               comcat_event_id=geo["id"], event_resource_id=event_id,
               event_resource_id_source_file=xml_name,
               event_url=geo["properties"]["url"],
               catalog_aliases=[value for value in geo["properties"]["ids"].split(",") if value],
               product_resource_ids=[product["id"] for products in geo["properties"]["products"].values()
                                     for product in products],
               scope="Service discovery; not manuscript input selection"))
    print("Verified {} provider resource IDs, {} picks with full SEED/FDSN identities, "
          "and unchanged raw-file hashes.".format(len(resources), len(observations)))


if __name__ == "__main__":
    main()
