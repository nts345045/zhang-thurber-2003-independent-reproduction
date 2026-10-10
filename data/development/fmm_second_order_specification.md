# Optional second-order FMM comparison

This specification proposes an isolated numerical comparison. The first-order
header is unchanged while its refinement audit is being completed. Passing the
field-extraction fixture does not resolve the recorded first-arrival failures
near the direct/diving crossover.

## Published stencil and eligibility

Sethian's 2001 review, Section 5.1, Eq. (17), uses a second-order one-sided
operator only when both upstream values are known and the farther value is no
greater than the nearer value. Otherwise it uses first order. The formula takes
the maximum of the two directional operators and zero on each axis. This is
the primary specification for the proposed switch.
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
A minimal implementation can bracket the root between the minimum effective
offset and the minimum single-direction value `a_e+b_e*s(x)`, then solve the
active quadratic piece with a safeguarded bracket. The bracket follows directly
from zero versus sufficient one-direction derivative, and does not add a
physical constraint. It also allows a simple independent scalar-root reference
test of the optimized local solve.

The existing first-order shortcut chooses the smaller accepted neighbor per
axis. Do not silently reuse that shortcut for the higher-order formula: the two
directions may now have different slopes `1/b_e`, so the smaller raw neighbor
does not always select the larger operator at the root. Test the actual maximum
or prove the selected active direction satisfies it.

## Causal fallback and recorded evidence

Keep an explicit constructor option, such as `order=1` by default, with the
original first-order branch preserved. For `order=2`, unavailable or nonmonotone
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

Increasing acceptance times do not make the high-order finite-difference
operator monotone in all input values: `T2` enters the extrapolation with the
opposite sign. Thus the method should be called a switched second-order stencil,
not given the first-order monotone-scheme convergence proof without further
analysis. The proposed fallback enforces local upwinding; it does not establish
global branch completeness at a finite grid spacing.

## Source accuracy and validation

Sethian and Vladimirsky give the same second-order directional formula in
Eqs. (5)-(6), and explain that accurate initial values near a source singularity
are needed to obtain higher accuracy. They also distinguish stencil order from
observed convergence order near nonsmooth travel-time fields.
[Sethian and Vladimirsky, 2000, p. 5702](https://math.berkeley.edu/~sethian/2006/Papers/sethian.fasteikonal.pnas.2000.pdf).

Keep the present exact-coordinate seed convention for the first isolated
comparison, but report it explicitly. It does not guarantee a globally
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

The next implementation decision should follow the pending first-order
0.125/0.0625 km auxiliary and path refinement results. No production integration
or new inversion is justified solely by this optional comparison.
