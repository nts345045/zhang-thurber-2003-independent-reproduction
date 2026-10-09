#!/usr/bin/env python3
"""Archive USGS terrain corroboration; never assign seismic sensor coordinates."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent
STATIONS = ROOT.parent


def run():
    with (STATIONS / "channel_epochs.csv").open() as f:
        epochs = list(csv.DictReader(f))
    for station in ("CCH1", "CGP1", "CSU1"):
        rows = [r for r in epochs if r["station_seed_id"] == "NC." + station]
        coordinates = {(r["latitude_deg"], r["longitude_deg"]) for r in rows}
        if len(coordinates) != 1:
            raise ValueError("Terrain query requires one explicit coordinate per station")
        lat, lon = coordinates.pop()
        params = dict(x=lon, y=lat, units="Meters", wkid="4326", includeDate="true")
        url = "https://epqs.nationalmap.gov/v1/json?" + urlencode(params)
        path = ROOT / ("terrain_usgs_NC_" + station + ".json")
        provenance = path.with_suffix(".json.provenance.json")
        if path.exists():
            raw = path.read_bytes()
            meta = json.loads(provenance.read_text())
            if meta["url"] != url or meta["sha256"] != hashlib.sha256(raw).hexdigest():
                raise ValueError("Cached terrain query differs from provenance")
        else:
            try:
                response = urlopen(Request(url, headers={"User-Agent": "IndependentTomographyReproduction/1.0"}), timeout=45)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read()
                meta = dict(url=url, final_url=response.geturl(), http_status=response.status,
                            retrieved_utc=datetime.now(timezone.utc).isoformat(),
                            bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), source_file=path.name,
                            query_parameters=params,
                            purpose="Terrain corroboration only; not sensor coordinates or survey evidence")
            path.write_bytes(raw)
            provenance.write_text(json.dumps(meta, indent=2) + "\n")
        identifiers = dict(meta,
            station_seed_id="NC." + station, station_fdsn_source_id="FDSN:NC_" + station,
            identifier_basis="FDSN identifiers derived from authoritative SEED codes; USGS EPQS supplies no seismic station ID",
            coordinate_source_file="../channel_epochs.csv",
            coordinate_source_sha256=hashlib.sha256((STATIONS / "channel_epochs.csv").read_bytes()).hexdigest(),
            input_horizontal_reference="WGS84 from station metadata, explicitly requested with wkid=4326",
            vertical_datum_note="USGS documents CONUS DEM elevations as NAVD88; the point response supplies no explicit vertical datum. No conversion to geoid or ellipsoid was performed.",
            role="independent interpolated ground-surface check, not an authoritative sensor elevation or surveyed well-head height",
            channel_epochs=[{k: r[k] for k in ("network_code", "station_code", "location_code", "channel_code",
                "channel_seed_id", "channel_fdsn_source_id", "metadata_epoch_start", "metadata_epoch_end",
                "source_file", "source_sha256")} for r in rows])
        path.with_suffix(".json.identifiers.json").write_text(json.dumps(identifiers, indent=2) + "\n")
        print(station, meta["http_status"], raw.decode("utf-8", "replace"))


if __name__ == "__main__":
    run()
