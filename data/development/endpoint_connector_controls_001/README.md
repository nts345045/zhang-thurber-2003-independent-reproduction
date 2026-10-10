# Constrained endpoint connector: invented controls

The 33 invented cases pass 304 checks. This tests a changed local action in an
affine or homogeneous medium; no native ray, global polygon optimization,
production function, stopping flag or inversion was used. The earlier endpoint
mesh failures remain unchanged, and the native experiment remains held.

The connector supplies travel time, a stable increment relative to horizontal
bottom travel, and both endpoint derivatives. Exact rational comparisons of
the binary64 input coordinates distinguish a positive guide, its zero-length
limit, and an admissible interior arc. Stable series and rationalized differences
avoid subtracting nearly equal action totals or contact distances.

The independent 80-digit calculation uses Snell distances, logarithmic leg
integrals and endpoint momenta. Across the fixtures, the largest action error
is 2.323e−16 seconds and the largest endpoint-component error is 2.884e−17
s/km. Separate high-precision finite differences of that continuous action
check both endpoint vectors, with inward differences at the bottom. Their
1e−32 km increments are Decimal perturbations; they are **not** representable
binary64 perturbations or a finite-difference test of production ray output.
Small action increments are assessed separately from rounded full times.

Moving the first knot among 1/4, 1/8 and 1/16 km along the bottom preserves the
connector-plus-horizontal-remainder value and source vector. The old straight
action instead retains normal partials −0.00347222, −0.00173611 and −0.000868056
s/km. Independent inward differences of that old action confirm those partials,
so substituting zero momentum into its derivative alone is inconsistent.

Both one-leg and two-leg transitions are checked immediately below, exactly
at, and immediately above critical distance using `nextafter`. A 0.001 km
connector loses its guide for a finite inward displacement; the interior arc
is retained. The homogeneous oblique source has normal derivative
+0.1178511302 s/km, and a positive-gradient guide-free oblique case has
+0.1066973999 s/km. Neither is zeroed. Gradients as small as 2^-40 s^-1 approach
the homogeneous action continuously within the stated checks.

Reproduce only in a fresh directory, from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python diagnostics/check_endpoint_connector.py \
  --output data/development/endpoint_connector_controls_FRESH
```

`summary.json` pins the four inputs and frozen source artifacts and preserves
every check and case. The component derivative allowance is 2e−13 s/km,
separate from the unchanged 3e−6 s/km scientific source limit. The Snell
calculation is high-precision arithmetic, not an outward interval proof. These
tests supply no full nodal-grid Jacobian, general trilinear-medium connector,
arbitrary-scale guarantee, or optimized whole-path envelope certificate.
The source/control review must precede any implementation decision.
