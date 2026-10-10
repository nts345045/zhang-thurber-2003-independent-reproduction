# O3 controls for the separately guarded Hayward inverse

Variant `001` passed 30 controls on invented geometry. No real earthquake
inversion or real ray evaluation was run by this suite. The source comparison
and intended reuse scope are recorded in
`../hayward_guard_adoption_plan_001/`.

Both the exact frozen Hayward004 source and the guarded source were compiled
through fresh CMake builds with
`-std=gnu++17 -O3 -Wall -Wextra -Wpedantic -fopenmp`.
The rebuilt old binary is byte-identical to the historical004 binary
(`951fa8bf5c43809bc4386bc41a6d6bdefccec33d7124fec2aacbd4e7bc7f13c8`).
The separate guarded binary has SHA256
`c8c1b56a78fc55cbe3fbbf6c7370a799ce0819e9a90db34e6f931a2f895e6203`.
These are measured binary identities, not an assumption about compiler
equivalence.

At one and four threads, successful inverse outputs and production-entry
linearization/raycheck CSVs were byte-identical between the two sources.
The forward controls used path spacing 0.03125 km and FMM spacing 0.125 km,
including the ordinary factor-two refinement. A deliberately unconverged
zero-update case continued in the old executable and stopped in the guarded
executable, preserving identified failed and last-accepted states. Component
controls exercised current, trial and final failure handling. Native metadata
controls retained the two distinct epochs in cross-epoch differential rows.

These finite controls support reuse of the already measured initial-model
evidence when the mathematical source, inputs, configuration, toolchain and
native ray support remain unchanged. They do not establish accuracy for a
later three-dimensional inverse model or global first arrivals. The guarded
launcher still requires the completed real preflight and its explicit
scientific accuracy review.

Reproduce in a fresh variant directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_hayward_guard_adoption.py --variant NEW
```

`001/summary.json` retains the original command, source, binary and 581 artifact
hashes. Its original inventory omitted nested files named `summary.json`,
including the two component summaries. Those files were retained unchanged;
`001/publication_inventory.json` additionally pins every delivered file,
including both component summaries and the original top-level summary.
No numerical artifact or frozen source was rewritten to add that inventory.
