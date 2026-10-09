# Authoritative observational subset

On 2026-10-09 the user authorized: “Use teh documented authoritative subset
with differences reported.” This supersedes earlier notes awaiting a decision
about the unidentified manuscript event and station lists. The observational
identity and authoritative-source requirements in `../../AGENTS.md` still apply.

USGS and EarthScope discovery responses are retained in `discovery/`. NCEDC is
the regional archive identified by those services for the Northern California
Seismic Network. The manuscript's software, simulation output, and plotting
inputs remain excluded. Archive observations are independently retrieved.

## Hayward selection

The acquisition in `hayward/` queries 1984-01-01 through 1999-01-01, excluding
the latter endpoint, with magnitude 0.2–4.5. A broad geographic query covers
37.2–38.3 degrees north and −122.7 to −121.4 degrees east. Preferred NCSS
origins must be identified as earthquakes, have current geoid depths 0–20 km,
and lie within |x| ≤ 10 km and |y| ≤ 30 km. These spatial and depth bounds are
new selection choices, not a recovered manuscript cohort. No event-count target
is imposed.

The coordinate origin is 37.72 degrees north, −122.06 degrees east. Positions
on the zero-height WGS84 ellipsoid are projected onto tangent east/north axes
at that origin. Then x = E cos(35 degrees) + N sin(35 degrees) and
y = −E sin(35 degrees) + N cos(35 degrees). Thus x increases northeast and
y northwest. Horizontal projection and current geoid depth are separate
approximations; the vertical coordinate is not the ellipsoid's tangent height.

Preferred-origin P arrivals must resolve to provider pick resource IDs and
concrete NC network channel codes. The initial quality selection requires
reported pick uncertainty no greater than 0.15 s; absent uncertainty is recorded
as an exclusion. Subsequent receiver-domain and event-pair selection will be
reported separately. Every numerical index must map to its provider event,
origin, arrival, and pick IDs and its channel SEED/FDSN identifiers and epoch.

StationXML channel elevation is treated as sensor elevation, following the
[StationXML definition](https://docs.fdsn.org/projects/stationxml/en/latest/reference.html#elevation-required).
Sensor depth below ground is preserved separately. A depth correction must not
be applied twice. The provider's stated coordinate datum and any unstated
vertical-reference assumptions are retained with normalized metadata.

## Differences that affect comparison

- The manuscript reports 1,489 earthquakes and 52 stations. Current preferred
  catalog records and this spatial selection need not recover those counts or
  the same earthquakes.
- Historical catalogs have been revised. In particular,
  [NCSS changed its catalog depth reference to the geoid in 2015](https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html).
  Current geoid depths cannot be treated as the original 2003 model depths.
- Catalog pick differences contain correlated errors because picks recur in
  many pairs. They are not independent precision measurements.
- Independently measured waveform differences require retrieved waveform data.
  Catalog differences will not be relabeled as waveform correlations.
- The resulting model and figures can test the method on an authoritative
  subset. Agreement with the exact manuscript result remains a separate claim.

Authoritative archive: [NCEDC services](https://service.ncedc.org/),
[NC network description](https://ncedc.org/ncsn/), doi:10.7932/NCEDC.
