# Full tangent-cone metric: guarded identified-ray control

This separate diagnostic joins the same complete provider record through `observation_index=9692`: event `quakeml:NC.anss.org/Event/NC/403533`, origin `quakeml:NC.anss.org/Origin/NC/3739369`, pick `quakeml:NC.anss.org/Arrival/NC/42790539`, its arrival association, and native channel `NC.CMO..EHZ` / `FDSN:NC_CMO__E_H_Z` with epoch 1993-10-15T19:23:00 to 1995-07-06T22:27:00. `identified_ray.csv` is byte-identical to the unchanged-stopping audit. Input, configuration and production-source hashes remain frozen.

At each update we solve the full tangent-cone quadratic with the existing weighted path Laplacian. The primal feasible active-set method takes first blocking steps and releases wrong-sign multipliers, retaining incident-edge stiffness. Details and 9,007 independent invented checks are in `../cone_ray_metric_checks/README.md`. Every nonzero returned outer direction must also be strict descent; a zero direction at a nonstationary ray raises an explicit diagnostic error. The existing 1e-10 km numerical boundary activity convention, action, domain, Armijo and ray stopping rules are unchanged. This solves the declared quadratic within a documented floating-point KKT tolerance; it is not an exact-real arithmetic certificate.

| Seed | Spacing (km) | Original updates to its stop | No-release metric updates | Full cone updates | Final projected gradient (s/km) |
|---|---:|---:|---:|---:|---:|
| Straight | 0.5 | 1249 | 12 | 12 | 7.59059e-8 |
| FMM | 0.5 | 1155 | 12 | 4 | 1.03881e-7 |
| Straight | 0.25 | 3009 | 20 | 20 | 1.47547e-8 |
| FMM | 0.25 | 2703 | 21 | 4 | 2.15603e-8 |

All four runs satisfy the existing stopping rule. Coarse FMM uses the combined action-change/gradient criterion; the other three meet the strict 1e-7 s/km projected-gradient threshold. All 40 directions have negative slope, and all 40 accepted steps strictly reduce action with one line-search evaluation. The FMM runs release 23 and 46 coordinates across their quadratic solves. Straight runs release none and reproduce the no-release result exactly. All four instrumented results match unobserved controls exactly.

The maximum free-equation residual is 1.15e-16; its maximum row-scaled backward error is 2.02e-16. Primal violations are zero, dual violations are at most 4.67e-18, and complementarity errors are at most 1.01e-19. Straight/FMM source-derivative differences are 1.61e-8 s/km at 0.5 km spacing and 2.16e-8 at 0.25 km. Corresponding time differences are 60.0 ns and 13.9 ns. These agreements do not supply an independent global first-arrival or exact endpoint-derivative reference.

`../ray_stopping_i775_cone_metric/` preserves the first complete run before the explicit outer descent guard was added. Every observed direction was already negative. The guarded and pre-guard `results.csv` are byte-identical, and both source snapshots remain available. The failed fallback-only and successful no-release experiments are also preserved independently.

Reproduce with fresh variant names:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_cone_metric_descent_guard --budgets 1000 --cone-metric
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_cone_ray_metric.py data/development/ray_stopping_i775_cone_metric_descent_guard
```

The runner rejects overwrite, stores the generated optimizer diff and normalized exact source archive, and records relative commands plus input/source/binary/output hashes. `cone_metric.csv` holds every quadratic certificate and solve/release count. Undefined initial/final step fields and endpoint internal-gradient fields are explicitly not applicable. Only one identified ray, two path spacings and two seeds are tested here. No production optimizer, model, configuration, observations or inversion is changed.
