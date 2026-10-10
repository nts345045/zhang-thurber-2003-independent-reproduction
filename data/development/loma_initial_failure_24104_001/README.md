# Observed LOM initial boundary-source failure

Pair 24104 has the largest source-derivative error in the full LOM initial
comparison. It is event `quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`
(`FDSN:NC_HQR__E_H_Z`), epoch `1989-07-11T19:55:00` to
`1990-03-24T19:55:00`. Its complete metadata and current perturbed coordinates
are attached to `identified_ray.csv` and the saved CSV sidecars. Original
catalog coordinate fields remain separately preserved.

The selected FMM-seeded polygon has 2,528 knots, time 13.315128114663265 s
and projected gradient norm 8.2369646098967681e−7 s/km. It retains its true
local flag after 33 accepted updates. Its vertical source derivative is
−1.5850655663167801e−5 s/km; the independent continuous finite-bottom
reference has zero vertical derivative. Thus successful local stopping does
not establish source-derivative accuracy. The source and leading segment lie
at the 16 km bottom face; 394 path knots are bottom-active.

The direct-seeded polygon terminates after 391 updates at
13.315128319709917 s, also with a true local flag. The observation-only replay
retains the frozen model, compiler, FMM/path spacing and 1,000-update budget.
For both seeds its driver records exact equality of observed and unobserved
path, action, derivative arrays, gradients and status. The independent
saved-record review and evidence limits are documented in
`../loma_initial_failure_review_001/README.md`.

Recorded helper, with fresh output/build paths required for another run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/observe_loma_initial_failure.py \
  --comparison data/development/loma_lom_initial_accuracy_001 \
  --pair 24104 --output data/development/loma_initial_failure_24104_FRESH \
  --build tmp/loma_initial_failure/24104_FRESH
```

The [separate leading-segment calculation](../loma_boundary_endpoint_001/README.md)
evaluates subdivision and the tied-knot chain rule without a new ray solve.
It leaves both the successful local flag and failed source-accuracy result
unchanged. No production correction is included.
