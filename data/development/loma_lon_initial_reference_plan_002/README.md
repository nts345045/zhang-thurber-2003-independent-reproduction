# LON initial-reference attempt 002

This plan recomputes all 724 × 52 saved perturbed initial-source/receiver pairs using the same LON grid and complete native metadata as attempt 001. Source time corrections remain metadata and are excluded from pure propagation time. It selects the separately reviewed rational turning-speed reconstruction; isolated roots, physical formulas, finite box and original numerical limits remain unchanged.

`prepare.py` rechecks the passed simulation review and original plan, preserves links to the invalid attempt 001, and pins the new numerical module and independent review. Attempt 001 is retained with pair 8156 invalid. No original reference helper or wrapper is modified.

After review of the separate runner and its 48 invented controls, run:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_initial_precise_turn_reference.py --data data/loma_lon_analytic_001 --plan data/development/loma_lon_initial_reference_plan_002/plan.json --output data/development/loma_lon_initial_reference_002 --workers 4
```

The exclusive output directory freezes source, complete inputs and numerical review before calculation. All native results and unresolved certificates are retained. Execution completion is separate from reference comparison readiness. The terminal audit must compare every validity flag, candidate count, selected branch and time with attempt 001; this plan does not accept a numerical forward model or an inversion.
