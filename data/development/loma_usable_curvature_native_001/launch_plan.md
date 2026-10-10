# Isolated usable-curvature replay D

Prepared only; native execution requires a separate hash-bound root launch review.

The replay uses the reviewed C raw saved Candidate, its complete metadata and the same 199-field native context for observation 3426 (event 65, receiver 46, NC.JSJ..EHZ). It constructs no FMM field. The unchanged driver runs straight and saved-FMM starts, with unobserved/observed full-array parity for each start. The native source differs from C only in the reviewed core/observed helper calls and the added usable-curvature helper. The inherited action accumulator is C's long-double outer sum returning double.

Path spacing 0.03125 km, recorded field spacing 0.125 km, 1000 updates, one OpenMP thread, the same GNU++17/O3/OpenMP compiler, resampling, gradient, box, Armijo acceptance and stopping are fixed. Time and Euclidean source-derivative comparisons retain 25 microseconds and 3e-6 s/km. No datum or grid changes are made.

The five expected C tables are results.csv, history.csv, paths.csv, path_gradient_checks.csv and cone_metric.csv. The runner records all five full-file byte comparisons and their conjunction native_C_neutrality_pass. Differences remain visible; a completed diagnostic is not automatically a neutrality, scientific-success, convergence or production-adoption claim. Each native output receives the full identified sidecar. Both results retain their actual flags/history even on a negative outcome.

Usable computed positive curvature is not an exact-sign or information certificate. Cancellation can yield a positive computed dot for a negative exact sum. The candidate rejects nonfinite or unrepresentable reciprocal/current-metric/two-loop quantities; unusable memory invokes the existing cone fallback and memory reset, and an unusable fallback preserves its existing exception. It does not relabel failure as convergence.

The existing exclusive execution lock, child-group termination/wait and withheld hashes with surviving children are retained. A durable controller will record/reap the wrapper. Frozen sources, original inputs, compiler, binary and runtime libraries remain hash-bound.

Authorized preparation command:

```sh
python3 diagnostics/run_usable_curvature_native.py --phase prepare --output data/development/loma_usable_curvature_native_001 --build tmp/loma_usable_curvature_native_001
```

Prospective command after root review:

```sh
python3 diagnostics/run_usable_curvature_native.py --phase run --output data/development/loma_usable_curvature_native_001
```
