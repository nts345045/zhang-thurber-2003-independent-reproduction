# DD displacement and constraint review

This review uses the completed 18-update DD result and the prepared, identified
Hayward inputs. It does not establish nonlinear convergence or hypocentral
accuracy. Standard and fixed-velocity location inversions were still running
during the review. No solver input, configuration, production source, or active
process was changed.

Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3
data/development/hayward_dd_constraint_review.py` from the repository root to
recreate the event CSV, selected ray CSV, and JSON summary. The JSON records
input, archived provider-response, solver-source, diagnostic-source, and output
SHA-256 hashes. Each event row retains the saved event/origin IDs and metadata;
its receiver list includes native channel IDs, metadata epochs, and source
hashes. The selected-ray table retains every original observation field,
including pick and arrival resource IDs.

## Observations and calculations

The initial pair graph contains one component of 1,058 events and 34 unlinked
events. Reconstructing the solver's final-stage weights at the saved final model
gives a component of 1,057 events and 35 unlinked events. This calculation uses
the existing row-inclusion rule, weight at least `1e-12`, and the existing
10 km distance taper. These are the weights a subsequent final-stage solve
would form; they are not the unavailable weights before the last accepted step.

The 34 initially unlinked events have median catalog displacement 2.589 km,
compared with 1.165 km for the 1,058 linked events. The three largest shifts,
8.799, 7.953, and 6.827 km, belong to events 518, 4, and 930, each with eight
absolute picks and no DD link. Event 518 is
`quakeml:NC.anss.org/Event/NC/164172`, with origin
`quakeml:NC.anss.org/Origin/NC/2939944`. Its receiver azimuthal gap increases from
281 to 318 degrees as it moves onto the upper y boundary. These gaps use the
retained receivers and the initial or final source position, respectively.

The negative-depth result is not confined to unlinked events: 15 of the 19
negative-geoid-depth events were initially linked, including events with the
maximum allowed degree of ten. Ten of the 13 upper-depth-boundary events were
initially linked. Only event 1089,
`quakeml:NC.anss.org/Event/NC/30209219`, loses all remaining active DD links.
Graph fragmentation alone therefore does not account for the shallow solutions.

Final reconstructed weights retain 14,234 of 14,262 absolute rows and 41,886 of
44,718 catalog rows. The residual taper zeros 28 absolute and 2,634 catalog
rows; the distance taper zeros 243 catalog rows. These exclusion reasons can
overlap. Displacement has descriptive Spearman correlations of -0.254 with
initial pair degree, -0.220 with absolute pick count, and +0.183 with initial
azimuthal gap. The correlation with archived provider depth uncertainty is
+0.091. These associations neither establish causation nor identify reliable
events by a threshold.

The initial catalog has no used absolute ray with both endpoints in the
z=[-1,0] km top layer. The final DD geometry has 186 such rays, across all 19
negative-depth events and 120 native receiver epochs. They are identified in
`hayward_dd_top_layer_rays.csv`. The initial velocity model is exactly constant
between those two depth nodes at all 77 horizontal grid positions. The final DD
model has no exactly equal vertical pair: v(0)-v(-1) ranges from -0.015865 to
+0.014715 km/s. A flat-layer first-arrival counterexample therefore motivates
testing these actual DD rays, but does not by itself demonstrate that they are
incorrect. No intermediate fixed-velocity event positions were saved, so its
current affected-ray count cannot be reconstructed.

The event table also records a singular-value ratio for the dimensionless
matrix of straight source-to-receiver unit directions and a constant origin-time
column, using unique receiver positions. It is a geometric proxy. It does not
include ray bending, coupled velocity parameters, DD correlations, or active
coordinate bounds and is not a posterior covariance or rank test of the solver.
Provider uncertainties retain their archived units and confidence fields; they
are not assumed to be calibrated one-standard-deviation errors.

## Algorithmic limits and next numerical action

The source inspection found no new DD sign or receiver-index mismatch.
`src/core.hpp:552-566` normalizes columns before adding damping. In physical
parameters the added penalty is
lambda squared times diag(A-transpose A), so a weak source-depth column also
receives weak physical damping. Uniformly scaling all rows of an isolated
source-only problem cancels out of its update. Thus the damping value and a
decreasing weighted objective do not impose a fixed physical step scale.
This is a property of the specified regularization, not proof of a coding error.

`src/main.cpp:614-638` recomputes robust and distance weights between updates
but freezes them during each line search. Accepted objective values therefore
do not form one fixed objective across iterations. `src/main.cpp:655-660`
computes an unconstrained step and clips coordinates to the grid; it does not
solve a new active-set system or test the projected source gradient.
`src/main.cpp:672-711` accepts any decrease in that iteration's objective and
has no small-step or source-stationarity termination test. All 18 DD linear
solves met the existing LSQR criterion, while the last accepted source-coordinate
step was 2.76144 km. Linear-solve convergence does not resolve the nonlinear
question.

The next numerical action should first test the ray branch against an
independent first-arrival reference, including the identified shallow endpoint
geometries. A locally stationary path is insufficient when another path can
arrive earlier. Continuing iterations before that check would mix forward-model
error with inversion behavior. Preserve the present results as this attempt.

After the forward check, an instrumented continuation should save identified
per-event proposed and accepted steps, model/event checkpoints, stage/iteration
state, active row weights, and predicted versus actual objective reduction.
It should evaluate the projected source gradient at coordinate bounds and the
actual source/model Jacobian conditioning. A restart from saved files must retain
the intended weighting stage; restarting the current `invert` command would
otherwise repeat stage one. These diagnostics can distinguish a weak physical
direction, a clipped inconsistent step, and a ray-branch change without imposing
new geographic constraints or selecting a larger damping value by inspection.

No individual event can be assigned the 2.76144 km final update from the existing
history: only the maximum was saved. Catalog displacement is not error against
truth, and negative geoid depth does not alone establish a source above local
terrain.
