# Local quadrature coordinates on unchanged stored partitions

This is an isolated **source-only numerical-method draft**. No compilation,
control, native observer, root location or integration has been run. The
original three selected-curve sources are preserved in `original/`; that
kernel is the reviewed failure-context variant `5e36db84…`. Frozen/public
packages and production sources are unchanged.

## Exact identities

Let a curve piece have parameter `t ∈ [0,1]`, constant parameter speed `L`,
and an existing positive partition `[a,b]`. Write `w=b−a` and

`t = a + w q`,  `1−t = (1−b) + w(1−q)`,  `0<q<1`.

These equations define the change of variable, not a requirement to store a
global floating `t`. The measure is `ds = L w dq`. For an original Gauss node
`x_j`, sign `s=±1` and weight `W_j` on `[-1,1]`, use
`q=(1+s x_j)/2` and sample measure `L (w/2) W_j`. The patch retains the
existing arithmetic expression `length*half*weights[j]`, with
`half=(b−a)/2`; the Gauss tables, rule order and accumulator order are unchanged.

For a straight piece `P(t)=P0+(P1−P0)t`, the backward identity is
`P(t)=P1−(P1−P0)d`, where `d=1−t`. This includes vertical and guide pieces.
Here `L=|P1−P0|`.

For a circular meridional piece, let `S>0` be its sweep, `κ>0` its curvature,
`θ0` its starting angle, and `θe=θ0+S`. Its parameter speed is `L=S/κ`.
With `δ=S t`, the forward increment is

`P(t)=P0 + [2 sin(δ/2)/κ] (sin(θ0+δ/2), cos(θ0+δ/2))`.

With `ε=S(1−t)`, the exact backward identity is

`P(t)=Pe − [2 sin(ε/2)/κ] (sin(θe−ε/2), cos(θe−ε/2))`.

The backward identity assumes **the mathematical endpoint of the same
start-defined circle**. It follows by integrating the tangent
`(sin θ, cos θ)/κ` from `θe−ε` to `θe`. It is not an independent circular
arc chosen to fit two rounded endpoint coordinates.

## Working arithmetic and anchor choice

The sample anchor is whichever piece endpoint is nearer the partition's
midpoint, tested as `a <= 1−b`; ties use the forward expression. This is a
numerical conditioning rule, not a physical constraint. Forward distance is
`a+(b−a)*q`; backward distance is `(1−b)+(b−a)*(1−q)`. Thus a tiny terminal
partition is sampled through a small backward increment, without adding its
Gauss displacement to a global parameter near 1.

`PieceSampler` recomputes the endpoint with the unchanged `Piece::at(1)` and
the end angle with `theta0+sweep`. For arcs it never reads the public,
otherwise unchecked `r1`, `z1` or `theta1` fields. Line endpoints retain their
existing validated definition. The original `Piece::at`, `Curve::at`, curve
constructor and all face-root computations remain unchanged.

The computed anchor, end angle, trigonometry and subtraction are rounded.
Backward and forward evaluations are therefore **not bitwise equivalent** and
do not define identical exact working curves. The returned result records two
finite observations, maximized over pieces: backward-at-start displacement
from the defining start, and the forward/backward midpoint discrepancy. These
are measured consistency residuals, not upper error bounds. They do not prove
agreement at every grid crossing. The old root finder still partitions its
original working curve; the new sample formulation requires the controls and
native assessment below. In particular, a tiny sliver's depth placement can
be sensitive to the anchor's rounding error.

Cartesian embedding and point-based cell selection are unchanged. Every
trilinear nodal basis contribution remains: action `ds/v`, velocity kernel
`−N_j ds/v²`, and path-basis length `N_j ds`. No sample is projected, snapped,
clamped or assigned to a presumed cell. Samples may coincide in working
coordinates or round to a face, but their positive quadrature measures are
retained and the actual point must pass all original box/basis/speed guards.

## Guard changes and retained failures

A positive real interval does not require a representable global floating
midpoint or interior global Gauss parameter. Those two guards are replaced
by finite `0≤a<b≤1`, positive finite stored width/half-width, strict local
`0<q<1`, and positive finite sample measure. An unrepresentable half-width or
measure remains a failure; no interval is silently dropped or merged. The
sample's endpoint-relative distance must remain finite in `[0,1]`. Its
coordinates may round even though the mathematical local point is interior.

All root bracketing/bisection/adjacency, strict interior crossing-parameter,
physical-box, velocity, basis, model-eligibility and final finite-result
guards remain. A face root that cannot be stored is still rejected. The
failure-context message now reports local `q` and `ds` instead of a global
`t`; completed-sample/subpiece counters retain their original meaning. Neither
branch completeness nor derivative eligibility is promoted.

## Bounded validation plan — not executed

1. After source review, compile and run the existing affine control program
   once and the existing full-nodal control program once against this kernel.
   Their sources, fixtures, **58 + 24 assertions and tolerances remain
   unchanged**. This reuses homogeneous/affine travel-time and momentum
   checks, independent full-nodal polynomial/trigonometric antiderivatives,
   reversal, display independence, ineligible-model rejection and branch
   metadata checks. New result fields do not replace those assertions.
2. Add only `check_tiny_partition.cpp`: constant `v=4`, fixed `x=y=1/4` in
   `[0,1]²`, depth nodes `[-1,0,1]`, and a vertical line from `z=1` to
   `z=−δ`, `δ=2^-63`. The exact total length-kernel mass on the lower z=−1
   plane is `∫[-δ,0](−z)dz = δ²/2 = 2^-127`, summing its four lateral
   nodes. Exact action is `(1+δ)/4`. Require positive lower-plane mass,
   relative error at most `512*epsilon(Real)` for that tiny mass and action,
   and two subpieces/48 samples/one face crossing. These are four assertions
   in one integration, with finite floating regression allowances rather
   than error certificates. A zeroed tiny contribution fails the mass test;
   an unrelated absolute tolerance would not establish retention. This
   antiderivative is independent of the local-q implementation. Quantization
   of individual point/basis values remains possible and is not waived.
3. Only after those outcomes are reviewed, use exactly the two original
   LOM24104/LON8670 numeric/spec inputs and complete native/reference sidecars.
   Compile the isolated observer once and invoke it once per case in a fresh
   output location. Preserve any failure without retry or method changes.
   This plan is not execution authorization.
4. Compare all inherited input, model, construction, curve/join and identity
   fields against the closed diagnostic outputs. Observe both new anchor
   consistency residuals, face residuals, full sample/subpiece counts, all
   nodal lengths/kernels, their existing scaling/sum identities, and 8/16-rule
   differences. A completed rule inventory must have 24 samples per stored
   subpiece; no old tiny partition may be omitted.
5. If native integrals complete, compare action to the **existing** selected
   reference intervals (`reference_record.time_s` for LOM and the saved LON
   selected candidate). No new reference calculation is needed. This
   discrepancy includes curve construction and working arithmetic, not just
   quadrature. No independent native all-node kernel oracle exists here;
   scaling identities and invented nodal controls cannot supply that claim.
   Preserve failed, unresolved or inaccurate outcomes. No optimizer,
   inversion, production adoption, first-arrival or optimized-source
   derivative acceptance follows solely from successful execution.
