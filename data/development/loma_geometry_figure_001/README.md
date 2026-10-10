# Loma Prieta geometry candidate for Figure 2

This partial replacement shows the saved horizontal input geometry: 724 catalog-defined
simulation sources, 52 NC EHZ receiver epochs at 52 stations, and the 48 horizontal
grid nodes specified by the manuscript's Figure 2 caption. Black points show sources,
orange open triangles show receivers, and gray crosses show grid nodes. Both axes
are in kilometres with equal distance scales. The plot contains no inferred fault trace.

NCEDC NCSS catalog origins supply the event coordinates. EarthScope discovery routed
the receiver request to authoritative NCEDC StationXML. The event selection spans
1989-10-18 to 1989-11-18 UTC, magnitudes 2.0–5.5, and catalog depths 0–16 km;
the receiver snapshot is 1989-11-01 UTC. Full selection criteria and exclusions remain
in `data/authoritative/loma_prieta/README.md` (repository-relative paths throughout).

The horizontal coordinates use WGS84 tangent east/north directions at 37.0361667° N,
−121.8798333° E, followed by X=(E+N)/sqrt(2), Y=(−E+N)/sqrt(2). That origin is the
saved USGS mainshock geometry: event `quakeml:nc.anss.org/Event/NC/216859`, origin
`quakeml:nc.anss.org/Origin/NC/2642104`. The rotation, windows, magnitude limits,
NC EHZ restriction, and receiver snapshot are independent choices. The exact 2003
study cohort, projection, and map layout have not been recovered. No target cohort
count is asserted, and no map was digitized. These positions define a simulation;
they do not establish historical source–receiver incidence or inversion recovery.

The native grid has X=[−35,−15,0,2,4,6,20,35] and Y=[−60,−40,−20,0,20,40] km.
The documented five depth levels [0,3,7,11,16] km are extended by a −1 km top level
to contain all receivers. Thus the saved grid has 8×6×6 nodes; its horizontal
projection matches the written 8×6 specification. Receiver z ranges from −0.921
to −0.039 km under the saved sensor-elevation convention. Neither depth nor model
velocity is encoded in this horizontal plot. See `data/development/loma_specification/README.md`.

`inputs/truth_events.csv`, `inputs/stations.csv`, and `inputs/initial_grid.csv` are
byte-identical copies of the closed native tables used here, originally under
`data/loma_lom_analytic_001`. Three small completion/preparation/review JSON records
are also copied. A fresh checkout can rebuild this figure from these files and the
tracked authoritative inputs; the multi-gigabyte simulation archive is not required.
Every selected authoritative metadata field is
matched by event resource ID or channel SEED ID plus effective epoch. Event,
origin, magnitude, and available provider resource IDs; station/channel SEED and
derived FDSN identifiers; epochs; raw-response hashes; and valid blank locations
are preserved. Provider station/channel resource-ID fields that were absent remain
explicitly empty. Derived FDSN identifiers are labeled in the native metadata.
Provider `source_file` paths retain their `data/authoritative/loma_prieta` base.

The plotted event x/y values use the saved C++ serialization at 12 significant
digits; the full-precision authoritative x_km/y_km values remain in the same rows.
Their maximum coordinate difference is below 5e−11 km. No coordinate is recomputed,
perturbed, relocated, or omitted. The former random `figures/figure02` files remain intact.

Run from the repository root, choosing a fresh output directory for each run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B diagnostics/plot_loma_geometry.py --output tmp/loma_geometry_figure_rebuild_001
```

The script uses only Python's standard library and Matplotlib, verifies the closed
source hashes and complete joins, and saves PDF/PNG plus identified sidecars.
`manifest.json` records source/output hashes, counts, checks, command, and versions.
This package does not alter the report, panel audit, solver, or published figures.
