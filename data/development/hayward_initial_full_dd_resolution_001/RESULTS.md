# Initial-model conditional result

The full catalog-DD calculation completed at the unchanged saved initial
Hayward model and explicitly chosen stage 0: **58,980 observations, 58,671 active
rows, 4,368 coupled source parameters and 462 model nodes**. The noise operator
shares the same 14,262 primitive catalog-pick errors across absolute and DD
observations. No cross-correlation data were included.

The fresh same-ray export was necessary: the older absolute Jacobian did not
retain the path-basis lengths needed to reproduce the 0.005 km DD mask. Its
source differs from the historical old-core run; the changed files and exact
exporter snapshot are disclosed in [scientific_verification.json](scientific_verification.json).
All 14,262 new initial-model rays passed the saved local/initializer checks and
the unchanged 1D time/source comparison. Maximum absolute time error was
0.959 microseconds; maximum source-vector error was
1.782 × 10⁻⁶ s/km, below the existing 25 microsecond and 3 × 10⁻⁶ s/km limits.
Independent saved geometry readback checked 11,506,620 path nodes, exact
endpoints/domain and native associations, and 414,792 source matrix entries.

The source solve, model resolution equation and noise-transfer relative
residuals were 6.53 × 10⁻¹⁶, 5.95 × 10⁻¹⁶ and 1.05 × 10⁻¹⁵. The model Schur
condition number was 2,295.59. The masked resolution diagonal ranges from
−1.6511 × 10⁻⁵ to 0.801721; its two small negative entries are retained.
Nodal propagated velocity standard deviations range from 0.0040493 to
0.0494122 km/s under the declared pick-uncertainty assumption.

Closed saved-output checks joined all native tables and the full identifier
companion, all 462 node rows and 14,262 pick rows, and the four finite 462 × 462
arrays. The saved velocity transformation and all reported diagonals matched
exactly. The covariance matrix was symmetric in the saved representation.
These checks did not repeat the ray trace or matrix solves.

One separate, documented packaged-input numerical replay subsequently completed
successfully. Both CSVs, the matrix archive and both complete identifier
companions matched byte-for-byte; all four arrays matched bit-for-bit. The
result manifest differed only in its twelve fresh input-path keys. This tested
the portable matrix procedure without repeating ray tracing or reference work;
the [replay comparison](evidence/numerical_replay.json) preserves the evidence.

This is conditional linear information with frozen weights, masks, scales,
regularization and computed branches. Source-bound active sets, model/station
error, regularization bias, selection effects and nonlinear/ray errors are
excluded. The source-partial comparison does not independently establish all
model-derivative accuracy. Reported timing uncertainty is assumed to be one
sigma; this is unrelated to instrument-response correction. The result is not
an inverse-normal posterior covariance, a final-model certificate, or evidence
of nonlinear convergence. Manuscript panel statuses remain 1 reproduced and
61 partial.

The [scientific manifest](scientific_manifest.json) binds the closed files;
the [README](README.md) gives fresh-destination replay and separate export
regeneration commands. Scientific outputs are preserved without runtime or
machine-state records.
