# Tangent-cone metric quadratic controls

`baseline/` contains 9,007 checks with zero failures over 1,009 invented problems. They test all 3^6 combinations of free/lower/upper coordinates for two internal nodes, 200 randomized three-node problems, and 80 larger randomized problems. Weights span four orders of magnitude. The first 929 problems are compared with an independent exhaustive enumeration of every possible active face, using dense elimination and direct edge-energy evaluation. The maximum normalized direction difference is zero at the recorded precision. Larger problems check primal/dual/free residuals, complementarity and the quadratic descent identity. The maximum active-set solve count is 70; 22 blocking steps and 4,952 releases are exercised.

The component minimizes g·d + d^T L d/2 over the declared tangent cone. It starts from feasible d=0 with all boundary coordinates active. It solves the current free principal system, takes the first blocking step if that minimizer crosses a cone face, and releases a wrong-sign active multiplier only after a feasible full equality step. Original incident-edge diagonals remain in every principal matrix. Unlike the earlier no-release control, it can remove an initially frozen coordinate when neighboring motion makes that necessary.

A returned certificate requires finite arithmetic and primal, free, dual and complementarity residuals within the stated floating-point bounds. The row scale is |g_i| + sum_j |L_ij d_j|, so cancellation in Ld cannot hide the arithmetic scale. The multiplier/free tolerance is 64 machine epsilons times that row scale. Positive finite principal coefficients and pivots are checked. An explicit finite solve guard reports failure. Overflowing coefficients, overflowing directions, lost positive pivots and guard exhaustion have dedicated fail-closed tests. These are numerical algebra criteria, not changes to ray stopping or physics.

The original fixture source snapshot predates the subsequent outer strict-descent wrapper check; its quadratic solver and all KKT tests are identical. The final guarded ray variant preserves its own complete later source snapshot. A KKT certificate alone is not used as permission to pass a non-descent direction to Armijo.

Reproduce the component from the repository root using a fresh variant name:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_cone_ray_metric_checks.py --variant baseline
```

Existing variants are never overwritten. The runner freezes exact sources, normalizes archive metadata, compiles under repository `tmp`, and records relative commands plus source/binary/output hashes. These invented controls contain no observational data and do not establish global first-arrival or production-optimizer correctness.
