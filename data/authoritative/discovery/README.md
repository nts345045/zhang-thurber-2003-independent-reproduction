# Authoritative data discovery, 2026-10-09

The user resumed the reproduction and required authoritative observations and
metadata, beginning with USGS and EarthScope. This supersedes the original
task's exclusion of source observations. A subsequent instruction requires
SEED naming codes and resource IDs in every saved real-data record. The
independent implementation and prohibition on using published plots as inputs
remain in force.

These files establish service access. They are not a selected manuscript
dataset, and no new inversion or reproduced panel has been generated from them.

## Retrieved records

| Source | Saved record | Verified content |
| --- | --- | --- |
| USGS ComCat | `usgs_nc216859.geojson` | Loma Prieta mainshock event and product metadata |
| USGS, NC phase product | `usgs_nc216859_phases.xml` | QuakeML with 315 P picks and their arrival associations |
| EarthScope station service | `earthscope_nc_1989_station.txt` | 364 NC stations with metadata overlapping 17–19 October 1989 |
| EarthScope federated catalog | `earthscope_nc_1989_fedcatalog.txt` | 122 station requests routed to NCEDC within a provisional regional search window |

The mainshock and the station-query window are availability checks only.
Their dates, counts, and spatial bounds do not define the paper's cohort.
Provenance JSON files retain exact request URLs, retrieval times, response
hashes, and purpose. Raw responses are preserved unchanged.

USGS's event API does not implement `includearrivals`, but the event's
`phase-data` product supplies a separate QuakeML resource. The retrieved
mainshock product confirms that historical picks are accessible through that
route. [USGS API documentation](https://earthquake.usgs.gov/fdsnws/event/1/).
NCEDC also documents an event service with `includearrivals=true`.
[NCEDC event service](https://service.ncedc.org/fdsnws/event/1/).

## Identification barrier

The target manuscript specifies actual Loma Prieta seismicity and USGS
stations, citing Kissling et al. (1994), but its written synthetic-test
description does not supply event IDs, station codes, dates, counts, or
geographic selection bounds.

For Hayward, the manuscript specifies 1984–1998, 1,489 earthquakes with
magnitudes 0.2–4.5, 52 stations, 20,257 absolute P picks, 767,127 catalog
differences, and 17,955 waveform-correlation differences. The stated local
origin is 37.72 degrees N, 122.06 degrees W with 35-degree anticlockwise
rotation. The small geographic rectangle in its Figure 6 caption describes
a zoom region, not the full event selection.
[Target manuscript](https://www.researchgate.net/publication/215754286_Double-Difference_Tomography_The_Method_and_Its_Application_to_the_Hayward_Fault_California).

The cited precursor describes approximately 1,700 events and 260 stations
for its 1984–1998 catalog-difference example. That broader set does not identify
the target's 1,489-event/52-station subset. The exact selected event IDs,
station identities and epochs, exclusions, and correlation observations have
not been recovered. [Waldhauser and Ellsworth (2002)](https://www.ldeo.columbia.edu/~felixw/papers/Waldhauser_Ellsworth_JGR2002.pdf).

The repository's stop-and-ask rule has therefore been invoked. The user was
asked whether to continue tracing the exact selection, use an explicitly
documented independent authoritative subset, or provide identifiers/criteria.
Dataset selection and inversion await that clarification. The later
identifier requirement does not resolve this selection question.

## Identifier preservation

Run `python3 data/authoritative/discovery/attach_event_identifiers.py` from the
repository root to rebuild the USGS identifier sidecars and the pick CSV.
The helper verifies raw-response hashes, event agreement between GeoJSON and
QuakeML, unique provider public IDs, and resolvable object references. The CSV
retains event, origin, arrival, and pick resource IDs and full SEED channel
codes. QuakeML itself remains the complete observational source, including
origin coordinates, uncertainties, amplitudes, and processing metadata.

Run `python3 data/authoritative/discovery/normalize_earthscope_identifiers.py`
to rebuild both EarthScope sidecars and
`earthscope_nc_1989_stations_identified.csv`. It verifies source hashes,
station coordinates, epoch bounds, and unique station/epoch keys. Both helpers
use the saved responses and perform no new network requests. Independent
checks compared all 315 exported pick times and SEED codes with QuakeML and
all 364 exported station identities with their sidecar records; all passed.

Station resources use `FDSN:NET_STA`; channel resources use
`FDSN:NET_STA_LOC_B_S_SS`, derived from the provider's SEED codes according to
the [FDSN source-identifier specification](https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html).
For example, `NC.JTG..EHZ` maps to `FDSN:NC_JTG__E_H_Z`. An empty location
code is preserved. A station-level record does not imply a particular
channel. FDSN identifiers constructed by this standard mapping are labeled
as derived, distinct from the provider's verbatim QuakeML public IDs.

Identifier attachment uses the already retrieved records; it does not select
a replacement cohort. Channel metadata and responses still need retrieval
and epoch matching for any events eventually selected for inversion or
waveform processing. [EarthScope findings](earthscope_findings.md) record
station normalization and the historical depth-datum and channel-mapping
changes that must also be resolved.
