# Two reference-selected curved-ray diagnostics

Prepared source only. No input generation, compilation or native curve
evaluation has been performed by this source package. It implements the
two-case plan in ../layered_reference_selected_curve_plan_001.md; the
completed invented component is separately retained in
../../data/development/layered_curved_components_001.

The fixed roster is the original LOM24104 bottom guide and LON8670 turn.
prepare.py consumes the reviewed original numeric files and full native
identity sidecars, the closed three-depth LOM reference record 0, and the
closed LON certificate for pair 8670. It checks complete case/row/model and
reference source/closure joins, retains exact rational phase-speed and turn
records plus enclosures, and prepares only two specs and their sidecars.
The original polygons supply their fixed endpoints; no polygon knot is used
to approximate a continuous leg.

Each whitespace spec has exactly eight tokens:

    reference_selected_curve_v1 CASE_ID BRANCH U_RATIONAL TURN_RATIONAL GUIDE_RATIONAL not_assessed_by_this_component selected_curve_only

Rational tokens preserve numerator and denominator. C++ converts those two
integers with strtold and then divides in long double; this is a declared
working conversion, not a correctly rounded rational conversion. For the
bottom guide, its exact supplied rational is the midpoint of the retained
reference guide-length interval. No phase parameter or guide length is fitted
to force endpoint closure.

reference_selected_curve.hpp constructs the selected positive-gradient
affine arcs and constant-layer lines. Increasing-depth sweep uses

    q(v) = sqrt((u-v)*(u+v))
    delta = atan2(u*u*(vb-va)*(vb+va)/(vb*qa+va*qb), va*vb+qa*qb), va<vb.

The shallower-going leg uses the same positive sweep, with its higher starting
speed as vb and starting angle atan2(vb,-qb). At a supplied turn q=0 is an
explicit endpoint condition; the separately computed profile velocity at the
supplied turn is reported. A constant layer with q=0 and nonzero depth change
is rejected. This fixed roster has nonzero horizontal range and finite
positive phase speed; it does not add a general vertical-branch dispatcher.

Every new piece begins at the exact stored end of its predecessor. The
intended interface depth and actual stored join, tangent jump and receiver
closure are separate saved diagnostics. These working curves may differ
slightly from the mathematical selected branch through arithmetic rounding.
No grid coordinate, endpoint, guide or speed is clamped or snapped. In
particular, the existing strict arc-turn guard can reject an unresolved
working angular representation. That is a recorded construction failure,
not an invitation to change the frozen kernel.

observe_reference_curve.cpp takes ORIGINAL_INPUT CURVE_SPEC ABSENT_OUTPUT_JSON.
It requires all three identity sidecars before evaluation, reads only the
original endpoints/model and supplied spec, and emits full pieces, joins,
model values and result vectors as lossless hexadecimal working scalars.
The original exact rational tokens are included verbatim. The wrapper-side
preparation binds complete sidecar contents; the C++ observer checks their
presence rather than implementing another JSON metadata reader.

## Finite scope

Future execution, only after concrete review, consists of one ordinary C++17
compile and exactly two observer invocations. Each observer attempts at most
one unchanged lcr::integrate call, followed by at most one display call at
1 km spacing. Construction failure makes zero integration calls. Integration
failure retains the constructed curve; display failure retains the completed
integrals. Errors and partial construction are saved with nonzero exit.
There is no automatic retry.

The intended geometry has six LOM pieces and five LON pieces. On each 8x6x6
grid a monotone piece can encounter at most 14 internal coordinate planes:
at most 90 and 75 subpieces, or 2,160 and 1,800 total 8/16-rule samples,
respectively. These are conservative bounds, not reported completed counts.
Actual counts are saved by the unchanged kernel. No reference enumeration,
optimization, mesh solve, finite-difference probe or numerical reference
recalculation is included.

Action/reference differences can subsequently be computed from saved output
and the supplied reference records; their different interval/rounded-value
types must remain explicit. The nodal vectors have no new independent native
oracle. Basis-sum and velocity-homogeneity residuals and 8/16 discrepancies
are working diagnostics. Supplied reference branch evidence does not become
branch completeness established by this C++ component. It emits neither
production convergence flags nor a polygon stationarity residual.
