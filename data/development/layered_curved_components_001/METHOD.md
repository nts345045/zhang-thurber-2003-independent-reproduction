# Isolated continuous layered-ray components

This development source does not replace the maintained forward solver. It
keeps a continuous curve separate from display samples and from polygon
stationarity. Numerical results and execution receipts, when available, are
separate artifacts.

`layered_curved_ray.hpp` supplies a small meridional curve representation and
integrates action and every trilinear nodal kernel. The branch enumerator is a
separate source. A branch's supplied completeness and derivative-availability
strings are copied into the result; the integration kernel does not establish
them or set production convergence/first-arrival flags.

For horizontal unit azimuth `e`, a meridional point `(r,z)` embeds as
`(origin_x + e_x*r, origin_y + e_y*r, z)`. A positive-gradient affine arc has
tangent `(sin(theta), cos(theta))`, curvature `kappa = p*g`, and arc measure
`ds = dtheta/kappa`. The start-anchored implementation evaluates a partial sweep
`delta` using

```
dr = 2 sin(delta/2) sin(theta0 + delta/2) / kappa
dz = 2 sin(delta/2) cos(theta0 + delta/2) / kappa.
```

`arc_increment` retains the sweep independently so a small angle does not vanish
when added to a much larger starting angle. `arc` is a convenience factory for
already resolved endpoint angles. Split an arc at its depth turn, `pi/2`.
Straight pieces cover homogeneous oblique legs, vertical legs, and guides.
Zero-length pieces are omitted by the branch constructor. Pieces join exactly
at their stored meridional coordinates. Endpoint closure against the requested
receiver is a separate branch diagnostic; neither the kernel nor the display
sampler overwrites the integration curve to repair it.

The grid is eligible only when every binary64 nodal velocity is positive and
exactly equal across x and y at each depth. All three grid axes remain in the
model parameterization. The action and kernels are

```
T        = integral ds / v
dv[j]    = -integral N_j ds / v^2
length[j]= integral N_j ds.
```

The full eight trilinear basis weights are used at every sample. Velocity is
computed from the two depth values, which is algebraically identical under the
checked exact lateral equality and preserves that equality in working
arithmetic. The model columns remain independent nodal velocity partials,
including lateral perturbations about this layered base. The existing
log-slowness columns would be `-v[j]*dv[j]`; the separate `length` kernel is
needed by the existing DD path-length mask. Layer-coherent finite differences
alone would not validate these nodal columns.

Each monotone piece is partitioned at every crossed x, y, and z grid face.
Root locations use bounded long-double bisection; an unresolved root or a
partition without representable interior nodes fails explicitly. Exact ties
are deduplicated. The maximum coordinate residual at returned face parameters
is reported. Samples select their actual cells and retain all basis weights.
No coordinate, angle, velocity, or basis weight is clamped. Endpoints and
samples outside the physical box fail, including any unresolved finite-bottom
roundoff. Thus a branch constructor must retain and resolve such failures
rather than silently move its guide.

The 16-point Gauss-Legendre result is returned; a separate 8-point result on the
same partition supplies action and maximum per-node discrepancies. All curve,
root, basis, accumulation, and transcendental arithmetic uses `long double`.
These discrepancies are numerical diagnostics, not outward error bounds or a
universal accuracy certificate. `samples` counts both rules, 24 per subpiece;
`face_crossings` counts individual crossed axis/plane pairs before tie
deduplication. `arclength` is the sum of the declared piece arc measures. The
azimuth must have unit norm within eight working-arithmetic epsilons.

`display_samples` returns a polyline for inspection only. Its points never feed
the action or kernels. A polyline obtained from it generally has a different
action and endpoint partial. Likewise, unique source momentum alone does not
establish a unique nodal model derivative: tied guide allocations can share
time and endpoint momentum while having different nodal kernels.

The frozen Python layered references remain separate reference evidence.
Comparing an adapter with code that it directly calls would not constitute
independent validation. Invented controls here use independent polynomial and
trigonometric nodal moments and a separately implemented affine branch formula.
Any later heterogeneous model update must use a separately validated generic
3D route; this exact-layered specialization does not relax its gates.
