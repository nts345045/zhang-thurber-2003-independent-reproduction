# Comparison attempt checkpoint

At the 11 October 2026, 06:38 UTC checkpoint, the fixed-model comparison has
closed after all 18 scheduled updates. Its accepted geometry passed saved-output
review. The first standard attempt is closed after an execution interruption;
the separate standard replacement remains active. Scheduled completion and
accepted geometry do not establish nonlinear convergence.

| Mode | Numerical output directory | State |
| --- | --- | --- |
| Standard tomography, attempt 001 | `data/hayward_standard_guarded_001/` | Interrupted before the first inverse update; no final model |
| Standard tomography, attempt 002 | `data/hayward_standard_guarded_002/` | Replacement inversion active |
| Fixed-model DD relocation | `data/hayward_loc1d_guarded_001/` | Closed, return code 0; 18 verified accepted states |

The fixed-model attempt closed at 06:38:03 UTC with stable outputs. All six
executed command stages returned zero and were reaped. Its
[published result](../hayward_comparison_saved_outputs_001/loc1d_001/README.md)
preserves 18 joined history/trial/snapshot states, six per weighting stage,
and 12 rejected trials. Every accepted grid retains the initial velocities
exactly. The last accepted snapshot is `loc1d_accepted_it_17_*`;
`last_accepted_*` records an earlier checkpoint associated with a rejected
trial. Final convenience CSVs use lower text precision than the snapshots.
The result figure and source tables retain 1,092 event identities and 372
receiver epochs. Median and maximum source displacement are 2.849 and
8.397 km. History RMS and ray diagnostics are pre-update quantities; this
readback adds no final accuracy, covariance or convergence claim.

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
records the subsequent actual launches, closed interruption and completed
fixed-model attempt. Original
process logs and runtime records remain local. No accepted state, recovered
model or final diagnostics are claimed for the active comparisons before
their outputs close and are reviewed.
