# Frozen Loma initial-ray observer review

The independent saved-record audit passed for `loma_initial_failure_3426_001` and `loma_initial_failure_24104_001`. Each review verifies 20 input, 14 frozen-source and 38 output hashes, the frozen compiler and binary records, every attached native field, exact current initial coordinates, complete path/history inventories, and both initializers' saved times against the original full-preflight table at its declared 12 significant digits. The original catalog coordinate metadata remain separately attached as `native_source_*`; the observer's `source_xyz_km` are the current perturbed initial coordinates. Pure ray time excludes the saved source origin correction.

The checker reconstructs raw and projected Euclidean gradient norms from the saved node gradients with the frozen boundary rule; all four values match exactly. It also verifies the recorded update counts, accepted action decreases and original termination conditions. Pair 3426's selected FMM path retains its false flag and one exhausted 24-evaluation line search after 53 accepted updates. Pair 24104 retains its original successful local flag; this review does not replace the separate failed continuous-reference source-accuracy result.

The frozen C++ driver compares observed and unobserved action, path, source derivative, model derivative/length arrays, gradients, updates, merge count and flag by exact floating-point value equality. All four saved equality records are true. The unobserved arrays are not separately exported: this audit verifies the comparison code and saved records, rather than independently reading a second copy of those arrays. No ray calculation was repeated.

The exact executed checker is preserved as `diagnostics/review_loma_initial_observers.py`; it is byte-identical to the temporary source named in `execution_receipt.json` and each review. It uses only the Python standard library. The recorded command was:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tmp/review_loma_initial_observers.py
```

The preserved diagnostic can run from the repository root in a scratch copy of the evidence without existing `review.json` outputs. It requires the pinned original files, frozen preflight binary/compiler and observer binaries recorded by the two summaries. Output creation is exclusive. The receipt links both review files and the exact checker hash. The audit does not establish a global first arrival, explain the cause of either failure, or assess a new method.
