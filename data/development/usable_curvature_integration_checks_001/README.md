# Bounded integration checks for the usable-curvature candidate

The isolated candidate completed all eleven commands with code zero at 2026-10-10 08:25:14 UTC; its durable controller reaped the wrapper at 08:25:15. No maintained production source, runner, configuration, live binary or long-running job was changed. The source snapshot contains the exact prepared candidate source/CMake roster and nine existing diagnostic dependencies.

The production executable passed all 48 `dd validate` checks. The actual inversion-guard component passed its invented current/trial/final rejection, native sparse/epoch identity, accepted-versus-failed state, and diagnostic preflight checks. The existing external-input component passed its CSV/native identity, cross-epoch DD source/model row and mismatch controls. Those fixtures use invented geometry; they are not real-data inversions.

The layered first-arrival refinement retained all 44 comparisons, with all 37 pre-existing finest-grid gates passing and all 58 production-entry comparisons exact. All selected rays have true local flags, exact endpoints and no outside nodes. At field/path spacing 0.0625/0.0625 km, the maximum time error is 1.7978061990e-6 s and source-vector error is 4.4274986916e-7 s/km. The coarser 0.125/0.125 km, 14.68 km-offset row has source-vector error 3.2403529176e-6 s/km, exceeding the 3e-6 target. It remains in the results; the unchanged gate inventory evaluates the finest grid. Passing the suite does not claim all coarse rows meet that accuracy target.

All six oblique affine comparisons and 72 existing checks pass, including six exact production-entry comparisons. The maximum FMM-bent time error is 4.3075931471e-6 s and source-vector error is 4.5737496508e-7 s/km. These fields have independently known contained analytic geodesics. The production-entry comparisons additionally check dispatch parity with the shared diagnostic implementation; that shared-code parity is distinct from the independent analytic accuracy checks. No global first-arrival completeness claim follows.

The copied layered and oblique runners differ only by adding `src/usable_ray_curvature.hpp` to their explicit frozen source lists. Their exact packaging diffs and original versions are retained. The action accumulator and optimizer candidate are identical to the reviewed D numerical implementation after include-path/comment normalization. The Fermat segment action, derivatives, Armijo rule, stopping tests and test thresholds were not changed.

`summary.json` binds 44 original inputs, 20 copied source files, 217 completed artifacts, compiler/flags and the three outer executable hashes. Child analytic summaries retain their exact source archives, commands, binary and output hashes. `execution.json` and `controller_completion.json` bind terminal states. Sources executed under the separate `tmp` workspace match the frozen snapshot, and all maintained input hashes were rechecked after execution. Build binaries remain local. The README and independent review are added outside the immutable summary inventory.

The command was:

```sh
/usr/bin/python3 diagnostics/run_usable_curvature_integration_checks.py --output data/development/usable_curvature_integration_checks_001 --build tmp/usable_curvature_integration_checks_001
```

A rerun requires fresh directories and the exact prepared baseline input hashes; this historical runner refuses to reinterpret a changed maintained source tree as the same candidate. No additional native row3426 replay, full real-cohort field construction, inverse acceptance or production adoption is performed by this package.
