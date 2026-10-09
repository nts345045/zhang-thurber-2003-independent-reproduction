# Channel metadata for the independent Hayward subset

These station records support the independently selected event/pick cohort in `../hayward/`. They do not establish the manuscript's original station subset.

## Acquisition status and required clarification

Acquisition returned 4,970 channel epochs representing 511 NSLCs. Of 42,236 selected picks, 42,094 have unique metadata matches and 142 have none; no overlapping matches were found. The helper stopped at this check. These data have not been used in an inversion. New observational queries are paused while the user clarifies the following cases.

All 142 unmatched picks belong to `NC.CMW1` (`FDSN:NC_CMW1`) during 1995-08-23 through 1998-12-22, across 142 events. Channel counts are `NC.CMW1..HN1` 129, `..EP3` 4, `..HN3` 3, `..HV1` 3, `..EP2` 2, and `..HN2` 1. Of these picks, 138 have positive provider arrival-association weights and four have zero weights. The saved [NCEDC request and response](raw/ncedc_channels_NC_26a85a0b6a04.xml) explicitly requested `CMW1` but returned no metadata for it. Its [provenance](raw/ncedc_channels_NC_26a85a0b6a04.xml.provenance.json) records the complete URL and hash. No station name or coordinates have been substituted. The provider's distance values are not used to infer coordinates or selection; their units require separate clarification.

Thirty returned epochs at three stations have nonzero burial depth, but their channel elevation equals station elevation. This raises a provider-convention question relative to the generic StationXML sensor-elevation definition below. Seventeen of the 18 returned channels are used by 322 selected picks, of which 289 have positive association weights. All three stations lie inside the proposed Hayward model's horizontal bounds:

| Station resource ID | Channel/station elevation (m) | Burial depth (m) | Selected picks | Positive association weights |
| --- | ---: | ---: | ---: | ---: |
| `FDSN:NC_CCH1` | 107 | 119 | 134 | 125 |
| `FDSN:NC_CGP1` | 219 | 121 | 115 | 114 |
| `FDSN:NC_CSU1` | 375 | 124 | 73 | 50 |

The raw records are in [the CCH1/CGP1 response](raw/ncedc_channels_NC_987aa2b70b3c.xml) and [the CSU1 response](raw/ncedc_channels_NC_26a85a0b6a04.xml), with channel/epoch IDs in their sidecars. These 30 records have `vertical_coordinate_status=ambiguous_provider_borehole_elevation_convention` and a blank `sensor_z_geoid_km`, so a solver cannot silently adopt either interpretation. The explicitly conditional columns `z_if_sensor_elevation_km` and `z_if_ground_elevation_km` retain the two calculations. They differ by the 119–124 m burial depths; neither resolves the provider convention.

`metadata_clarification.json` preserves per-channel counts, all affected event/origin/arrival/pick IDs, metadata epoch IDs and raw-response links. `matching_summary.json` and `pick_epoch_matches.csv` retain the complete join outcome. No missing epoch or unresolved burial convention is silently repaired.

## Rebuilding the acquisition and join

After event/pick acquisition has written `../hayward/channel_requests.csv` and `../hayward/picks_selected.csv`, run from the repository root:

```bash
python3 data/authoritative/stations/acquire.py acquire
```

Use `acquire --offline` to regenerate normalized metadata and sidecars from the pinned raw-response cache without permitting network retrieval. The unresolved metadata matches intentionally still produce a nonzero exit status after writing the diagnostic files.

The helper first asks the [EarthScope federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/) for station-service routing, then requests [NCEDC StationXML](https://service.ncedc.org/fdsnws/station/1/) for batches of 25 stations and the relevant pick-time interval. It retrieves channel metadata, not waveform samples or full instrument responses. Channel epochs from the station batches can include channels unused by the selected picks; the pick-to-epoch join identifies the used records.

Raw replies under `raw/` are preserved unchanged. Their sibling `.provenance.json` files record the exact request URL, retrieval UTC, status, byte length, and SHA-256 hash. Cached replies are reused only after checking their request URL and hash. `.identifiers.json` sidecars attach SEED names, standardized FDSN identifiers, provider IDs where present, metadata epochs, and raw-file links. IDs derived under the [FDSN Source Identifiers standard](https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html) are explicitly distinguished from identifiers present in the provider's XML. Empty location codes remain empty, for example `NC.BAV..EHZ` and `FDSN:NC_BAV__E_H_Z`.

`channel_epochs.csv` preserves network/station/location/channel codes, the channel and station source identifiers, coordinates, station elevation, channel sensor elevation, burial depth, parent and channel epoch bounds, and raw-response provenance. `metadata_epoch_start/end` are the intersection of the supplied network, station, and channel epochs. Matching uses a start-inclusive, end-exclusive interval; an absent end means unbounded. Epochs sharing an NSLC are retained separately.

`pick_epoch_matches.csv` preserves event and pick resource IDs and links each pick to its NSLC, FDSN channel identifier, metadata epoch, and raw response. `matching_summary.json` records counts and any missing or overlapping matches. Such matches stop processing for clarification rather than silently choosing a station epoch. Rerun only this local join with:

```bash
python3 data/authoritative/stations/acquire.py match
```

The [StationXML reference](https://docs.fdsn.org/projects/stationxml/en/latest/reference.html) defines `Channel/Elevation` as sensor elevation and `Channel/Depth` as burial depth below local ground. Under that convention, model depth is `-channel_sensor_elevation_m / 1000`, positive downward. Burial depth is preserved independently. The alternative interpretation treats the elevation field as ground elevation and gives `(burial_depth - elevation) / 1000`; ambiguous records retain both conditional values with no solver depth assigned. The [NCEDC depth-datum documentation](https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html) places station elevations and event depths on the same geoid datum. StationXML supplies no explicit per-channel vertical datum, so its documentary basis is recorded separately. Latitude/longitude datum attributes are preserved; absent attributes use the explicit StationXML WGS84 default.
