# Reusing an unchanged continuous reference

This replay compares the completed Hayward preflight 003 initial linearization with its previously calculated continuous references. Both `comparison.csv` and `references.jsonl` are byte-identical to the original 14,262-ray comparison. It performs no ray tracing or reference enumeration. The initial events, native receiver epochs, model grid, and complete observation table must match the reference inputs byte for byte, including every provider resource ID and SEED/FDSN identifier.

The comparison verifies the cached module and candidate hashes, complete and valid unique arrivals, every ordered native row/index join, and unchanged inputs at completion. A cache cannot be reused for moved sources, changed receiver metadata, a changed model, or a different observation selection. Path and initialization-field settings may differ because the cached reference describes the same continuous model and endpoints.

The new summary reports the existing analytic accuracy controls separately from original local convergence flags: absolute time error at most 25 microseconds and Euclidean source-vector error at most 3e-6 s/km. The replay matches the independent original review: 2,326 time passes, 1,842 source-vector passes, and 603 passes of both limits. This is a validation of the comparison, not a new numerical reproduction result.

The executed command was:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_hayward_1d_support.py --data data/hayward_first_arrival_003 --output data/development/hayward_cached_reference_check_001 --completed-linearization-only --reference-cache data/development/hayward_first_arrival_003_1d_support
```

Use a new output directory for a repeat. The completed-linearization option verifies the driver ledger and freezes completed tables while a separate preflight stage may still be running; it does not assert preflight success.

`frozen_tables.tar.gz` preserves the captured inputs and two comparison outputs without changing their bytes. `packaging.json` records every member and archive hash. Expand it in this directory to inspect those tables. The original reference archive must also be expanded in its own directory before running the cache comparison or replay controls. Source snapshots and `summary.json` are stored separately. The sibling `../reference_cache_controls_001/` records 17 passing rejection/replay checks, including changed geometry, changed observations, altered modules, altered candidates, incomplete references, nonunique arrivals, and missing derivatives.
