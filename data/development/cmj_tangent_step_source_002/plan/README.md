# One tangent metric direction on the two prescribed CMJ polygons

This is a derivation and proposed source plan only. No direction, metric,
trial polygon, action, ray, or optimizer has been evaluated for this proposal.
The starting data are the terminal, independently reviewed
[exact-face candidates](../hayward_cmj_face_action_001/summary.json), not the
original failed paths or a D solution. Their original convergence flags remain
zero; the candidate convergence field remains null.

## Question and minimum experiment

The saved candidate tangent norm lower bounds are about 3.4636652e-5 and
4.1306217e-5 s/km. These exceed 1e-5 s/km even before unavailable normal
components are considered. Selecting normal support values cannot remove this
tangent residual. The first coordinate witness happens to be far from the
modified face nodes; it is not the proposed direction.

The smallest useful next experiment is **one metric direction and one
predeclared trial per polygon**, using every available tangent component.
This tests whether a coupled, geometrically scaled tangent move gives a
certified full-action decrease. It does not need a new iterative optimizer.
A rejected or unresolved single trial would leave the finite-step question
open; it would not disprove the strictly negative directional slope. Do not
try other directions, halve the trial repeatedly, increase precision, or
escalate to an optimizer within this bounded experiment.

## Unchanged action and diagnostic search subspace

For the original continuous piecewise-trilinear velocity v, the polygon action
is

    T(p) = sum_e L_e integral_0^1 1/v((1-u)p_e + u p_(e+1)) du,
    L_e = |p_(e+1) - p_e|.

Coordinates are km, velocity km/s, action seconds, and nodal derivatives s/km.
The original finite model box, positive velocities, fixed endpoints, node
count, and node order remain unchanged. Every candidate node and model value
is reconstructed from the reviewed exact rational mapping of the original
binary64 values; the previously prescribed x=0 replacements are retained.
There is no additional snapping or resampling.

Let F contain all interior node-coordinate slots whose complete saved tangent
derivative interval is available. Set d=0 only at fixed endpoints and at the
31 or 32 unavailable face-normal slots. This chooses a feasible linear search
subspace of the original Fermat problem for one diagnostic direction. It is
not a new physical constraint, a reduced definition of stationarity, or a
normal-support selection. In particular, a later zero residual within F could
not certify stationarity of the full problem.

The reviewed candidates have no active physical box coordinates. Recheck that
fact from their exact coordinates. If it no longer holds, stop this scoped
experiment rather than silently project, fix additional coordinates, or
introduce a cone solver. The full action evaluator permits interior cell
crossings; the direction does not freeze nodes to their current cell.

For each edge a->b, with e=b-a and endpoint direction da,db, the complete
first variation is

    dT_e = (e dot (db-da))/L_e * integral_0^1 1/v du
           - L_e * integral_0^1 grad(v) dot ((1-u)da+u db)/v^2 du.

Cell-boundary terms cancel because v is continuous. On an edge aligned with
one internal plane, both endpoint normal directions are zero; the in-plane
trace of v and its tangent derivative agree from either adjacent cell. Thus
the saved available component intervals enclose the full first variation on
this subspace. Every slot is accounted for: unavailable normal terms multiply
exact zero, and endpoint variations are exact zero. Multiple aligned faces
remain outside the existing component helper's scope and must be rejected.

## Positive metric and complete slope certificate

Use the already reviewed metric formula at this unchanged candidate:

    w_e = 1 / (v((p_e+p_(e+1))/2) * L_e) > 0,
    Q(d) = sum_e w_e |d_(e+1)-d_e|^2.

Weights have units s/km^2 and Q has units s for a displacement d in km. The
midpoint formula is a numerical search metric, not an added objective penalty
or a claim about the true Hessian. Freeze and reuse `ray_metric_weights` and
`solve_free_ray_metric` from the old replay sources pinned in provenance.json;
no ray tracing or L-BFGS state is needed.

Choose each right-hand-side value as the nearest binary64 representation of
the exact midpoint of its saved derivative interval. Preserve that midpoint,
converted value, interval, and slot identity. Set unavailable RHS slots to
zero only for this solve. Require all weights/RHS/pivots/direction values finite,
all weights and principal pivots strictly positive, and no overflow. An
unusable arithmetic state is an explicit failed diagnostic, not a replacement
metric or new tolerance.

With fixed endpoints, the weighted Laplacian M is positive definite. Its
principal free-coordinate matrix M_FF remains positive definite. On each axis,
a fixed coordinate separates tridiagonal blocks, but the diagonal remains
w_(i-1)+w_i: an edge to a fixed coordinate still contributes stiffness. Solve

    M_FF d_F = -g_hat_F,
    d_not_F = 0.

In exact arithmetic g_hat dot d = -d' M d < 0 for a nonzero direction. The
actual finite solve need not be treated as exact. Save its weights, direction,
principal pivots, residual, and the two quadratic/slope evaluations, without
using a new residual cutoff to assert a numerical certificate.

Instead, regard every emitted binary64 direction as its exact dyadic rational
and contract it with **all** saved complete derivative intervals:

    S = sum_(j in F) [min(glo_j*d_j, ghi_j*d_j),
                      max(glo_j*d_j, ghi_j*d_j)].

Exact rational interval addition gives a complete directional slope bound.
Only S.upper < 0 certifies descent. If the bound includes zero, preserve an
unresolved outcome and do not form an action-decrease claim. There is no
magnitude cutoff, selected-coordinate omission, or reinterpretation of the
original stopping tolerance.

## One actual trial and full action verification

For a certified direction, compute the existing helper's positive geometric
step bound B from the box and from each changed edge:

    alpha <= distance_to_box_face / outward_direction,
    alpha <= lower(|e|) / (2 * upper(|db-da|)).

The latter is the triangle-inequality guarantee that an edge retains at least
half its positive length. It is a geometry bound, not an accuracy threshold.
Take one step alpha=min(1,B), represented by the largest binary64 value no
greater than that exact rational minimum. One is the existing metric full-step
convention. No trial is evaluated if alpha is zero or not finite.

Form the trial with the declared original binary64 multiply/add order, record
all resulting coordinates at 17 digits and in hex, and promote those actual
coordinates to exact rational values. Save the rounded displacement separately
from alpha*d. Require identical endpoints, identical unavailable normal
coordinates, unchanged node order/count, positive edge lengths, and exact box
containment. Do not clamp, merge, resample, or repair a failed trial. Contract
the saved derivative intervals with the actual rounded displacement as a
second complete slope check; an unresolved or nonnegative bound stays an
explicit diagnostic failure, without a substitute step.

Evaluate the **full original trilinear action** on this one rounded trial,
using the same frozen degree-8, one-subdivision, 128-bit outward arithmetic.
Reuse the reviewed starting action records and cancel identical ordered edges
by identity. Recompute every changed edge, including edges incident on fixed
face-normal slots. Save complete trial and starting action sums plus the
changed-edge difference enclosure Delta. No frozen-plane surrogate action is
allowed.

Report whether Delta is strictly negative, strictly positive, or unresolved.
Also test the inherited Armijo rule conservatively: with c equal to the exact
binary64 value of the original `1e-4` literal, require

    Delta.upper <= c * alpha * S.lower.

This sufficient test certifies the original Armijo inequality for every slope
in S; it introduces no new constant. Only this outcome, plus all geometry and
actual-displacement checks, may be called an accepted **diagnostic trial**.
A decrease that does not pass this inherited rule remains separately labeled.
No accepted trial becomes a converged ray, a first arrival, or an inversion
input. No trial source/model derivative is computed. The diagnostic supplies
no post-step full stationarity claim.

## Native identity, preservation, and prospective controls

| Event index | Event resource ID | Origin resource ID | Nodes | Unavailable normal slots |
| --- | --- | --- | --- | --- |
| 981 | quakeml:NC.anss.org/Event/NC/518943 | quakeml:NC.anss.org/Origin/NC/4251144 | 1029 | x at nodes 724 through 754 |
| 987 | quakeml:NC.anss.org/Event/NC/519264 | quakeml:NC.anss.org/Origin/NC/4252064 | 1031 | x at nodes 726 through 757 |

Both use receiver index 160, NC.CMJ..EHZ, FDSN:NC_CMJ__E_H_Z, with the valid
empty location and channel epoch 1996-11-12T23:45:00 through
1998-06-09T19:30:00. All source/receiver metadata and raw model mappings must
be copied byte-for-byte or linked by their reviewed hashes, then preserved in
full native sidecars for every direction, matrix, trial, and action output.
Do not create a new event/pick identity or reinterpret the failed inversion
trial as an accepted state. Exact candidate-to-original mappings, original
false flags, and unevaluated source partials remain attached.

Before any native evaluation, a small independent invented suite should check:

- Principal-block versus dense positive-system agreement, retained incident
  edge diagonals, exact fixed zeros, and homogeneous analytic first variation.
- A stationary homogeneous straight path produces no negative-slope claim;
  unresolved derivative intervals and unusable finite arithmetic fail closed.
- A nonstraight homogeneous single trial has the known full length action,
  correct complete slope sign, and separately reconstructed Armijo arithmetic.
- Endpoint/normal immutability, actual rounded displacement, box/positive-edge
  checks, and refusal of a prior output or changed native input.

These are prospective controls, not executed results. Review the concrete
metric-only source, command, fixed budget, output identity schema, and frozen
inputs before authorizing either native trial. The maximum native action work
is 1028+1030 trial edge actions, fewer if exact unchanged edges cancel. There
are two small principal-block solves and interval contractions; no new tangent
integrations, fields, ray traces, inverse solves, or iterative searches.

The original failed paths, reviewed face candidates, live Hayward binary and
configuration, and both active Loma preflights remain untouched.
