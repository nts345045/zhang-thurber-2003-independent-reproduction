# Reduced weighted-Laplacian direction control

This diagnostic follows the unchanged-stopping audit of event `quakeml:NC.anss.org/Event/NC/403533` and channel `NC.CMO..EHZ` (i775/k184). `identified_ray.csv` is byte-identical to that audit's complete native event/origin/pick/arrival/channel/epoch record. All numerical tables join it through `observation_index=9692`. Source, receiver, DD grid, observation, production source and configuration hashes are recorded in `summary.json` and checked before/after execution.

## Direction and limitation

Let L be the existing fixed-endpoint weighted path Laplacian, with positive segment weights equal to midpoint slowness divided by segment length. The diagonal at an internal node remains the sum of both incident weights. At an active lower face, coordinates with positive action gradient are initially fixed; at an upper face, those with negative gradient are fixed. We solve the principal system L_FF d_F = -g_F, with zero displacement on fixed coordinates. If another boundary coordinate points outward, we fix it and solve again. Every nonzero direction therefore satisfies g·d = -d_F^T L_FF d_F < 0 and is feasible in the tangent cone.

**This is not the exact tangent-cone quadratic minimizer.** Coordinates are never released during one direction solve. A fixed coordinate can consequently have a wrong-sign quadratic multiplier after its neighbors move. These residuals are reported, not suppressed. The fixed set is recomputed from the new path and gradient on the next outer iteration. In this experiment, such multiplier violations occur in 10 of 12 coarse FMM directions and 20 of 21 fine FMM directions (13 and 27 coordinate violations); none occur in the straight-seed controls. The largest violation is -0.00264145 in the quadratic multiplier's units. They do not prevent the existing ray stopping criterion from being reached here.

The variant uses this direction at every update. Curvature corrections are unused. It changes no action, model, endpoint, domain, Armijo or ray stopping threshold. The generated optimizer diff is saved. The failed fallback-only variant is preserved separately in `../ray_stopping_i775_reduced_fallback/`.

## Results

| Seed | Spacing (km) | Original updates to its stop | Reduced updates | Reduced projected gradient (s/km) | Reduced time (s) |
|---|---:|---:|---:|---:|---:|
| Straight | 0.5 | 1249 | 12 | 7.59059e-8 | 5.98218085186137 |
| FMM | 0.5 | 1155 | 12 | 1.03934e-7 | 5.98218079216311 |
| Straight | 0.25 | 3009 | 20 | 1.47547e-8 | 5.98217982014690 |
| FMM | 0.25 | 2703 | 21 | 2.16405e-8 | 5.98217980634782 |

Three runs meet the existing projected-gradient threshold of 1e-7 s/km. The coarse FMM run stops by the existing combined action-change <1e-11 s and projected-gradient <1e-5 s/km condition. All 65 directions have negative slope; all 65 accepted updates strictly decrease the action and use one line-search evaluation. The largest free-equation residual is 1.67e-16. No metric solve adds a new outward coordinate in these particular four runs. Instrumented and unobserved variants agree exactly in all recorded final outputs.

The straight/FMM endpoint-derivative difference falls from 1.93e-5 to 1.55e-8 s/km at coarse spacing and from 1.33e-5 to 1.44e-8 at fine spacing. Their action differences remain 59.7 ns and 13.8 ns, respectively. These are numerical agreements within one saved model, not errors against an independent first-arrival solution. One real ray and two initializers cannot establish general optimizer or first-arrival correctness.

## Reproduce and inspect

From the repository root, choose a fresh variant name:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_reduced_all --budgets 1000 --reduced-all
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_reduced_ray_metric.py data/development/ray_stopping_i775_reduced_all
```

The runner refuses to overwrite existing variants. `summary.json` records relative commands, `TMPDIR=tmp`, thread count and source/input/binary/output hashes. `source_snapshot.tar.gz` preserves the exact compiled source, with normalized archive metadata; `instrumentation.diff` includes the direction change and observation hooks. Undefined initial/final step fields and endpoint internal-gradient fields are explicitly not applicable (`nan`). `reduced_metric.csv` records descent, free residuals and frozen-multiplier violations for every direction.

Independent invented controls are in `../reduced_ray_metric_checks/`: 560 fallback-variant checks and 564 pure-metric checks, all passing. They include dense principal-matrix comparisons across all six-coordinate masks, no-bound inverse comparisons, feasible-direction/descent checks, a constructed no-release counterexample, and smooth affine rays. The pure-metric affine controls satisfy the existing 2.5e-5 s time and 3e-6 s/km derivative limits, with maximum errors 1.35e-6 s and 3.10e-7 s/km. These checks do not convert the no-release method into an exact constrained quadratic solve.
