# Usable-curvature arithmetic controls

Both frozen variants pass 183 invented checks. The four complete Ray bit dumps
and their CSV histories are identical between C and D. C is the reviewed
positive-only diagnostic, with its extended outer action accumulator; D adds
finite/representability checks to pair admission and the existing two-loop
direction. No native ray, receiver field, inverse calculation, or production
source was evaluated or changed by this run.

The shared helper accepts a pair only when its supplied computed dot is finite
and positive, the component arrays are finite, and its reciprocal is finite and
positive. Use-time checks reject nonfinite loop intermediates, invalid metric
coefficients/pivots, and nonpositive or nonfinite metric energy/scaling. Finite
zero or positive slope is an arithmetic result, not an accepted search direction:
the unchanged caller still requires feasible strict descent. Unusable memory
uses the existing cone fallback and clears memory; an unusable fallback throws.
The Fermat action, source/model derivative formulas, Armijo rule, stopping tests,
and ray budget are unchanged.

The scalar controls include the values adjacent to the former absolute cutoff,
normal/subnormal reciprocal behavior, product overflow/underflow, cancellation,
closed-form one- and two-node metric inverses, and an independently derived
oblique BFGS matrix. Separate cases exercise first-loop and second-loop overflow,
zero rounded pivots, denominator/gamma range failures, and nonfinite slopes.
The actual D admission and direction/fallback blocks are copied byte-for-byte
into the generated fixture header. Those controls verify rejected-pair memory
preservation, eight-pair eviction, fallback memory clearing, and thrown failures.
They do not return a Ray or claim convergence.

Both component builds use the same D helper and extracted caller blocks. The
actual C trace remains unchanged and does not call that helper. Actual C/D
trace parity uses four invented geometries: homogeneous and mildly affine
positive velocity, each with direct and bent supplied initial paths. Their
update counts are 0, 1, 1, and 3, and their reported convergence flags are all
true. The maximum affine time error against the analytic unconstrained travel
time is 2.7776689171e-8 s; the mild arc remains inside the box. Full Ray fields,
endpoints, coordinates, derivatives, length arrays, flags, and histories are
compared without a numerical tolerance. This bounded parity does not replace a
separately authorized native comparison.

Representable computed curvature is not an exact-sign or information
certificate. The preserved case `(1e16,-1,-1e16,.5) dot (1,1,1,1)` has exact
real value -1/2 but ordered binary64 value +1/2 and is admitted. Zero padding can
give the same example a multiple-of-three dimension. Exact positive dots lost
to cancellation or underflow are rejected without a numerical rescue rule. One
explicitly labeled inconsistent finite reciprocal tests defensive use-time
rejection; it is not claimed reachable from normal admission.

`summary.json` pins the prepared source, all copied source files, compiler,
binaries, commands, checks, and parity outputs. Both compiler logs retain the
inherited warning that the renamed unused native-driver entry can reach the end
of a non-void function. The fixture never calls that entry point. No compilation
or numerical failure occurred. The README and helper source-review record were
added after the immutable terminal summary; no consumed numerical file changed.

Reproduce in fresh directories from the integration worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 python3 diagnostics/run_usable_ray_curvature_checks.py --output data/development/usable_ray_curvature_controls_NEW --build tmp/usable_ray_curvature_controls_NEW
```
