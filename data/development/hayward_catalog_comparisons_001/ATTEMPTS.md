# Comparison attempt checkpoint

Both documented commands passed preparation and compilation and started their
native inversions on 11 October 2026. Neither has a completed numerical outcome
at this checkpoint.

| Mode | Numerical output directory | State |
| --- | --- | --- |
| Standard tomography | `data/hayward_standard_guarded_001/` | Inversion active |
| Fixed-model DD relocation | `data/hayward_loc1d_guarded_001/` | Inversion active |

Each preparation reproduced the eight original scientific catalog files
exactly and the remaining selection-manifest fields except its declared
preparer hash. Both fresh builds produced executable SHA-256
`cc7504adfc875fe4a846ef43d0a9322ef04443acefa6cbddba5e3bd53141940d`,
matching the frozen accepted-state-export solver used by the combined DD
attempt. Each uses four OpenMP threads and a 128 GiB address-space limit.
The wrapper's source review verified both native mode branches, the original
catalog-only settings and the common initial reference support. It did not
establish updated-state accuracy or inverse convergence.

The source-preparation manifest and README remain unchanged. Their
not-executed status describes that earlier preparation checkpoint; this file
records the subsequent actual launches. Original process logs and runtime
records remain local. No accepted state, recovered model or final diagnostics
are claimed before the attempts finish and their saved outputs are reviewed.
