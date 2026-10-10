# Saved exact-trial comparison review

The checker requires a terminal exact-action comparison and its neutral native
replay review. It verifies source/input/artifact hashes, full native context and
sidecars, all 24 recorded decisions, exact rational interval relationships and
their classifications. No ray is retraced.

It independently checks the first trial certified to pass the saved-slope
Armijo comparison and the last trial using 80- and 100-digit Decimal arithmetic.
If none passes, the first trial is used and that fact is recorded. Input
coordinates and velocities are the exact rational interpretation of binary64
values. Straight segments are split at actual depth-grid planes, then their
reciprocal-affine actions are integrated with Decimal logarithms and square
roots, without importing the interval evaluator. Only these two selected trial
polygons and the base are integrated.

The two-precision agreement and membership inside the saved rational bounds are
independent numerical consistency checks, not new rigorous error certificates.
The saved interval classifications and original false local-convergence flag
remain separate from any production acceptance or optimizer change.

After terminal completion, run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_failed_trial_exact_review_001/review_saved_result.py
```

The checker writes `decimal_checks.json` here and a new `review.json` in the
exact-trial comparison directory; it refuses to replace either result.
