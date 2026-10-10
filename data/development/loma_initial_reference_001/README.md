# Complete Loma initial-depth reference

This is an independent continuous reference for every saved perturbed initial source and native receiver in the completed LOM simulation. It does not use the x-dependent truth travel times and does not run the numerical forward solver, generate observations, or perform an inversion.

All **37,648 pairs** (724 sources × 52 receivers) have complete, valid references, no near ties, and defined finite source derivatives. The retained 37,750 candidates yield 19,367 selected turning paths, 18,221 direct paths, 59 finite-bottom paths, and one flat direct path. Four ordered workers completed the batch and native readback in 408.1 seconds. `reference_comparison_ready` describes reference-table usability; it does not certify a future forward calculation.

The exact saved initial model is depth dependent, with depth/velocity knots in km and km/s:

| Depth | Velocity |
|---:|---:|
| -1 | 3 |
| 0 | 3 |
| 3 | 5.160638297872341 |
| 7 | 5.9521387283237 |
| 11 | 6.113988439306358 |
| 16 | 6.316300578034682 |

The finite box is x ∈ [-35,35], y ∈ [-60,40], z ∈ [-1,16] km. Every candidate stays within the finite depth profile; horizontal motion is monotone between the endpoints and remains inside the original convex rectangle. Exact endpoint boundary flags are saved, including the nine sources at z=16 km. Selected branch derivatives at boundaries do not justify a centered perturbation outside the box.

`references.csv.gz` contains event-major, receiver-minor rows with `pair_index=event*52+station`. Every original event and receiver string is preserved with `source_` and `receiver_` prefixes, including valid empty location/end-epoch fields and native resource IDs. Coordinates and `source_dx_s_per_km`, `source_dy_s_per_km`, `source_dz_s_per_km` use the **original xyz axes**, with no x-truth permutation. `time_s` is pure propagation time; saved `source_t` remains metadata and is excluded from it. Compare future raw C++ `ray_time` and `source_dx/dy/dz` to those quantities. Observation predictions additionally contain source-time corrections.

`certificates.jsonl.gz` preserves all candidate families, root/closure certificates, near-tie information, and explicit numerical failure fields. The numerical helper is unchanged at SHA-256 `13020fef85113c302b27d846e1b4286c13576348a10710ba8a4c6fbd999e1c98`. No tolerances were changed: candidate distance closure remains 1e-8 km, and the largest residual here is 4.26530277763959e-9 km. Branch enumeration and ordinary floating-point time ranking remain distinct; no interval certificate for time ordering is asserted.

`check.py` independently reads the saved hashes, complete native support, coordinate/derivative joins, boundary flags, and candidate validity. Selected times are no greater than independently integrated straight-path actions; the largest excess is zero. The largest endpoint slowness-norm residual is 8.33e-17 s/km. These are necessary physical consistency checks, not a second completeness proof. `review.json` records the results; `independent_review.json` contains a separate artifact/native readback when present.

Exact input tables, the completed simulation/review links, the earlier plan, and numerical/wrapper sources are frozen in `inputs/` and `source/`. The earlier plan's pending-review wording is historical; the separately frozen passed simulation review and its linked terminal hashes are required by this run. `summary.json` and `execution.json` distinguish completion, validity, and comparison readiness. The controller output is retained separately. The existing 38 invented wrapper checks are in `../loma_initial_reference_checks/002/`.

Run the post-completion review without repeating ray/reference calculations:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 data/development/loma_initial_reference_001/check.py
```

Reproduce the reference batch using the recorded matching sources and a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_initial_reference.py --data data/loma_lom_analytic_001 --output data/development/loma_initial_reference_new --plan data/development/loma_inverse_plan_001/plan.json --workers 4
```
