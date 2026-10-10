# Saved-output review of the second tangent trial

`check_saved.py` is source only until root reports step 002 terminal, writes
its outer reaping receipt and approves this checker. It imports only standard
library modules. It does not call the native loader, numerical helpers, metric
solver, rounding executable or an action/tangent integrator.

`check_saved.patch` shows the adaptation of the completed first-step checker.
The new starting data are the first accepted rounded path and the reviewed raw
post-step components. Their complete native contexts, all nine catalog uses,
terminal receipts and independent reviews are bound to the second-step chain.

The checker resolves each first-trial edge reference directly against either
the original saved action cache or the first trial's new-edge records. It
checks the last-index convention for identical original ordered edges, every
reference's geometry, the complete action sum and exact unchanged-edge
cancellation. No starting action is reevaluated. Actual starting coordinates
are joined to decimal tokens, hexadecimal values and post-step provenance.
Raw components retain both incident-edge contributions; availability is
independently derived from exact geometry, with fixed endpoints omitted.

The existing checks remain for all emitted metric equations and energy,
midpoint RHS values, complete nominal and actual-displacement slope sums,
fixed endpoints/normals, box and half-edge feasibility, binary64 rounding,
full/paired action sums, new-edge inventory, conservative Armijo arithmetic,
statuses, identities, source/output hashes and all helper/outer reaping.
There are at most two metric solves, two rounded trials and 2058 new action
edges. Original false flags and null candidate convergence are preserved.

The final `source_review.json` must bind the approved checker SHA and native
summary, execution and outer receipt hashes. A single saved-only execution may
then write a fresh `review.json`, retaining full identities and exact rational
results. Until terminal approval, neither that receipt nor review is created.

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 data/development/hayward_cmj_tangent_step_review_002/check_saved.py
```

Saved algebra checks do not replace the reviewed primitive error bounds.
Sidecar creation order and historical process cleanup remain facts attested
by the frozen source and owned execution receipts; final files alone do not
prove their timing. No post-second-trial tangent norm is evaluated here, and
no stationarity, first-arrival or source/model derivative claim follows.
