# Independent Loma Prieta geometry: acquisition pending

The user authorized an independent authoritative subset for the synthetic
experiment. `acquire.py` implements the selection below, but **no Loma Prieta
catalog or station request has been made by this helper**. Acquisition was
paused on 2026-10-09 after the separate Hayward metadata review found missing
channel epochs and an unresolved elevation convention for buried sensors.
The prepared script is syntax checked only. No geometry count or successful
metadata match is claimed here.

## Prepared event selection

The NCEDC NCSS preferred catalog origins and magnitudes will be queried for:

- Origin time from 1989-10-18 00:00:00 UTC inclusive to 1989-11-18 00:00:00
  UTC exclusive, and magnitude 2.0--5.5 inclusive.
- Broad query rectangle 36.5--37.6 degrees N and -122.6 to -121.2 degrees
  longitude; explicit earthquake type; current geoid depth 0--16 km.
- Local coordinates X from -15 to 20 km and Y from -45 to 25 km, inclusive.

The local horizontal origin is 37.0361667 degrees N, -121.8798333 degrees
longitude, taken from the already retrieved USGS mainshock record in
`../discovery/usgs_nc216859.geojson`. Its native event and origin IDs are
`quakeml:nc.anss.org/Event/NC/216859` and
`quakeml:nc.anss.org/Origin/NC/2642104`. The mainshock location defines the
coordinate origin; the stated time, magnitude, depth, and geometric filters
define the aftershock subset separately.

Horizontal geographic positions at zero ellipsoid height are converted to
WGS84 ECEF coordinates and projected onto the origin's tangent east and north
directions. A 45-degree rotation gives `X=(E+N)/sqrt(2)` and
`Y=(-E+N)/sqrt(2)`. This rotation and all selection windows are independent
choices. They were not recovered from the paper's maps. Catalog geoid depths
are retained separately from this horizontal construction.

All candidates, native event/origin/magnitude IDs, decisions, and exclusion
reasons will be exported. Query pagination has no cohort cap. Only event
geometry is requested; observations for a later synthetic experiment must be
generated and identified as synthetic.

## Prepared receiver selection and unresolved vertical convention

The requested historical snapshot is 1989-11-01 00:00:00 UTC, for network NC
and EHZ channels at all valid locations. EarthScope's federated catalog is the
first station-discovery service; the returned NCEDC route supplies channel
StationXML. Effective channel epochs must contain the snapshot under the
half-open convention `start <= time < end`. Overlapping active epochs for one
NSLC identity stop acquisition for review.

The intended receiver domain is X from -35 to 35 km and Y from -60 to 40 km.
All channels in this horizontal domain will be retained, and their sensor
depth range will be reported before choosing the above-geoid grid extension.
The proposed top is `min(-1, floor(minimum sensor z))` km. A sensor below
16 km would require review before any vertical exclusion.

The current helper reuses the station parser's generic StationXML convention:
sensor Z equals minus Channel/Elevation, divided by 1000. The Hayward review
has identified provider records whose burial depth may make that convention
inappropriate. Therefore this part of the prepared helper must be reconciled
with the user's resolution of the metadata issue before use. Station elevation,
channel elevation, burial depth, and provider identifiers remain separate
fields; no missing epoch or elevation is invented.

## Rebuild design

The helper reuses time/provenance utilities from `../hayward/acquire.py` and
the identifier/StationXML parser from `../stations/acquire.py`; it writes only
inside this directory. The `events` and `stations` stages will save unchanged
raw replies with request URLs, UTC times, SHA-256 hashes, and identifier
sidecars. `--offline` will verify and normalize only pinned replies, failing
before network access if a reply is absent. These commands have not yet been
run. The later completed manifest must replace this pending status.

Written API references inspected 2026-10-09:
[NCEDC event service](https://service.ncedc.org/fdsnws/event/1/),
[EarthScope federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/),
[StationXML reference](https://docs.fdsn.org/projects/stationxml/en/latest/reference.html).
