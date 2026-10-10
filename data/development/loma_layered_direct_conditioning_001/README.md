# Near-critical direct-root conditioning

The failed full reference batch is preserved in `../loma_layered_full_001/` and commits `ebcd543`/`d2b4eaa`. This isolated diagnostic changes no maintained reference or production code. It compares all 11 identified failed direct roots and ten invented plateau cases, keeping the original 1e-8 km distance-closure requirement.

The old parameter is k = p vmax, near 1 for a nearly grazing direct ray through a short fast plateau. Finite spacing of binary64 k limits the recoverable normal velocity offset: for nine of the 11 native cases, even the best of the three representable k values surrounding the high-precision root exceeds the closure requirement. The proposed parameter is delta = u - vmax, with u = 1/p represented as **exact rational addition** `Q(vmax) + Q(delta)`. The existing leg function then forms u² - v² in rational arithmetic before its square root. Rounding `float(vmax + delta)` would discard the improvement.

All 21 additive-offset roots meet the unchanged closure requirement; the maximum residual is 7.11e-15 km. Independent 80-digit `decimal` reciprocal-affine integrals and monotone bisection agree in travel time to 3.91e-15 s and in source-vector norm to 2.87e-17 s/km. The decimal calculation independently evaluates the segment formulas; it is not an outward interval certificate. The invented controls have plateau depths from 1 to 1e-12 km and transverse distances of 5 and 50 km, and are explicitly distinguished from the 11 native pairs.

The high-precision calculation uses the same binary64 transverse differences and `math.hypot` distance target as the frozen reference. It checks leg integration and root arithmetic at 80 digits; it does not recompute the original geometry at 80 digits.

`results.json` retains each native row, original failed candidate, additive parameter and exact rational u, neighboring representable k values, 80-digit values, and the residual caused by rounding u or reconstructing it from p. General path sampling must preserve the rational parameter: the existing monotone sampler uses u = 1/p and can reintroduce this rounding loss. That sampler was not modified.

Run from the repository root into a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_layered_direct_conditioning.py --output FRESH_DIRECTORY
```

The minimal proposed maintained change affects the direct root parameter only, with explicit bracket-overflow failure and rational-u metadata. Candidate-family enumeration, turning roots, closure tolerances, and native geometry remain unchanged. Regression validation is required before another full batch; no simulation or inversion follows from this diagnostic alone.
