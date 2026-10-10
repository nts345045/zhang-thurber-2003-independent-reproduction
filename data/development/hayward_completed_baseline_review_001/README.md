# Completed legacy Hayward baseline: independent readback

The saved-table audit passes for the original, unguarded, straight-initialized
baseline. This is an integrity and numerical-results review, not a scientific
convergence certificate. It does not concern the newer guarded integration run.
`review.json` pins the terminal rebuild result, run manifest, numerical review,
source/binary and all consumed mode outputs. `check.py` reproduces the readback
without tracing rays or solving an inverse problem.

All three methods retain 1,092 event identities and all 58,980 identified
observations: 14,262 absolute picks and 44,718 catalog differences. There are no
waveform-derived observations in these runs. Every residual metadata field and
all 210 native associations for each 32-ray final sample match the saved inputs.
All event coordinates, velocities and residuals checked are finite; no event
lies outside the computational box.

The final absolute/catalog-difference RMS values are:

| Method | Absolute (s) | Catalog difference (s) | Accepted updates |
| --- | ---: | ---: | ---: |
| Standard | 0.07868923 | 0.07161650 | 12 |
| DD | 0.16063750 | 0.06159809 | 18 |
| Fixed velocity (`loc1d`) | 0.29188148 | 0.25423396 | 10 |

The fixed-velocity method still uses staged catalog-DD weights. Its catalog
difference RMS exceeds the initial 0.09340099 s, and it records three failed
line searches with zero updates. Its velocity grid is unchanged apart from
12-digit output rounding. Seven sources reach the computational top and one
reaches the y maximum; 23 have negative geoid depth. The median displacement
from catalog coordinates is 2.6383 km, which is not error against known truth.

The last recorded all-ray iterations contain 572, 3 and 277 failed local flags
for standard, DD and fixed velocity. History rows precede their update; DD
accepts its final configured update with a 2.76144 km maximum coordinate step.
The final deterministic samples have 31/32, 32/32 and 32/32 local flags at both
spacings. Maximum timing refinements are 101.494, 8.458 and 164.252 microseconds,
respectively. For fixed velocity the maximum production/refined source-FD
component discrepancies are 1.20699e-4 and 8.83194e-5 s/km. The legacy local
stopping rule, finite-difference traces without saved flags, and small sample
cannot establish globally earliest arrivals or nonlinear convergence.

The final DD absolute-data linearization retains two failed local rays, with
complete native identity records in `review.json`. The conditional resolution
calculation assumes independent one-sigma picking errors and unconstrained
source coordinates, even though some estimates reach domain bounds. It omits
correlated errors, regularization bias, nonlinear effects and ray errors. It is
not full-DD resolution or total velocity uncertainty.

`check_derived.py` and `derived_review.json` additionally verify every native
field in the 1,092-row geographic and 159-row common catalog-selected zoom
tables. They reconstruct all 83,895 displayed resolution interpolation points
from the 462 model nodes. The resolution manifest links these derived model
quantities to the fully identified absolute-data row and source-column tables;
the interpolation points themselves are not real station or earthquake records.
No figures, plot source, PDF or Figure 4 manifest are consumed by this audit.

The checkers require fresh output paths to preserve these reviews. Copy this
directory's checkers to a new sibling audit directory, then run them from the
repository root with `PYTHONDONTWRITEBYTECODE=1 python3 path/to/check.py`, followed
by the corresponding `check_derived.py`. They use only the standard library and
do not modify the solver inputs or output tables.
