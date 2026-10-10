# Hayward initial ray 14099: The 0.25 km field still selects the slower branch

The FMM start remains on the deeper, slower branch at 14.139 km. It is 2.185653 milliseconds later than the first arrival. Refining the initialization field from 0.5 to 0.25 km does not resolve this branch failure.

This is the same identified observation as the original
[field-0.5 diagnosis](../initial_ray_first_arrival_003_14099_audit001/README.md):
event `quakeml:NC.anss.org/Event/NC/30204761`, origin
`quakeml:NC.anss.org/Origin/NC/4674144`, pick
`quakeml:NC.anss.org/Arrival/NC/54504884`, association
`quakeml:NC.anss.org/AssocArO/NC/54504884`, and receiver `NC.JJR..EHZ`
(`FDSN:NC_JJR__E_H_Z`), native epoch 1998-05-04T18:00:00 through
1999-02-18T18:15:00. Source index 1079 and receiver index 314 are retained with
all original metadata and provider hashes in `identified_ray.csv`.

Only the FMM field spacing changes to 0.25 km. Path spacing remains 0.03125 km,
the update budget is 1000, and both the straight and FMM starts are retained.
The order-2 closed-stencil field, frozen run-003 solver source, original
inputs, and stopping rules are unchanged. The straight result exactly matches
the previous fine-path control. Both cases report local convergence and match
the unmodified frozen trace exactly in path, time, source/model derivatives,
length weights and stopping state.

| Start | Updates | Time (s) | Maximum depth (km) | Excess over earliest branch (microseconds) | Source-vector error against earliest branch (s/km) |
| --- | ---: | ---: | ---: | ---: | ---: |
| straight | 12 | 10.777721304353879 | 14.139000954592 | 2185.905387 | 0.0335757 |
| fmm | 8 | 10.777721051986752 | 14.139000983302 | 2185.653020 | 0.0335757 |

The complete independent 1D reference is unchanged: its three turning depths
are 10.896102391, 12.271016264 and 14.139000063 km, with times
10.775535398967, 10.785471139933 and 10.777720708968 s, respectively.
Branch association uses retained path depth and separately checks time and
source derivatives. Reference time ordering uses ordinary floating-point
arithmetic; candidate-family completeness is not an interval bound on the time
gap. There are no near ties at the declared 1e-9 s label.

Independent exact reciprocal-affine integration of the retained polygons agrees
with the production Gauss action within 1.44e-14 s. Fixed-interior endpoint
finite differences of that independent action agree with the source gradient
within 3.17e-09 s/km at a 1e-5 km step. These checks support action/gradient
consistency for the saved paths; the dominant original discrepancy was branch
selection. The field/trace executable took 27.510 seconds, excluding compilation.

`summary.json` retains exact execution commands, input/source/binary/output
hashes and original flags. `spacing0_031250/` contains the path, optimizer
history and gradient checks. Its rows join to `identified_ray.csv` through the
observation index. `branch_review/` contains all three reference branches,
fully identified comparisons and fixed-path gradient checks. All source
snapshots and referenced stdout/stderr logs are retained. No full preflight,
observations, inversion, thresholds or production source were changed.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_initial_ray_diagnosis.py \
  --run first_arrival_003 --observation 14099 --variant NEW_VARIANT \
  --spacings 0.03125 --budgets 1000 --field-spacing 0.25
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_initial_ray_branches.py \
  --diagnosis data/development/initial_ray_first_arrival_003_14099_NEW_VARIANT \
  --output data/development/initial_ray_first_arrival_003_14099_NEW_VARIANT/branch_review
```
