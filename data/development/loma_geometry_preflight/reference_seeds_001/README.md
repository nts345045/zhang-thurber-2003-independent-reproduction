# Exact-reference seed controls for four Loma rays

This isolated diagnostic supplies the continuous first-arrival guide branch to
the unchanged frozen Loma tracer. It tests diagnostic rows 5, 49, 57 and 88;
the latter three had locally converged production paths with large travel-time
errors. All four first arrivals follow the x=0 critical guide. Native
event/origin/channel identifiers and metadata epochs accompany each numerical
result and saved path. These remain catalog-defined simulation geometry,
not observed arrival times or inferred earthquake ground truth.

The reference sampler uses `(y,z,-x)` and a reversed velocity profile, so both
guide legs have the outward orientation required by the sampler. Its circular
arcs and straight guide are sampled at five spacings. We evaluate each sampled
polygon, the production tracer after its initial uniform resampling, and its
1000-update result. A separate copied function changes only initial resampling
to retain the supplied points; all interior nodes remain free afterward.
`initialization_only.diff` records the entire change. The untouched optimizer
and null-seed suffix are checked byte for byte; eight exact controls cover
unseeded and uniform-seed behavior. No production file or tolerance changes.

Maximum errors across the four rays are:

| Spacing (km) | Sampled reference polygon time error (microseconds) | Uniform-resampled optimized time error (microseconds) | Uniform-resampled optimized source-vector error (s/km) | Optimized local flags, uniform / retained |
| --- | ---: | ---: | ---: | ---: |
| 0.5 | 849.949 | 475.043 | 1.139e-4 | 0/4 / 0/4 |
| 0.25 | 254.059 | 146.744 | 5.686e-5 | 0/4 / 0/4 |
| 0.125 | 69.954 | 76.086 | 1.847e-5 | 0/4 / 0/4 |
| 0.0625 | 18.392 | 19.103 | 4.651e-6 | 0/4 / 0/4 |
| 0.03125 | 4.703 | 4.750 | 4.349e-7 | 1/4 / 0/4 |

The original flags are retained: 39 of 40 optimized runs fail their local
stopping test. Of those, 22 exhaust 1000 accepted updates and 17 terminate
through the existing line search without satisfying the stopping test; 15 of
these accept no updates. These terminations follow directly from the unchanged
control flow and saved update counts; no iteration histories are reconstructed.
The only successful flag is the uniform-resampled row 88 at 0.03125 km.

The experiment separates several errors. Supplying the correct guide branch
removes the large wrong-branch discrepancy, but coarse chordal sampling still
has a measurable action error. Uniform resampling also increases initial error:
for row 5 at 0.5 km it adds 473.730 microseconds and changes the source-vector
error from about 1e-15 to 0.003516 s/km. That extra action falls to 0.05368
microseconds at 0.03125 km. Retaining the original nodes therefore isolates
initial resampling damage, but does not repair convergence.

For the finest retained row-5 path, the continuous-reference discrepancy is
4.696 microseconds and the source-vector discrepancy is about 2e-15 s/km, yet
the chosen smooth gradient norm is 0.0751 s/km and the optimizer accepts no
updates. Collective normal perturbations of the exact guide nodes have very
different one-sided action slopes. At a 1e-6 km step, their forward/backward
slopes are about 3.25203 and -1.597e-5 s/km. The computed gradient follows the
positive-side slope. This is evidence of a nonsmooth objective at an
interface-aligned path; testing this single direction does not establish full
nonsmooth stationarity. Lowering the stopping tolerance or declaring these
flags successful would not address that issue.

Independent exact integration of each straight polygon segment agrees with
the production quadrature within 2.242e-13 s. Fixed-polygon endpoint central
differences at 1e-5 km agree with the reported segment source derivative within
6.078e-9 s/km. Those checks establish action/derivative consistency for the saved
polygons, not the accuracy of their optimized-travel-time derivative. All four
sources start in the constant-speed trough: the analytic seed's first straight
leg retains the exact source tangent, which explains its very small endpoint
derivative error even at coarse spacing. This does not certify arbitrary
curved source segments or a general 3D first-arrival initializer.

`summary.json` pins all frozen sources, commands and inputs. `cases.csv` and
`selected_references.jsonl` retain complete geometry metadata and reference
certificates; `results.csv` has all 100 stages. `review/summary.json` checks all
84,667 saved path rows, native joins, action/source errors and one-sided
differences. The C++ field `strict_interface_crossings` counts all x grid
planes; the review separately counts exact nodes at the actual slope changes
x=0,1,5,6 km. The reference candidate enumeration is complete for these cases,
but its minimum-time ordering uses floating-point actions, not an interval
minimum-time certificate. This experiment changes no simulation acceptance
gate and generates no observations.

Large tables, frozen inputs and command logs are published losslessly in
`frozen_tables.tar.gz`; `packaging.json` lists all 15 member hashes, verified by
reading the completed archive. Extract it in this directory before running
the saved-output review. Readable sources, result tables and reviews remain
outside the archive.

Reproduce in a fresh variant directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_reference_seeds.py --variant repeat
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_loma_reference_seeds.py --input data/development/loma_geometry_preflight/reference_seeds_repeat
```
