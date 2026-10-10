# Exact partition and fixed-cell controls

All 59 declared checks passed on nine invented edges: nine calls each to the frozen segment and isolated fixed-cell evaluator, 17 exact pieces and 136 quadrature samples. The four original cut-case actions, gradients and cut inventories reproduce their [prior saved values](../internal_face_contact_controls_001/RESULTS.md) exactly. One compiler, the driver and nine helpers exited zero and were reaped; stderr was empty. No production, native, ray-tracing or inversion calculation was changed.

The isolated evaluator uses every exact rational crossing, an exact open-piece cell, and the existing eight-point Gauss constants. Local basis factors, global endpoint factors and scaled weights are rounded separately to binary64. The cell does not come from a rounded global sample point. These are declared arithmetic changes together, not an isolated change to the cut predicate. The finite roster also requires binary64 endpoint subtraction to equal the exact endpoint difference; generic subtraction is not established.

## Measured endpoint errors

The table gives approximate endpoint-gradient error norms in s/km against the saved independent bounds. All six ordinary components are compared except for the aligned case, whose two normal components are explicitly unavailable and whose four tangent components are compared. All complete error intervals remain in [results/summary.json](results/summary.json).

| Case | Frozen segment | Exact partition / fixed cell |
| --- | ---: | ---: |
| Below displacement cutoff | 1.1322 × 10⁻⁴ | 7.4166 × 10⁻¹⁷ |
| Above displacement cutoff | 6.1085 × 10⁻¹⁷ | 6.1085 × 10⁻¹⁷ |
| Below endpoint cutoff | 3.2342 × 10⁻¹² | 5.7856 × 10⁻¹⁸ |
| Above endpoint cutoff | 5.0938 × 10⁻¹⁸ | 3.8688 × 10⁻¹⁸ |
| Translated adjacent binary64 endpoints | 7.5209 × 10⁻³ | 2.2902 × 10⁻¹⁷ |
| Constant velocity | 5.2412 × 10⁻¹⁷ | 5.2412 × 10⁻¹⁷ |
| Translated edge reversed | 7.5209 × 10⁻³ | 6.1933 × 10⁻¹⁷ |
| Aligned face, available components | 5.2336 × 10⁻¹⁷ | 5.2336 × 10⁻¹⁷ |
| Three-dimensional trilinear field | 1.2275 × 10⁻¹⁷ | 1.2542 × 10⁻¹⁷ |

The three-dimensional case uses `v = (2+x)(3+y)(4+z)` and has nonzero sampled derivatives on all three axes. Its largest reference-component interval width is about 5.5699 × 10⁻²⁴ s/km; its action-reference width is about 6.4701 × 10⁻²⁵ s. The displayed errors therefore remain resolved by the reference. The changes do not improve every case, and no accuracy threshold was imposed or relaxed. Error intervals combine quadrature and floating arithmetic; they are not labeled rounding error alone.

For the translated edge about `x = 1`, four of its 16 prepared exact-cell quadrature points round to global coordinates that `upper_bound` would place in the other cell. The reversed edge has another four such points; the other 104 samples have no mismatch. This saved-only inventory concerns the prepared fixed-cell sample points, **not the old evaluator's runtime sample locations**. The old translated edge also omits its crossing, so its improvement cannot isolate the cell-selection effect from the partition and other arithmetic changes.

## Evidence and limits

[Independent readback](review.json) checked 80 distinct hashes and 3,715 saved-data conditions, including every rational-to-binary64 handoff, numeric input file, old four-case equality, error interval and squared norm. Its [exact executed source](review_saved.py) and [terminal receipt](review_execution.json) are retained. The [native-free execution ledger](execution.json) and [outer receipt](outer_reaping.json) bind the closed control outputs. No helper or oracle was rerun for this review.

The returned vector approximates the continuous first variation; it is not claimed to be the exact derivative of the finite quadrature objective. An aligned-face branch normal is not an ordinary derivative. These bounded controls do not validate a production replacement, explain the original CMJ failures, or certify first arrival or optimizer convergence.
