# Zero aligned-normal support on the retained accepted first trial

Source only; not imported or executed. The second full-size tangent trials increased the action and were rejected. This assessment uses the accepted **first** trials for events 981 and 987 at receiver160, with the already reviewed post001 edge-component arrays. It does not evaluate any new tangent, normal, action, metric, rounding, ray or field integral, and does not search for another support or trial.

## First variation

On an edge aligned with exactly one internal grid face, the normal component of its length variation is zero. Split the edge at its other grid crossings using the unchanged exact partition. On each patch, the continuous face velocity is positive, and each one-sided velocity normal derivative is a quadratic in the local parameter. The frozen `quadratic_bounds` routine checks both endpoints and every interior stationary vertex with rational arithmetic. Require the entire minus-side derivative `gm >= 0` and plus-side derivative `gp <= 0`.

Then the slowness normal derivatives satisfy `s_minus = -gm/v² <= 0 <= -gp/v² = s_plus`. Where `gm-gp > 0`, the pointwise convex mixing parameter is `theta = gm/(gm-gp)` in `[0,1]`. The centered convention is `lambda = 2*theta-1`. At a zero denominator, the proved signs imply both derivatives are zero; choose `theta=1/2`, `lambda=0`. The same pointwise choice makes both coupled endpoint normal moments zero. This uses the convex first directional variation and does not independently clip endpoint derivatives. Continuity cancels moving-cut boundary terms. Positive jump alone is insufficient for this particular zero choice.

Record every exact side polynomial, cell, patch interval, complete range and sign result. If any whole-patch sign condition fails, preserve `inconclusive_sign_condition_failed`, with no constructed full vector or alternative integration. Zero and equality cases are allowed exactly, without a tolerance.

## Saved vector assembly

Keep every available tangent component unchanged. For each aligned edge, substitute zero only for its proved normal contribution. Add all ordinary contributions from unaligned edges, including every normal contribution at entry and exit of a face segment. Sum incident edges at every free node and project only at the true physical box using the unchanged exact projection. Fixed source and receiver slots remain omitted. No source or model partial is produced.

The available tangent **lower** squared norm remains a residual obstruction. The full constructed vector's **upper** squared norm bounds one feasible supporting vector; it is not the minimum support norm. A large upper value is inconclusive. The full vector's lower squared bound also refers only to this chosen vector; it is **not** a lower bound for the minimum support residual. The exact decimal `1e-7` and `1e-5` scales are diagnostic comparisons only. Neither comparison changes an original flag, accepts a path, or certifies a first arrival or source derivative.

The raw arrays are checked against both incident edges, exact first-trial coordinates, unchanged masks, the hash-bound independent post001 review, the full native event/origin and receiver SEED/FDSN/epoch identities, and all nine original catalog uses per ray. Original flags remain false, original source partials blank, and candidate convergence null.

## Execution boundary

The wrapper reuses post001's model loader, exact projected norm and owned single-process ledger pattern. Identified sidecars precede polynomial work. Inputs and runtime bytes must match a prepared manifest and independent prelaunch review. Root owns and reaps any later invocation. Exceptions preserve completed polynomial evidence; failed sign conditions are an explicit inconclusive scientific outcome, not an execution failure. No subprocess is spawned. `post001_to_saved_support.patch` shows the complete source adaptation.

The abandoned `../hayward_cmj_post_step_support_002` draft remains unexecuted: it was written before the second-trial rejection became known and has no prepared manifest or numerical output.
