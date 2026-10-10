# Original failed-polygon internal gradients

This source-only preparation compares the saved old-kernel raw free-knot gradients with independent ordinary component bounds on the **unchanged original** CMJ polygons. It does not move a knot, retrace a ray, repair grid cuts, or compute optimized-ray source/model partials.

The fixed roster is event 981 / receiver 160 (1,029 nodes, 1,028 edges) and event 987 / receiver 160 (1,031 nodes, 1,030 edges). [native_contexts.json](native_contexts.json) preserves the full event/origin/channel/epoch identities and all 18 original catalog uses, including both sides of each differential record and valid empty location codes. Original local flags remain false, derivative-evaluation flags remain zero, and source partials remain blank.

The exact binary64 coordinates and 462 nodal velocities are promoted to rational values. The existing reviewed component primitive is copied byte-for-byte from `cmj_tangent_step_source_002`; it uses series degree eight (nine retained powers), one subdivision, and 128 bound bits. At most **2,058 edge component evaluations** are allowed, in one Python process. Fixed endpoint component arrays are omitted from saved results. Internal components unavailable on an exactly aligned interface remain explicitly unavailable. There is no new support integration, fit, optimizer, FMM field, compiler, or subprocess in this wrapper.

`run.py` sums adjacent ordinary component intervals independently and compares each available sum with the saved **raw** C++ gradient at that same free node. The error interval is saved C++ minus reference; its squared norm is enclosed without rounding a square root. Exact physical-box projection is applied separately to the reference and saved raw vectors. The historical C++ values projected with the old boundary activity band remain labeled separately. A difference between those projections is not called a component-evaluator error.

`event_981.json.gz` and `event_987.json.gz` will retain the original coordinate/native rows, all component-edge records, exact geometric availability, incident sums, old raw/projected values, component error intervals and squared norms. Full identifier sidecars are written before the first component call. A failure preserves completed/partial records and an explicit failed ledger. Root owns the outer process and its eventual reaping receipt.

The completed [original cut inventory](../hayward_cmj_original_cut_inventory_001/RESULTS.md) found no omitted/spurious cuts on this roster. That does not establish generic cut correctness or accuracy of samples rounded onto a face. This component audit measures the remaining original-path evaluator discrepancy directly. It does not certify first arrival, local stationarity, source derivative accuracy, or change either original convergence flag. No new error threshold is imposed.

From the published integration checkout, after all paths in `prepared.json` are present and the root prelaunch review passes:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 data/development/hayward_cmj_original_gradient_bounds_001/run.py
```

The preparation pins source, saved inputs/reviews, Python and runtime bytes. Preparing this package used file reads/copies/hashes and AST/schema inspection only; no primitive was imported or evaluated. `load_inputs()` is a saved-table-only prelaunch join and lazily verifies the reused stdlib utility module before import.
