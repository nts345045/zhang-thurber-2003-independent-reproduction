# Isolated reference for nonmonotone layered velocity

`diagnostics/first_arrival_layered_reference.py` accepts a finite, positive,
continuous piecewise-linear velocity profile in the third coordinate. It
does not change `first_arrival_1d_reference.py`, the production tracer or any
simulation input. A coordinate permutation can put a different normal axis
in the third coordinate; the original finite box must be permuted with it.

The implementation enumerates direct paths whose normal coordinate is
monotone, single turns on either side of the endpoints, and critical guides
at accessible local maxima, plateaus or domain faces. It bounds turning
slowness using every preceding velocity maximum, including maxima between
endpoints. Critical guides may lie between the endpoints. A positive-width
leg at constant critical speed requires infinite transverse distance and
is explicitly excluded from finite candidates. Equal maxima can yield
distinct guide allocations with identical time and endpoint momentum;
these candidates are retained.
Here `complete` means that the candidate families suffice to represent the
minimum travel time. Equal-maximum guide allocations can form a continuum;
the output is not a finite listing of every geometrically distinct ray.

For positive continuous velocity, projecting a path's transverse coordinates
onto the endpoint line cannot increase action. A stationary nonvertical path
has conserved transverse slowness p > 0 and monotone transverse progress.
Every traversed speed is at most u = 1/p; a normal turn has v = u. If a path
has multiple normal turns, keep its first turn and replace the remaining
normal excursions with a monotone leg to the receiver. Add a guide at the
first turn to restore the removed transverse distance. This replacement is
feasible in the same finite box. Each removed traversal saves

`T - p X = integral sqrt(v^-2 - p^2) |dz|`,

which is positive for a nondegenerate excursion. Thus a multiply-turning
ray cannot be first. This guide is a feasible comparison even when the
turn lies on an ordinary gradient and the guide itself is not stationary.
Actual stationary guide families require a local maximum, plateau or
constrained face. A non-tangent corner at a continuous interface or face
can be shortened locally and is not an additional minimizing family.
Zero transverse separation is handled by the direct normal slowness integral.

The numerical implementation reuses the existing exact rational leg
coefficients and outward interval root isolation. Reflection supplies left
turns; signed coefficients are retained. Unresolved critical signs, layer
membership or root intervals invalidate the reference instead of removing
a possible arrival. Candidate enumeration and floating-point time ranking
are separate claims. These are km-scale numerical calculations; no general
arbitrary-magnitude floating-point guarantee is made.

`signed_turn003/results.json` records 265 passing checks. They cover direct,
turning, guide and finite-boundary paths; reflected affine profiles with an
independent exact travel time; equal maxima and tied derivatives; a deeper
turn independently constructed by integrating the Snell equations; all 17
saved monotone cases; nearly constant velocity; and finite-boundary
`nextafter` cases. The planted deeper turn exercises a negative coefficient
in the transformed distance equation. Endpoint derivatives are checked by
finite differences only when all tied first branches have the same derivative.

`initial001` retains two failed fixture expectations: it required a unique
guide allocation at equal maxima and assumed that an easy example would
need more than one isolation box. `corrected_fixtures002` corrects those
expectations and passes 256 checks. The reference module did not change
between these three runs; source snapshots and hashes are saved in each.
The additional signed-turn control accounts for the nine further checks in
`signed_turn003`.

An independent source review found no concrete completeness, orientation,
source-sign or arithmetic defect. Its further multi-extremum reflection
sweep is reproduced in `reviewer_sweep004`: six profiles at three transverse
separations, each checked forward, reflected and reciprocal, with an
independently integrated straight-path upper bound. All 355 checks in that
extended fixture pass. The source module remains identical to the preceding
runs. Review scope and source hashes are saved in `independent_review.json`.

Reproduce with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_layered_reference.py --output data/development/layered_reference_checks/repeat
```

The component fixtures use invented endpoints and no provider records. Passing
them is not a claim about the accuracy of any production ray, and it does not
authorize replacing synthetic truth or bypassing simulation gates. An
independent review precedes an identified comparison with the Loma sample.
