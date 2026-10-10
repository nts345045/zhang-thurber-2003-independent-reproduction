# Failed reduced-fallback-only control

This preserved comparison changes only the fallback taken when the projected full-space L-BFGS direction is non-descent. It replaces the unpreconditioned projected negative gradient by the reduced weighted-Laplacian direction described in `../ray_stopping_i775_reduced_all/README.md`. Original L-BFGS attempts, objective, domain, Armijo and stopping thresholds remain unchanged. Every output joins the complete original native identity in `identified_ray.csv` through observation index 9692 (event NC403533 / NC.CMO..EHZ, i775/k184).

The reduced direction freezes initially KKT-active coordinates and any newly outward boundary coordinates, retaining incident-edge diagonals. It **does not release** a frozen coordinate during the solve and is **not** the exact tangent-cone quadratic minimizer. Wrong-sign frozen multipliers occur in these results and are retained in `reduced_metric.csv`.

All 27 reduced fallback directions have negative slopes and free-equation residuals at most 6.51e-19. The unchanged Armijo search accepts their actual action decreases. Nevertheless, three of four runs fail the unchanged 24-evaluation line-search limit on subsequent retained L-BFGS directions:

| Seed | Spacing (km) | Accepted updates | Converged | Final projected gradient (s/km) |
|---|---:|---:|---|---:|
| Straight | 0.5 | 36 | false | 2.95414e-4 |
| FMM | 0.5 | 9 | false | 4.39738e-4 |
| Straight | 0.25 | 72 | false | 4.34069e-4 |
| FMM | 0.25 | 29 | true | 2.16894e-8 |

At all three failures, `gradient_fallback=0`: the projected L-BFGS direction has a negative but very small slope (about -1e-10), so replacing only the non-descent fallback does not address it. Repeated halvings reach displacements about 1e-13–1e-12 km without a successful Armijo evaluation. These observations establish failure of this limited variant; they do not attribute every final line-search failure to one mechanism. The successful fine FMM run meets the original strict projected-gradient threshold. Instrumented and unobserved variant outputs agree exactly in all four cases.

Reproduce from the repository root using a fresh variant name:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_reduced_fallback --budgets 1000 --reduced-metric
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_reduced_ray_metric.py data/development/ray_stopping_i775_reduced_fallback
```

The runner rejects overwrite. The exact source snapshot, direction/instrumentation diff, relative commands, raw histories and all input/source/output hashes are retained. Undefined step fields at initial/final states and endpoint internal-gradient fields are explicitly not applicable. This failed variant remains distinct from both the unchanged production baseline and the later successful pure reduced-metric control. No production code, inputs, configuration or inversion was modified.
