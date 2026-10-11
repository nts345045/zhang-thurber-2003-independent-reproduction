# Comparison attempt checkpoint

At the 11 October 2026, 02:45 UTC checkpoint, the first standard attempt is
closed after an execution interruption. A separate standard replacement and
the fixed-model comparison have passed preparation and compilation and are
running their inversions. No completed scientific inverse result is claimed.

| Mode | Numerical output directory | State |
| --- | --- | --- |
| Standard tomography, attempt 001 | `data/hayward_standard_guarded_001/` | Interrupted before the first inverse update; no final model |
| Standard tomography, attempt 002 | `data/hayward_standard_guarded_002/` | Replacement inversion active |
| Fixed-model DD relocation | `data/hayward_loc1d_guarded_001/` | Inversion active |

The [closed standard-001 record](standard_001_outcome.json) preserves zero
inverse updates and null recovered-model/source outputs. The controller
recorded SIGTERM handling; the native child returned `-15`, and the enclosing
command exited `143`. The child was reaped and its outputs were stable. Its
history and matrix-census files, stdout and stderr were empty; no accepted-state
or final-model tables were written. Preparation and compilation had succeeded.
The evidence does not identify the signal's origin or establish a numerical
failure. The interruption remains preserved.

Standard attempt 002 began its native inversion at 02:45:01 UTC in fresh
output and build directories. It uses the same inputs, configuration and
numerical source as attempt 001. Its enclosing command uses a terminal
execution channel; that execution change does not identify or resolve the
cause of the earlier signal. It is a separate manually launched attempt,
with no automatic retry.

Each preparation reproduced the eight original scientific catalog files
exactly and the remaining selection-manifest fields except its declared
preparer hash. All three fresh builds produced executable SHA-256
`cc7504adfc875fe4a846ef43d0a9322ef04443acefa6cbddba5e3bd53141940d`,
matching the frozen accepted-state-export solver used by the combined DD
attempt. Each uses four OpenMP threads and a 128 GiB address-space limit.
The wrapper's source review verified both native mode branches, the original
catalog-only settings and the common initial reference support. It did not
establish updated-state accuracy or inverse convergence.

The source-preparation manifest and README remain unchanged. Their
not-executed status describes that earlier preparation checkpoint; this file
records the subsequent actual launches and the closed interruption. Original
process logs and runtime records remain local. No accepted state, recovered
model or final diagnostics are claimed for the active comparisons before
their outputs close and are reviewed.
