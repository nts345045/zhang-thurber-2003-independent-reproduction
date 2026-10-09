# Channel metadata for the independent Hayward subset

These station records support the independently selected event/pick cohort in `../hayward/`. They do not establish the manuscript's original station subset.

## Metadata investigation and adopted interpretation

The user requested metadata investigation before exclusions, with documented study exclusions omitted from reproduction but preserved for a later additional-data comparison. The [written-source review](investigation/study_membership.md) found no evidence establishing inclusion or exclusion of `NC.CMW1`, `NC.CCH1`, `NC.CGP1`, or `NC.CSU1` in the manuscript cohort. Their membership remains **unknown**. No station is excluded on a study-membership claim.

The original StationXML retrieval supplied 4,970 epochs and left 142 CMW1 picks unmatched. Targeted EarthScope and NCEDC queries found that their StationXML coverage begins in 2000. The authoritative [NCSN station-history file](https://ncedc.org/pub/doc/ncsn/ncsn.stations) explicitly supplies historical SEED channel names and operation dates. Its ten CMW1 operation epochs have now been added, giving **4,980 epochs, 521 NSLCs, and unique matches for all 42,236 selected picks**. No alias or backward extension of modern StationXML was used. The [CMW1 investigation](investigation/cmw1_report.md) preserves the exact records and all 142 identified pick matches.

| Station SEED name | Derived station resource ID | Adopted elevation (m) | Model z (km, downward positive) | Initial selected picks |
| --- | --- | ---: | ---: | ---: |
| NC.CCH1 | FDSN:NC_CCH1 | 107 | −0.107 | 134 |
| NC.CGP1 | FDSN:NC_CGP1 | 219 | −0.219 | 115 |
| NC.CSU1 | FDSN:NC_CSU1 | 375 | −0.375 | 73 |
| NC.CMW1 | FDSN:NC_CMW1 | 214 | −0.214 | 142 |

For CCH1/CGP1/CSU1, the current provider `Channel/Elevation` is used as sensor elevation under StationXML semantics; burial depth is not subtracted again. Equality with `Station/Elevation` alone does not demonstrate a provider error. Historical BSL wellhead tables conflict: later values exceed earlier ones by exactly one burial depth. Their ellipsoid labels also differ from the provider's stated geoid convention. The [elevation review](investigation/borehole_elevations.md) records these conflicts and the USGS terrain corroboration. These are provider-declared coordinates, not independently surveyed sensor positions; no inferred datum correction is applied.

For CMW1, the historical `ELEV=214 m` is used unchanged as receiver elevation. **Interpreting this field as sensor elevation is an explicit assumption**, consistent with the later StationXML value but not independently verified by it. The history's external-GPS-antenna location flag `E` is preserved. Historical burial depth and StationXML-specific elevation fields remain blank; the later 155 m burial depth is not backfilled. Historical dates identify instrument operation epochs, not calibrated response epochs. All selected picks fall strictly inside those intervals, so unspecified endpoint inclusion does not affect their matches.

`channel_epochs.csv` records these source types, epoch bases, interpretation flags and provenance. `pick_epoch_matches.csv` preserves every event/origin/arrival/pick identity and matching metadata source. `metadata_clarification.json` retains the original issue snapshot plus the adopted investigation outcome. No raw response or pick was deleted or altered.

## Reproduction and additional-data selections

`study_station_policy.csv` records investigated stations and written evidence. Unknown or unlisted membership does not cause exclusion. A confirmed inclusion/exclusion requires an evidence URL, locator and summary. The default preparation omits only documented study exclusions, in addition to its separately declared quality and model-domain filters:

```bash
python3 prepare_hayward.py --selection reproduction
```

A later comparison can restore the eligibility of documented study-excluded stations while retaining the same metadata and other selection checks, writing a separate directory:

```bash
python3 prepare_hayward.py --selection additional
```

These write `data/hayward/` and `data/hayward_additional/` respectively. All acquired observations remain under `data/authoritative/`; prepared `excluded_picks.csv` files retain identities and explicit reasons. Currently there are no confirmed study exclusions, so these two station-policy choices alone do not select different observations. The additional run has not been performed.

## Rebuilding the acquisition and join

After event/pick acquisition has written `../hayward/channel_requests.csv` and `../hayward/picks_selected.csv`, run from the repository root:

```bash
python3 data/authoritative/stations/acquire.py acquire
```

Use `acquire --offline` to regenerate normalized metadata and sidecars from the pinned raw-response cache without permitting network retrieval. The current pinned inputs pass the complete join. Any future missing or overlapping match still produces a nonzero exit status after writing diagnostics.

The helper first asks the [EarthScope federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/) for station-service routing, then requests [NCEDC StationXML](https://service.ncedc.org/fdsnws/station/1/) for batches of 25 stations and the relevant pick-time interval. It retrieves channel metadata, not waveform samples or full instrument responses. Channel epochs from the station batches can include channels unused by the selected picks; the pick-to-epoch join identifies the used records. Offline normalization also parses the pinned NCSN historical file through `investigation/cmw1_normalize.py`; it does not extend modern response epochs.

Raw replies under `raw/` are preserved unchanged. Their sibling `.provenance.json` files record the exact request URL, retrieval UTC, status, byte length, and SHA-256 hash. Cached replies are reused only after checking their request URL and hash. `.identifiers.json` sidecars attach SEED names, standardized FDSN identifiers, provider IDs where present, metadata epochs, and raw-file links. IDs derived under the [FDSN Source Identifiers standard](https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html) are explicitly distinguished from identifiers present in the provider's XML. Empty location codes remain empty, for example `NC.BAV..EHZ` and `FDSN:NC_BAV__E_H_Z`.

`channel_epochs.csv` preserves network/station/location/channel codes, the channel and station source identifiers, coordinates, station elevation, channel sensor elevation, burial depth, parent and channel epoch bounds, and raw-response provenance. `metadata_epoch_start/end` are the intersection of the supplied network, station, and channel epochs. Matching uses a start-inclusive, end-exclusive interval; an absent end means unbounded. Epochs sharing an NSLC are retained separately.

`pick_epoch_matches.csv` preserves event and pick resource IDs and links each pick to its NSLC, FDSN channel identifier, metadata epoch, and raw response. `matching_summary.json` records counts and any missing or overlapping matches. Such matches stop processing for clarification rather than silently choosing a station epoch. Rerun only this local join with:

```bash
python3 data/authoritative/stations/acquire.py match
```

The [StationXML reference](https://docs.fdsn.org/projects/stationxml/en/latest/reference.html) defines `Channel/Elevation` as sensor elevation and `Channel/Depth` as burial depth below local ground. Under that convention, model depth is `-channel_sensor_elevation_m / 1000`, positive downward. Burial depth is preserved independently. The alternative interpretation treats the elevation field as ground elevation and gives `(burial_depth - elevation) / 1000`; the two conditional calculations remain in the StationXML rows, but the selected sensor-elevation interpretation and its caveats are now explicit. They are not two equally endorsed receiver depths. The [NCEDC depth-datum documentation](https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html) places station elevations and event depths on the same geoid datum. StationXML supplies no explicit per-channel vertical datum, so its documentary basis is recorded separately. Latitude/longitude datum attributes are preserved; absent attributes use the explicit StationXML WGS84 default.
