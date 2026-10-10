# Fixed 4000-update cap comparison

This final bounded comparison makes two null-seed straight calls for pairs 8670 and 8674 using the independently reviewed strict-1000 source byte-for-byte. Only the update cap changes from 1000 to 4000. The driver validates that changed setting; spacing 0.03125 km, strict 1e-7 projected-gradient stop, disabled combined early stop, Armijo budget 24, grid, endpoints, derivative formulas, helper and accuracy limits remain unchanged. Existing D and strict-1000 outputs are reused without repeating those calls. There is no adaptive escalation beyond 4000, receiver-field construction, history instrumentation, full-cohort calculation or production edit.

Both rays use source 166, event `quakeml:NC.anss.org/Event/NC/10090456`, origin `quakeml:NC.anss.org/Origin/NC/2644764`. Pair 8670 uses `NC.JHL..EHZ` (`FDSN:NC_JHL__E_H_Z`, epoch 1989-10-19T20:40:00–1990-08-21T18:35:00); pair 8674 uses `NC.JRG..EHZ` (`FDSN:NC_JRG__E_H_Z`, epoch 1989-03-24T22:55:00–1990-08-07T20:50:00). Full native fields, empty locations and initial coordinates are preserved in `inputs/native_context.json` and every path/model-partial row. Source time is excluded from propagation time; original FMM information is saved metadata only.

Preparation requires the passed strict-1000 terminal review and checks the exact source/config/driver differences, original inputs, compiler/runtime, and unchanged process-group cleanup functions. The exclusive runner then requires a passed independent `prelaunch_review.json` bound to `prepared.json`. From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 prepare.py
PYTHONDONTWRITEBYTECODE=1 python3 run.py
```

Existing preparation and execution files are never overwritten. Final paths, source/model partials, flags, update/merge counts and comparisons with both prior runs are saved. A count of 4000 means the loop budget was exhausted, with the post-return strict flag retained separately; earlier true/false flags distinguish the inspected strict-check and failed-search exits. These labels are derived from unchanged control flow, not from an instrumented history. Exceptions remain failed executions. Any merge or node-count change is reported rather than suppressed.

The limits remain 25 microseconds for travel time and 3e-6 s/km for the Euclidean source-derivative error. Both strict-1000 flags were false; pair 8670's source error improved while the control's worsened. The 4000 results can expose further cap sensitivity or meet the existing strict criterion, but cannot certify a global first arrival, a fully optimized polygon when the flag remains false, or a production stopping policy. Computation completion, local convergence and continuous-reference accuracy remain separate outcomes.
