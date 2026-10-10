# Final finite-guard hybrid control

This final diagnostic uses the feasible L-BFGS / full tangent-cone hybrid described in `../ray_stopping_i775_cone_hybrid/README.md`. Independent review added an explicit requirement that every retained direction component and its directional slope be finite. A slope of negative infinity is therefore rejected rather than accepted as strict descent. The earlier hybrid evidence and exact source remain preserved.

The same four identified controls (event NC403533 / NC.CMO..EHZ, observation 9692) reproduce the pre-guard hybrid and guarded pure-cone `results.csv` byte for byte: 12/4 updates at 0.5 km spacing and 20/4 at 0.25 km. Thirty-eight directions use the cone replacement and two initial straight-seed directions are retained. Every accepted direction has a finite negative slope, and every accepted action strictly decreases. Coarse FMM uses the original combined action-change/gradient stop at 1.039e-7 s/km; the other three meet the strict 1e-7 gradient threshold. All four instrumented/unobserved results agree exactly.

`identified_ray.csv` retains the complete native provider event, origin, pick, arrival association, full NSLC/FDSN channel, metadata epoch and source hashes. All numerical outputs join through `observation_index`. No observation, model, production source, configuration or inversion is changed. The exact compiled source, generated diff, original identities, KKT records, histories, relative commands and source/input/binary/output hashes are preserved.

Reproduce with a fresh variant name:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_cone_hybrid_finite_guard --budgets 1000 --cone-hybrid
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_cone_ray_metric.py data/development/ray_stopping_i775_cone_hybrid_finite_guard
```

The earlier hybrid has four bitwise unchanged no-bound affine controls in `../cone_ray_metric_checks/hybrid_no_bound/`. Those control sources precede this final nonfinite guard; the present four real-ray controls execute it. The full cone solver passes 9,007 separate invented exhaustive/KKT/arithmetic checks. These bounded tests support broader component regression, not global first-arrival correctness or production readiness. Quadratic certificates use the documented row-scaled floating-point tolerance, while all outer ray thresholds remain unchanged. Undefined initial/final step fields and endpoint internal gradients remain explicitly not applicable (`nan`).
