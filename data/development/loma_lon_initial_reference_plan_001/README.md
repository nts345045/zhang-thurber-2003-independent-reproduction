# LON initial-depth reference plan

This plan pins the complete saved LON initial geometry and its distinct depth-dependent initial grid after the exhaustive simulation-output audit passed. It authorizes a standalone continuous reference calculation only; no LON numerical forward run or inversion is performed by this plan.

The saved 724 initial events and 52 native receivers are byte identical to LOM. The initial grid differs: LON uses velocities 2.53, 2.53, 5.50640625, 6.03765625, 6.345629139072848 and 6.478079470198676 km/s at depths -1, 0, 3, 7, 11 and 16 km. Every one of the 37,648 propagation references must therefore be calculated independently for this profile. Source-time corrections remain separate metadata. The shared observation hash is reported from the two passed exhaustive audits; this plan does not reread observations or use them in the reference calculation.

`prepare.py` checks terminal/review links, small input hashes, complete native indices, finite endpoints inside the original box, and a complete positive nondecreasing z-only model. It records an explicit LON `plan.json`; the earlier LOM plan would correctly reject this different initial-grid hash. The existing `diagnostics/run_loma_initial_reference.py` and unchanged numerical helper are used without modification. Existing native metadata, numerical gates, invalid-reference handling and boundary interpretation remain unchanged.

The authorized command is:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_initial_reference.py --data data/loma_lon_analytic_001 --output data/development/loma_lon_initial_reference_001 --plan data/development/loma_lon_initial_reference_plan_001/plan.json --workers 4
```

The reference output has its own exclusive ledger and frozen inputs. This plan makes no forward-solver accuracy or inversion-acceptance claim.
