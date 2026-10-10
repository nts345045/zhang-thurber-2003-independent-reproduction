# Hayward initial ray 14099: a slower locally converged branch

The identified absolute observation uses event
`quakeml:NC.anss.org/Event/NC/30204761`, origin
`quakeml:NC.anss.org/Origin/NC/4674144`, pick
`quakeml:NC.anss.org/Arrival/NC/54504884`, and association
`quakeml:NC.anss.org/AssocArO/NC/54504884`. Its receiver is `NC.JJR..EHZ`
(`FDSN:NC_JJR__E_H_Z`), native epoch 1998-05-04T18:00:00 through
1999-02-18T18:15:00. `identified_ray.csv` retains every observation/source/receiver
field and original provider source hash. Observation row 14099 maps to source
index 1079 and native receiver index 314; that join was checked explicitly.

The source is at 9.309 km depth. Complete continuous 1D enumeration gives three
turning branches inside the saved model:

| Branch index | Turning depth (km) | Travel time (s) |
| --- | ---: | ---: |
| 0, earliest | 10.896102391 | 10.775535398967 |
| 1 | 12.271016264 | 10.785471139933 |
| 2 | 14.139000063 | 10.777720708968 |

All root intervals and distance-closure residuals are retained in
`branch_review/summary.json`; maximum absolute closure is 3.49e-12 km.
The reference is complete for this monotone 1D profile. Time ranking uses
ordinary floating-point evaluation, rather than an interval bound on the time
gap. None of the three branches is a near tie under the declared 1e-9 s label.

Both the straight and FMM starts converge to branch 2 at every tested path
spacing. The FMM field stays at 0.5 km. Selected FMM results are:

| Path spacing (km) | Updates | Excess over branch 2 (microseconds) | Excess over earliest branch (milliseconds) | Source-vector error against branch 2 (s/km) |
| --- | ---: | ---: | ---: | ---: |
| 0.5 | 746 | 46.863936 | 2.232174 | 5.10e-6 |
| 0.125 | 177 | 3.733466 | 2.189043 | 1.26e-7 |
| 0.03125 | 10 | 0.353345 | 2.185663 | 4.10e-9 |

All 12 cases report local convergence and match the unmodified frozen trace
exactly in path, time, source/model derivatives, length weights and stopping
state. Increasing the iteration budget from 1000 to 4000 gives identical
results because each case stops earlier. The 0.5 km selected result also exactly
reproduces the saved run 003 time/gradient/flag at its 12-digit serialization.
At the finest spacing, the selected path reaches 14.138998472 km depth, agreeing
with the deeper reference branch. Its source vector remains 0.0335756845 s/km
away from that of the earliest branch. Local convergence and path refinement
therefore do not establish the first arrival.

## Integration and gradient checks

An independent reciprocal-affine integral splits each retained polygon at
every depth plane. It agrees with the production Gauss action within
1.44e-14 s. Fixed-path endpoint finite differences of that independent action
agree with the saved source gradient within 3.06e-9 s/km at a 1e-5 km step and
1.38e-10 s/km at a 1e-6 km step. Constant, affine, crossing and reversed-segment
controls pass. These tests concern the same retained polygons and do not
reoptimize a perturbed ray.

The large discrepancy against the earliest branch is explained by selection
of the slower deep branch. Polygonal discretization accounts for a much smaller
remaining error within that branch, which decreases under refinement. These
checks find no integration or endpoint-gradient inconsistency on the saved
paths. They do not prove that every production ray is correct.

## Frozen execution and files

The diagnostic uses run 003's pinned source and native inputs. Frozen source
is under `source/`; `instrumentation.diff` records observation-only history
hooks and `driver_adaptation.diff` records the identified input/field-spacing
arguments. No production source, input, local flag or threshold was changed.
`summary.json` contains the exact compiler/run commands, hashes, all results
and parity checks. Each spacing directory retains optimizer histories,
coordinates, gradients and finite-difference checks; its CSV rows join through
`observation_index` to `identified_ray.csv`. All referenced stdout/stderr logs
are retained.

`branch_review/identified_branch_comparison.csv` preserves the original native
metadata inline and compares every case with the full reference.
`reference_paths.csv` samples all three analytic branches at 0.03125 km with
explicit endpoints, layer crossings and turning points; native identities are
attached to every row. `exact_source_gradient_checks.csv` retains the same
identities and fixed-path checks. The exact branch association uses path depth,
then independently checks time and source-vector agreement; it does not relabel
a slower branch as the earliest arrival.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_initial_ray_diagnosis.py \
  --run first_arrival_003 --observation 14099 --variant NEW_VARIANT \
  --spacings 0.5,0.125,0.03125 --budgets 1000,4000 --field-spacing 0.5
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_initial_ray_branches.py \
  --diagnosis data/development/initial_ray_first_arrival_003_14099_NEW_VARIANT \
  --output data/development/initial_ray_first_arrival_003_14099_NEW_VARIANT/branch_review
```

Separate fresh diagnostics refine the FMM field to 0.25 and 0.125 km while
holding path spacing at 0.03125 km. Their results are not part of this original
field-0.5 evidence. No full preflight, observations or inversion was launched.
