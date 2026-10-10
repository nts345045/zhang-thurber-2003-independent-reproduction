# Alternative paths at the saved DD model

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_hayward_audit.py
```

This diagnostic compares the original trace with an FMM-seeded, continuously
bent candidate in the saved Hayward DD velocity model. It performs no inversion
and changes no model, event, observation, or metadata record. The selection is
all 186 absolute rays whose final DD source and receiver depths are both in
the top interval `[-1,0] km`, as preserved in
[`hayward_dd_top_layer_rays.csv`](../hayward_dd_top_layer_rays.csv).
It is a targeted set, not a representative sample of all rays.

The auxiliary spacing and continuous path spacing are both 0.5 km. Receiver
fields are shared only for exactly identical xyz positions; all native epoch
and channel associations remain distinct. The output retains every input
column verbatim, including both event/pick/arrival identities, SEED/FDSN codes,
native metadata epochs, source hashes, and the original observation index.
The runner checks these mappings against the saved event/station tables before
calculation, and verifies their preservation afterward.

Of 186 rays, two receive feasible candidate paths more than 1 ms faster than
the original paths. The largest reductions are 3.691561 and 2.238467 ms;
a third reduction is 0.072532 ms. A faster continuously integrated admissible
path establishes that the original path did not minimize the action in this
fixed model. It does not establish that the new path is the first arrival.
The first-order initializer still misses near-crossover branches in the
independent analytic experiment. Most of the other differences are much
smaller and require path-refinement checks before interpretation.

One FMM extraction fails explicitly with no descending step; its original
direct-seed candidate is retained and the failure flag is saved. All selected
paths stay inside the model domain. One selected ray misses the
existing local optimizer stopping rule. In 21 rows the original direct-path
endpoint arithmetic differs from the specified receiver by roundoff, with
maximum `3.56e-15 km`; these fail the strict exact-endpoint check and remain
recorded failures. The seeded entry point explicitly preserves its endpoints.
No numerical accuracy threshold is relaxed to convert those failures to passes.
The command therefore exits with status 1 after writing the complete results
and provenance summary.

`results.csv` stores all identified comparisons; `summary.json` reports the
counts, limitations, and input/source/binary/output hashes. No causal claim
about source displacement or overall inversion error follows from this
fixed-model comparison. The original full Hayward workflow remains an
independent record of the unmodified solver.
