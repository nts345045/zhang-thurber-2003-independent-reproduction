# First variation at an internal velocity ridge

This is an invented, fixed-path diagnostic. It evaluates no ray trace, field,
optimization, source relocation or inverse problem. The copied D kernel is
unchanged. Coordinates are in km, velocity in km/s, action in s and endpoint
partials in s/km. Fixed endpoints lie inside the box; all retained edges have
positive length. A point on the interface is specified exactly by the invented
geometry, not moved there using a distance tolerance.

## Two exact one-midpoint controls

Take the grid x = {-1,0,1}, y = z = {-1,1}; velocities are constant in y and z.
Fix endpoints a=(0,-h,0), b=(0,h,0), h=1/2. Move only the middle vertex
p=(x,0,0). Let u=|x| and L=sqrt(h²+u²).

For the fast ridge v(x)=6-|x|, direct integration of reciprocal velocity on the
two straight edges gives

    T_fast(x) = 2 L log(6/(6-u))/u,   T_fast(0)=2h/6.
    T_fast(x) = 2h/6 + (h/36)|x| + O(x²).

Every connecting curve has length at least 2h and speed at most 6. Thus the
straight face path achieves the global lower bound 2h/6 = 1/6 s. Nevertheless,
the right and left ordinary midpoint-gradient limits are +h/36 and -h/36.
The exact directional derivative is (h/36)|d_x|. At h=1/2, the nonzero
right-cell partial is 1/72 s/km. Tangential first variations vanish for this
straight polygon. Tangential displacement can still contribute at second order.
There is no ordinary differentiable gradient at the face. This example proves
that a nonzero selected branch gradient can coexist with a true minimum; it
does not prove that every ridge minimum has nonzero limiting gradients.

For the slow face v(x)=5+|x|,

    T_slow(x) = 2 L log((5+u)/5)/u,   T_slow(0)=2h/5.
    T_slow(x) = 2h/5 - (h/25)|x| + O(x²).

Both normal directions decrease action to first order. The convex hull of
ordinary gradient limits is [-h/25,h/25] and contains zero. A minimum-norm
convexified-gradient test therefore cannot by itself certify local minimality
or nonnegative actual directional derivatives. This negative control must
remain nonstationary in the all-direction sense.

The C++ observation uses `path_eval` for x=0 and x=±2^-8, ±2^-16, ±2^-24 in
both models, plus one face `segment` evaluation per model. `Grid::sample` uses
`upper_bound`, so the exactly aligned face receives its right-cell partial.
Fourteen path evaluations and two direct segment evaluations are planned.
Decimal 80/100-digit closed-form action and derivative comparisons are
numerical consistency checks; their agreement is not an interval proof.
The 5e-14 s / 5e-12 s/km comparison bounds apply only to these invented
quadrature checks and do not define a scientific stationarity threshold.

## Correlated endpoint normal directions

For a face-contained edge parameterized by u in [0,1], its normal displacement
under endpoint directions (a,b) is q(u)=(1-u)a+ub. For constant symmetric
normal slopes the nonlinear part of its first variation is c I(a,b), c>=0,
where

    I(a,b) = integral_0^1 |(1-u)a+ub| du
           = (|a|+|b|)/2                         if ab>=0,
           = (a²+b²)/(2(|a|+|b|))               if ab<0.

The script checks this against independent exact rational integration split
at the zero of q. With the declared smooth linear term

    F(a,b) = -(3c/8)a + (3c/8)b + c I(a,b),   c=1,

all four signed coordinate probes are at least c/8, while F(1,-1)=-c/4.
This is an abstract segment directional component plus a specified smooth
term, not a constructed physical whole ray. Its canceling target (3/8,-3/8)
lies in the independent marginal box [-1/2,1/2]² but outside the correlated
moment set. The endpoint supports cannot be selected independently.

The already reviewed constant-jump proof describes moments A,B of a selector
0<=lambda<=c: (A+B)²<=2cA and (A+B)²<=2cB, including c=0 separately.
For the symmetric slopes, use lambda=(s+1)/2 to map s in [-1,1] to that set.
Here the false-box target maps to (A,B)=(7/16,1/16), which violates the second
inequality. See the frozen copies of
[the prior proof](inputs/moment_set_proof.md),
[its 156-control summary](inputs/moment_set_summary.json), and
[its independent review](inputs/moment_set_review.json).
Those earlier controls are not rerun by this package.

## Extension to a continuous trilinear face

For a positive-length edge lying in one internal face, let s=1/v and let
s_minus,n(u), s_plus,n(u) be the two normal slowness slopes. Tangential slopes
agree by continuity. Ordinary transverse crossings can be split and their
moving-cut first-order terms cancel because s is continuous; positive-length
face containment is a different case. The existing intersection splitting
alone does not choose its direction-dependent normal derivative.

Keeping the complete smooth length and tangential contributions in b·d, the
normal contribution is exactly

    integral L [s_plus,n(u) max(q(u),0) + s_minus,n(u) min(q(u),0)] du.

If s_plus,n>=s_minus,n pointwise, write m=(s_plus,n+s_minus,n)/2 and
w=(s_plus,n-s_minus,n)/2>=0. Include the m q integral in b·d. The remaining
term is integral L w(u)|q(u)| du. Its support set consists of the correlated
moments

    K_edge = { integral L w(u) lambda(u) (1-u,u) du : |lambda(u)|<=1 }.

Assemble these edge contributions at their shared vertices, retaining fixed
endpoint conditions. Then the first-variation functional is the support
function of b plus the assembled moment sets. Zero membership is equivalent
to nonnegative first variation in every free direction for this convex-jump
case; it is only a first-order statement. With a physical box boundary, add
the ordinary outward normal cone. A feasible supporting vector gives a
sufficient residual bound but an independent endpoint box is only an outer
set and can create a false zero. A reversed jump is excluded: convexifying it
can hide descent, as the slow-face control shows.

For general trilinear data, v restricted to the face edge is quadratic in u,
and each one-sided normal velocity slope is also quadratic. The corresponding
slowness slopes are rational functions with positive v² denominator. This
requires justified integral bounds for a continuous certificate; finite
quadrature or finite nearby-gradient sampling alone is not such a certificate.
Edges contained in multiple faces, zero-length edges, topology changes and
native path classification are outside this first component calculation.

The distinction between Clarke stationarity and ordinary directional
stationarity at nonregular points is discussed by
[Burke, Lewis and Overton (2005)](https://cims.nyu.edu/~overton/papers/pdffiles/gradsamp.pdf).
[Lewis and Overton (2013)](https://people.orie.cornell.edu/aslewis/publications/13-nonsmooth.pdf)
study nonsmooth quasi-Newton behavior; that work does not justify applying a
single smooth-gradient stopping test at this kink or certify the current ray
solver. Only these written mathematical sources were consulted, not their code.

## Planned execution and limits

After independent source/preparation review, execute from the integration root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/internal_ridge_stationarity_controls_001/run.py
```

The runner requires `prelaunch_review.json` to bind the frozen preparation,
checks compiler/runtime/source pins before and after, and uses the reviewed
process-group cleanup. Outputs stay in fresh `build/`, `logs/` and `results/`
subdirectories of this package. No native data or flags are imported or changed.
The general trilinear formula above is a derivation; no native stationarity,
minimum, first-arrival, endpoint-envelope derivative or remedy is asserted.
