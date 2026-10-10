# Closed receiver-cell extraction regression

The invented homogeneous cube has velocity 4 km/s, auxiliary spacing 1 km,
receiver coordinates chosen from 0.49/0.51 km, and the closest seed corner at
0/1 km along each axis. Each of eight reflected source-to-receiver segments
lies in the closed seed cell and has exact action sqrt(3)*0.49/4 seconds.

The original half-open cell lookup fails seven reflected cases: its closest
seed corner lies on an upper face and is more than h/2 from the receiver. That
corner is an auxiliary-field minimum with no strictly descending neighbor.
The fix includes the upper faces when deciding to connect the exact receiver.
All eight cases then pass; the recorded auxiliary field times are unchanged.
No field construction, bending rule, convergence threshold, or production code
changes in this comparison.

The before/after CSV and summary files retain their source hashes. The before
header is available in commit `2d662da`; the after header hash is recorded in
`summary.json`. The runnable component is `diagnostics/check_fmm_field.cpp`.
Use a new variant directory for subsequent checks:

```sh
python3 data/development/fmm_field_checks/run_checks.py --variant NEW_NAME --suite closed-cell
```

The runner sets TMPDIR to the repository tmp directory. Its summary metadata
was later clarified to name this narrow suite; no CSV results were changed.
The saved real-data failure that motivated the regression remains unchanged in
`data/development/fmm_hayward_audit/results.csv` and retains native identifiers.
The invented case establishes the geometric defect. A subsequent, separate
[identified field-ray check](../closed_cell_hayward/summary.json) re-extracts
the previously failed observation, preserving every native input column. It
succeeds with exactly unchanged reported FMM field time and improves the
continuous action by only `1.9984e-7 s`. This verifies the extraction correction
for that ray, not a global first arrival. The full 39-path field/extraction
fixture also passes in `../closed_cell_full/`.
