# Next invented control: one-cell stationary shooting candidates

This proposes an isolated calculation, not a native correction. The endpoint
mesh controls retained 32 source-accuracy failures despite 836 arithmetic and
parity checks. Their unchanged stopping rule can accept an unresolved endpoint
layer. The scalar contact calculation removes that optimizer ambiguity in its
affine example but retains a 6.066% leading excess-action error and a biased
fixed receiver partial. More unchanged polygon refinement does not address
these findings.

The smallest useful extension is a short stationary connector in the actual
eight-node trilinear field, solved by a few shooting variables. A fixed curved
shape would introduce another approximation to endpoint variations; instead,
integrate Fermat's equations along the local curved branch. Use the same field,
action and equations for every nodal perturbation. No affine dispatch is used.
Exact affine formulas serve only as independent oracles.

## Equations and candidate families

For positive v(x) = sum N_j(x) v_j in one finite cell, use the Hamiltonian
H = (v^2 |p|^2 - 1)/2. With the launch momentum normalized to |p| = 1/v,

    x' = v^2 p,
    p' = -v |p|^2 grad(v),
    T' = v |p|,
    K_j' = -N_j |p|.

On the exact invariant H = 0, the parameter is travel time, T' = 1, and
K_j = dT/dv_j = -integral N_j/v^2 ds. The negative-log-velocity column is
-v_j K_j. Integrating the unsimplified Hamiltonian form avoids substituting a
numerically imperfect invariant into the ODE. Report the integrated action T,
the invariant residual and its agreement with duration; do not renormalize p.

Compare two candidate topologies using this same action:

* Direct: two launch angles and duration, matched to the three receiver
  coordinates. The entire arc must remain inside the finite box.
* One bottom guide: two launch angles, first-cap duration, guide duration and
  second-cap duration. Match z = B and p_z = 0 at the first contact, then the
  three receiver coordinates after the final cap. Across contact, retain the
  actual tangential momentum. The guide integrates the two-dimensional
  Hamiltonian of v(x,y,B), with p_z = 0. Its normal reaction is
  grad(v)_z/v on the invariant; it must be nonnegative along the guide for
  the domain z <= B. A negative reaction rejects this constrained candidate.

When the source is already on the bottom, a zero first cap leaves one tangent
launch angle, guide duration and final-cap duration. With both endpoints on
the bottom and both caps zero, only tangent angle and guide duration remain.
For an interior source and bottom receiver, the mirror zero-last-cap topology
uses two launch angles, first-cap duration and guide duration; match the first
contact's z and p_z and the final two horizontal coordinates. Do not obtain
either zero cap by solving a singular positive-duration system.
These are explicit limiting topologies, not artificial short arcs. A zero
guide is handled by the direct/grazing branch. Never clip a negative duration
or silently accept an infeasible arc. Failure to match a branch stays visible.

For numerical conditioning, the planned implementation parameterizes the
positive-guide system by its first contact instead: (c_x,c_y), tangent angle,
backward-cap duration, guide duration and forward-cap duration. Integrate with
the same forward-oriented tangent momentum backward from c to match a, and
forward through guide and final cap to match b. These are six unknowns and
six endpoint equations. The backward action/kernel integrals acquire a minus
sign when accumulated in the physical forward direction. Zero-cap cases
retain explicit reduced systems. The mathematical reviewer confirmed both
parametrizations and signs before implementation; neither enumerates all roots.

For a regular matched stationary branch the endpoint derivatives are -p_a
and +p_b, and the original-node derivatives are K_j. These identities follow
from variation of the same action, unlike substituting momentum into the old
polygon functional. At a positive guide, a bottom endpoint has a tangential
momentum; its normal statement is inward one-sided. A homogeneous oblique
direct ray has a nonzero normal derivative and must remain so. A singular
contact or a tied branch requires same-value perturbation checks rather than
an arbitrary momentum choice. Both endpoints must be tested, because replacing
only the source component would leave the assembled first-vertex force wrong.

This is a stationary-candidate calculation. A shooting root need not minimize
the action, and these topologies need not enumerate other faces, corners,
multiple contacts or all curved roots of a general trilinear cell. Retain
root/continuation, domain, reaction and branch-selection limitations. Do not
name the result the exact constrained local value without that evidence.

Each duration variable is bounded by the cell diagonal divided by the minimum
positive nodal velocity, expressed in its own numerical scale. This is a
physical upper bound on the admissible in-cell straight path time and hence on
any minimizing branch's nonnegative leg times. It leaves slack for this
interior-endpoint roster; a root at a bound remains a numerical limitation.
The local-gradient contact estimates and scale choices are initial guesses,
not physical constraints. A guide is rejected before solving only if all
four bottom-face normal derivatives are strictly negative, which makes the
bilinear normal derivative negative everywhere. Mixed-sign faces still proceed
to the actual-arc reaction check; whole-face positivity is not required.

## Small control roster and decision

Use the existing cell and epsilon ladder, with a rotated horizontal separation
of length 0.25 km to break the previous y-mirror symmetry. First test v = 6 + z:
one endpoint inward, the reciprocal case, both inward, and both on the bottom.
Compare below/at/above the exact critical guide length. The action excess must
agree with the continuous affine oracle rather than the scalar family's
1.06066017 coefficient ratio. Check the full source and receiver derivative
vectors against the oracle using the existing 3e-6 s/km limit, and the existing
25-microsecond time limit. Preserve finite-step truncation separately.

Include a homogeneous oblique bottom source, a small positive gradient and a
negative-gradient example so tangency is not imposed on every boundary ray.
Then perturb each original node by v_j exp(-h), in both signs, and add one
mixed perturbation with genuine x and y dependence. For every model use the
same ODE, field interpolation, contact equations and action. Compare all eight
integrated kernels against central differences of re-matched branch actions;
compare tangential and admissible normal endpoint perturbations at both ends.
The old one-sided fixed-polygon partial is only a comparator.

Use a small direct numerical root solve and repeat with tighter ODE settings;
do not build an interval-proof framework. The scalar example already shows
that absolute action agreement is insufficient for small-displacement
differences. If changing integration/root settings changes a difference by
more than its derivative budget times the perturbation, preserve that case as
unresolved. Track branch changes and finite-step truncation explicitly.
Finite-precision agreement is evidence about this control, not a completeness
certificate. A failed source/receiver/model consistency check blocks native
use; passing it would justify only a separately reviewed saved-component trial.

Inputs motivating this proposal are the frozen endpoint mesh controls,
scalar contact controls and reviews, and the original proposal in this
directory. No native path, production code, inverse calculation or observational
data acquisition is part of the proposed control.
