# Native usable-curvature diagnostic D

The isolated replay completed with code zero on 2026-10-10 at 08:13:28 UTC. The durable controller reaped the wrapper. All five numerical tables are byte-identical to the reviewed positive-curvature diagnostic C: `results.csv`, `history.csv`, `paths.csv`, `path_gradient_checks.csv`, and `cone_metric.csv`. The unobserved and observed trace implementations also return identical full arrays for each start. No FMM field was rebuilt.

D adds the shared usable-curvature checks validated by 183 invented controls in each of the C/D builds. Admission requires finite component arrays, positive finite computed curvature, and a representable positive reciprocal. Direction construction checks the current path metric's computed pivots and the original two-loop arithmetic, including positive finite scaling. Unusable memory uses the existing cone fallback and clears memory; an unusable fallback still throws. D inherits C's long-double outer action accumulation returning double. The segment action/gradient formulas, raw saved Candidate, resampling, box, Armijo rule, stopping tests, and 1000-update budget remain unchanged.

The selected saved-FMM start retains all 145 curvature pairs and stops after 145 accepted updates at 6.5184200416919014 s. Its ordinary/projected gradient norm is 9.733534530359096e-6 s/km. This is the existing combined small-action-change/gradient stopping condition, not the stricter 1e-7 gradient condition. Its last accepted reported action change is 7.860379014346108e-13 s. The straight start stops after 54 updates and is 0.5055721663 microseconds later. Both reported local flags are true. The FMM result is 0.8606089059 microseconds later than the independent continuous 1D reference, with Euclidean source-derivative error 3.1776618948e-8 s/km; the existing 25-microsecond and 3e-6 s/km comparisons pass.

The native record remains observation 3426, event 65, receiver 46, NC.JSJ..EHZ. `identified_ray.csv` and every table sidecar retain all 199 context fields, including provider event/origin IDs, channel SEED/FDSN identifiers, valid empty location, and epochs. Original catalog geometry and the simulated perturbed geometry remain separately labeled. The saved pure travel time excludes the simulated origin-time correction.

This result establishes unchanged arithmetic on this finite trajectory. It does not certify an exact positive curvature sign: the invented cancellation example with exact dot -1/2 and computed dot +1/2 remains admitted. Nor does it prove informative curvature, general optimization convergence, global first-arrival completeness, or inversion readiness. No production source or live run was changed, and no convergence flag was relabeled.

`prepared.json` pins the reviewed source, inputs, settings and five C reference tables. `summary.json` pins the completed outputs, compiler, binary and runtime libraries; `execution.json` and `controller_completion.json` record process termination. The summary explicitly sets production adoption and scientific success to false. The README and subsequent independent saved-output review are separate explanatory records, added after the immutable summary.

The exact executed command was:

For historical replay from a fresh checkout, first restore the pinned terminal
evidence using the [inert sentinel archive](../terminal_lock_archive_001/README.md).
Use a new output directory for a new execution.

```sh
/usr/bin/python3 diagnostics/run_usable_curvature_native.py --phase run --output data/development/loma_usable_curvature_native_001
```
