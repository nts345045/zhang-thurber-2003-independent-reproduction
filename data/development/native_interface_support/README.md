# Continuous support bound for the retained native guide

The saved row-5 guide polygon retains a tangential descent direction after the normal cusp is treated with a valid continuous supporting slope. The calculation in `001` uses the existing 2705-node path, including 1874 exact segments on x=0. It does not optimize the path or change its original convergence flag of zero.

The identified geometry is event `quakeml:NC.anss.org/Event/NC/20091683`, origin `quakeml:NC.anss.org/Origin/NC/2660124`, and receiver `NC.BSL..EHZ` (`FDSN:NC_BSL__E_H_Z`), epoch `1989-08-25T19:45:00` through `1990-09-10T19:20:00`. Full native metadata is frozen in the input copy and retained in the summary; every output knot carries the event/origin and channel/epoch identifiers.

In the saved x-only model, the one-sided slowness derivatives at x=0 are exactly 0 and 1/18 s/km². Selecting the left slope, alpha=0, gives a feasible supporting vector G for arbitrary joint displacements of the existing movable knots. Reciprocal-affine segment primitives and rational interval arithmetic enclose this vector without path quadrature. The derivation and error bounds are in [proof.md](proof.md).

The computed norm bound is approximately B=6.825848321932667e-6 s/km, with an integration/arithmetic enclosure radius norm no greater than approximately 2.443130757215734e-37 s/km. Its precise meaning is

    F(d) >= G·d >= -B ||d||₂,

where F is the continuous first variation and d moves existing internal knots while fixing both endpoints. This equation expands the shorthand interpretation in the recorded summary: the lower bound is **minus B times the direction norm**, not the positive number B. A large upper bound alone does not establish nonstationarity.

The independently saved in-plane direction has a continuous first-variation interval strictly below zero, approximately -6.825839466036337e-6 s/km. Its normal displacement vanishes at every knot incident on the guide, so its interval dot product with G equals the actual directional derivative. This confirms the previously recorded tangent descent. The largest unaffected tangent component is bounded below by approximately 4.013439067298824e-6 s/km. The rational endpoints, rather than these rounded decimal displays, are authoritative.

All 23 controls passed: 12 logarithm/reciprocity checks, eight independent Decimal action/finite-difference checks, the actual face slopes, the exact guide inventory, and the negative continuous tangent slope. Additional preconditions require a positive x-only Cartesian model, finite-box inclusion, strictly interior movable knots, nonzero segment lengths, ordered native identities, fixed endpoint directions, and unchanged input hashes. The Decimal controls are consistency checks; exact rational remainder and square inequalities supply the inclusion bounds.

Reproduce from the integration repository root with a fresh output path:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
python3 diagnostics/check_native_interface_support.py \
  --output data/development/native_interface_support/reproduction
```

The recorded command used `--output data/development/native_interface_support/001`. The summary pins the maintained helper, its reviewed square-root dependency, all native inputs, the frozen source copies, and the output table. The original monotone reference and all production sources remain unchanged.

This result concerns the binary64 geometry and model values stored in the existing evidence. It does not bound physical model uncertainty, path discretization error, inserted-knot variations, or global first-arrival error. No QP was solved. No source or model derivative was selected, and fixed endpoint derivative fields are deliberately blank in `support_vector.csv`. A future nonsmooth envelope derivative needs a separate argument.
