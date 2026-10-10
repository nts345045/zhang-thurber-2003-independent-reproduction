# Unchanged stopping for NC403533 / NC.CMO..EHZ

This isolated component examines the one locally nonconverged selected ray in the 186-ray DD-model first-arrival diagnostic. The ray joins saved event index 775 and receiver-epoch index 184. `identified_ray.csv` preserves the complete original observation record, including event `quakeml:NC.anss.org/Event/NC/403533`, origin `quakeml:NC.anss.org/Origin/NC/3739369`, pick `quakeml:NC.anss.org/Arrival/NC/42790539`, arrival association, `NC.CMO..EHZ`, `FDSN:NC_CMO__E_H_Z`, native channel epoch and metadata hashes. Every result, path and history row joins this record through `observation_index=9692`.

The source is on the model top at z=-1 km. The receiver is at z=-0.745 km. Here z is positive downward from the adopted vertical reference; the artificial model face is not an inferred Earth surface.

## Reproduce

From the repository root, choose a fresh variant name:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_budget_path
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_ray_stopping.py data/development/ray_stopping_i775_budget_path
```

The first command refuses to overwrite an existing variant. It compiles a frozen source copy under `tmp/ray_stopping/`, sets `TMPDIR=tmp` and one OpenMP thread, and records relative commands and source/input/binary/output SHA-256 hashes in `summary.json`. `source_snapshot.tar.gz` contains the exact sources and generated optimizer bodies with normalized archive metadata. `instrumentation.diff` shows every observation-only insertion. The instrumented and unmodified functions return identical paths, time, gradients, derivatives, update counts and flags in all 12 cases. The review command reads existing results only and verifies the recorded evidence and unchanged inputs.

The FMM initializer uses the frozen order-two, closed-source-cell prototype at auxiliary spacing 0.5 km. Continuous bending uses the unchanged action, L-BFGS update, domain/Armijo checks and stopping rules. The comparison changes only the maximum update budget (1000/2000/4000) and polyline spacing (0.5/0.25 km). Production source, inputs, configuration and inversions are unchanged.

## Results

| Initialization | Path spacing (km) | Updates at unchanged stopping | Projected gradient (s/km) | Final time (s) | Non-descent direction fallbacks |
|---|---:|---:|---:|---:|---:|
| Straight | 0.5 | 1249 | 3.15641e-6 | 5.98218085539009 | 1220 |
| FMM | 0.5 | 1155 | 3.15533e-6 | 5.98218079551299 | 1153 |
| Straight | 0.25 | 3009 | 5.61965e-6 | 5.98217982993573 | 2952 |
| FMM | 0.25 | 2703 | 5.79304e-6 | 5.98217981135764 | 2700 |

These four runs satisfy the existing combined condition: accepted action decrease below 1e-11 s and projected gradient below 1e-5 s/km. They do **not** satisfy the separate projected-gradient threshold of 1e-7 s/km. Budgets of 4000 reproduce the coarse 2000-budget results exactly because both stop earlier.

The fallback follows a concrete sequence in the existing code: the full L-BFGS direction is projected at active domain faces; its dot product with the gradient is nonnegative; curvature memory is cleared; the code uses the unpreconditioned projected negative gradient. This happens on every one of the final 200 accepted updates in each row above. A positive-definite full-space inverse does not guarantee descent after this component projection.

The final paths have 10/10 top-bound internal nodes at 0.5 km and 18/19 at 0.25 km (straight/FMM). The raw gradient norms are 1.15e-4 to 1.61e-4 s/km, largely in constrained normal directions; tangential gradient norms are only 1.37e-8 to 1.03e-7 s/km. No nodes merge. Final minimum segment lengths are 0.499/0.410 km at coarse spacing and 0.249/0.225 km at fine spacing. Late coarse updates take one line-search evaluation; late fine updates take two. No line search fails. The tested largest feasible coordinate derivative agrees with central finite differences to at most 2.16e-11 s/km at perturbation 1e-4 km in these four runs. Internal nodes are at least 0.024 km from an interior model-grid plane. These observations identify boundary handling of the metric as the immediate slowdown; they do not establish that all possible interface or parameterization effects are absent.

Extending the coarse budget changes the time by only -3.96 ns (straight) or -2.02 ns (FMM). The source-derivative vector changes by 3.40e-6 or 2.06e-6 s/km. Refining the path after each run reaches its own unchanged stopping condition lowers time by about 1.0 microsecond, while changing the source derivative by 4.62e-6 or 1.06e-5 s/km. The straight/FMM derivative discrepancy remains 1.93e-5 s/km at coarse spacing and 1.33e-5 at fine spacing. Travel-time agreement therefore exceeds derivative agreement. Flipping the local convergence flag alone is not an accuracy certificate.

## Evidence and next component

`results.csv` contains all 12 outcomes, including every false stopping flag. `history.csv` contains initial, accepted and final states; `paths.csv` contains final node coordinates and internal gradients; `path_gradient_checks.csv` contains the perturbation comparison. Initial/final history step fields and endpoint internal-gradient fields are explicitly not applicable (`nan`); all modeled values checked by the review are finite. `review.json` preserves counts, numerical comparisons, the complete native identity and evidence hashes.

The next isolated comparison uses the same weighted path Laplacian on free coordinates. It must retain principal-matrix incident-edge diagonals and solve again when a boundary coordinate points outward, rather than clipping a full-space inverse direction. The objective, domain, Armijo and stopping thresholds remain fixed. This test addresses the measured boundary bottleneck; it neither certifies a global first arrival nor establishes a production-ready constrained optimizer.
