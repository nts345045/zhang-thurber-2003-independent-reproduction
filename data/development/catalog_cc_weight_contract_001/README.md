# Proposed catalog-plus-correlation input and weighting contract

This is a read-only scientific/code audit and a proposal, not an imported
dataset, changed solver, selected uncertainty model, or launched inversion.
Written-source access: 2026-10-10 UTC.

## Written weighting specifications

Zhang and Thurber (2003), p. 1877, describe linearized absolute and differential
equations with damping and smoothing, equation weights based on prior data
uncertainty, data type, separation, and residual size, and unit-L2 column
scaling. Their successive absolute/catalog/WCC factors are
`(1, 0.1, 0.01)`, `(0.1, 1, 0.01)`, and `(0.001, 0.01, 1)`.
The prose does not calibrate our independently computed normalized CC to a
standard deviation or uniquely specify its objective-weight conversion.
[Author-posted manuscript](https://www.researchgate.net/publication/215754286_Double-Difference_Tomography_The_Method_and_Its_Application_to_the_Hayward_Fault_California).

Waldhauser and Ellsworth (2002), section 2.3, paragraph 18, p. ESE 3-4,
describe squared-coherency prior weights, catalog quality weights, and
residual/distance reweighting. Squared spectral coherence and the square of
our time-domain Pearson maximum are different quantities.
[Written precursor](https://www.ldeo.columbia.edu/~felixw/papers/Waldhauser_Ellsworth_JGR2002.pdf).
EQcorrscan's `write_correlations` documentation defines a legacy export using
the squared maximum correlation by default; it also permits the unsquared
coefficient. This file convention does not establish a formal inverse
variance or require a particular least-squares row interpretation.
[EQcorrscan documentation](https://eqcorrscan.readthedocs.io/en/latest/submodules/autogen/eqcorrscan.utils.catalog_to_dd.write_correlations.html).

## Current implementation

`src/main.cpp:12` defines no uncertainty member in `Datum`. The loader reads
`a_priori_weight` as a finite nonnegative number at lines 626–630; columns such
as `uncertainty_s` remain metadata. The real-input identity checks at lines
756–789 do not require a numerical uncertainty. An unestimated CC uncertainty
can therefore remain blank without inventing a placeholder sigma.

At `src/main.cpp:906`, the row multiplier is

```
w = stage * a_priori_weight * residual_biweight * distance_taper.
```

`src/core.hpp:539` multiplies both Jacobian entries and the residual by `w`.
The nonlinear trial objective explicitly sums `w*w*residual*residual` at
`src/main.cpp:1200`, holding these weights fixed during that iteration's line
search. Thus the following are distinct, internally consistent choices:

| Input prior multiplier | Conditional quality factor in the squared data objective |
| --- | --- |
| `CC` | `CC^2` |
| `CC^2` | `CC^4` |

Neither interpretation should be selected implicitly from a column called
“weight.” The residual and distance factors are already squared tapers, and
their contributions are squared again in this objective. Combined multipliers
below `1e-12` omit the row. Changing prior multipliers also changes column
normalization and the physical effect of scaled damping; it does not only
change a displayed residual score.

The existing catalog preparation uses `0.05 s / sigma`, with pair sigma
`hypot(sigma_i, sigma_j)` (`prepare_hayward.py:217`, 238–239). These are
dimensionless row multipliers. Catalog differences share picks and are not
independent measurements. Provider uncertainty confidence levels do not
establish the assumed one-sigma calibration used in the conditional noise
diagnostic.

## Minimal proposed import

1. Use a fresh, separately labeled catalog-plus-CC run. Preserve the 58,980
   current catalog observations and their native fields and multipliers. Append
   only the 98 reviewed accepted measurements as type 2; retain the complete
   44,718-row measurement/status sidecar. The resulting roster would have
   59,078 rows. Do not replace catalog values or import rejected candidates.
2. Import from the complete identified sidecar, not the station-only legacy
   text. Map existing event/origin identities and both receiver epochs exactly;
   retain the local measurement ID, original row ID, both native pick/arrival
   IDs as reference-pick provenance, full SEED/FDSN identities, all raw/sample
   hashes, and the frozen processing and independent-review hashes. The
   waveform difference is a derived measurement, not a new provider pick.
3. Keep `value=dt_cc_i_minus_j_s`, without an additional origin correction.
   Keep `legacy_cc_relative_weight=CC^2` separately. A minimal explicit choice
   is `objective_quality=CC^2`, hence `a_priori_weight=CC`, using the positive
   accepted maximum. This is a declared empirical weighting convention, not
   a claimed recovery of the paper's exact prior weights. Literal legacy
   `CC^2` as the row multiplier is also possible, but must instead be labeled
   as giving a `CC^4` objective quality. Do not mix the two conventions.
4. Keep the derived measurement's `uncertainty_s` blank with an explicit
   unestimated status. Retain the original reported pick uncertainties in
   provenance fields; they are not CC uncertainties. Neither the 10 ms sample
   spacing nor the robust cutoff floor supplies a 0.01 s sigma.
5. A CC-enabled configuration must explicitly disable `catalog_only_dd`, which
   otherwise rejects type 2. Write every stage factor in the separate config;
   adopting the manuscript's hierarchy is an empirical experiment, not a
   demonstrated accuracy ratio for these 98 measurements. Preserve the
   independently reviewed guarded forward solver and all preflight/accuracy
   requirements. Reuse no later 3D accuracy claim from initial 1D validation.

The proposed CC prior has a dimensionless unit-quality reference, as do the
catalog priors when sigma is 0.05 s. No additional CC error scale is implied.
The accepted subset covers only 103 events and four channels; comparisons
must state this limited support and preserve the original catalog run.

## Uncertainty and required verification

`resolution_full_hayward.py:86` deliberately rejects type 2 because its noise
matrix is built from shared *catalog-pick* errors. Retain that rejection for a
combined run until a separate, defensible CC covariance—including shared
waveforms and possible catalog/CC dependence—is specified. Acceptance of a
correlation screen does not define this covariance. A catalog-only conditional
noise diagnostic at a combined solution would need that restricted scope in
its name and caption; it would not be uncertainty of the combined estimator.

Before import, use invented identity/sign controls, assert the 98 accepted
rows and all original catalog fields, verify both native epochs, and check
the actual assembled row/objective coefficient for a known `CC`. Verify
roundtrip `CC^2` separately from the adopted row multiplier and preserve blank
derived uncertainty. No real import, code change, or new solve was performed
for this proposal.
