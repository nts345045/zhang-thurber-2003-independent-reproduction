# Ray-kernel correction audit

This work addresses numerical failures independently of the unresolved real
event/station selection. No observational dataset was selected, no inversion
was rerun, and no manuscript panel acquired a new reproduction status.
The existing inverse solutions and main panel data remain the baseline outputs.

## Two separate defects

The baseline (`8f51613`) used a scalar initial L-BFGS metric and two-point
Gauss integration. All 31 nonconverged production rays in each saved final
model reached the 180-update cap. Most refined failures reached 1,000 updates.
A small difference between their travel times did not establish stationarity.

First, a segment crossing the sandwich-model velocity transitions had a
33.4-microsecond integration error and a 1.19e-4 s/km discrepancy between
its variational endpoint gradient and finite differences of its computed time.
Eight-point quadrature reduces these errors to 5.6e-17 s and 5.6e-12 s/km for
that case. A separate three-dimensional segment gradient check gives
8.9e-11 s/km. This is an integration-accuracy correction; it does not make
the variational formula algebraically identical to finite moving-cut
quadrature for every possible field.

Second, free ray vertices have stiff transverse modes and nearly free
tangential sliding. In a homogeneous straight ray the transverse Hessian is
the fixed-endpoint path Laplacian times slowness/spacing; its condition number
grows quadratically with the number of segments. The current L-BFGS metric
inverts a weighted path Laplacian with positive weights
`w_i = 1 / (v(midpoint_i) * segment_length_i)`. This changes only the search
direction, not the objective, physical constraints, or stopping tolerances.
It does not eliminate tangential null modes or guarantee global first arrivals.

## Analytic isolation

`diagnostics/ray_optimizer_audit.cpp` uses equal-depth endpoints in
`v(z) = v0 + g*z`, with `v0=5 km/s`. The continuous ray is a circular arc;
its exact time is `T = (2/g)*asinh(g*D/(2*v0))`. The two tests have
`(g,D)=(0.05/s,20 km)` and `(0.2/s,40 km)`. Their maximum depths lie within
the 16-km model. The endpoint-slowness reference is also analytic.

| Gradient | Spacing (km) | Baseline updates, 180 cap | Corrected updates |
| --- | --- | --- | --- |
| 0.05/s | 1 / 0.5 / 0.25 | 24 / 55 / 117 | 3 / 3 / 3 |
| 0.2/s | 1 / 0.5 / 0.25 | 180 / 180 / 180, all unconverged | 32 / 23 / 25 |

The stronger baseline cases also fail at 1,000 updates. The metric-only
experiment retains the baseline quadrature and achieves the same iteration
counts as the combined correction. Thus preconditioning, rather than the
quadrature change, explains this smooth-case improvement. Corrected time
errors decrease approximately fourfold when spacing halves. The coarse
strong-gradient cases satisfy the unchanged small-step plus 1e-5 gradient
criterion; they do not all satisfy the stricter 1e-7 alternative.

Rebuild all three analytic variants from the repository root:

```sh
python3 diagnostics/run_ray_optimizer_audit.py
cmake --build build -j 4
OMP_NUM_THREADS=4 build/dd validate data/development/ray_optimizer_audit
```

The runner retrieves our baseline header from Git, reconstructs the
metric-only variant by restoring that header's segment integration function,
and compiles each variant in project-local `tmp/`. Its manifest records
header and output hashes. Elapsed seconds are diagnostic timings and vary
between runs. `validation.csv` contains all 48 passing checks, including
the new crossing-integral, gradient, metric inversion/symmetry/positivity,
analytic stationarity, and mesh-refinement regressions.

## Frozen-model checks and remaining failures

These checks reuse the initial generated geometry and recovered models only
as numerical regression inputs. They are not authoritative seismic records.
The five source-file hashes are in `frozen_model_summary.json`.

| Frozen model | Production convergence before / after | Refined convergence before / after |
| --- | --- | --- |
| Standard | 1/32 / 5/32 | 3/32 / 22/32 |
| DD | 1/32 / 9/32 | 8/32 / 23/32 |

Remaining production failures are substantial. The largest refined gradient
remains 0.00603 s/km for the standard model and 0.000136 s/km for DD.
Maximum source finite-difference errors remain below the existing 0.003 s/km
check threshold, but the refined DD maximum increases from 0.000179 to
0.000249 s/km. Improvement in one diagnostic is not uniform improvement in
every diagnostic. These results do not establish that the 0.439-s baseline
DD differential residual has been explained or corrected.

To reproduce forward checks without overwriting baseline files:

```sh
mkdir -p tmp/frozen_ray_audit
for name in stations.csv standard_events.csv standard_grid.csv dd_events.csv dd_grid.csv; do
  git show "8f51613:data/synthetic/$name" > "tmp/frozen_ray_audit/$name"
done
OMP_NUM_THREADS=4 build/dd raycheck configs/synthetic.cfg tmp/frozen_ray_audit standard
OMP_NUM_THREADS=4 build/dd raycheck configs/synthetic.cfg tmp/frozen_ray_audit dd
```

The corresponding convergence and derivative CSVs are saved beside this
document. Both the iteration budgets and spacing settings match the earlier
diagnostic. Production versus refined columns still change spacing and
iteration budget together; only the separate analytic audit isolates those
effects. Full inverse-problem validation and authoritative-input selection
remain outstanding.
