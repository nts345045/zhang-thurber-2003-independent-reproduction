# Optional second-order FMM comparison

The optional switched second-order stencil is now implemented in
`diagnostics/first_arrival_fmm.hpp` as an isolated prototype. The constructor is
`Field(grid, receiver, spacing, order=1, closed_seed_cells=false)`. The first-order
stencil and original source-seeding rule remain the defaults. Neither option is
integrated into the production solver. Passing the field/root fixtures does not
resolve the recorded first-arrival failures near the direct/diving crossover.

## Published stencil and eligibility

Sethian's 2001 review, Section 5.1, Eq. (17), uses a second-order one-sided
operator only when both upstream values are known and the farther value is no
greater than the nearer value. Otherwise it uses first order. The formula takes
the maximum of the two directional operators and zero on each axis. This is
the primary specification for the implemented switch.
[Sethian, 2001, manuscript p. 16](https://math.berkeley.edu/~sethian/2006/Papers/sethian.levelsetreviewarticle.2001.pdf).

For a grid point x and direction sign e, write `T1=T(x-e*h)` and
`T2=T(x-2*e*h)`. Require both nodes to be accepted, inside the domain, and
`T2 <= T1` before using

`d_e(T) = (3*T - 4*T1 + T2)/(2*h) = (T-a_e)/b_e`,

where `a_e=(4*T1-T2)/3` and `b_e=2*h/3`. Otherwise, if the first node alone is
accepted, use `a_e=T1`, `b_e=h`. An unavailable direction contributes no positive
upwind derivative. The effective offset obeys `a_e >= T1 >= T2`; consequently a
positive second-order derivative uses only values below the new candidate.

For all three axes solve the piecewise quadratic equation

`sum_axes max(0, d_minus(T), d_plus(T))^2 = s(x)^2`.

This scalar left side is continuous and nondecreasing on the relevant range.
A scalar solve brackets the root between the minimum effective offset and the
minimum single-direction value `a_e+b_e*s(x)`, then solves the active quadratic
piece. Bisection handles floating-point ambiguity at piece boundaries. The bracket follows directly
from zero versus sufficient one-direction derivative, and does not add a
physical constraint. It also allows a simple independent scalar-root reference
test of the optimized local solve.

The existing first-order shortcut chooses the smaller accepted neighbor per
axis. Do not silently reuse that shortcut for the higher-order formula: the two
directions may now have different slopes `1/b_e`, so the smaller raw neighbor
does not always select the larger operator at the root. Test the actual maximum
or prove the selected active direction satisfies it.

## Causal fallback and recorded evidence

The explicit `order=1` constructor default preserves the original first-order
branch. For `order=2`, unavailable or nonmonotone
two-point stencils fall back to first order in that direction, as the published
switch prescribes. If the computed mixed-order root is nonfinite or violates
the nonnegative upwind derivative/accepted-neighbor ordering, recompute the
whole update with the existing first-order rule and record the fallback. Do
not repair an invalid candidate by clipping its time to a desired answer.

Retain the check of nondecreasing heap acceptance times. Record counts of
second-order directional stencils, eligibility fallbacks, numerical/causality
fallbacks, and extraction fallbacks. Accepted values remain immutable. A
two-step stencil can become newly eligible when its farther node is accepted;
the implementation must either reconsider affected trial nodes or explicitly
retain first order until their next ordinary update. Equal-time ties and axis
reflections should be tested so their effect is visible.

The implementation also revisits trial nodes when an equal-time second neighbor
becomes accepted. A strictly lower second neighbor was already accepted before
the near neighbor under heap ordering. Causality checks apply only to positive
winning directions, not an inactive opposite neighbor.

Increasing acceptance times do not make the high-order finite-difference
operator monotone in all input values: `T2` enters the extrapolation with the
opposite sign. Thus the method should be called a switched second-order stencil,
not given the first-order monotone-scheme convergence proof without further
analysis. The fallback enforces local upwinding; it does not establish
global branch completeness at a finite grid spacing.

## Source accuracy and validation

Sethian and Vladimirsky give the same second-order directional formula in
Eqs. (5)-(6), and explain that accurate initial values near a source singularity
are needed to obtain higher accuracy. They also distinguish stencil order from
observed convergence order near nonsmooth travel-time fields.
[Sethian and Vladimirsky, 2000, p. 5702](https://math.berkeley.edu/~sethian/2006/Papers/sethian.fasteikonal.pnas.2000.pdf).

The first isolated order comparison retains the original exact-coordinate seed
convention. It does not guarantee a globally
second-order field. If source error dominates, test a separately refined source
neighborhood or a factored eikonal formulation as a distinct change; do not
attribute its benefit to the stencil alone.

Compare both orders at identical auxiliary grids and identical continuous
bending settings. Retain the analytic crossover sweep, off-grid homogeneous
cases, boundaries, constant-gradient references, reciprocity, and source
derivatives away from crossings. Add an affine travel-time local-update test,
axis permutations/reflections, and a case where both opposite directions are
accepted with different eligible stencil orders. Preserve all failures at the
existing tolerances. Improvements at 20 or 40 km do not resolve a missed branch
at 14.68, 15, or 16 km; agreement among several finite grids also does not do so.

The independent reflection fixture exposed an inherited source-seeding
asymmetry: a receiver exactly on an auxiliary node was assigned exact diagonal
seed bounds only in the half-open upper cell. The optional `closed_seed_cells`
rule instead uses the union of vertices of every closed cell containing that
receiver, and the same cell union for the final exact-receiver connection. This
uses exact coordinate equality, without a tuned radius or alignment tolerance.
It is a separate option so its effect can be distinguished from stencil order.
The recorded 224-case comparison restores reflection symmetry at faces, edges,
and nodes for both orders and leaves off-grid nodal fields and extracted paths
bitwise unchanged. Default-rule reflection failures remain in the evidence.

Reproducible field, scalar-root, affine-stencil, and source-seeding comparisons
are documented in `fmm_field_checks/README.md`. The scalar-root comparison uses
independent long-double bisection; its maximum discrepancy is 4.44e-15 s over
100,000 invented mixed-operator cases. These are local arithmetic/geometry
checks. Analytic first-arrival and bent-path audits still test branch selection
and continuous action accuracy. No production integration or new inversion is
justified solely by the component passes.
