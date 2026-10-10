# Parallel receiver-field preparation

Receiver fields were constructed serially before parallel ray bending. The revised cache gathers exact missing receiver coordinates in request order, then constructs independent fields with the existing OpenMP thread setting. Each constructor reads the same immutable model and writes its own temporary slot. Cache lookup, invalidation and publication remain serial. The ray action, FMM equations, quadrature, path optimization, selection rules and stopping criteria are unchanged.

Native station indices remain separate. Coincident receiver coordinates can share a field; event/station/observation records and output order remain unchanged. Model axes, every velocity value and field spacing still require exact equality for reuse. Constructor exceptions are captured inside workers and rethrown in first-request order with the original native source/receiver context. No new field is published if a constructor fails. Existing cache entries survive a same-model failure; a model/spacing change invalidates them before construction. This atomic-publication statement does not claim recovery from an allocation failure while publishing the final map entries.

The same preparation is applied to the sampled `raycheck` production and refinement caches. Those two cache preparations run sequentially, each internally parallel. The existing path and FMM half-spacing refinement and ordered derivative/identifier output are retained.

## Controlled comparison

The runner freezes the old serial source from preflight 003 and the revised source, then compiles both with identical GCC C++17/O3/OpenMP options. It requires the core, FMM, metric, CSV and ray-check headers to match the frozen numerical dependencies exactly. In diagnostic copies only, one `public:` access declaration exposes raw field state for reading; both access diffs and exact compiled-source hashes are saved. This does not change numerical statements.

All four executions passed:

| Preparation | Threads | Component controls passed |
| --- | ---: | ---: |
| Frozen serial | 1 | 22/22 |
| Frozen serial | 4 | 22/22 |
| Parallel | 1 | 29/29 |
| Parallel | 4 | 29/29 |

Eight artifact groups are byte-identical across all four executions: the raw field/candidate/ray snapshots, identified exception text, three actual `raycheck` CSVs and three actual absolute-linearization CSVs. Snapshots serialize explicit values and vectors, not object padding or addresses. They include field axes, spacing, shape, every time/parent entry, counters, complete candidates, and all reported ray fields, paths, source/model derivatives and length weights.

The invented geometry exercises duplicate coordinates with separate native records; adjacent representable coordinates; reordered cache hits; changes to model velocity, a single representable velocity increment, an interior model axis and field spacing; sparse native output indexing; ordered worker errors; no publication after constructor failure; nonfinite-coordinate rejection; changed-model invalidation on failure; and successful reuse after failure. Actual `raycheck` and linearization functions produce the compared CSVs, including the unchanged refined spacing and native mapping. There are no observational records in this fixture.

This is an implementation consistency test, not a first-arrival accuracy certificate or a whole-field performance benchmark. On this small fixture, parallel overhead exceeds construction savings (about 0.9 s versus 0.7 s); no measured production speedup is claimed. Compiler output retains two misleading-indentation warnings in the fixture's explicit file-closing lines; production syntax checking succeeded. The complete output and every warning are preserved.

## Files and replay

`summary.json` records commands, return codes, timings, exact source/binary hashes and the eight parity hashes. `source/` contains unmodified serial/parallel source snapshots and the executed runner. `*_field_access.diff` gives the diagnostic-only access change. `resource_estimate.json` records prospective Hayward field storage; it is separate from fixture timing.

`frozen_outputs.tar.gz` losslessly contains all four fixture directories and compiler/execution output. `packaging.json` records each member's exact hash, verified by reading the archive back. Expanded copies remain local and ignored. Extract in this directory to inspect raw snapshots and CSVs:

```sh
tar -xzf frozen_outputs.tar.gz
```

To repeat the comparison from the integration repository, choose a fresh output variant:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_parallel_field_checks.py --variant NEW_VARIANT
```

The runner requires the preserved preflight-003 source manifest and refuses to overwrite prior evidence. No production inversion or full-support forward run was used in these checks.
