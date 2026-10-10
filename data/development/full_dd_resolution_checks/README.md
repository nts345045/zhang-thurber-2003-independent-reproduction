# Full DD resolution and shared-pick noise controls

All 34 invented component checks pass. No real-data resolution, uncertainty,
ray trace or inversion is calculated by this fixture.

The exact two-pick example observes each pick and their redundant difference.
With primitive standard deviations 0.05 s and differential row multiplier
1/sqrt(2), the propagated parameter covariance is 0.05² times the identity.
Incorrectly treating the difference as independent instead gives 0.05² times
`[[0.75, 0.25], [0.25, 0.75]]`. The extra row adds no independent error source.

The second fixture has three events with x/y/z/origin-time parameters, three
model parameters, six primitive picks and twelve observation rows. It checks
the maintained Schur calculation against an independent dense joint solve,
including unequal pick uncertainties, fixed robust/stage/distance weights,
an omitted row, two DD model masks, smoothing and column-scaled damping.
One coefficient is deliberately stored as two entries. Their individual
squared values determine the exported scale even after the operator entries
are coalesced. Signed single-pick injections reproduce the calculated
covariance. Common origin-time shifts cancel in DD rows and remain in
absolute rows. The mask-induced response difference is retained explicitly.

Separate native-metadata fixtures preserve repeated pick identities, blank
location codes and open epoch ends, and reject inconsistent uncertainty,
epoch or arrival association and unsupported type-2 differential data.
All fixture resource IDs are explicitly invented.

Run from the repository root with a fresh evidence directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_full_dd_resolution.py --output data/development/full_dd_resolution_checks_repeat
```

The original command, source snapshots and hashes are retained in
`results.json` and `source/`. Comparisons use a declared floating-point
algebra tolerance of 2e-11 times the reference scale; this is not a ray or
field-data acceptance threshold. The assumptions remain fixed weights,
masks, scales and reference origin baselines with independent primitive pick
errors. Active source bounds and nonlinear estimator behavior are outside
these checks. Pick uncertainties already enter the noise matrix; there is
no additional 0.05² multiplier.
