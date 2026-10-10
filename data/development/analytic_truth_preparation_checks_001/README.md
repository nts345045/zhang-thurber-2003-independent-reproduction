# Analytic truth preparation checks

Ten checks passed for `prepare_loma_analytic_truth.py`. The positive fixture is
an invented, identified two-source/two-receiver constant-speed model. Rejection
checks cover unresolved or nonunique references, failed or stale independent
reviews, changed candidate bytes, and changed native geometry even when its
file hash is updated. The preserved real `loma_layered_full_001` reference,
which has eleven invalid distance closures, is rejected.

The helper only prepares inputs after a complete reference and two reviews
agree on the exact terminal artifacts. It copies all provider metadata and
the original reference certificates into a fresh bundle. It does not run the
simulator, accept the inverse forward operator, or revise earlier failed ray
diagnostics.

For an exported bundle, `analytic_truth_manifest.json` supplies the explicit
truth mode and timing definition. Its continuous first-arrival times replace
the local polygon-ray timing description in the retained generic
`preparation_manifest.json`; the generic manifest still documents geometry,
initial models, noise, and observation counts. This is a declared change of
the synthetic truth calculation, not a repair of the polygon-ray solver.

Reproduce the checks in a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_analytic_truth_preparation.py --output data/development/analytic_truth_preparation_checks_NEXT
```

`summary.json` records every check and seventeen frozen artifact hashes. No
real truth bundle or simulation was produced by these tests. The exporter's
reference, native join, and copy guards also received an independent source
review with no material issue found.
