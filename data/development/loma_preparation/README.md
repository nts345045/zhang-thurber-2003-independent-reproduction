# Authoritative Loma simulation preparation

The prepared inputs in `data/loma_lom/` and `data/loma_lon/` retain all 724 catalog
sources and 52 receiver placements. Each canonical numeric row carries the full
native metadata from the selected authoritative CSV, including event, origin,
magnitude and channel resource IDs, SEED names, station epochs, query/source
hashes and original coordinates. Their two raw authoritative responses are
checked against the attached hashes. No provider retrieval or real-geometry ray
calculation was performed in this preparation.

The complete selection is unchanged: 37,648 source–receiver rays, 152,834
unordered source pairs with strict three-dimensional distance below 20 km,
7,947,368 catalog differences and the same number of precise synthetic
differences. The expected total is 15,932,384 observation rows. Every receiver is
used by each source and selected pair. This is a declared simulation incidence,
not a recovered historical observation roster.

## Model and initialization definitions

The LOM configuration is the first candidate; LON is a documented alternate.
Both are written gradient adaptations in USGS OFR 93-578, Table 4, pp. 17–18:

| Profile | Depths (km) | Velocities (km/s) |
| --- | --- | --- |
| LOM, Pacific side | 0, 2, 6.7, 24, 26 | 3.00, 4.95, 5.94, 6.64, 8.00 |
| LON, North American side | 0, 2.5, 8.9, 24, 26 | 2.53, 5.44, 6.29, 6.69, 7.98 |

These are not verified numerical inputs to the target manuscript. The target
refers to Dietz–Ellsworth (1990) without tabulating its model or specifying a
side. The preparation samples the chosen gradient adaptation at inversion depths
0, 3, 7, 11 and 16 km. The solver interpolates between these samples; it therefore
does not retain every original gradient break. Above the geoid, the surface
velocity extends constantly to −1 km. This extension contains all archived sensor
positions without clipping them. The manifest records the exact sampled values.
The [written-profile review](../../../reference/specification_notes.md) records
source links and the distinction from an exact target model.

The x-only truth is the written sandwich: 6 km/s at x≤0, linear fall to 4 at
x=1 km, 4 through x=5 km, rise to 5 at x=6 km, and then rise to 6 at x=38 km.
The finite domain stops at x=35 km. Truth x nodes additionally include 1 and
5 km; inversion x nodes are −35, −15, 0, 2, 4, 6, 20, 35 km. Both use y nodes
−60, −40, −20, 0, 20, 40 km and depth nodes −1, 0, 3, 7, 11, 16 km.

`simulate` sets every catalog-defined truth origin correction to zero. Initial
coordinates receive independent Gaussian errors with standard deviation 0.6 km,
projected onto the closed grid domain; initial origin corrections have standard
deviation 0.05 s. These magnitudes are explicit independent assumptions because
the target does not supply them. The precursor instead describes trial
hypocenters obtained by 1-D relocation; this initialization does not reproduce
that procedure. The random sequence uses C++ `mt19937`, seed 2003, and C++ normal
and uniform distributions. All source-coordinate/origin perturbation draws occur
before the station-bias and pick-noise draws. Freeze compiler/library and source
for replay. `initial_events.csv` is created by `simulate`, not by preparation.

For each source–receiver pair, let T be the selected continuous ray action and
Q = 0.01 round(T/0.01) s, using C++ half-away-from-zero rounding. A noisy absolute
pick is A = Q + B + E, with one uniform B in [−0.3,+0.3] s per station and an
independent Gaussian E of standard deviation 0.04 s per pick. Catalog differences
are A_i−A_j; precise differences are Q_i−Q_j. This is the existing declared order.
Differencing two rounded times allows nearly 0.01 s error, whereas the paper
states 0.005 s without resolving the order. This remains a disclosed difference.
The full provider identities accompany the synthetic rows; no provider
pick/arrival identity is invented.

## Numerical gates before observations

Candidate settings are 0.5 km path spacing, 1000 local iterations, and a 0.5 km
FMM field, using the production second-order implementation with closed receiver
seed cells. These are assessed candidates, not established sufficient accuracy.
The geometry-only command compares them against 0.25 km paths and FMM spacing,
with 1000 iterations. Known layered near-critical examples can require 0.0625 km
FMM spacing. Local flags, continuous-action differences, endpoint derivatives,
and finer checks must inform any change before inversion; no global-first-arrival
certificate is claimed.

The declared 104-ray diagnostic sample contains the nearest and farthest source
at each receiver, with deterministic index tie-breaking. Its CSV includes all
source/receiver metadata and coordinates. It changes no simulation source,
receiver, path incidence, or event-pair selection. Geometry-only result mappings
carry native identities directly, with no fictitious observation-row or pick ID.
The first eight samples also receive the existing endpoint finite-difference
checks. This finite sample is not a proof over all 37,648 rays.

Before rounding travel times or drawing observation noise, `simulate` saves every
ray to `simulation_ray_status.csv`, with native identities, coordinates, time,
finite/convergence/gradient/iteration flags and initializer diagnostics. Any
nonfinite selected ray, nonconverged local path or failed initializer rejects
creation of arrivals, observations and initial events. Source perturbation draws
have occurred but no observation-noise draw or observation row has been created.
The status file preserves the complete failed support. Successful `arrivals.csv`
rows carry these same flags alongside their exposed rounding/bias/noise values.
OpenMP worker exceptions are caught and rethrown outside the parallel loop with
source and receiver identities; simulation retains the failed records for its
gate. Receiver-field construction failures also identify the affected geometry.
Use fresh directories after a failure; existing simulation outputs are protected.

## Exact staged commands

The following commands are prepared for the **validated combined solver**. They
have not been executed on the real Loma geometry in this checkpoint. Preparation
alone is safe to repeat into a new directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 prepare_loma.py --profile lom --output data/loma_lom_NEW
PYTHONDONTWRITEBYTECODE=1 python3 prepare_loma.py --profile lon --output data/loma_lon_NEW
mkdir -p build/loma
TMPDIR="$PWD/tmp" g++ -std=c++17 -O2 -fopenmp src/main.cpp -lstdc++fs -o build/loma/dd
```

Freeze the combined source/configuration and executable hashes with each actual
execution; preparation manifests describe the preparation stage, not a later
combined executable. With the currently prepared LOM directory, first run:

```sh
(ulimit -v 134217728; OMP_NUM_THREADS=4 build/loma/dd geometrycheck data/loma_lom/run.cfg data/loma_lom truth)
```

Inspect the complete geometry diagnostic and its 0.25 km refinement before the
full truth-ray gate. Only after that check is accepted:

```sh
(ulimit -v 134217728; OMP_NUM_THREADS=4 build/loma/dd simulate data/loma_lom/run.cfg data/loma_lom)
```

This traces every truth ray and enforces the full-support gate. A failure leaves
identified `simulation_ray_status.csv` and creates no synthetic observation
table. A success creates all 15,932,384 rows; validate their complete counts,
identities and finite values, then count the actual first-iteration matrix:

```sh
(ulimit -v 134217728; OMP_NUM_THREADS=4 build/loma/dd invert data/loma_lom/preflight.cfg data/loma_lom dd)
```

`preflight.cfg` sets `matrix_preflight_only 1`: it first writes every used native
ray to `dd_preflight_ray_status.csv`, then writes the actual row/NNZ and memory
table and exits without a solve or model update. Its history is header-only.
Nonfinite rays, failed initialization, or missing model derivatives stop the
count after the status table is saved. Finite local nonconvergence is retained in
that table while the storage count proceeds; this does not accept those rays for
inversion. Review both tables before any full inversion. The 128 GiB limit is a
process address-space ceiling, not an RSS
estimate or a data cap. Any allocation failure stops the process. No pair is
removed to fit the budget. A normal inversion would use `run.cfg`, never
`preflight.cfg`, after these gates pass.

The [capacity snapshot](resource_snapshot.json) records 96 visible CPUs and about
754 GiB total memory, with roughly 686 GiB available at inspection. Load averages
were already above 100; these are shared, time-varying resources, not an exclusive
allocation. The initial operational choice is four OpenMP threads. The full CSV
is expected to occupy about 6.8 GB before compression. Preserve canonical IDs in
any lossless archival compression; do not upload large generated files blindly.

## Focused component evidence

The final [gate_004 checks](gate_004/summary.json) passed. The preceding three
variants preserve successful incremental checks; their source snapshots identify
which additional cases were not yet present. The
[preparation audit](preparation_checks.json) confirms exact preservation of every
native metadata value, the two raw response hashes, both prepared variants, and
all 104 diagnostic identity mappings. No real geometry has been traced.

`diagnostics/run_simulation_gate_checks.py --variant NEW_VARIANT` freezes all
current C++ headers (including a subsequently merged `ray_metric.hpp`) and the
pinned legacy source. It checks geometry-only identity output, an identified
outside-domain exception inside OpenMP, complete failed-ray retention, rejection
of failed local/initializer/nonfinite cases, a successful four-ray/eight-row
invented simulation, and protection of existing outputs. It checks all native
preflight status rows and rejection of invalid geometry before matrix counting.
It also compares
successful observations, initialization and all old arrival fields exactly
against the legacy generator. The failure fixtures are invented; no real rays
or inverse model are involved. Compiler/run `.log` streams remain local and
rebuildable under the repository ignore policy.
