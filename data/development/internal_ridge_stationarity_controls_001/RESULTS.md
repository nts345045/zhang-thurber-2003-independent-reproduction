# Completed invented ridge controls

All 37 exact rational checks and 62 numerical consistency checks passed.
The five commands exited zero. The executable performed 14 fixed-path and
2 direct segment evaluations; there were no trace or optimizer calls.

The fast-ridge face path has exact global minimum time 1/6 s, proved by the
velocity and length bounds. Its exact selected right-cell midpoint partial is
1/72 s/km; the frozen kernel reports 0.013888888888888888 s/km. Its y/z
partials are zero. Thus a true nonsmooth minimum need not make the selected
ordinary branch-gradient norm small.

The slow-face directional derivative is -|d_x|/50. Both normal directions
decrease action, although zero belongs to the convex hull of the two limiting
gradients. The recorded right-cell partial is -0.020000000000000011 s/km.
This is a negative control for treating minimum-norm convexification as a
local-minimum or all-direction stationarity certificate without regularity.

The coupled component has positive coordinate probes 1/8, 7/8, 7/8, 1/8,
but derivative -1/4 in direction (1,-1). Its canceling target is inside the
independent endpoint box and outside the exact correlated moment set.

For the 14 invented paths, the largest action discrepancy from the separately
evaluated 100-digit closed form is 6.96842e-17 s; the largest normal-gradient
discrepancy is 1.08247e-17 s/km. These are quadrature consistency observations,
not interval certificates. The global-minimum and directional statements
above follow from the analytic proof and rational identities, not from the
small discrepancies. No new stationarity threshold is introduced.

The exactly aligned invented geometry does not relabel any nearby native
polygon. At a nonzero distance from the face, its actual ordinary derivative
still applies. The variable-coefficient trilinear extension remains a
mathematical derivation; it has not been used for native acceptance or a new
solver.

Documentation clarification: the frozen README's statement that no native
data are imported refers to the new calculations. The copied prior
`inputs/moment_set_summary.json` also retains its original fully identified
historical native example as provenance. Neither executable nor checker reads
that native example numerically. No historical record or flag was changed.

`read_saved.py` verifies the frozen maps and saved counts without reevaluating
action or derivatives. `completion.json` records the owned command's observed
zero exit and the closed child-command ledger. An independent mathematical
result review can be attached separately without changing the frozen outputs.
