# Historical NC.CMW1 channel identity

The historical identity gap is resolved. All 142 selected CMW1 picks match exactly one channel operation epoch in the authoritative NCSN master station-history file. The documented subset now adopts the provider's historical elevation of 214 m unchanged as receiver elevation, giving model depth −0.214 km. Interpreting that historical field as sensor elevation is an explicit assumption, not independent survey verification. The integrated metadata and its conventions are documented in the [station metadata README](../README.md).

## Evidence and limitations

The investigation began with USGS report discovery and EarthScope web services, then followed the authoritative NCEDC archive. USGS grant report 01HQGR0157 appeared as a search lead, but the preserved retrieval returned HTTP 404; it is not used as direct station evidence. Successfully retrieved BSL station tables are documented in the separate membership and elevation investigations.

Both the [EarthScope station service](https://service.earthscope.org/fdsnws/station/1/query?network=NC&station=CMW1&level=channel&format=xml) and the [NCEDC station service](https://service.ncedc.org/fdsnws/station/1/query?net=NC&sta=CMW1&level=channel&format=xml) return CMW1, but their earliest channel epoch is 2000-09-24T15:00:00. EarthScope returns 69 channel epochs; NCEDC returns 60. EarthScope fedcatalog routes nine BV1/SP2/SP3 epochs to EarthScope and 60 other epochs to NCEDC. The independently downloaded NCEDC channel-summary file also begins CMW1 in 2000. These responses cannot identify metadata epochs for the selected 1995–1998 picks. They do not show that the station was absent then.

The [NCEDC 2008 catalog migration notice](https://ncedc.org/blog/2008/07/18/changes-to-the-ncsn-ncedc.html) links its historical station file and documents the conversion of older station/channel names to SEED nomenclature. The [station-history format documentation](https://ncedc.org/pub/doc/ncsn/README.ncsn.stations) describes the master file's station and naming history. In the current [NCSN historical station file](https://ncedc.org/pub/doc/ncsn/ncsn.stations), lines 843–852 explicitly identify ten NC.CMW1 channels and their operation dates. No station alias or backward extension of modern StationXML was needed.

| Channel SEED identity | History line | Operation start, GMT | Operation end, GMT | Selected picks | Positive arrival weights |
|---|---:|---|---|---:|---:|
| NC.CMW1..EP2 | 843 | 1995-03-04 00:00 | 2012-01-11 20:23 | 2 | 2 |
| NC.CMW1..EP3 | 844 | 1995-03-04 00:00 | 2012-01-11 20:23 | 4 | 4 |
| NC.CMW1..HN1 | 845 | 1995-03-04 00:00 | 3000-01-01 00:00 | 129 | 128 |
| NC.CMW1..HN2 | 846 | 1995-03-04 00:00 | 3000-01-01 00:00 | 1 | 1 |
| NC.CMW1..HN3 | 847 | 1995-03-04 00:00 | 3000-01-01 00:00 | 3 | 3 |
| NC.CMW1..HV1 | 851 | 1995-06-08 00:00 | 3000-01-01 00:00 | 3 | 0 |

The year-3000 values are preserved provider sentinels. Operation-epoch endpoint inclusion is not specified; the nearest selected pick is more than 172 days from an epoch boundary, so endpoint interpretation does not affect these matches. Instrument operation epochs are distinct from calibrated response epochs.

The history reports 37°32.4155′N, 121°53.2549′W, equivalent to latitude 37.5402583333 and longitude −121.8875816667. Every CMW1 row gives elevation 214 m and location-status code E. The format defines E as an external GPS antenna location and describes GPS-site elevations as geoid referenced. It does not separately identify the historical sensor elevation or burial depth. Modern StationXML gives elevation 214 m and depth 155 m, but begins in 2000. Its agreement with the historical elevation supports the adopted interpretation; it likely shares underlying metadata and therefore does not independently validate it. Conflicting annual-report elevations remain documented in the [borehole elevation investigation](borehole_elevations.md).

The original investigation CSV retains a blank `sensor_z_geoid_km` and its initial unresolved status as a record of that investigation stage. The integrated [channel metadata](../channel_epochs.csv) instead records `sensor_z_geoid_km=-0.214` and `vertical_coordinate_status=historical_elevation_interpreted_as_sensor_explicit_assumption`. It preserves `provider_elevation_m=214` and status E. StationXML-specific sensor-elevation and burial-depth fields remain blank for historical rows; no later 155 m burial depth, antenna-to-sensor offset, or numerical datum correction is imported. This is an explicit interpretation of an authoritative value, not a claim that its historical sensor reference is fully resolved.

This investigation provides no evidence that Zhang and Thurber excluded CMW1. Missing StationXML coverage must not be used as a manuscript membership criterion. The separately documented study-membership review remains applicable.

## Saved records and checks

- `cmw1_historical_channel_epochs.csv`: ten explicit channel operation epochs with SEED codes, derived FDSN source identifiers, coordinates, raw elevation/status fields, operation/use dates, source line, URL, retrieval time and SHA-256. This investigation-stage CSV leaves model depth blank; the subsequent interpretation is in `../channel_epochs.csv`. FDSN identifiers are standardized derivations; the text provider does not supply resource IDs. Empty location codes are preserved from provider `--` values.
- `cmw1_historical_pick_matches.csv`: all 142 picks with provider event, origin, arrival and pick resource IDs, channel identities, the matched history line and both input hashes.
- `cmw1_historical_match_summary.json`: 142 unique matches, zero missing, zero overlaps; 138 positive association weights. Pick times span 1995-08-23T09:16:26.250000Z through 1998-12-22T21:10:07.560000Z. It distinguishes the original investigation state from the current adopted assumption.
- Nine raw responses are unchanged and each has `.provenance.json` and `.identifiers.json` sidecars. Text identity sidecars cover all 14,595 historical rows, all 33,764 channel-summary rows, all 69 concrete fedcatalog request rows and five current DART directory channels. Directory entries and routed requests are not represented as independently verified historical epochs.
- `cmw1_fetch.py` fetches or verifies pinned responses. `cmw1_normalize.py` regenerates identities and the historical pick join entirely offline. Both helpers pass Python syntax checks. The offline normalizer validates ten unique historical channel epochs and 142 unique pick resource IDs.
- The later `acquire.py` integration reads `historical_rows()` without running the investigation writer. Independent review verified all ten integrated rows against exact raw lines, identifiers, bounds and hashes. The complete cohort now has 42,236 unique metadata joins across 4,980 returned epochs and 521 NSLCs; those counts include metadata channels unused by selected picks.

History SHA-256: `ae8165b4adc28ceb18dbf0b7386bbd53e86d27dfbb2463c2db0ce632da7ddc0a`.

Selected-pick SHA-256: `34e2f64f7a95b4fb6c63bafeffde833d6d02054ab83170a502edcf95f9b74044`.

The vertical convention is now an adopted, recorded assumption with unresolved survey/datum limitations. Preserve these recovered records for both the reproduction selection and any later expanded comparison; do not modify selection based on an unsupported claim of manuscript exclusion. This review establishes metadata consistency and does not assert that an inversion has been run or validated.
