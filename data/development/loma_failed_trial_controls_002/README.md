# Exact comparison of recorded line-search trials

Seventeen invented controls pass for
`diagnostics/check_loma_failed_trials.py`. The independent source/control
review is `review.json`; its bytes are frozen for the subsequent native
comparison. No ray is traced and no optimizer or inverse calculation runs.

The helper uses the existing reviewed rational reciprocal-affine segment
integrals, logarithm remainder bounds and square-root enclosures. It permutes
physical coordinates as `(z,x,y)` for a depth-only model, sums the full
polygon action and directional derivative, and compares each recorded trial
with the original Armijo condition. Saved binary64 values are decoded as
exact rationals. An unchanged segment cancels identically; rounded trial
coordinates are never replaced by their ideal real-arithmetic coordinates.
The comparisons retain both the original saved gradient slope and the
separately enclosed continuous gradient slope.

Closed-form controls cover a homogeneous triangular path, its full nodal
directional derivative, exact cancellation, a resolved decrease, a decrease
hidden by rounding the total action to binary64, and collapse of a small
coordinate perturbation under binary64 rounding. A depth-affine horizontal
path checks the axis permutation and normal derivative. Interval comparisons
distinguish certified acceptance, certified rejection and unresolved bounds.

The native reader requires the complete identified failed-search export,
original failed flag, neutral-replay assertions, exact base-path/gradient
joins, all 24 evaluated steps, fixed endpoints, unchanged topology, domain
membership and full SEED/resource-ID sidecars. The final post-loop halved
step is distinct from the last evaluated step. Aligned nonsmooth base edges
are outside this ordinary-gradient comparison. These conditions define this
diagnostic's scope; they do not certify a replacement optimizer.

Recorded command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_loma_failed_trials.py \
  --output data/development/loma_failed_trial_controls_002
```

Use a fresh output path to repeat it. `source/` freezes all three executed
Python sources. The completed earlier `../loma_failed_trial_controls_001/`
snapshot precedes the stricter original-path and post-loop-step joins; its
same 17 arithmetic controls also pass. It is not a failed numerical attempt.
The independent control review does not replace review of the actual replay
or establish why the original line search failed.
