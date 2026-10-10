# Replay the bounded integration checks

The historical runner deliberately requires its original maintained-source
inputs. The integration branch has since adopted the tested candidate. To
repeat that experiment, reconstruct the earlier inputs in a **fresh scratch
checkout**, then let the runner create its own isolated candidate workspace.
Existing worktrees, live jobs and old output directories are outside this scope.

From the published integration checkout, with no existing destination below:

```sh
mkdir -p tmp
PYTHONDONTWRITEBYTECODE=1 python3 data/development/terminal_lock_archive_001/restore.py --scratch tmp/curvature_integration_replay_001
git archive first-arrival-integration | tar --extract --file=- --skip-old-files --directory=tmp/curvature_integration_replay_001
PYTHONDONTWRITEBYTECODE=1 python3 data/development/terminal_lock_archive_001/restore.py --verify tmp/curvature_integration_replay_001
cp -R data/development/usable_curvature_integration_prepared_001/before/. tmp/curvature_integration_replay_001/
cp data/development/usable_curvature_integration_checks_001/runner_before/run_fmm_initialization_audit.py tmp/curvature_integration_replay_001/diagnostics/
cp data/development/usable_curvature_integration_checks_001/runner_before/run_fmm_rotated_affine.py tmp/curvature_integration_replay_001/diagnostics/
cd tmp/curvature_integration_replay_001
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_usable_curvature_integration_checks.py --output data/development/curvature_integration_replay_001 --build tmp/curvature_integration_replay_001
```

Use the matching immutable published integration commit in place of the branch
name to pin the checkout. The restoration helper refuses an existing destination;
the overlay preserves the exact historical sentinels. The three copy commands
restore only the declared source prerequisites inside that new scratch checkout.
The runner verifies their hashes, builds the frozen candidate, executes the
bounded invented controls and preserves all results, including coarse accuracy
failures. Its original command and compiler/runtime pins are in the saved
integration-check summary. A changed compiler or library remains a changed
execution environment.

This replays the historical bounded experiment. It does not validate the entire
observational cohort, replace the running frozen binaries, or launch an inversion.
