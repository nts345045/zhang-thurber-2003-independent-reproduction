# Adopted catalog-plus-CC input weighting

The isolated prepared dataset retains the literal exported `CC^2` as the
solver's `a_priori_weight`. That number multiplies both a residual and its
Jacobian row. The resulting squared data objective therefore contains
`CC^4`, before the squared stage, residual, and distance factors. This is an
explicit empirical convention for this comparison, not an inverse variance
or a reconstruction of the manuscript's exact weighting.

The earlier [read-only proposal](../catalog_cc_weight_contract_001/README.md)
is retained unchanged. It discussed both a `CC` row multiplier and the
literal legacy `CC^2` multiplier. This decision selects the latter without
silently taking a square root of the exported value. Changing that choice
would require a separately named sensitivity experiment, since the row
multipliers also affect column normalization and the physical effect of
scaled damping.

All original 58,980 catalog rows keep their values, order, reported reference
pick uncertainties, and prior multipliers. The 98 accepted waveform
differences are appended as type 2, preserving their local measurement IDs,
both provider event/origin/pick/arrival identities, full SEED/FDSN channel
identities, both native receiver epochs, raw and decoded sample hashes, and
processing/review provenance. The measurement value is `T_i - T_j`, with no
additional origin correction. Reference picks identify the source data;
they are not new provider picks assigned to the derived measurement.

The derived `uncertainty_s` is blank and `cc_uncertainty_status` is
`unestimated`. Neither sample spacing, correlation acceptance, nor the
robust-cutoff floor supplies a timing standard deviation. Existing
catalog-pick covariance calculations continue to reject type 2; shared
waveforms and catalog/CC dependence require a separately justified noise
model before a combined uncertainty calculation.

The adapter created no run configuration and invoked no solver. A future
reviewed configuration must set `catalog_only_dd=0` and all nine stage
factors explicitly. Forward and inversion accuracy gates remain separate.
In particular, adding measurements does not certify a later 3D forward
operator or remove the initial preflight requirements.

The independent invented controls exercise the actual C++ loader,
prediction, Jacobian, and Matrix assembly without tracing rays or solving.
For `CC=0.5`, the prior is `0.25` and the conditional squared-objective ratio
is `0.0625`. The 002 fixture also uses nonunit stage and distance factors,
retains empty location codes and two receiver epochs, and rejects stale
provenance and identity mismatches. Its 70 Python and 36 C++ checks and
hash-bound root review are pinned in `decision.json`. They validate this
contract, not waveform precision or recovery quality.
