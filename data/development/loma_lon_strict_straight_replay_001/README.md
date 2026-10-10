# Two-call stopping diagnostic

This copy evaluates pairs 8670 and 8674 from the reviewed D straight replay, with only the combined small-action/1e-5 gradient stopping alternative disabled. The existing strict 1e-7 projected-gradient condition remains. Grid, endpoints, null-seed straight initialization, spacing 0.03125 km, 1000-update cap, 24 Armijo trials, derivative formulas, metric, curvature handling and numerical accuracy gates are unchanged. Maintained production sources and live jobs are untouched.

Both rays use source 166, event `quakeml:NC.anss.org/Event/NC/10090456`, origin `quakeml:NC.anss.org/Origin/NC/2644764`. Pair 8670 uses `NC.JHL..EHZ` (`FDSN:NC_JHL__E_H_Z`, epoch 1989-10-19T20:40:00–1990-08-21T18:35:00); pair 8674 uses `NC.JRG..EHZ` (`FDSN:NC_JRG__E_H_Z`, epoch 1989-03-24T22:55:00–1990-08-07T20:50:00). Full native records, empty locations, initial coordinates and saved reference rows are frozen in `inputs/native_context.json`. Source.t is excluded from propagation time.

The existing reviewed D outputs are the comparison; no baseline or FMM call is repeated. Exactly two public `trace` calls save full final paths, source/model partials, statuses and update/merge counts. The driver has no history instrumentation. Termination is derived from the inspected loop: 1000 updates means the loop budget was exhausted; otherwise a true returned strict flag means the top-of-loop gradient check stopped it, and a false flag means the 24-trial line search failed. A post-return strict flag at the update cap is retained separately from loop termination. Any exception remains a failed execution, not a convergence result. If merging changes the node count, the unchanged algorithm has altered representation dimension and that limitation is reported.

`prepare.py` verifies the independently reviewed baseline and freezes the one-condition core diff. `run.py` preserves the previous reviewed process-group cleanup safeguards and requires a passed independent `prelaunch_review.json` bound to `prepared.json`. From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 prepare.py
PYTHONDONTWRITEBYTECODE=1 python3 run.py
```

These are exclusive commands; existing preparation or execution is never overwritten. The strict-copy flags are diagnostic results, not changes to the saved production flags. Unchanged limits are 25 microseconds in travel time and 3e-6 s/km in the Euclidean source-derivative error. Better accuracy would demonstrate stopping sensitivity for these calls; budget or line-search failure would leave the fully optimized fixed-representation error unresolved. Even strict convergence would not certify a global discrete or continuous first arrival. No new production stopping rule, full-cohort acceptance, path-spacing refinement or inverse calculation follows from this test.
