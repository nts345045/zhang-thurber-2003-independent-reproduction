# Completed Hayward004 sampled forward assessment

This package reads the completed Hayward004 outputs against the independently
reviewed continuous initial-profile reference. It runs no production ray tracer
or inversion and changes no inputs, flags or accuracy limits. All 32 sampled
time rows, 24 saved source components (eight complete vectors), 48 reference
endpoint perturbations, and 210 original observation associations are retained
with event/origin, pick/arrival, channel and both epoch identities.

The 32 production/refined time errors are at most 0.716517/0.180597 microseconds.
The eight production/refined source-vector errors are at most
8.554815e-8/1.828812e-8 s/km. All pass the existing 25 microsecond and 3e-6 s/km
controls. All sampled, refined and perturbed original local/initialization flags
pass. The separate full-support comparison already verifies all 14,262 initial
production time and source-vector errors against these same controls.

The largest saved source-component versus finite-difference discrepancy is
3.047295e-6 s/km. The reference evaluated at the actual binary64 source
coordinates plus/minus 0.01 km gives a maximum central-difference truncation
error of 3.127681e-6 s/km. The largest difference between the saved finite
difference and the reference central difference is 3.265418e-8 s/km; the largest
saved perturbed-ray time error is 0.107166 microseconds. Thus the finite-
difference check must be interpreted separately from the source-vector control.
No new finite-difference threshold was introduced. `derivative_comparison.csv`
retains every term of this decomposition.

`review.json` is the independent saved-output and identity readback. The final
scientific decision is a separate hash-bound `accuracy_review.json`; package
completion alone does not authorize an inverse. These results concern the
initial depth-only model, not later three-dimensional models or globally
earliest arrivals in arbitrary media. Only eight refined source vectors were
saved, and the 48 perturbed reference times retain ordinary floating time
ordering with unique, complete branch enumerations.

Reproduction command:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/review_hayward_sampled_preflight.py --output data/development/hayward_sampled_accuracy_004_002
```

Use a fresh output directory for another execution. The first attempt under
`../hayward_sampled_accuracy_004/` is preserved: formatting the recorded command
used a relative `__file__` against an absolute root and failed before reference
calculation. The maintained helper resolved that path and the fresh second
attempt completed with exit code 0. No numerical formula or input changed.
