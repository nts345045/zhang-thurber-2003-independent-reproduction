# Optional refined receiver-field batching

All 83 checks passed. Twelve frozen-baseline/current groups produced byte-identical
travel-time, source finite-difference, native-identifier, and identified-error
artifacts at one and four threads. Current groups use the unchanged default,
explicit zero, and batch limits 1, 2, and 4. The geometry-only CLI also preserves
its distinct identifier schema and numerical outputs exactly.

`raycheck_receiver_batch B` limits only the refined cache to B distinct exact
receiver coordinates in contiguous sample blocks. Zero retains the previous
all-at-once behavior. The full production cache, sample order, native indices,
finite-difference support, path spacing, and FMM h/2 refinement are unchanged.
Completed ray values own their data before the next cache is cleared. Repeated
coordinates in later blocks are rebuilt. A later failure may retain earlier
partial diagnostic rows; it remains a terminal failure.

The invented fixture has 16 ordered samples, six native receivers at five
positions, noncontiguous repeats, blank location/open epoch fields, quoted
metadata, and source-domain boundaries. It retains all 20 valid derivative
components from the first eight samples. Diagnostic cache censuses verify each
limit; B=4 contains four receivers for the first 12 samples and three for the
last four. Invalid direct Config values and CLI tokens (including malformed
earlier duplicates) are rejected before input access; valid comments and integer
decimal values are accepted. No observational data are used.

`source/` retains exact baseline/current sources and both helpers. Only the
compiled diagnostic copies add one stderr cache-count statement after the
unchanged refined trace; the complete patches and compiled hashes are saved.
The production code contains no such instrumentation. `summary.json` pins the
baseline commit, binaries, source, commands, and all 291 generated artifact
hashes. The original frozen Hayward004 and Loma simulation binaries were not
changed or rerun.

Small-fixture maximum resident sizes were 5,300–7,072 KiB, recorded by
`/usr/bin/time -v`. These are not Loma memory measurements or a guarantee that a
real run fits 128 GiB. Batching does not establish continuous first-arrival
accuracy or inversion convergence.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_raycheck_batching.py --output data/development/raycheck_batching_NEW --build tmp/raycheck_batching_NEW
```
