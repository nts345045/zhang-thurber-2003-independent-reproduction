# Independent Hayward observations

The user explicitly authorized a documented authoritative subset after the
paper's exact event and station cohort could not be identified. This directory
contains newly retrieved NCEDC observations, not the Zhang--Thurber input files
or their numerical results. USGS and EarthScope service discovery preceded
these requests; see `../discovery/README.md`. Its earlier exact-cohort hold is
superseded by this authorization.

## Catalog selection

The acquisition script queries the NCEDC NCSS catalog in annual partitions,
using its current preferred origins and magnitudes. The independent criteria
are:

- Origin times from 1984-01-01 00:00:00 UTC inclusive to 1999-01-01 00:00:00
  UTC exclusive.
- Magnitudes 0.2--4.5 inclusive and a broad query rectangle of 37.2--38.3
  degrees N, -122.7 to -121.4 degrees longitude.
- Explicit earthquake event type. Quarry blasts, explosions, and unknown
  types are excluded and counted.
- Current catalog geoid depths of 0--20 km inclusive.
- A local corridor with absolute X at most 10 km and absolute Y at most
  30 km, centered on 37.72 degrees N, -122.06 degrees longitude.

For horizontal coordinates, geographic positions at zero ellipsoid height
are converted to WGS84 ECEF coordinates, using semimajor axis 6378.137 km and
inverse flattening 298.257223563. Their difference from the origin is
projected onto its tangent east and north directions. We then use
`X = E*cos(35 degrees) + N*sin(35 degrees)` and
`Y = -E*sin(35 degrees) + N*cos(35 degrees)`. Thus positive X points northeast
and positive Y northwest. This tangent-plane approximation is an explicit
independent choice. Vertical depth is the provider's geoid depth; it is not
the ellipsoid height used in the horizontal construction.

The initial download returned 24,301 broad-query candidates. The stated
criteria select 1,768 earthquakes. All 15 annual pages contain fewer than the
10,000-event page limit. The script implements pagination if needed and
applies the exclusive end bound explicitly. `catalog_candidates.csv` retains
every partitioned candidate, provider identifiers, source provenance, and all
applicable exclusion reasons. `selected_events.csv` retains the selected
records with the same fields. `event_selection_manifest.json` records exact
parameters and counts. Exclusion-reason totals are nonexclusive.

## Pick selection and identities

Event-specific QuakeML requests use batches of 25 provider event IDs and
`includearrivals=true`. The response event-ID set must equal the requested set,
and its preferred origin ID must match the summary. No event-count cap is
applied. An explicitly requested `--max-batches` diagnostic run is marked
incomplete in `pick_selection_manifest.json`.

`picks_all.csv` preserves all origin/arrival associations and any unassociated
picks, with selection decisions and rejection reasons. `picks_selected.csv`
requires the preferred-origin association, exact phase label `P`, network
`NC`, known symmetric timing uncertainty from 0 to 0.15 s inclusive, and known
event/origin/arrival/pick resource IDs and SEED channel identity. Unknown
uncertainties are excluded, not imputed. The exact provider uncertainty text,
arrival weight, residual, phase, and pick time remain available. Acquisition
does not impose a further arrival-weight cutoff; subsequent solver selection
must explicitly report exclusions, including zero provider arrival weights.
`arrival_distance_provider_value` preserves the native distance text without
assigning a verified unit. QuakeML defines this field in degrees, but the
provider convention has not been independently verified. `distance_unit_status`
records this limitation. This field is unused in selection and inversion;
horizontal distances are calculated from source and receiver coordinates.

QuakeML public IDs remain verbatim. `channel_seed_id` preserves the full
`NET.STA.LOC.CHA` name, including an empty location code. Missing location
attributes are distinguished from valid empty locations and fail selection.
`channel_fdsn_source_id` and `station_fdsn_source_id` are **derived** using the
FDSN standard, not presented as provider-supplied public IDs. For example,
`NC.CLC..EHZ` maps to `FDSN:NC_CLC__E_H_Z`. A channel name does not establish
its metadata epoch: `channel_requests.csv` supplies the observed time ranges
for the separate station/channel metadata acquisition and epoch join.

`event_pick_counts.csv` and `pick_selection_manifest.json` record which of
the 1,768 events have selected picks, all exclusion counts, phase/network
counts, and channel/station totals. Check `acquisition_complete` before using
an export. A smaller solver cohort caused by metadata, domain, pick-count, or
pair-connectivity requirements must have its own exclusion record.

The completed acquisition contains 52,553 arrival/pick rows, of which 42,236
pass this quality filter and 10,317 are excluded. The retained picks cover
all 1,768 selected events, 464 channels, and 387 stations. Their native pick
and arrival IDs are unique. Of the retained picks, 5,795 have zero provider
arrival weight and 36,441 have positive weight; none has an unknown or
negative weight. The solver adapter must report the removal of the zero-weight
associations separately. A complete offline rebuild on 2026-10-09 verified
all 86 raw responses against their saved request URLs and SHA-256 hashes,
matched all requested event identities, and checked preferred-origin IDs,
times, coordinates, depths, and magnitudes between summaries and pick replies.

## Raw replies and rebuild

Each `raw/*.xml` file is the unchanged provider response body. Its companion
`.provenance.json` retains request parameters and URL, UTC request/retrieval
times, response metadata, byte count, and SHA-256. The `.identifiers.json`
companion indexes native public IDs and parent resources without rewriting
the response. Cached responses are accepted only when their request URL and
hash match; HTTP and identity failures stop acquisition for review.

From the repository root, initial acquisition is:

```sh
python3 data/authoritative/hayward/acquire.py summaries
python3 data/authoritative/hayward/acquire.py picks
```

Rebuild normalized records from pinned responses without network access:

```sh
python3 data/authoritative/hayward/acquire.py summaries --offline
python3 data/authoritative/hayward/acquire.py picks --offline
```

Offline mode fails if a required cached response is missing. It verifies
hashes and identities again. Regenerated manifest creation timestamps may
change; raw retrieval timestamps and observational records remain pinned.
The script works with Python 3.6 or later and the available `requests` package.

These observations support an independent catalog-based experiment. Matching
the paper's time span and a similar event count does not identify its exact
selection. This directory supplies no waveform-correlation measurements and
does not substitute a later relocated catalog for such measurements.

Sources accessed 2026-10-09:
[NCEDC event API](https://service.ncedc.org/fdsnws/event/1/),
[NCEDC geoid-depth change](https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html),
[FDSN source identifiers](https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html).
