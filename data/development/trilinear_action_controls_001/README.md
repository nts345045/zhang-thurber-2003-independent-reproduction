# Rational trilinear action and directional controls

This package is prepared source only. No arithmetic control, native geometry,
ray trace, field construction, or optimizer has run. The proposed command below
must wait for the independent source and budget review. The earlier
[design](../cmj_face_action_design_001/README.md) and its
[root review](../cmj_face_action_design_001/root_review.json) define the scope.

The two new sources are
[trilinear_action_bounds.py](../../../diagnostics/trilinear_action_bounds.py)
and [check_trilinear_action_bounds.py](../../../diagnostics/check_trilinear_action_bounds.py).
Their exact copies and the two reused arithmetic dependencies are under
`source/diagnostics`. `prepared.json` binds those files, this document, and the
reviewed design. It records preparation, not a passed control result.

## Numerical target and bounds

The target is the continuous trilinear interpolant of strictly positive nodal
velocities on a finite Cartesian box. Coordinates and velocity values supplied
as finite binary64 numbers become their exact rational values. Rational inputs
remain exact. Lengths are in km, velocities in km/s, action in seconds, and
coordinate partials in s/km. Directions have units km per dimensionless
perturbation parameter, so the directional derivative is in seconds.

Each positive-length edge is partitioned at exact rational grid intersections.
No small cut is dropped. On each closed cell piece, the velocity is a polynomial
of degree at most three. Positive vertex bounds and exact Bernstein bounds give
`0 < lo <= v <= hi`. With `c=(lo+hi)/2`, `q=(c-v)/c`, and
`rho=(hi-lo)/(hi+lo)`, the finite polynomial sums for `1/v` and `f/v^2` have the
explicit tails in the design. Numerators may have either sign. The reused
square-root enclosure is checked by exact squared inequalities. The reused
interval operations round outward only after exact piece calculations.

The proposed fixed settings are degree 32, four equal subdivisions per exact
cell/sign interval, and 128-bit outward bounds. Oracle lengths use 192 bits;
the reused logarithm uses its existing 160-bit absolute tail. Degree zero and
one subdivision are deliberate controls for wide, unresolved bounds. These
are finite integration budgets, not physical tolerances. There is no adaptive
budget escalation. Identical edges cancel exactly in a paired action
difference, before interval subtraction; an interval containing zero leaves
its sign unresolved.

The full first variation includes length and medium terms. On an exactly
aligned internal face, it uses the incident side selected by the sign of the
affine interpolated normal direction, split at its exact zero. Tangential
components include both adjacent edges. A jump sign is checked over the whole
quadratic face-patch polynomial, including any interior extremum. This check
does not solve the coupled support problem or replace it with independent
endpoint intervals. Action remains defined on edges aligned with two faces,
but their directional and tangent-component evaluations are explicitly
unsupported in this implementation.

The public edge-directional function rejects outward directions at the outer
box. Full-path directions also keep source and receiver fixed. The tangent
witness examines coordinate directions in deterministic node/axis order,
blocks every normal component incident on an aligned face edge, and checks
physical box feasibility and positive edge lengths. It reports descent only
if the explicitly evaluated full directional interval is strictly negative.
It reports a positive geometric step bound without taking a step. No resolved
witness does not establish stationarity. Tangent-component intervals at outer
boundaries are algebraic components; only feasible directions are eligible
for a witness.

## Six invented families

1. **Constant velocity:** rational and irrational lengths, zero series tail,
   signed inverse-square moments, reversed edges, and a full two-edge tangent
   witness with fixed endpoints.
2. **Reciprocal-affine velocity:** both slope signs, independent bounded-log
   action, inward endpoint derivatives, and degree-zero versus degree-32
   enclosures.
3. **Trilinear cell and exact cuts:** the cubic diagonal restriction of
   `v=(2+x)(3+y)(4+z)`, its partial-fraction action primitive, and the inward
   endpoint derivative `-sqrt(3)/60`. The same curve is checked across a grid
   plane and an inserted collinear knot. Adjacent binary64 numbers around a
   plane retain the exact cut at parameter `1/3`.
4. **Fast and slow ridges:** analytic normal variations for `6-|x|` and
   `5+|x|`, a sign-changing normal direction, and the previously reviewed
   coupled example whose coordinate probes miss a descending combination.
   The slow-face result cannot be promoted from a convexified zero support.
5. **Variable face:** complete adjacent-edge tangent terms, boundary
   feasibility, and a quadratic jump with positive endpoint values but minimum
   `-1/16` inside. An additional face has `v=(2-|x|)(3+y)(4+z)` and
   `Q(u)=1-2u`. Its action is
   `sqrt(2)/2 [log(4/3)-log(5/4)]`. Its normal variation is
   `sqrt(2)/4 [2F(1/2)-F(0)-F(1)]`, where
   `F(u)=7 log(u+3)-9 log(u+4)`. These independent primitives check both
   reciprocal and signed inverse-square integrals with variable coefficients.
6. **Failure and cancellation:** zero length, nonpositive/nonfinite values,
   out-of-box and outward directions, multiple aligned faces, deliberately
   unresolved high-contrast bounds, exact unchanged-edge cancellation, and
   a resolved action difference below binary64 total-action resolution.

All geometry in these controls is invented. No original CMJ coordinate,
candidate projection, convergence flag, source/model partial, or status is
loaded or changed. Any later witness would belong to its explicitly defined
new polygon. It could not relabel the original false CMJ flags or establish
all-direction stationarity, a local minimum, first arrival, or a cause of the
original stopping failure.

## Proposed execution after review

From the integration repository, use the maintained driver, which checks its
own source pin and imports the frozen arithmetic copies. It first requires
`prelaunch_review.json` with `status="passed"` and the exact
`prepared_sha256`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_trilinear_action_bounds.py \
  --output data/development/trilinear_action_controls_001
```

The driver makes no subprocess or solver call. It records `results.json`,
`checks.json`, and `summary.json` exclusively and refuses prior or partial
output. Any failure remains in the same package. The only current validation
is syntax parsing without importing or executing either new module. The
reused reference module imports NumPy and SciPy; its root solver and numerical
reference routines are not called. The arithmetic used here consists of exact
rational operations and the bounded logarithm/square-root helpers.
