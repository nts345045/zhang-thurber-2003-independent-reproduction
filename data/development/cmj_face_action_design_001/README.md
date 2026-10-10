# Bounded action and tangent variation of a face candidate

This is a design only. It contains no candidate coordinates, action evaluation,
native call, optimization, or new convergence criterion. The first proposed
implementation evaluates action and one tangent witness. It does not solve a
dual problem or search for an improved path.

## Geometry and numerical model

Use the two original selected CMJ polygons and exactly the 31 and 32 internal
nodes in the reviewed [near-face inventory](../hayward_cmj_interface_geometry_001/README.md).
A separately identified candidate sets those nodes' x coordinates to the exact
grid plane x=0. Preserve the original coordinates, node order, endpoints, full
native context, and original false status. The inventory is a descriptive
selection, not a physical constraint or stopping tolerance. Do not reuse these
indices on a different polygon. Require positive edge lengths and the original
finite box; retain an ineligible result if either check fails, without merging
nodes. Keep every real-coordinate output identified, including JSON sidecars.

The target is the continuous piecewise-trilinear interpolation of the recorded
binary64 grid values, evaluated along the recorded binary64 coordinates and
the stated exact-zero replacements. Convert each parsed finite binary64 input
to its exact rational value, retaining the original text and binary64 identity.
This encloses integration and arithmetic error for that numerical model. It
does not enclose observational error, input quantization, model uncertainty, or
the rounding error of the production floating-point interpolation/quadrature.

For an edge e=b-a, let L=sqrt(e.e)>0 and r(u)=a+u e, 0<=u<=1. Coordinates and
L have units km; velocity has units km/s; the action is

    T_edge = L integral_0^1 1/v(r(u)) du.

Partition u exactly at every interior grid-plane intersection. Sort and
deduplicate rational cuts without a small-distance exclusion. The edge lies in
one closed cell on each resulting interval. Its velocity restriction is a
rational polynomial of degree at most three; its velocity partial derivatives
have degree at most two. A face-contained edge has a quadratic velocity on
each face-patch interval, not necessarily one quadratic on the entire edge.
Use the common continuous face value and retain both normal derivatives.

Positive cell vertex velocities give a strict positive lower bound throughout
the closed cell, because trilinear interpolation is a convex combination of
its eight vertices. This is the initial positivity certificate. Rational
Bernstein coefficient bounds after interval restriction can tighten it; an
unhelpful Bernstein lower bound does not invalidate the positive vertex bound.
Nonpositive or nonfinite input velocities are outside this proposed scope.

## Polynomial integrals with explicit tails

On one parameter interval I of width ell, take certified rational bounds
0<v_min<=v(u)<=v_max. Define

    c = (v_min+v_max)/2,
    q(u) = (c-v(u))/c,
    rho = (v_max-v_min)/(v_max+v_min) < 1.

Then |q|<=rho and v=c(1-q). For integer N>=0, exact integration of the finite
polynomial sum gives

    A_N = (1/c) sum_{k=0}^N integral_I q(u)^k du,
    | integral_I 1/v du - A_N |
        <= ell rho^(N+1) / [c(1-rho)].

This follows directly from the pointwise remainder
q^(N+1)/[c(1-q)]. All finite polynomial coefficients and integrals are rational;
no numerical quadrature is needed for these terms. The rho=0 constant case has
zero tail, including N=0.

For the medium term in the first variation, use

    B_N(f) = (1/c^2) sum_{k=0}^N (k+1) integral_I f(u) q(u)^k du,
    | integral_I f(u)/v(u)^2 du - B_N(f) |
        <= ell M_f rho^(N+1) [(N+2)-(N+1)rho]
                    / [c^2(1-rho)^2],

where f is a rational polynomial and |f|<=M_f is certified on I. The bound is
the absolute series tail sum_{k=N+1}^infinity (k+1)rho^k multiplied by
ell M_f/c^2. It remains valid for signed f; use polynomial bounds rather than
assuming its sign. The relevant numerator f=grad(v).d(u) has degree at most
three, with d(u) affine. Individual endpoint-gradient components use the same
formula with f=(1-u)v_axis or u v_axis.

Reuse the reviewed [rational square-root enclosure](../../../diagnostics/first_arrival_1d_precise_turn_reference.py)
for L and its reciprocal. Verify the squared lower/upper bounds exactly, then
propagate intervals through multiplication, division and addition. Any dyadic
rounding of accumulated bounds must be outward. Sum full-path bounds, and
also accumulate a paired action difference in which identical untouched edges
cancel exactly before interval operations. The difference includes changed
edges joining selected and unselected nodes as well as new face edges.

Subdividing a parameter interval or increasing N can reduce the explicit tail.
Declare finite term/subdivision budgets and report the resulting bounds. An
interval containing zero leaves an action sign unresolved. Exhausting the
budget is not a sign decision. Future precision choices are integration
budgets, not ray-stopping or scientific-accuracy thresholds.

## First variation and a bounded tangent witness

Let d_a,d_b be endpoint directions in km per dimensionless perturbation h,
d(u)=(1-u)d_a+u d_b, and delta_e=d_b-d_a. On ordinary edge pieces,

    D T_edge[d] = (e.delta_e)/L integral 1/v du
                 - L integral grad(v)_incident.d(u)/v^2 du.

Use the actual incident cell on each open interval. Terms from moving internal
cuts cancel because reciprocal velocity is continuous. The formula includes
length, tangential-medium and normal-medium contributions; it is not an
endpoint-momentum substitution. Fixed source and receiver directions are zero.

For a positive-length x=0 face edge, define the normal slowness slopes
g_minus=-v_x_minus/v^2 and g_plus=-v_x_plus/v^2. With

    Q(u) = (1-u)d_a,x + u d_b,x,
    m(u) = (g_plus+g_minus)/2,
    w(u) = (g_plus-g_minus)/2,

the normal contribution is

    integral L [m(u) Q(u) + w(u)|Q(u)|] du.

For a specified rational direction, split exactly at an interior root of the
affine Q as well as all grid cuts. Q identically zero needs no side choice.
The inverse-square polynomial bounds then enclose each signed piece. The
smooth length and tangential terms still belong to the full variation.

A convex supporting construction requires w>=0 over each whole face-patch
interval. The positive denominator reduces this check to the polynomial sign
of v_x_minus-v_x_plus. Exact quadratic extrema or certified Bernstein bounds
can establish it; node samples cannot. Under that condition the normal support
is the coupled endpoint moment set

    { integral L w(u) lambda(u) (1-u,u) du : |lambda(u)|<=1 },

plus the fixed m term. Shared-node contributions must be assembled together.
The [constant-jump moment proof](../interface_moment_set/proof.md) does not give
this variable-weight set by substituting endpoint samples. Independent boxes
for the two endpoint moments are invalid. If the jump reverses sign, do not
use a convexified zero support as a directional-minimum claim. Simultaneously
aligned second faces need an explicit separate treatment, not an inferred
single-face certificate.

The first implementation stops short of a support optimization. Assemble the
enclosed smooth/tangent components with every adjacent edge included. At knots
incident on an aligned face, a tangent direction has zero normal component;
therefore its first variation is independent of the normal support choice.
One coordinate direction, selected from a sign-resolved tangent component and
checked against the physical box, suffices for a descent witness. Keep the
endpoints fixed and check the available positive step from exact box/edge
geometry, without taking that step. Evaluate its full D T interval explicitly:
only an upper endpoint strictly below zero establishes directional descent for
the new polygon. If no such witness is resolved, report that limitation. This
does not establish all-direction stationarity, a local minimum, an endpoint or
model derivative, global first arrival, or a cause of the original failure.

## Minimal invented controls before any native calculation

| Control | Required distinction |
| --- | --- |
| Constant velocity, rational and irrational lengths | Exact constant integral, rho=0 tail, squared sqrt bounds, full geometric first variation, fixed endpoints and reversed-edge consistency. |
| Positive reciprocal-affine segment | Compare with the independently bounded logarithmic primitive, both slope signs and signed derivative numerators; verify N=0 and a later finite sum against its explicit tail. |
| Genuine trilinear cell and crossing edge | Use v=(2+x)(3+y)(4+z) on the unit cell and its diagonal. The cubic reciprocal has the independent decomposition 1/[2(u+2)]-1/(u+3)+1/[2(u+4)], giving a bounded-log action oracle. Also check exact rational cuts, a nextafter-near-plane binary64 endpoint and a tangent-plane case, common face values, and split/unsplit additivity where the same polynomial applies. |
| Fast and slow invented ridge | Recover the existing analytic one-sided variations and coupled false-box example. Convex support applies only to the fast ridge; slow-face Clarke zero is not a nonnegative-directional-variation result. |
| Variable face and full tangent assembly | Use varying quadratic face velocity/slopes, one prescribed Q sign change, and a nonzero adjacent-edge tangent term. Verify polynomial jump signs over the full interval and a feasible sign-resolved tangent witness. Preserve the independent-box counterexample. |
| Failure and cancellation cases | Reject zero-length/out-of-box/nonpositive inputs; cancel identical edges exactly; retain an action interval containing zero and an exhausted high-rho budget as unresolved. A change below binary64 total-action resolution must not be inferred from rounded totals. |

High-precision numerical comparisons may supplement these controls but are
not interval proofs. Reuse the existing exact rational interval operations,
square-root checks and unchanged-edge cancellation. The existing
[general directional quadrature](../../../diagnostics/interface_directional.hpp)
may later serve as a numerical crosscheck; it has no integral-error certificate.
The x-only native support script supplies reusable arithmetic and provenance
patterns, not a general trilinear primitive. The first future source and its
invented results require review before the proposed native action calculation.

`input_pins.json` records the reviewed sources and evidence consulted for this
design. It records hashes only; it does not imply that new numerical source or
native outputs have been prepared or executed.
