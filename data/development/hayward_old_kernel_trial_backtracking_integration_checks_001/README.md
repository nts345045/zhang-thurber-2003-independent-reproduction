# Frozen old-kernel integration checks (prepared only)

This package uses the complete frozen old7111 kernel and CMake source from
`hayward_old_kernel_trial_backtracking_candidate_001/after`, whose sole
production-source change is the reviewed candidate003 main.cpp trial policy.
Maintained sources and the earlier D draft are unchanged.

The proposed commands compile at the original optimized, assertion-enabled
flags, run the existing 48 core checks and unchanged external-input fixture,
and run the copied guard fixture. Only its obsolete immediate-trial-abort
expectation is adapted. All original fixture geometry/settings and the
current/final, altered-ray, worker-exception, native-epoch, preflight and
17-digit round-trip assertions remain. The first pure local-stopping failure
must be retained before subsequent halved trials. Actual outcomes are recorded:
completion, no objective-evaluable trial, or a later current/final fatal guard.
The last case may follow a successful action-only trial; it is not exhaustion.
Unexpected or mixed trial exceptions are not accepted as pure-quality recovery.

No compilation or numerical run has occurred at preparation. Execution requires
an independent `prelaunch_review.json` bound to `prepared.json`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_old_kernel_trial_backtracking_integration_checks_001/run.py
```

All outputs remain in this fresh project subdirectory. Six lifecycle/check
functions are AST-identical to the reviewed CMJ saved-gradient runner, including
termination/reaping of child process groups and withholding output hashes if
live descendants remain. This bounded invented suite makes no native trial,
cohort, inversion acceptance, first-arrival or general convergence claim.
