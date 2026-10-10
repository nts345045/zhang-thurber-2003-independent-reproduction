# Saved D/C replay review

`check.py` reads the completed usable-curvature diagnostic and the reviewed C
baseline. It does not invoke a ray tracer, quadrature, or action evaluator.
All five numerical CSV files have exact byte parity with C. The review also
checks all source/input/output/controller pins, full native context and sidecars,
saved path gradient norms, history ordering, approximate-total Armijo arithmetic,
memory evolution, and continuous-reference error arithmetic.

The FMM start retains all 145 pairs and stops after 145 updates. Its final
projected gradient is 9.7335345304e-6 s/km and final action change is
7.8603790143e-13 s. The straight start retains 54 pairs and stops after 54
updates. Both flags use the unchanged combined test; neither meets the strict
1e-7 gradient test. Both starts retain the original time and source-vector
accuracy limits. The FMM history has 73 decreases and 72 equal saved action
totals, with no recorded increase or metric fallback.

The passed native review is `../loma_usable_curvature_native_001/review.json`;
`stdout.json` preserves the exact checker output. No stored scalar prefix or
byte-identical table is used to claim an exact curvature sign, a certified
Fermat action difference, global first arrival, or general convergence. The
observed/unobserved model-array equality is the original recorded C++ numeric
comparison; those arrays are not separately exported for bitwise readback.

Reproduce without overwriting the frozen review:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_usable_curvature_review_001/check.py
```
