# Original cut inventory result

The reviewed saved-only inventory completed with exit 0 and was reaped. All consumed inputs and closed outputs were rehashed; see [summary.json](summary.json) and [execution_receipt.json](execution_receipt.json).

Root's [independent saved readback](review.json) also passed, with its [reaped execution receipt](review_execution.json). It rechecked the complete crossing roster, scalar cut decisions, retained parameter comparisons, native identities and input/output closure without invoking an evaluator.

| Original event / receiver | Edges | Exact open-segment plane crossings | Core cut insertions | Omitted / spurious cuts | Short-edge skips / duplicate cuts |
| --- | ---: | ---: | ---: | ---: | ---: |
| 981 / 160 | 1,028 | 30 | 30 | 0 / 0 | 0 / 0 |
| 987 / 160 | 1,030 | 30 | 30 | 0 / 0 | 0 / 0 |

These are the original **old-kernel** failed polygons, not the prescribed exact-face candidates, D paths or later tangent iterates. Event 981 is `quakeml:NC.anss.org/Event/NC/518943`, origin `quakeml:NC.anss.org/Origin/NC/4251144`; event 987 is `quakeml:NC.anss.org/Event/NC/519264`, origin `quakeml:NC.anss.org/Origin/NC/4252064`. Receiver 160 is `NC.CMJ..EHZ` / `FDSN:NC_CMJ__E_H_Z`, with empty location and epoch `1996-11-12T23:45:00` to `1998-06-09T19:30:00`. [native_contexts.json](native_contexts.json) retains complete source/receiver metadata and all 18 catalog uses, including their pick/arrival IDs and both receiver epochs. Both original convergence flags remain false and source partials remain unevaluated.

The existing length, displacement and endpoint-parameter cutoffs therefore omit no crossed plane in these two saved polygons. Retained cut parameters still undergo binary64 rounding, which is recorded per edge. This scalar source-predicate replay does not establish quadrature accuracy, rounded sample-cell selection, ordinary-gradient accuracy, or the behavior of other off-face trials. It invokes no compiled evaluator or integration and changes no path or running job.
