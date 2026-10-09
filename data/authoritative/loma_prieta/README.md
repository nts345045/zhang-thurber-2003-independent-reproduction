# Independent authoritative Loma Prieta geometry

Acquisition completed on 2026-10-09 with **724 earthquakes and 52 NC EHZ receiver channels at 52 stations**. These are independently selected authoritative coordinates for a later synthetic experiment. They are not an identified manuscript cohort. No observed arrivals, synthetic travel times, simulation, or inversion were produced by this acquisition.

| Records | Queried candidates | Selected | Excluded and preserved |
| --- | ---:| ---:| ---:|
| Catalog events | 823 | 724 | 99 |
| Channel metadata epochs | 355 | 52 | 303 |

The event and station manifests record the complete criteria, query counts, prior USGS/EarthScope discovery, and normalization-script hashes. All candidates retain their resource IDs, source hashes, selection flags and exclusion reasons. Exclusion reasons can overlap: event counts include 53 outside the depth range, 35 outside Y, 22 outside X, and four quarry blasts; receiver exclusions are horizontal-domain checks.

## Event selection and coordinate origin

NCEDC NCSS preferred catalog origins and magnitudes were queried with no cohort cap. The selection is unchanged from the previously documented plan:

- Origin time from 1989-10-18 00:00:00 UTC inclusive to 1989-11-18 00:00:00 UTC exclusive; magnitude 2.0–5.5 inclusive.
- Broad query rectangle 36.5–37.6 degrees N and −122.6 to −121.2 degrees longitude. Retain explicit earthquake type and current catalog geoid depth 0–16 km.
- Local coordinates X from −15 to 20 km and Y from −45 to 25 km, inclusive.

The projection origin is latitude 37.0361667 degrees, longitude −121.8798333 degrees, verified against the pinned [USGS mainshock GeoJSON](../discovery/usgs_nc216859.geojson) and [QuakeML](../discovery/usgs_nc216859_phases.xml). The provider event and origin IDs are `quakeml:nc.anss.org/Event/NC/216859` and `quakeml:nc.anss.org/Origin/NC/2642104`. Both raw-file hashes are checked before either acquisition stage.

Geographic positions at zero ellipsoid height are converted to WGS84 ECEF coordinates and projected onto the origin's tangent east and north directions. A 45-degree rotation gives `X=(E+N)/sqrt(2)` and `Y=(-E+N)/sqrt(2)`. The rotation and selection windows are independent choices, not recovered from the paper's maps. Catalog geoid depth is retained separately from this horizontal construction. Native event, preferred-origin and preferred-magnitude resource IDs remain attached to each coordinate record.

## Receiver snapshot and elevation convention

EarthScope's federated catalog routed the 1989-11-01 00:00:00 UTC snapshot to the authoritative NCEDC station service. The query requested network NC, EHZ channels and all valid locations. Effective channel epochs contain the snapshot under `start <= time < end`; no end denotes an open interval. All 52 selected NSLCs have one active epoch, with no overlap. These frozen receiver coordinates define the planned synthetic geometry; the acquisition does not establish which receivers recorded each selected earthquake.

The receiver domain is X from −35 to 35 km and Y from −60 to 40 km. All channels in this horizontal domain were retained. Receiver model depth is `−Channel/Elevation/1000`, positive downward, following StationXML sensor-elevation semantics and the documented [metadata interpretation](../stations/README.md). Channel elevation, station elevation and burial depth remain separate. No burial correction is applied twice and no numerical datum conversion is inferred.

Selected sensor depths range from −0.921 to −0.039 km; all 52 records report zero burial depth. The planned grid extension `min(-1, floor(minimum sensor z))` therefore gives a suggested top of −1 km, preserving every selected receiver above the geoid. This acquisition did not construct that grid. NCEDC documents catalog depths and station elevations on a common geoid reference; StationXML has no explicit per-channel vertical-datum field. These are provider-declared coordinates, not independently surveyed positions.

## Comparison with the written experiment

The manuscript's synthetic experiment uses real Loma Prieta source and receiver geometry. Its exact input roster and a verified original synthetic-cohort count have not been established in this review, so no original-count agreement is claimed. Our month-long event window, magnitude/depth limits, 45-degree projection, station snapshot and NC EHZ restriction are disclosed independent choices. The repository's earlier 120-source/32-station random baseline is not evidence of manuscript cohort size. No map coordinates were digitized and no author code, input deck or numerical output was used.

## Files and reproducibility

`catalog_candidates.csv` and `selected_events.csv` preserve event geometry and native event/origin/magnitude IDs. `channel_candidates.csv` and `selected_channels.csv` preserve SEED NSLC, derived FDSN station/channel identifiers, provider IDs where supplied, effective epochs, coordinates and metadata provenance. Empty location codes are preserved. FDSN identifiers derived from SEED codes are distinguished from provider-supplied resource IDs. Routing selectors identify requests and are not fabricated channel identities.

The three raw responses under `raw/` are unchanged, with exact URLs, retrieval UTC, HTTP status, SHA-256 and identifier sidecars. [Acquisition checks](acquisition_checks.json) record identity, epoch, exclusion-preservation and hash checks. Offline rebuilds reproduced all four normalized CSVs and three raw-response hashes exactly; manifest creation times may change.

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 data/authoritative/loma_prieta/acquire.py events --offline
PYTHONDONTWRITEBYTECODE=1 python3 data/authoritative/loma_prieta/acquire.py stations --offline
```

Omitting `--offline` permits retrieval only when a pinned reply is absent. Cached responses must still match their URL and hash. The helper writes inside this directory and reuses the project's time, projection, provenance, identifier and StationXML parsers. The historical station snapshot is not a request for calibrated instrument responses or waveform samples.

Service references: [NCEDC event service](https://service.ncedc.org/fdsnws/event/1/), [EarthScope federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/), [StationXML reference](https://docs.fdsn.org/projects/stationxml/en/latest/reference.html), [NCEDC depth datum](https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html).
