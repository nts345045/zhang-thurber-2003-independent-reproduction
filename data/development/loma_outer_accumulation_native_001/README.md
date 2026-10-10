# One-change outer-accumulator replay

Changing only the `path_eval` total from `double` to `long double` did not
resolve convergence of the selected FMM-start path. The modified run avoided
the original early line-search termination, then exhausted all 1,000 updates.
The public action return remains `double`; segment calculations, derivatives,
seeds, resampling, Armijo condition, stopping rules, and update budget are
unchanged. The complete change is in `inputs/single_change.diff`.

This is native initial pair 3426: event
`quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, receiver `NC.JSJ..EHZ`
(`FDSN:NC_JSJ__E_H_Z`, epoch 1989-05-02T15:00:00 through
1990-09-14T21:50:00). `identified_ray.csv` and every numerical-table sidecar
retain the complete native metadata and actual perturbed initial geometry.

## Recorded outcomes

A is the already reviewed original observer and its neutral replay. B is this
new run. Both use path spacing 0.03125 km, FMM spacing 0.125 km, the original
two starts, the original compiler/flags, and one OpenMP thread.

| Variant and start | Updates | Local flag | Termination | Final projected-gradient norm (s/km) |
| --- | ---: | ---: | --- | ---: |
| A, straight | 54 | 1 | Combined action-change and gradient condition | 8.58810e-6 |
| B, straight | 54 | 1 | Combined action-change and gradient condition | 9.68343e-6 |
| A, FMM | 53 | 0 | Line search exhausted 24 trials | 1.37618e-5 |
| B, FMM | 1,000 | 0 | Update budget exhausted | 4.72000e-5 |

The minimum-action B result is the FMM start, with time
6.5184200416971239 s. Its continuous-reference time error is 0.860614 microseconds
and its source-derivative error norm is 1.41175e-7 s/km. The straight start has
time error 1.366181 microseconds and source-derivative error norm 4.67852e-8 s/km.
Both pass the existing 25-microsecond and 3e-6 s/km limits. The FMM local flag
remains false. These accuracy checks do not make this path or an inversion
acceptable under the unchanged forward gate.

The FMM history contains 436 strictly decreasing and 564 unchanged recorded
binary64 actions, with no accepted increase. Forty curvature pairs were
retained; the last was at iteration 434, update 435. Memory contains eight
pairs through termination. A retained 34 pairs, last at iteration 33, update
34, and recorded 48 decreases and five equal actions. These counts do not
establish whether rejected curvature pairs were informative.

Initial action totals already differ between A and B. Excluding only action
and action-change columns, saved scalar histories first differ at FMM
iteration 48: A accepts step 2^-19 after 20 trials; B accepts step 1 after one
trial. The corresponding first difference for the straight start is iteration
43. These are comparisons of saved scalar histories; complete intermediate
paths were not exported. B therefore follows a different trajectory before
the original failed iteration 53.

## Evidence and scope

`summary.json` and `execution.json` record terminal executable return code 0,
all results, source/input/compiler/binary/library hashes, commands, and the
original A results separately. `review.json` independently reconstructs the
native joins, history counts, termination conditions, path gradient norms and
reference errors. Its reproducible checker is in
`../loma_outer_accumulation_review_001`. No additional ray was run by that review.

Both B starts pass the original in-process observed/unobserved comparison of
path, time, derivatives, model arrays, and optimizer state. That comparison
uses exact numerical equality; it does not distinguish signed-zero bit
patterns. The JSON field `original_local_convergence_flag` records B's
unmodified reported flag. Original A flags remain under `original_results`.

`launch.json` records the detached driver. `controller_completion.json` pins
the saved logs and terminal native ledger, preserving the distinction between
the observed executable exit codes and the unreaped detached driver's unknown
exit code. The run started at 06:31:33 UTC and completed at 06:37:24 UTC on
2026-10-10.

Preparation and execution used:

```sh
python3 diagnostics/run_outer_accumulation.py --phase prepare \
  --controls data/development/loma_outer_accumulation_001 \
  --reference data/development/loma_lom_initial_accuracy_001 \
  --output data/development/loma_outer_accumulation_native_001 \
  --build tmp/loma_outer_accumulation_native_001
python3 diagnostics/run_outer_accumulation.py --phase run \
  --output data/development/loma_outer_accumulation_native_001
```

The execution phase requires the immutable hash-bound `prelaunch_review.json`.
A repeat requires fresh directories. This diagnostic changes no production
source, live input, threshold, convergence flag, or inversion acceptance.
