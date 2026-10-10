# Full Hayward004 initial-support comparison

All 14,262 initial rays pass the unchanged continuous-reference controls:
absolute travel-time error ≤25 microseconds and source-gradient Euclidean
error ≤3×10^-6 s/km. Every saved local flag and initializer-success flag is
true. The frozen run uses path spacing 0.03125 km and FMM spacing 0.125 km,
four threads, and the unchanged 1,000-update ray budget. This completed
comparison does not assess the separately running sampled refinement or
authorize an inversion by itself.

| Quantity | Median | Maximum |
|---|---:|---:|
| Absolute time error (microseconds) | 0.333103 | 0.958511 |
| Source-gradient Euclidean error (s/km) | 2.42170×10^-8 | 1.78163×10^-6 |

All references have complete, valid branch enumeration and a unique selected
arrival: 9,069 direct and 5,193 turning branches, with no near ties. The selected
numerical candidate came from FMM in 14,261 cases and the direct seed in one.
The largest source-vector error is original observation row 10753, event index
851, native receiver epoch index 61 (`NC.CCY..EHZ`), event resource ID
`quakeml:NC.anss.org/Event/NC/30069851`. Complete event/origin/pick/arrival/channel
identities and native metadata remain in every original row.

The earlier coarser Hayward003 comparison passed both controls for 603 of the
same 14,262 rays. Those original failures remain preserved. This later initial
model result does not establish first-arrival accuracy for subsequent updated
three-dimensional velocity models, or nonlinear inversion convergence.

## Reference reuse and evidence

The command in `summary.json` ran only after initial_linearize exited with
code 0 and its execution ledger advanced to initial_raycheck. It freezes that
completed stage independently of the remaining sampled preflight. The ledger
is retained exactly as captured; it must not be interpreted as an overall
preflight-success record.

The helper reused the independently enumerated Hayward003 references only after
verifying byte-identical initial events, native stations, initial velocity
grid, observations, mathematical module and immutable reference cache. It
then rechecked all row/event/receiver joins and every captured hash. The
comparison took 9.66 seconds including its final table work; it did not rerun
the numerical rays or repeat the unchanged branch enumeration. Interval
calculations certify branch enumeration where marked complete; minimum-time
ordering uses floating-point actions and explicit near-tie handling. This is a
reference for the saved monotone, horizontally uniform initial profile.

`summary.json` retains the executed command, versions, exact source/input/output
hashes, reference-cache hashes, flags, component statistics and separate vector
acceptance counts. The source criterion is the Euclidean norm of three
derivative errors; individual component statistics are descriptive. `source/`
retains both executed Python files. The companion independent review checks
the saved native/source-column joins and numerical subtraction without rerunning
the reference mathematics.

## Lossless archive

`frozen_tables.tar.gz` contains `comparison.csv`, `references.jsonl` and every
file under `inputs/`: full observations and native metadata, original numerical
tables, run manifest, captured ledger and source archive. `packaging.json`
records each member's original byte count/hash and the verified archive hash.
Every member was read back. Only tar/gzip administrative metadata is normalized;
CSV formatting, numerical precision and identifiers are unchanged.

The expanded tables remain local and are ignored. Restore them from this
directory with:

```sh
tar -xzf frozen_tables.tar.gz
```

Restoration runs no ray solver, provider query or inversion. Sampled refinement
and any later inverse run require their own terminal evidence.
