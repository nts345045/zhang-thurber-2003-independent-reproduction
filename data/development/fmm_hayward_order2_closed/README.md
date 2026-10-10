# Controlled identified Hayward ray comparison

This diagnostic uses exactly the 186 identified absolute rays from the frozen
`fmm_hayward_audit` selection. Their saved DD-final sources and receivers both
have depths in [-1,0] km. All original observation columns, provider IDs, NSLC
and FDSN channel identifiers, native metadata epochs, source hashes, and source
and receiver coordinates are preserved in `results.csv` and
`historical_comparison.csv`. The input/model hashes are unchanged. This is a
saved-model forward calculation, with no inversion or production change.

The new run uses optional order 2 and closed-cell source seeding at auxiliary
spacing 0.5 km. Continuous bending remains the unchanged production optimizer,
with path spacing 0.5 km and at most 1,000 updates. Every ray retains the smaller
continuous action from its straight and FMM initial paths. The FMM field time
is diagnostic only. Recomputed straight-seed actions and convergence flags
match every historical row exactly.

| Quantity | Frozen first-order audit | Current comparison |
| --- | ---: | ---: |
| Identified rays | 186 | 186 |
| Extraction failures | 1 | 0 |
| Selected nonconverged rays | 1 | 1 |
| Strict endpoint check failures | 21 | 22 |
| Maximum endpoint discrepancy, km | 3.55e-15 | 3.55e-15 |
| Maximum action reduction from straight seed, ms | 3.69156 | 3.69162 |
| Rays with reduction greater than 1 ms | 2 | 2 |

There are no nonfinite modeled values, selected paths outside the domain, or
selection-induced action increases. The current selected action minus the
historical selected action ranges from -0.566 to +0.675 microseconds: 83 are
smaller, 16 equal, and 87 larger. Those counts use the saved numerical values;
they are not a new accuracy gate. The largest source-derivative change from
the straight-seed ray is 0.0228726 s/km, subject to stationarity and path-spacing
limitations.

The same nonconverged ray remains at event index 775 and station epoch index 184:
event `quakeml:NC.anss.org/Event/NC/403533`, origin
`quakeml:NC.anss.org/Origin/NC/3739369`, pick
`quakeml:NC.anss.org/Arrival/NC/42790539`, channel `NC.CMO..EHZ`, epoch
1993-10-15T19:23:00 through 1995-07-06T22:27:00. Its selected FMM-bent path reaches
1,000 updates with recorded projected gradient 4.09495e-6 s/km. All 22 strict
endpoint mismatches occur where the direct-seed action is selected; their small
magnitude is recorded without changing the exact endpoint gate. The runner
therefore exits nonzero with status `failed_checks_recorded`.

Relative to the historical audit, this comparison includes the separately
verified extraction fix and the changed stencil. The closed-cell source option
is enabled, but all 30 physical receiver groups retain eight seed vertices, so
it does not enlarge their source seed sets. The comparison does not isolate
one code change. A lower feasible action shows a prior path was not optimal;
small differences or agreement do not establish a global first arrival.
This selected shallow subset does not represent all field rays.

Rebuild in a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_hayward_audit.py --variant NEW_NAME --order 2 --closed-seed-cells
```

The runner refuses existing variant directories and validates the original
186-row mapping and frozen production/input hashes before running. It snapshots
all compilation sources, including the unchanged generated bending body, under
`tmp`, uses one OpenMP thread, and sets `TMPDIR` to repository `tmp`. Commands
and archive member paths are relative; Unix owner fields and archive timestamps
are zeroed. `summary.json` retains every failed row with full native metadata,
all source/input/result hashes, and the command. `review.json` provides the
bounded comparison aggregates. The historical audit remains unchanged.
