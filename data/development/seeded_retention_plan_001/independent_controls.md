# Prospective independent invented controls

The control sources are `diagnostics/check_seeded_retention.cpp` and `diagnostics/run_seeded_retention_controls.py`. They are prepared for source review; no compilation or execution has occurred. The prepared B/C headers remain unchanged. These controls do not read authoritative ray geometry or construct an FMM field.

The loader fixtures preserve every raw Candidate field, quoted identifiers/messages, empty messages, signed zero, adjacent binary64 values, and a small **normal** value `2^-900`. Separate mutations require rejection of changed schemas, identities, statuses, counters, node inventories, frame order, endpoints, nonfinite coordinates, and coordinates outside the box. Every attempted CSV pair and rejection message is retained. A separate subnormal string probe records the implementation's parse behavior without broadening the round-trip claim or changing `csv_double`.

The post-resampling frame is structurally validated by the loader; it is neither returned nor recomputed there. A valid but deliberately different post frame makes that limitation explicit. The trace still performs its original resampling from the loaded raw seed. These invented controls cannot replace the later required five-file native replay parity.

Retention tests compile the predicate extracted from each actual frozen core. They include the values adjacent to the old cutoff, powers-of-two scaling, cancellation in the actual core dot product, underflow, NaN, and both infinities. The minimum positive subnormal is constructed directly in C++, independent of CSV parsing. Its overflowing reciprocal and the admission of positive infinity are recorded as failed generalizations of a positivity-only rule, not as safe optimizer behavior.

The sole ray fixture uses a homogeneous 5 km/s box, invented endpoints, a bent three-point raw seed, 0.5 km spacing, and an 80-update budget. The controls require the loaded and original raw seeds to produce bit-identical complete rays; the observed trace must match the actual trace. Its actual B history must show exactly one accepted and retained pair, establishing that the computed curvature already exceeds the old cutoff. Complete B/C ray bits and history bytes must then match. This one-update case does not exercise subsequent use of newly retained tiny-curvature memory.

The runner verifies every preparation/source pin, the two exact numerical literal changes, the extracted predicates, and the compiler hash. It freezes both source variants, preserves compilation/execution logs and failures, and rehashes consumed files at completion. An invented stale-file control exercises the same hash verifier. Builds remain in a separate fresh project-local temporary directory.

After independent source approval, the prospective command is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_seeded_retention_controls.py \
  --output data/development/seeded_retention_controls_001 \
  --build tmp/seeded_retention_controls_001_build
```

Execution is held for review. No native trace, production edit, inverse calculation, threshold change, or Git mutation is authorized by this document.
