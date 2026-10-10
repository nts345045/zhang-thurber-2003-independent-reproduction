# Seed-loaded baseline B neutrality

The native replay completed with code 0 on 2026-10-10 at 07:32:39 UTC. The
controller reaped the wrapper. Compilation took 31 seconds; the two-start native
observer ran from 07:32:14 to 07:32:39. It loaded the complete raw FMM Candidate
from the reviewed neutral capture instead of reconstructing its receiver field.
The captured field spacing remains a provenance declaration, not a new field
calculation.

All five original B numerical tables are byte-identical: `results.csv`,
`history.csv`, `paths.csv`, `path_gradient_checks.csv`, and `cone_metric.csv`.
The original core, observed optimizer, resampling, gradients, action, retention
rule, line search, stopping conditions, one-thread execution and 1,000-update
budget are unchanged. The sole driver change and added parser are preserved in
`seed_loader_driver.diff` and the frozen source. The loader restores path,
field time, success, message, descent count and fallback count; it also validates
the saved post-resampling frame structurally. Actual resampling still occurs in
the unchanged optimizer, and the complete output parity establishes neutrality
for this native case.

The straight-seeded ray retains 54 updates and convergence flag 1. The FMM-seeded
ray retains 1,000 updates, 40 retained curvature pairs, flag 0, time
6.5184200416971239 s and projected gradient 4.720002826341664e-5 s/km. Its initial
profile reference errors remain 0.860614 microseconds and 1.411747e-7 s/km in
source-vector norm. Passing those accuracy limits does not change the failed
local flag or make this ray eligible for inversion.

This is simulation pair 3426: event
`quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, receiver `NC.JSJ..EHZ`
(`FDSN:NC_JSJ__E_H_Z`, epoch 1989-05-02T15:00:00 through
1990-09-14T21:50:00). The complete context and the distinction between catalog
and perturbed source coordinates are retained in `identified_ray.csv`, the
input seed sidecars and every output table's sidecar.

`review.json` independently verifies all 598 original pins, 50 prepared files,
20 frozen source files, 72 outputs, controller/compiler/runtime records, seed
identities and five-table parity. Its reproducible readback is in
`../loma_seed_loaded_b_review_001/`. The separate positive-curvature experiment
requires its own preparation and launch review. This neutrality result changes
no production source, original output, convergence flag or live numerical job.
