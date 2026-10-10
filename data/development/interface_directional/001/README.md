# Directional stationarity of an interface-aligned polygon

The saved Loma row-5 guide path has a large gradient under the solver's selected
incident-cell convention, but only a small remaining descent within the guide
plane. This diagnostic separates those two effects without changing the path,
optimizer, stopping flags, or model. The original path accepted zero updates
and has `converged=0`; those values remain attached to every native result.

The calculation uses the continuous, piecewise-trilinear velocity model and
its Fermat action. For a straight segment with endpoints `a,b`, write
`p(u)=(1-u)a+ub`, length `L=|b-a|`, and endpoint displacement field
`q(u)=(1-u)d_a+u d_b`. For positive segment length, its right directional
variation is

```
D+T[d] = integral_0^1 [s(p) (b-a).(d_b-d_a)/L + L D+s(p;q)] du,
```

where `s=1/v` is slowness. On an internal face `x=x0`, continuity of the
interpolated velocity gives

```
D+s(p;q) = grad(s)_minus.q
           + (partial_x s_plus - partial_x s_minus) max(q_x,0).
```

The incident side therefore depends on the interpolated motion along the
whole segment. When adjacent knots move toward opposite sides, integration
must split where `q_x(u)=0`. Independent choices at the two knots would miss
this coupling. At an intersection of grid planes the first-order normal
contributions add; mixed terms enter at higher order. For segments crossing a
face transversely, the terms from the moving integration boundary cancel
because slowness is continuous.

`interface_directional.hpp` evaluates this variation with eight-point Gauss
integration on every cell and direction-sign interval. A four-subdivision
control changes the native variation by at most 3.56e-20 s/km. Exact equality
identifies aligned faces; no snapping or smoothing is used. Zero-length
segments are rejected because their length has a different directional
variation. Directions at outer boundaries must point into the model or along
its boundary. The private helper is called only with positive subdivision
counts 1 and 4 in this experiment.

Four invented controls constrain interpretation. A straight path in a
homogeneous model has zero first variation and attains the length lower bound.
A straight path along the edge of a fast plateau, `v=6-2 max(x,0)`, is also a
global minimum: speed is at most 6 km/s everywhere and every connecting path
has length at least the endpoint distance. Its chosen ordinary gradient is
nonzero, although all feasible first variations are nonnegative by the
formula. In the reversed cusp `v=6+2|x|`, both signed normal translations have
negative variations. Thus averaging incident gradients to zero would not
establish a minimum. A bent homogeneous path supplies a smooth descent
control. The computed variations agree with the closed forms for all 24
invented probe results to within the declared 2e-14 s/km component tolerance.

The native test retains the 2,705-node polygon from
`loma_geometry_preflight/reference_seeds_001`, case `row5_h0.03125`, stage
`retained_seed_optimized`. Its event is NC/20091683, preferred origin
NC/2660124, and receiver is `NC.BSL..EHZ`
(`FDSN:NC_BSL__E_H_Z`, epoch 1989-08-25T19:45:00 through
1990-09-10T19:20:00). Complete resource IDs and epoch strings accompany every
native direction, finite probe and reviewed classification. The geometry is
catalog-derived synthetic geometry, not an observed travel time.

The chosen ordinary gradient norm is 0.0751123 s/km. Its dot product with the
normalized negative-gradient vector is -0.0751123 s/km, whereas the correct
right variation is approximately -8.00e-10 s/km. The discrepancy follows from
using the positive-side derivative when the guide moves into the constant
velocity side. Opposite adjacent guide-normal motions give another direct
coupling control: their ordinary gradient dot product is near zero, but their
right variation is positive, 9.20302e-4 s/km.

Two different feasible directions establish a small remaining polygon
descent. Both leave the guide-normal components zero for this probe; this is
a choice of test direction, not an imposed restriction on admissible rays.
The second direction applies the existing weighted path-Laplacian inverse to
that subspace. Each full free-knot direction has unit Euclidean norm.

| Probe | Right variation (s/km) | Step (km) | Independently evaluated action change (s) |
| --- | ---: | ---: | ---: |
| In-plane negative gradient | -6.825839466e-6 | 1e-6 | -4.531734165e-12 |
| In-plane metric direction | -2.746098017e-7 | 1e-3 | -2.027866054e-10 |

The action changes integrate each segment of the displaced polygon exactly
for the x-only piecewise-linear velocity profile, using independent Python
Decimal arithmetic at 80 and 100 digits. The two precisions agree within
1.0e-76 s. The displacement first uses binary64 coordinates, matching the
saved C++ experiment; increasing precision changes only action evaluation.
The unchanged production quadrature also decreases at these two steps.
This is strong numerical evidence for residual descent in the retained
polygon, although the magnitude is much smaller than the discrepancy between
its chosen ordinary gradient and its true directional variation. It does not
justify relabeling the saved convergence flag.

Read `review/summary.json` for the final classification. It explicitly
supersedes the raw arithmetic booleans in `summary.json`: the negative chosen
gradient and negative guide translation give raw action changes around
1e-17 to 1e-18 s and are **inconclusive**, not independent descent evidence.
Those raw numbers remain unchanged. The two substantive tangent directions
were the only native directions replayed with Decimal arithmetic.

Seven component and identity checks pass. These finite probes do not certify
all-direction nonsmooth stationarity, global first arrival, or the source and
model derivatives of an optimized ray. The calculation identifies a needed
coupled directional treatment of aligned segments and a measurable residual
polygon error. It supplies no new production optimizer, stopping tolerance,
forward-acceptance rule, or simulation observation.

`summary.json` pins the frozen C++ sources, exact saved inputs, commands,
compiler log, binary and output tables. `review/summary.json` pins the review
source and all reviewed tables. Reproduce with a fresh variant:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_interface_directional.py --variant repeat
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_interface_directional.py --input data/development/interface_directional/repeat
```
