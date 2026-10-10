# An exact interface minimum rejected by ordinary-gradient stopping

This invented component uses the actual `segment()` and `trace()` from the
frozen Loma run001 source. It is independent of the current Loma ray results.
No production source, stopping threshold or active process was changed.

The bounded model is v(x) = 6 - 2 max(x,0) km/s, with x in [-1,1], y in [0,2],
and z in [-1,1] km. The endpoints are S = (0,0,0) and R = (0,2,0), with one
interior knot P = (p,1,0). Direct integration gives

\[
T(p)=\begin{cases}
\sqrt{1+p^2}/3, & p\leq0,\\
\sqrt{1+p^2}\,[-\log(1-p/3)]/p, & p>0.
\end{cases}
\]

Thus T(0) = 1/3 s, T'(0-) = 0, and T'(0+) = 1/18 s/km.
Every admissible path has length at least 2 km and speed at most 6 km/s,
so this straight path is a **global** minimum. The slowness is continuous,
but a positive-length segment on its gradient discontinuity produces a
nonsmooth action. Splitting quadrature at transverse cell crossings cannot
remove this physical property of the piecewise-linear velocity model.

The component reproduces the formulas to 5.6e-17 s. Nevertheless, unchanged
`trace()` returns zero updates, projected gradient 0.05555555555555555 s/km,
and `converged=false`. The half-open cell lookup chooses the positive-side
derivative at x = 0; its negative search direction does not decrease the true
action. The five saved checks establish this counterexample, rather than
asserting solver readiness or attribution of any actual Loma ray failure.

The returned source-x derivative is also 1/36 s/km, whereas the derivative of
the optimized travel time is zero. For a source displaced to x = epsilon < 0,
the fast-side straight path has O(epsilon²) excess action. For epsilon > 0,
a Snell leg tangent to x = 0 followed by a nonnegative guide has excess

\[
\int_0^\epsilon \sqrt{(6-2x)^{-2}-6^{-2}}\,dx
=O(\epsilon^{3/2}).
\]

The endpoint-distance/6 lower bound and these feasible upper bounds give a
zero optimized source-x derivative from both sides. A change that only
relabels convergence would leave this derivative error in the Jacobian.

Executed from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/interface_stationarity/check.py
```

The runner compiles `diagnostics/check_interface_stationarity.cpp` against
copied run001 `core.hpp` and `ray_metric.hpp`, sets repository-local TMPDIR,
and preserves their hashes and exact contents in `frozen_run001/source/`.
`raw_results.json` contains each action, gradient, one-sided secant and the
actual returned source derivative. `summary.json` records commands, compiler
output hashes, formulas, limits and checks. To repeat without overwriting
evidence, append `--output tmp/interface_stationarity_repeat`.

A suitable interface certificate must consider joint knot directions. On an
interface-aligned segment, the normal displacement is
delta x(t) = (1-t)d_i + t d_j. The first variation integrates the corresponding
one-sided slowness derivative over the positive and negative portions of this
function, in addition to the geometric length term. Independent coordinate
tests can miss coupled descent. Upward slowness-gradient jumps give a convex
directional functional; general interfaces need not. Clarke stationarity alone
does not exclude a cusp maximum. Endpoint sensitivities must use a consistent
joint interface solution and retain ambiguity where no unique derivative exists.
