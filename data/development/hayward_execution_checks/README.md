# Hayward preflight execution records

Attempt `first_arrival_002` lost its Python driver. The original tool session
reported terminal status 143 with empty output. Its linearization child was
subsequently observed running with parent PID 1, then absent with no exported
linearization tables and empty stdout/stderr. The child exit status and the
cause of termination are unknown. This is an interrupted attempt, not evidence
of a numerical ray failure. The copied interruption record and original manifest
preserve these distinctions. All 13 frozen files and nine source members matched
the manifest when the interruption was recorded; no frozen file was changed.

The maintained controller now reserves an exclusive execution record before
starting preflight commands. It atomically saves each stage, command, child PID,
and actual child return code. Python exceptions and SIGTERM/SIGINT record the
driver failure or interruption. An unknown child exit status remains null.
A successful child command does not mark the complete preflight successful.
The original native-identity, finite-value, coverage, and convergence validator
is unchanged. Existing output/build directories still reject another preflight.

The invented checks exercise configure failure with exit code 7, rejection of
an existing variant without changing its record, a driver-only SIGTERM with a
known surviving test child, and successful command recording. The test child is
explicitly identified and cleaned up. The exact validation AST equals the
frozen prior runner. No real solver or preflight was run in these checks.

`source_snapshot.tar.gz` freezes the maintained runner, the previous runner,
and the exact test script. Tar and gzip metadata are normalized; commands and
hashes are in `checks.json`. The local test ran from the integration worktree,
with its temporary fixture under `tmp/hayward_execution_checks` and the prior
runner available in the preserved attempt 002 source snapshot.

A fresh real attempt must use a separate variant. Launch its controller with
`subprocess.Popen(..., start_new_session=True, stdin=subprocess.DEVNULL)` and
explicit driver stdout/stderr files outside the variant's reserved output and
build directories. Record its PID immediately. Signal-resistant process
separation is not a completion guarantee: SIGKILL cannot be trapped, and absent
processes or stale records must still be investigated before another attempt.
