# Independent readback of the neutral curvature capture

The saved-record audit passed. No ray, field, action, reference enumerator, or optimizer was executed. The exact executed checker is [review_saved_capture.py](review_saved_capture.py); its command, timestamps, return code, and logs are bound by [readback_execution.json](readback_execution.json). Reproduction requires a fresh review-output location: the checker refuses to overwrite its two final review files.

The identical result is saved as [readback.json](readback.json) and [the native review](../loma_curvature_capture_native_001/review.json). It verifies 130 original input pins, 44 prepared files, 21 frozen source files, and 85 output pins; the five earlier B result tables remain byte-identical. The terminal execution, reaped-driver controller record and logs, metadata-only packaging receipt, retained raw CSV and its full 199-field native sidecar, gzip content, and all native joins are checked. The decoded gzip is exactly the retained 273,739,890-byte CSV; its compressed size is 100,494,158 bytes.

All 1,000 accepted-step/pair records and their memory creation IDs, ages, eviction decisions, history scalars, and strict `sy > 1e-14` decisions were checked. The full component stream contains 1,132,000 interior-node records. Sequential binary64 dot/norm sums were reconstructed for every pair. Independent exact Fraction reconstruction covers 22 iterations: the 19 selected iterations plus the initial, minimum-dot, and threshold-neighbor cases, with overlaps removed. All 1,000 saved exact classification rows were checked, including their recorded-total Armijo algebra; the other exact component sums were not redundantly recalculated.

For the 19 selected iterations, all 38 pre/post states (43,092 vertices) match `s = step*q`, gradient differences, rounded coordinate updates and actual displacement. The 3,040 adjacent-edge cut records match the frozen cut predicates. The 568-node raw seed reproduces the 1,134-node resampled initial polygon with exact saved numeric equality. These are geometric and stored-value checks, not new action evaluations.

## Reviewed numerical inventory

- All 1,000 computed, exact stored-component, and exact actual-displacement dot products are positive. All three forms retain exactly 40 pairs, with zero threshold-classification differences.
- The 960 rejected computed values range from `2.064992818519011e-20` to `8.91172417171982e-15`; the 40 retained values range from `1.0630538388861982e-14` to `0.08755030659687055`. With coordinates in km and action gradients in s/km, these dot products have units of seconds.
- The last retained pair is iteration 434. The subsequent 565 pairs are rejected by the unchanged absolute cutoff. At iteration 999, memory creation IDs are `[32, 33, 270, 404, 429, 432, 433, 434]`, with ages `[967, 966, 729, 595, 570, 567, 566, 565]`.
- Saved action totals decrease 436 times and remain equal 564 times; none increase. All 1,000 recorded binary64 Armijo tests pass. Exact algebra of those approximate saved totals gives 564 negative declared Armijo margins. This is not an exact Fermat-action test.
- Every stored `s` vector differs in at least one component from the separately captured rounded coordinate displacement. Their exact dot products nevertheless give the same retention decisions here.

The FMM run retains its original 1,000 updates and false local-convergence flag. Positive dot products do not prove that rejected pairs are informative, admissible replacements, or a remedy. The selected geometry does not recover unexported paths at other iterations. The capture supplies evidence about actual cutoff decisions and memory age; it does not change the optimizer, physics, tolerances, or flags.
