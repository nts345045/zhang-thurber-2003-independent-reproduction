# Invented saved-seed and retention controls

Both frozen variants pass **100 checks**. The old rule retains `sy > 1e-14`; the diagnostic alternative retains `sy > 0`. Their source difference is limited to the declared literal in the actual and observed optimizers, plus the extracted predicate used by these tests. No production source, authoritative ray, FMM field, or inverse calculation was run or modified.

`summary.json` is SHA-256 `7168b73438d57ad0db0de6c9f974794db93f122008a224a4c247494b5aba7273`; `execution.json` is `ea5e69ec636c0db056d7a7218252db8aa1b63b081bd8e0985d6e4708dcf4adf7`. The summary pins 71 inputs, 42 frozen source files, and 326 output artifacts. Both compilations and both executions returned zero. The two hash controls additionally accept a matching invented file and reject a changed one. Independent saved-artifact review is requested separately in `review.json`.

The fixture is [check_seeded_retention.cpp](../../../diagnostics/check_seeded_retention.cpp), SHA-256 `9543a9ca6a7b11d6c995c03e7d864a9c212771a0aa86737cb13dd536aed53296`. The runner is [run_seeded_retention_controls.py](../../../diagnostics/run_seeded_retention_controls.py), SHA-256 `5a6ba5ef2df4b2f2269da9d2a21bcc78266b271b8323a84c03fca2fd762a09ee`. Copies and all dependencies are retained under `source/`. The prepared manifest includes the identified native provenance of the frozen implementation; it does not make the invented fixture coordinates real records.

The loader round-trips every field of a successful raw Candidate, including normal finite binary64 values, signed zero, quoted identifiers, embedded newlines, and an empty message. Mutated schema, identity, status, counter, frame, node, endpoint, and coordinate cases are rejected. Every attempted input and exception is retained under each variant's `loader/` and `loader_rejections.csv`. `std::stod` rejects the attempted minimum-subnormal decimal string in this environment; that result is preserved in `subnormal_parse_behavior.txt`. The successful round-trip claim is limited to the stated normal finite fixtures.

The saved post-resampling frame is structurally validated, not recomputed or returned by the loader. The trace performs its original resampling from the returned raw path. A deliberately different valid post frame passes this structural check, making that boundary explicit. Later native five-file replay parity remains necessary to establish a full replay.

The homogeneous 5 km/s fixture uses one bent invented seed. Both variants take one update, retain its sole curvature pair, and return the same nine-node ray: time `0.7362064927722386` s and reported gradient `2.1228933251263786e-16` s/km. The original and loaded raw seeds, observed and actual traces, and complete B/C ray bits and history bytes match. The actual B retention flag proves that this pair already exceeds the old cutoff. The test does not exercise later use of newly retained tiny-curvature memory.

The positivity-only rule fails a general floating-point safety claim. It admits `sy = 4.9406564584124654e-324`, whose reciprocal is positive infinity. Both rules admit positive infinity itself. Actual core dot products also demonstrate cancellation to zero, order dependence, and underflow of a positive real product. These outcomes are retained in `retention_cases.csv`; a passing control means the declared limitation was reproduced, not that unsafe behavior was accepted for production.

Compilation logs preserve two nonfatal warning categories: the uncalled renamed driver main lacks an explicit return, and the fixture's CSV loop writes its newline after the loop on the same source line. Source bytes stayed frozen during both builds. Binaries remain only in the temporary build directory named by the manifest.

To repeat after the required source review, use fresh output/build names:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_seeded_retention_controls.py \
  --output data/development/seeded_retention_controls_NEW \
  --build tmp/seeded_retention_controls_NEW_build
```

No native outcome, corrected convergence flag, useful-curvature guarantee, or optimizer adoption follows from these invented controls.
