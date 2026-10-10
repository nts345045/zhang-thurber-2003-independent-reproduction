# FMM field and extraction checks

The root `results.csv` and `summary.json` preserve the first-order component
baseline from commit `88b60b5`. Subsequent checks use distinct variant folders
so that failed evidence is retained. To run the current generic field fixture,
choose a new folder name:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/fmm_field_checks/run_checks.py --variant new_field_check --suite full
PYTHONDONTWRITEBYTECODE=1 python3 data/development/fmm_field_checks/run_checks.py --variant new_corner_check --suite closed-cell
```

The `closed_cell_before` and `closed_cell_after` folders isolate a geometric
extraction defect: seven of eight reflected seed-corner cases failed when
upper faces of the receiver cell were excluded. All eight pass after using
the closed cell, with unchanged auxiliary field times. The full fixture still
passes 39 paths, 18 invalid-source cases, and eight invalid-field cases in
`closed_cell_full`.

`closed_cell_hayward` separately verifies the one identified extraction failure
from the original 186-ray DD audit. Its input and output preserve all native
event/pick/channel/epoch fields. Rebuild that check with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_fmm_failed_extraction.py
```

These checks establish extraction behavior, not completeness of first-arrival
branch selection. The analytic crossover failures remain recorded in the
separate initialization audits. No production inversion uses this prototype.
