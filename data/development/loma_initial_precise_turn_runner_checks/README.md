# Reviewed turning-speed runner controls

`001` passes 48 invented wrapper checks. It reuses the original initial-reference wrapper controls with a separate runner selecting the reviewed rational turning-speed module. The added controls reject changed numerical source/review/check evidence, check exact frozen selection, and compare homogeneous native tables/certificates byte for byte with the original wrapper. One- and two-worker outputs agree byte for byte. No actual LON reference is computed by these controls.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_initial_precise_turn_reference.py --output data/development/loma_initial_precise_turn_runner_checks/NEW_VARIANT
```

`001/source` retains the executed runner, check, selected numerical module, and unchanged original runner/module. `001/summary.json` pins their hashes and lists each assertion. `001/provenance.json` pins every saved fixture, log, source and result. The separate numerical evidence and independent review are frozen in each completed invented run's `inputs/numerical_{checks,review}.json`. Native metadata is invented and explicitly labeled.

This is an integration/provenance test, separate from the 135 component checks and unchanged 250- and 106-check numerical suites in `../precise_turn_reference_checks/003`. Full native LON validity, branch and time changes must be examined after a fresh complete run.
