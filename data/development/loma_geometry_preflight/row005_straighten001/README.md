# Exact straightening of a Loma guide candidate

This experiment lowers travel time but does **not** resolve the ray-convergence
failure. It is an isolated, restricted candidate search. No production source,
live run, stopping flag, or model velocity was changed.

The input is diagnostic row 5: event `quakeml:NC.anss.org/Event/NC/20091683`,
origin `quakeml:NC.anss.org/Origin/NC/2660124`, channel `NC.BSL..EHZ`
(`FDSN:NC_BSL__E_H_Z`). `identified_ray.csv` preserves the full native metadata,
epoch, coordinates, and provenance. Every path/history row joins this sidecar
through `diagnostic_row=5`; `run_id` identifies the saved starting path.
These calculated paths are not observed seismic trajectories.

The declared truth model has velocity at most 6 km/s throughout its finite
box, with velocity exactly 6 km/s throughout the plane x=0 and half-space
x<=0. A chord between two exact x=0 crossings therefore has action L/6.
Every intervening path has action at least its length divided by 6, and its
length is at least the chord length. Replacing the intervening portion by
that chord cannot increase travel time. The crossings are calculated from
line-plane intersections; no distance threshold moves a knot to the interface.

The candidate optimizer then fixes the two contact x coordinates at zero,
allowing their y/z coordinates and all other internal coordinates to vary.
Its L-BFGS metric uses the correct reduced principal matrix. The travel-time
integral, domain, fixed source/receiver endpoints, and Armijo condition are
unchanged. This constrains a stated candidate branch; it is not a general
solver for interface stationarity. In particular, collapsing the guide to one
edge omits variations that insert additional free guide knots.

Four saved FMM-started paths are used: 0.5 and 0.25 km spacing, each after
1,000 or 4,000 original updates. These are new searches from those saved
coordinates, without the original BFGS history and without resampling.
Straightening alone decreases time by 0.71--4.67 microseconds. After another
4,000 restricted updates, the total decreases are 27.7--223.6 microseconds.
All four searches still exceed the strict restricted-gradient threshold of
1e-7 s/km. Their actions remain 57.3--224.6 microseconds above the independent
continuous Snell-guide candidate. The result therefore supports neither
promotion to production nor a convergence claim.

`summary.json` records commands, exits, source/input hashes, and output hashes.
`source/` contains the frozen compilation sources. Each `spacing*` directory
contains the original, straightened, and final candidate paths, restricted
search history, endpoint partial derivatives, and exact x-only path action.
`review.json` records identity, domain, action, hash, and termination checks.
Run `python3 data/development/loma_geometry_preflight/row005_straighten001/check.py`
from the repository root to repeat the saved-output review.

To rerun a candidate into a fresh directory, compile
`source/diagnostics/straighten_loma_guide.cpp` with C++17, OpenMP and
`-lstdc++fs`. The executable takes `GRID PATHS RUN_ID OUTPUT_DIR`; for example,
use this directory's `truth_grid.csv`, `spacing050_input_paths.csv`,
`fmm_0.500000_1000`, and a newly created output directory. The recorded command
line gives each of the other three run IDs. Preserve the input sidecar when
moving or sharing a result.
