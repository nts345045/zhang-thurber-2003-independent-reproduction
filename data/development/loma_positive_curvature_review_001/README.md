# Positive-retention saved-output review

This readback passed for the isolated C diagnostic in `../loma_positive_curvature_native_001`. It verifies 674 original input pins, 55 prepared files, 20 frozen source files, 77 terminal outputs, the reaped controller and runtime records, all 199 native context fields, and every saved result/history/path/finite-difference row. It evaluates no ray, action, optimizer, or reference. The only numerical changes from reviewed seed-loaded B are the two `sy > 1e-14` to `sy > 0` retention literals; the separate extracted fixture predicate also changes but is not imported by the native driver.

C's FMM start accepts 145 updates and 145 pairs. Its original combined stop fires at iteration 144 with action change 7.860379014346108e-13 s and projected gradient 9.733534530359096e-6 s/km; the strict 1e-7 criterion is not met. The saved approximate action decreases 73 times, equals its previous value 72 times, and never increases. The first B/C saved scalar difference is the retention decision at iteration 34; excluding action and retention/memory fields, the first difference is iteration 35. Matching scalar prefixes do not establish equality of unsaved intermediate paths or directions. No fallback or node merge is recorded. All 145 pair decisions are retained, but C does not export computed `sy` or full `s/y` arrays, so this review does not reconstruct their values.

C's selected pure-time error is 8.60608905917104e-7 s and source-vector Euclidean error is 3.177661894806077e-8 s/km, passing the unchanged 25 microsecond and 3e-6 s/km limits for this ray. The straight start remains identical to B in its saved result/history/path fields: 54 accepted updates, 54 pairs, and the combined stop. Both starts retain the recorded exact numeric observed/unobserved path, source, velocity-derivative and length-array parity; the arrays were checked by the frozen C++ driver, not recomputed here. Original source-time correction is kept separately and excluded from pure travel time.

Positive-only retention is not a proposed safe general rule: its reviewed invented controls retain positive-subnormal reciprocal overflow and positive-infinity admission. Recorded Armijo arithmetic concerns approximate binary64 totals, not certified Fermat action. This single-ray result does not establish global first arrivals, a general convergence remedy, production adoption, or inversion readiness. All original flags and B outputs remain unchanged.

The exact executed command from the repository root was:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_positive_curvature_review_001/check.py --write-review
```

`--write-review` exclusively creates the native `review.json`; omit it for a later read-only repeat. `stdout.json` is byte-identical to that review. `execution.json`, the empty `stderr.log`, and `receipt.json` preserve the executed checker and its inputs/results. The review is distinct from root's prelaunch review and does not rerun any solver or numerical component controls.
