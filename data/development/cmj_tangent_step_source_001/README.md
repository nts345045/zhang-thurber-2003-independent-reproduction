# One tangent metric direction: source and invented controls

This package is prepared source only. No compilation, control execution,
metric solve, direction, trial polygon, or action evaluation has occurred.
It implements the bounded arithmetic in the reviewed
[tangent-step plan](../cmj_tangent_step_plan_001/README.md). It is outside the
current CMJ publication inventory. No maintained production source or live
input is changed.

## Source and numerical scope

`source/diagnostics/tangent_metric_step.cpp` includes byte-identical frozen
`core.hpp` and `ray_metric.hpp`. Its `solve` mode calls only
`ray_metric_weights` and `solve_free_ray_metric`; it calls no trace, field,
path optimizer, or cone solver. A separate `weights` mode supplies small
invented positive systems to the same principal solve. The `round` mode forms
one trial using the original `P` multiplication followed by addition. Explicit
`-ffp-contract=off` preserves that two-operation interpretation. It does not
alter the copied numerical headers.

The driver checks positive finite weights and pivots, finite elimination
arithmetic, direction, residual, quadratic energy and midpoint slope. It
retains the original principal diagonals when a neighboring coordinate is
fixed. Its residual is descriptive; no new numerical residual tolerance
certifies a Fermat derivative or a metric minimizer. Decimal and hexadecimal
binary64 outputs are retained together.

`source/diagnostics/tangent_metric_step.py` supplies small functions for
exact saved-interval contraction, downward step rounding, actual-displacement
validation and full changed-edge action accounting. `single_trial` permits
one metric callback and at most one rounding callback. If the nominal slope
is not strictly negative, it returns without a trial. If the actual rounded
displacement slope is unresolved, it returns without action evaluation.
There is no alternate direction, step halving, integration escalation,
resampling or repair.

The velocity/action arithmetic is copied unchanged from the reviewed
trilinear controls. The fixed options are degree 8, one subdivision and
128-bit outward bounds. The complete starting edge records are supplied by
the caller; identical ordered edges cancel exactly. Each new trial edge is
evaluated at most once. The full starting and trial actions remain available
alongside their paired difference. No tangent integration is repeated.

The sufficient Armijo test is

    Delta.upper <= binary64(1e-4) * alpha * nominal_slope.lower.

This applies the inherited nominal-direction rule to the **actual rounded
trial action**. The independently checked displacement slope does not assert
that rounded displacement equals `alpha * direction`. No accepted diagnostic
trial becomes a converged ray, first arrival, or inversion input. There is no
new source/model derivative or post-step stationarity claim.

## Prospective invented controls

The runner is `diagnostics/check_tangent_metric_step.py`. The following roster
is source, not a list of executed results.

| Family | Independent check | Declared work |
| --- | --- | --- |
| Principal stiffness | A small dense rational Gaussian solve versus the frozen tridiagonal solve; the exact principal matrix is `[[2,-1,0],[-1,3,0],[0,0,4]]`, its direction is `(-1,2,-1)` and its energy is 22 | 1 supplied-weight solve |
| Arithmetic eligibility | Zero, negative or nonfinite weight/RHS; diagonal overflow; cancellation to a zero pivot; forward-RHS overflow; solution overflow | 8 rejected supplied-weight calls |
| Homogeneous bent polygon | Endpoints `(0,0,0)`, `(1,0,0)`, middle `(1/2,1/4,0)`, speed 4: the action is `sqrt(5)/8`, its y partial is `1/(2 sqrt(5))`, and the ideal metric direction is `-1/4`; actual emitted direction/trial are checked against their own length formula | 1 metric solve, 1 rounded trial, at most 2 action edges |
| Stationary and unresolved cases | A straight homogeneous polygon has zero direction and no trial; complete interval contraction preserves an unresolved sign and rejects nonzero unavailable-normal movement | 1 metric solve, no trial/action |
| Actual rounding and geometry | A half-ULP move rounds to zero despite a negative nominal slope; endpoint/normal changes, box violation, collapse, changed component mask, exact physical boundary and multiple aligned faces reject | 1 standalone rounding call; no action |
| Accounting and preservation | Exact unchanged-edge cancellation, downward largest admissible binary64 step, step underflow, changed invented input pin and prior-output refusal | No C++ call or action |

Total C++ budget: **13 invocations** (3 successful solves, 8 rejected arithmetic
calls, 2 rounding calls). The only new trilinear action work is at most two
invented homogeneous edges. A small independent integer Newton square root
provides an absolute 192-bit dyadic enclosure for the invented radicals and
their analytic gradient; it does not import the action's square-root helper.
The starting and actual trial action intervals are also checked by exact
rational squaring against `5/64` and `(1+4*q^2)/16`, where q is the actual
rounded middle y coordinate.
All physical comparisons use the existing action and Armijo constants. The
small dense/principal-system agreement is exact; no comparison allowance is
needed for its representable entries and solution. In the homogeneous case,
z=0 is the sole internal aligned face; only z is unavailable. The x component
is available and zero. The ideal radical formula is kept separate from the
emitted binary64 direction and actual rounded coordinates.

The runner requires `prelaunch_review.json` with `status="passed"` and the
exact `prepared_sha256`. The binary is separately compiled and its exact hash
is supplied to the runner. All original and copied source pins are checked
before and after. Each child is owned and reaped; signals are blocked around
launch bookkeeping and cleanup. Partial cases and failure summaries remain.
If action evaluation fails after it begins, the count is explicitly unknown
until successful completion; it is not reported as zero.
`controller.py` is prepared source for the single compile and control run. It
owns/reaps each command, checks compiler process-group termination, and requires
the control runner's helper-reaping records before freezing control outputs.
An interrupted run with unknown descendant status has no frozen output map.
No controller or terminal receipt has executed or been produced here. Its
concrete commands remain subject to independent prelaunch review.

The proposed compile command and runtime pins are in `prepared.json`. The
proposed runner command is

```text
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 \
  diagnostics/check_tangent_metric_step.py \
  --output data/development/cmj_tangent_step_source_001 \
  --binary data/development/cmj_tangent_step_source_001/build/metric_step \
  --binary-sha256 COMPILED_BINARY_SHA256
```

This command has **not** run. A passed source review is required before either
compilation or invented execution.

## Later native use remains separately gated

There is deliberately no native loader or native executable entry point in
this package. The generic Python functions do not write coordinate files.
A later wrapper would bind the reviewed saved candidates and every starting
edge record, preserve all full native event/origin and SEED/FDSN/epoch fields,
and attach them to every metric input/output, direction, trial and action file.
Bound identifier sidecars must be written **before** any future native helper
launch, so even partial or failed numeric output retains complete identities.
It would recheck the exact unavailable-normal mask, fixed source/receiver,
node count/order, original false flags and unevaluated source partials. A
failed native pin or incomplete metadata would be fatal before numerical work.

The only contemplated native roster remains events 981 and 987 at receiver
160. Original convergence flags remain zero and candidate convergence remains
null. Their unavailable x-normal slots stay exactly zero in the direction.
This is a chosen feasible search subspace, not a physical constraint or a full
stationarity condition. The native input hashes and full context are pinned
through the unchanged plan provenance. No new native geometry is generated
or copied here.

The future native work would be at most two principal solves, two rounded
trials and 2,058 trial edge actions, with exact unchanged-edge reuse. Its
loader, sidecars, lifecycle, concrete preparation and execution still require
review; the invented controls cannot authorize them by implication.
