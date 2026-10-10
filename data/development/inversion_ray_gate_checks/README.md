# Reject unsupported forward evaluations during inversion

The parent solver recorded local ray failures in its iteration history but
still used those rays in the Jacobian. Trial objectives and final output
generation also lacked this check. A reduced objective could therefore describe
an update calculated from unconverged paths. Passing an initial-model preflight
did not address failures after the velocity model or source positions changed.

The guard checks each current-model, line-search-trial, and final-model forward
evaluation before its use. It requires the existing local stopping flag, finite
values, paths inside the model box, exact endpoints, successful initialization
when requested, and complete derivative arrays when derivatives were evaluated.
It changes no objective, derivative, ray optimizer, stopping tolerance, model
update, or observation selection. A failed evaluation aborts the inverse run.
The matrix-only preflight remains diagnostic: it saves failed local flags and
counts entries without solving an inverse system.

These checks are necessary conditions. They do not establish global first
arrivals, derivative accuracy, or nonlinear convergence. An exact interface
minimum can fail the existing ordinary-gradient stopping test; the separate
interface investigation must resolve that failure before it can be accepted.
The guard does not reinterpret that flag or try smaller inverse steps after an
unsupported trial evaluation.

## Failure files

For inverse mode MODE, the output directory receives:

- MODE_failed_forward_context.csv: current iteration, evaluation phase,
  zero-based line-search trial (or -1), whether derivatives were requested,
  whether initialization was required, and the exception.
- MODE_failed_forward_ray_status.csv: every requested native ray and its
  unchanged flags, source correction, and endpoint/path checks. A separate
  ray_derivatives_evaluated flag identifies action-only trial evaluations;
  unevaluated source derivatives are blank.
- MODE_failed_forward_ray_failures.csv: every failed native ray and its reasons.
- MODE_failed_forward_ray_paths.csv: available path vertices of failed rays.
  Empty paths remain explicit in the status table.
- MODE_failed_forward_events.csv and MODE_failed_forward_grid.csv: the state
  evaluated when the failure occurred.
- MODE_last_accepted_events.csv and MODE_last_accepted_grid.csv: the preceding
  accepted state, or the initial state before any accepted update.

The failure and accepted-state snapshots use 17 significant digits, preserving
finite binary64 values on reload. Native event/origin and channel SEED/FDSN IDs,
valid empty location codes, and epochs remain attached. A trial state is never
written to the conventional final MODE_events.csv or MODE_grid.csv filenames.
A field-construction exception can occur before any ray array exists; its
context and model states are preserved, but unavailable ray records are not
invented.

## Controlled checks

The fixtures use two invented events, two receiver epochs, four rays and eight
synthetic observation rows. No real inversion is run. They cover local failure,
nonfinite action, empty/outside paths, one-ULP endpoint changes, initialization
failure, missing derivative arrays, native sparse order, and distinct failed
trial versus accepted states. Complete inverse calls exercise all three
evaluation phases. Failure snapshots round-trip the saved floating-point values.

A successful two-update homogeneous fixed-model location inversion is compared
against parent commit609f04a. All seven numerical output files are byte identical.
The diagnostic preflight's complete status table, census and empty history are
also byte identical. The parent executable separately demonstrates the defect:
it writes inverse outputs after using locally unconverged rays.

Variant001 preserves the initial passing experiment. Variant002 adds native
failed-path vertex preservation and its round-trip checks. Variant003 clarifies
failed-coordinate metadata and leaves unevaluated source derivatives blank.
Variant004 distinguishes requested derivatives from available derivatives after
a caught worker exception; its empty Ray must not masquerade as zero partials.
Each variant pins
its source, compiler logs, commands, executable hashes and output artifacts;
later variants preserve earlier evidence.

Reproduce with a new variant:

    PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_inversion_ray_gate_checks.py --variant repeat

The current change is developed in an isolated worktree. Existing live
executables, configurations, source snapshots and results have not been replaced.
