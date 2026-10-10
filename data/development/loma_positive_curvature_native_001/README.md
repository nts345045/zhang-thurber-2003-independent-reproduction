# Isolated positive-curvature retention experiment

This completed diagnostic changes only the two corresponding retention tests
in the frozen actual and observed optimizers from `s*y > 1e-14` to `s*y > 0`.
The B action accumulator, gradient, raw saved Candidate, resampling, Armijo
test, stopping rules, 1,000-update budget, and geometry are unchanged. It does
not change any production solver or live run. The unused extracted predicate
header changes consistently for the invented controls.

The preceding [seed-loaded B replay](../loma_seed_loaded_b_native_001/README.md)
reproduces all five original B numerical tables byte-for-byte. This establishes
that loading the full saved Candidate avoids repeating field initialization
without changing that replay. Each native table here carries an identifier
sidecar. `identified_ray.csv` retains the complete catalog and simulation
context: event NC10090782, origin NC2642854, receiver NC.JSJ..EHZ, and its
1989-05-02 through 1990-09-14 metadata epoch. Source coordinates are the
perturbed simulation geometry; catalog IDs identify its authoritative basis.

| FMM-seeded result | B: original retention | C: positive retention |
|---|---:|---:|
| Accepted updates | 1,000 | 145 |
| Retained pairs | 40 | 145 |
| Existing local flag | false | true |
| Travel time (s) | 6.5184200416971239 | 6.5184200416919014 |
| Projected gradient norm (s/km) | 4.720002826341664e-5 | 9.733534530359096e-6 |

C stops under the existing combined rule: its last accepted action change is
7.860379014346108e-13 s and its gradient is below 1e-5 s/km. It does **not** meet
the separate strict 1e-7 s/km gradient condition. The FMM history contains 73
recorded action decreases, 72 equal totals, no increases, no fallback, and no
node merges. Equal approximate totals do not determine the signs of exact
Fermat-action changes. The first B/C difference is retention at iteration 34;
the later path-state scalars first differ at iteration 35. The straight-seed
result remains unchanged at 54 updates.

Against the same complete continuous 1D reference, C's selected travel-time
error is 0.860608905917104 microseconds and its source-vector error is
3.177661894806077e-8 s/km. Both satisfy the unchanged 25-microsecond and
3e-6 s/km controls. The observed and unobserved C implementations agree on
their complete path and numerical arrays. `review.json` independently verifies
674 input, 55 prepared, 20 source, and 77 output pins, all native joins, histories,
reference comparisons, and the reaped controller lifecycle without retracing.

This single case supports a role for the absolute retention cutoff in B's
stagnation. It does not establish general convergence, global first-arrival
completeness, informative curvature from a positive dot product alone, or
inversion readiness. The invented controls explicitly retain unsafe cases:
positive subnormal curvature can overflow its reciprocal, and positive
infinity passes both predicates. No general adoption of `s*y > 0` is claimed.

The frozen invocation was:

```sh
/usr/bin/python3 diagnostics/run_positive_curvature.py --phase run --output data/development/loma_positive_curvature_native_001
```

`controller.py`, `launch.json`, `execution.json`, and
`controller_completion.json` preserve the actual command, timestamps, child
status, source/compiler/runtime/binary hashes, and input/output hashes. The
native replay completed on 2026-10-10 at 07:40:17 UTC with code 0. This README
was added after the immutable summary and independent numerical review.
