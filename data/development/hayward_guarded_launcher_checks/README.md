# Guarded Hayward DD launcher controls

The launcher is prepared for one separately frozen DD attempt. No real inverse
run was launched by this work. Hayward004's sampled preflight and its scientific
accuracy review remain prerequisites; the old preflight binary is preserved
and is not silently replaced.

Variant `001` passed 25 controls. Variant `002` passed 30 controls and pins the
final maintained launcher. Each suite ran a real CMake build and one DD solve
on an invented homogeneous model with two events, two native receiver epochs,
three absolute observations and one differential observation. The invented
accuracy-review files exercise the review schema only. They are explicitly
identified as fixtures and cannot authorize the real Hayward cohort.

The controls check rejection of incomplete or failed preflights, stale input
and review hashes, unassessed finite differences, altered accuracy limits,
failed adoption controls and changed native input files. Variant `002` also
checks rejection of negative coverage, failed residual initialization,
inconsistent history initialization counts and incorrect matrix dimensions.
The observed-data output contract preserves resource IDs and both native
epochs. Successful test completion remains
`completed_pending_final_diagnostics` with `scientific_success=false`.

An actual SIGTERM during compilation verifies the interruption path. The
launcher terminates and reaps the subprocess group, records the terminal
state, and freezes partial hashes only after live descendants are gone. Both
the successful and interrupted attempts leave the original fixture inputs
unchanged. Variant `002` additionally checks that the original O3 control
bundle remains byte-identical while rejection tests mutate a private copy.

Reproduce in a fresh variant directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_hayward_guarded_launcher.py --variant NEW
```

Each variant retains exact source snapshots, commands, raw logs, original
inputs, native outputs and artifact hashes. `002/source_review.json` records
an independent read-only review. The reviewer found and verified the fix for
a gap between eligibility validation and source copying: every copied
mathematical source is now rechecked against the O3 evidence before building.
The tests do not establish nonlinear convergence, globally earliest arrivals,
or final-model derivative accuracy. Those are separate scientific assessments.

## Required real-run review

The maintained command is `run_hayward_guarded_inversion.py`. It requires
`--preflight`, `--reference`, `--accuracy-review`, `--parity-review`, and fresh
`--output` and `--build` directories. The parity review is the passed O3
`summary.json` in `../hayward_guard_adoption_checks/001/`.

The final accuracy review must bind the exact preflight manifest, terminal
execution ledger, preflight checks, full-reference summary and independent
review, and all three sampled diagnostic CSVs. It must explicitly assess full
reference controls, sample local flags, sample accuracy and finite-difference
truncation, with interpretation and limitations. The decision
`eligible_for_guarded_dd_attempt` authorizes only that attempt. No real passed
accuracy-review file is supplied by these fixtures.

The launcher preserves all inverse settings and uses four threads and a
128 GiB address-space limit. It builds a separate guarded binary, freezes
source/compiler/runtime/input/evidence hashes, and checks every inverse
forward evaluation using the existing flags. A failed evaluation stops before
its objective or Jacobian is used and retains identified failure artifacts.
Final ray/refinement, full-DD Jacobian and scientific output checks remain
explicit follow-up work. Other inverse modes do not start automatically.
