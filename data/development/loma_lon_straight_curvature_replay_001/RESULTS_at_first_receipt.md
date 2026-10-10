# Four-call result

The old-source replay exactly reproduced all 100 compared status, physical and native fields per ray at the original 12-significant-digit serialization. The eight excluded initializer fields remain saved original FMM metadata; neither replay constructed a receiver field.

The adopted D package produced byte-identical final path and model-partial tables, and byte-identical 12-digit scalar tables. At 17 digits, only travel-time totals differ: +4.4408920985e-16 s for pair 8670 and -8.8817841970e-16 s for pair 8674. Source derivatives, projected/raw gradients, update counts, node counts and local flags are unchanged.

| Pair and receiver | Updates, both variants | Local flag | Projected gradient (s/km) | Time error (microseconds) | Source vector error (s/km) |
|---|---:|---:|---:|---:|---:|
| 8670, NC.JHL..EHZ | 178 | 1 | 4.489354626e-6 | 1.523071245 | 4.807060122e-6 |
| 8674, NC.JRG..EHZ | 207 | 1 | 9.223983065e-6 | 1.437047202 | 1.059976299e-6 |

Both rays use source 166, event `quakeml:NC.anss.org/Event/NC/10090456`, origin `quakeml:NC.anss.org/Origin/NC/2644764`. Receiver FDSN identifiers are `FDSN:NC_JHL__E_H_Z` and `FDSN:NC_JRG__E_H_Z`, with epochs 1989-10-19T20:40:00–1990-08-21T18:35:00 and 1989-03-24T22:55:00–1990-08-07T20:50:00 respectively. Full native context, including valid empty locations, is retained in every path/kernel row and the selected input records.

The failing ray remains above the unchanged 3e-6 s/km Euclidean source-derivative limit. The matched control remains below it. Both time errors remain below 25 microseconds. Neither ray satisfies the strict 1e-7 projected-gradient test; the preserved true flags therefore arise from the unchanged combined stopping condition. No iteration history was captured, so this result does not establish equality of intermediate directions, curvature memory or accepted steps.

This is negative evidence for D alone as a remedy for this identified interior failure. It does not identify whether residual optimization, finite path representation or interface geometry causes the derivative error, and it does not extend the two-ray result to all 37 failures. D changes accumulation and usable-curvature handling together. No FMM branch selection, source/time correction, reference, tolerance or production source was changed.

`summary.json` and `execution.json` are the immutable numerical terminal records. `comparison.json`, produced by `read_results.py`, checks complete saved tables without new action evaluations. The wrapper's four child commands all returned 0; the driver exec handle also returned 0. Compiler and native stderr logs are empty. The old calls took about 1.43 seconds together and D about 1.45 seconds; these tiny timings are not a performance benchmark. See `controller_completion.json` for the actual return-code observation and terminal process-group readback.

`REPLAY.md` explains fresh-checkout reproduction, including the single historical inert flags file. Earlier preparation versions are preserved, superseded and unexecuted; the executed version is `prepared_v3.json` with `run_v3.py`. No Git operation, live-input mutation, extra native ray call or numerical history instrument was used.
