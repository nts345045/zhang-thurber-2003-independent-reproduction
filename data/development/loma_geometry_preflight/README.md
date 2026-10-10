# Loma geometry preflight

[Run 001](001/README.md) completed all 104 declared nearest/farthest rays from
the unchanged authoritative 724-event/52-receiver geometry. The scientific
review rejects the present settings for simulation: each spacing has 31 local
failures, and explicit faster candidates disprove first-arrival identification
for three locally converged production paths. No observations or inversion
were generated.

The [terminal guide comparison](all_guides_002/README.md) retains all 104 ray
identities, including candidate-inapplicability reasons. It evaluates one
bounded analytic family and makes no global first-arrival claim. The earlier
[65-row capture](all_guides_001/README.md) and run 001's 20-row snapshot are
preserved as partial evidence.

The [row-5 diagnosis](row005_audit001/README.md) preserves exact production
parity, iteration histories, paths and independent exact-action checks. It
shows underoptimization and branch dependence, with accurate integration on
those retained paths. The separate
[interface counterexample](../interface_stationarity/README.md) concerns an
exactly aligned invented path; it is not the demonstrated cause of the actual
row-5 failure. The [explicit row-5 guide](row005_guide_reference/README.md) and
[restricted straightening experiment](row005_straighten001/README.md) provide
additional bounded comparisons.

The launcher `diagnostics/run_loma_geometry_preflight.py` freezes committed
source, prepared input and binary hashes in a fresh directory. It retains
native metadata and checks every output association before reporting completion.
Completion and scientific acceptance are separate. The maintained launcher
requires an explicit source commit and a fresh variant:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_loma_geometry_preflight.py \
  --commit REVIEWED_COMMIT --variant NEW_VARIANT
```

The process uses four configured threads and a 128 GiB address-space limit.
It does not launch simulation automatically or alter the complete cohort/pair
selection. Frozen run 001 remains tied to its original source and settings.
