# Observed LOM initial local-stopping failure

This observation-only replay retains the frozen LOM initial model, source,
receiver, FMM/path spacing, 1,000-update budget and original C++ arithmetic.
Pair 3426 is event `quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, channel `NC.JSJ..EHZ`
(`FDSN:NC_JSJ__E_H_Z`), epoch `1989-05-02T15:00:00` to
`1990-09-14T21:50:00`. `identified_ray.csv` preserves its full native context
and current perturbed coordinates; original catalog geometry is retained
separately. CSV identity sidecars bind all saved paths and histories.

The selected FMM-seeded path has time 6.5184200416993878 s, 1,134 knots and
projected gradient norm 1.3761776565981102e−5 s/km. It stops after 53 accepted
updates when all 24 line-search evaluations fail, retaining its false local
flag. It does not exhaust the iteration budget. The last recorded
directional slope is −6.7631181427496004e−15 s and the final reported trial
movement is 1.438338018e−16 km. These values motivate an arithmetic and
direction investigation but do not alone establish a roundoff cause.
The largest gradient is at knot 484, depth 7.0000000950529291 km; the
continuous reference turns at 7.000000434350282 km, near the 7 km velocity
gradient break. The reference time and source-derivative accuracy tests pass.
Accuracy agreement does not replace the failed stopping condition.

The direct seed terminates with a true local flag after 54 updates at
6.5184205472639345 s, about 0.506 microseconds later. The replay does not swap
branches or promote the selected ray's flag. For both seeds the frozen
observer driver records exact equality of observed and unobserved path,
action, derivative arrays, gradients and status. The independent saved-record
review and its precise evidence limits are documented in
`../loma_initial_failure_review_001/README.md`.

Recorded helper, with fresh output/build paths required for another run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/observe_loma_initial_failure.py \
  --comparison data/development/loma_lom_initial_accuracy_001 \
  --pair 3426 --output data/development/loma_initial_failure_3426_FRESH \
  --build tmp/loma_initial_failure/3426_FRESH
```

The complete frozen source, observation-only diffs, commands, input hashes,
full paths, node gradients, histories and review remain saved. No inverse
calculation or production change is part of this diagnostic.
