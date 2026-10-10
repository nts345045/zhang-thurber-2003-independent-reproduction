# Feasible L-BFGS / tangent-cone hybrid control

This diagnostic tests the same fully identified i775/k184 ray (event NC403533 / channel NC.CMO..EHZ, observation 9692) with unchanged model, receiver, epoch metadata and production-source hashes. Every derived row joins the byte-preserved original provider record in `identified_ray.csv` through `observation_index`.

The hybrid first computes the original full-space L-BFGS direction. It keeps that direction only when the existing boundary projection would change no component and the gradient dot direction is negative. Otherwise it solves the full tangent-cone weighted-Laplacian quadratic and clears curvature memory. The final direction must pass explicit feasibility and strict-descent checks. This avoids both measured failure modes of post-projecting a full inverse direction: a nonnegative slope and a tiny negative slope that escaped the old fallback. The metric, action, boundary activity convention, domain checks, Armijo condition and ray stopping thresholds are unchanged.

All four identified controls reach the existing stopping rule: straight/FMM seeds take 12/4 updates at 0.5 km path spacing and 20/4 at 0.25 km. The two initial straight-seed directions are retained; 38 directions use the cone replacement. All 40 directions strictly descend, all 40 accepted updates strictly decrease the action, and each takes one line-search evaluation. Their final `results.csv` is byte-identical to `../ray_stopping_i775_cone_metric_descent_guard/results.csv`, whose README reports the gradients, derivative agreements and KKT residuals. The coarse FMM case stops by the original combined small-action-change/gradient condition at 1.039e-7 s/km; the other three meet the strict 1e-7 threshold. Instrumented and unobserved controls match exactly.

Four additional smooth affine rays without active boundaries preserve the complete original path, time, endpoint derivative, iteration count and convergence flag bitwise (both directions at 0.5/0.25 km). Their recorded fixture is `../cone_ray_metric_checks/hybrid_no_bound/`, with 560 total checks and zero failures. Those remaining checks repeat the principal-matrix controls; they do not replace the separate 9,007 full-cone checks. This small control confirms retention of interior L-BFGS behavior for these rays, not for every possible model or condition.

Reproduce from the repository root with fresh variant names:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_cone_hybrid --budgets 1000 --cone-hybrid
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_cone_ray_metric.py data/development/ray_stopping_i775_cone_hybrid
```

Existing variants are never overwritten. The exact source archive and generated diff show the complete optimizer change. Relative commands, `TMPDIR`, source/input/binary/output hashes, original identities, histories and quadratic certificates are retained. Undefined initial/final step fields and endpoint internal gradients are explicitly not applicable (`nan`). No production code, configuration, input or inversion is changed.

This is a candidate for broader component regression. The four identified controls concern one boundary ray, and the affine controls are smooth cases. Their success does not establish global first arrivals, general convergence of constrained L-BFGS, or scientific adequacy of the current domain bounds. The cone subproblem is certified only within its documented floating-point arithmetic bounds.
