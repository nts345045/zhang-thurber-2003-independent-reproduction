# Saved boundary-secant asymptotics

This package reads the reviewed [shooting controls](../loma_endpoint_shooting_controls_001/README.md)
and [retained mixed baselines](../loma_endpoint_shooting_baselines_001/README.md).
It performs no ODE/root/ray solve or action reintegration. All geometry is invented.
The eight original ladders and all 24 raw comparisons are retained, including
their failures against 3e-6 s/km. Sixteen extrapolates are separate consistency
calculations, not replacement observations, flags, or error certificates.

## Why a nonzero raw secant need not be a wrong endpoint derivative

Let the physical domain be z <= B, with affine speed v(z)=v_b+g(z-B),
v_b>0 and g>0. Suppose the selected branch has a positive bottom guide before
and after a small inward endpoint displacement h>0. Its horizontal momentum
is 1/v_b. The derivative of the minimized branch action with respect to inward
displacement epsilon is

    dT/d epsilon = sqrt((v_b-g*epsilon)^(-2) - v_b^(-2)).

Integrating from 0 to h gives

    T(B-h)-T(B) = c*h^(3/2) + O(h^(5/2)),
    c = (2/3)*sqrt(2*g)/v_b^(3/2).

Thus the outward-coordinate finite secant
D(h)=[T(B)-T(B-h)]/h equals -c*sqrt(h)+O(h^(3/2)), while the limiting normal
momentum is zero. The script derives c from the original g=1, v_b=6 fixture,
using 80-digit Decimal sqrt for the displayed coefficient, and compares its
leading term with the six saved affine secants. This leading term is not an
exact finite-h oracle or an outward enclosure.

For a smooth nonuniform field at a flat boundary, a regular grazing cap with
strictly positive normal reaction has contact length of order sqrt(h).
Under a stable, nondegenerate matched branch with a positive remaining guide,
the analogous local expansion has a leading h^(3/2) action term; tangential
variation can add an O(h^2) remainder. Consequently D(h)=p_n+a*sqrt(h)+O(h).
This is a conditional local branch statement. It does not cover zero reaction,
guide disappearance, a corner/cell kink, a singular matching system, a branch
switch, or an unproved global envelope. The mixed fixtures have no separate
exact analytic oracle. Saved sampled reaction, guide duration, topology,
endpoint and invariant residuals are retained as numerical eligibility evidence,
not proofs of these hypotheses.

For either expansion, the ratio-16 combination

    E(h) = [4*D(h/16)-D(h)]/3

cancels the sqrt(h) term. The general remainder is O(h); the affine remainder
is O(h^(3/2)). Exact rational combinations here mean exact arithmetic on the
saved binary64 secants, not exact continuous actions. Their maximum differences
from the limiting momentum are 3.46336e-9 s/km for the first pair
(2^-20,2^-24 km) and 4.97870e-8 s/km for the finer pair (2^-24,2^-28 km).
All sixteen are numerically below 3e-6 s/km, but the finer maximum worsens.
The old 24 raw failures are unchanged. This is evidence consistent with the
physical truncation explanation, not a certified extrapolation error.
The two ODE settings cannot bound their shared root, action-subtraction or
floating-point errors. For value error eta, a secant can amplify it by order
eta/h; further shrinking h is not justified by these results alone.

## Distinction from a fixed polygon

For a horizontal first straight element of length L at the same fast boundary,
with its other endpoint held fixed, the correct polygon partial is

    partial T_polygon / partial z_source = L*s'_z(B)/2 = -L*g/(2*v_b^2).

This produces a nonzero linear inward action term. It is a valid derivative
of that fixed polygon, but differs from the continuous guide value. Richardson
cancellation of sqrt(h) does not remove a constant derivative offset. The saved
positive-guide mesh fixture has g=1, v_b=6, L=(1/4)/n, hence partial=-1/(288*n)
for n=1,2,4,8,16. All five epsilon-zero optimized cases take zero updates; the
finest still has magnitude 2.17014e-4 s/km. Altering curvature memory cannot
change those initial stopping decisions or the fixed-element derivative formula.

This statement is about a fixed-knot partial. Tangentially nonunique minimizing
polygons may move their contact with the source, so it is not a proof that every
fully minimized finite-knot value has that partial. The retained native first-edge
calculation and coupled adjacent-knot accounting remain separate evidence.

## Reproduce

From the integration worktree, run the saved-only checker with a fresh output:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_endpoint_shooting_asymptotics_002/check.py --output tmp/loma_endpoint_asymptotics_NEW.json
```

The original summaries and independent reviews must match, every consumed
original/supplement pin is checked, and all inputs are rehashed after reading.
The checker does not import any numerical evaluator. `summary.json` contains
the full ladders, exact rational combinations, coefficient comparison, old
polygon controls, source pins and limits. No production or native acceptance
is inferred.
