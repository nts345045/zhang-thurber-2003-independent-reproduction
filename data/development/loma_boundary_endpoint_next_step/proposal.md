# Proposal: test endpoint refinement for one bottom-boundary ray

This is a bounded proposal, not an implemented correction. No experiment,
production edit, inversion, or observational retrieval accompanies this note.
Keep the finite model box and all current scientific acceptance limits.

Use only captured LOM initial pair 24104: event
`quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`, derived source
identifier `FDSN:NC_HQR__E_H_Z`, epoch `1989-07-11T19:55:00` through
`1990-03-24T19:55:00`. Its identified table preserves current perturbed and
original catalog coordinates separately. These provider IDs identify the
geometry; they are not identifiers for simulated observations.

## Mechanism and assumptions

The saved leading edge is horizontal at the 16 km bottom. Holding the other
knots fixed, its source partial is `L*s'_z/2`, equal to
−1.5850655663e−5 s/km. This is the derivative implemented by `segment()` and
returned from the first edge by `trace()`; it is not a sign or indexing error.
The continuous finite-bottom reference has zero normal source derivative.
Only displacement into the box defines the normal derivative here.

For a positive-length guide at a flat, fastest bottom in a continuous isotropic
medium, the branch leaves the source tangentially. Locally, if
`v(z)=v_B+g*(z-B)` with `g>0`, moving the source inward by epsilon gives

    T(B-epsilon)-T(B) = integral[B-epsilon,B] sqrt(1/v(z)^2-1/v_B^2) dz
                     = O(epsilon^(3/2)).

The derivative tends to zero while the branch remains applicable. A direct
oblique ray from a bottom source generally has a nonzero normal derivative;
boundary membership alone never justifies setting it to zero. Branch ties,
vanishing guide length, and different boundary geometry require separate
interpretation.

Collinear knots can slide along the constant-speed bottom guide without
changing the base action, while changing the first-edge length and its source
partial. Local fixed-polygon KKT stationarity is therefore **not a certificate
of a differentiable optimized-value envelope**. For an inward source shift,
balancing geometric `O(epsilon^2/L)` and medium `O(epsilon*L)` costs allows a
contact distance `L=O(sqrt(epsilon))`, even with finitely many free knots.
Node collapse and the existing merge convention must be recorded explicitly.

## Minimal proposed experiment

1. Retain the selected native polygon and subdivide only its first edge into
   1, 2, 4, 8 and 16 pieces. At each level, compare the source partial with
   inward finite differences holding all other knots fixed. Retain the tied
   inserted-knot contraction as a separate check of the original coarse
   perturbation family. Existing subdivision results already establish the
   base-action equality; they do not establish an optimized derivative.
2. Independently reoptimize each refined polygon with the same action,
   optimizer equations and box constraints. Added knots are free variables,
   not affinely tied constraints. Use a predeclared inward perturbation ladder
   and compare retraced travel-time secants with the continuous reference's
   finite-step changes. Compare these separately with the fixed-knot partial.
   Preserve all local flags, actual leading-edge lengths, knot redistribution,
   merges, topology changes and branch identities; do not hide unresolved cases.
3. Require mesh and perturbation convergence before proposing a correction.
   A later forward implementation must use the same refined action for time,
   source derivatives, velocity derivatives and inverse trial objectives.
   Subdivision alone, zeroing a component, or substituting endpoint momentum
   while retaining an inconsistent forward value does not meet that contract.

Use three small analytic controls: a positive-length affine fast-bottom guide,
a homogeneous oblique direct ray from a bottom source, and a guide approaching
zero length. Keep fixed-family and reoptimized-value finite differences
separate. These controls and this one identified native ray bound the next
step; do not expand to all 48 failures before its mechanism is resolved.

The present `trace()` uniformly redistributes seeded vertices in arclength
(`src/core.hpp:344`), erasing local refinement. A future isolated diagnostic
must retain an explicit knot mesh; it must not silently change the production
seed policy. Source partial construction is at `src/core.hpp:202` and `:488`;
the fixed/tied distinction is at `diagnostics/check_boundary_endpoint.cpp:65`.

## Source and evidence pins

Paths below are relative to the integration repository root. The maintained
and captured `core.hpp` bytes agree at proposal time. These pins preserve the
basis of the proposal rather than a completed experiment.

| Path | SHA-256 |
| --- | --- |
| `src/core.hpp` | `7111f67c896b7b93d344372423259e288533210807392e7da2eec72f0c55caed` |
| `data/development/loma_initial_failure_24104_001/source/src/core.hpp` | `7111f67c896b7b93d344372423259e288533210807392e7da2eec72f0c55caed` |
| `diagnostics/check_boundary_endpoint.cpp` | `016bb2b9876b4d6a688028a821b2b5384fa30f55ccd4f53b1403fdcb923d37f7` |
| `data/development/loma_initial_failure_24104_001/identified_ray.csv` | `69a4c5c662f9f0128cda637155285de2b13484eb8f7bd0e84ef5621f33c948b1` |
| `data/development/loma_initial_failure_24104_001/inputs/initial_grid.csv` | `845a3f93c8f0b96138850da8290e60c41905bf69c2c23abec572da95a59b3b7f` |
| `data/development/loma_initial_failure_24104_001/summary.json` | `05ee19cbfb2a8619e9613084354fa5d66f158794caa1b0159486171bd633c573` |
| `data/development/loma_boundary_endpoint_001/summary.json` | `3c7f6337d3eec829eaf048d6999bb97f0af749d55018cac4ea98ae4a067b1124` |
| `data/development/loma_boundary_endpoint_001/review.json` | `2f643811e53530cd4108bd9e412dfaa32f58b982399b5cb4eddde12be685cf07` |
