# Finite full-DD resolution outputs

The maintained helper now rejects a nonfinite optional unmasked-model response
and any nonfinite conditioning diagnostic before returning results to the file
writer. No numerical expression or finite condition-number threshold changes.

All 39 invented checks pass. The original 34 saved check records are exactly
unchanged. Five new checks cover finite ordinary outputs next to an overflowing
physical response, rejection of that response, rejection of an infinite
condition number, and acceptance of a finite condition number near 1e300.
These are representability checks, not an accuracy claim for ill-conditioned
systems.

The old frozen helper reproduces both omissions: finite R=1 and covariance=0
alongside an infinite physical response; and finite resolution/covariance
alongside an infinite condition number. `readback.json` preserves those facts
without nonstandard Infinity JSON values. Old fixtures and sources are intact.

The commands executed from the repository root were:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_full_dd_resolution.py --output data/development/full_dd_resolution_finite_checks_001
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 data/development/full_dd_resolution_finite_checks_001/readback.py
```

Both commands returned 0. The runner requires a fresh output directory and the
readback requires a new result file. `source/` freezes the executed numerical
helper and test. No field calculation, trace, inversion or production solver
change is included.

The separate
[maintained implementation comparison](../catalog_dd_resolution_controls_003/maintained_comparison.json)
uses the already frozen coupled/masked invented fixtures. Its six sparse versus
dense array comparisons agree within 9.4369e-16; the old and corrected maintained
arrays are exactly equal on both cases. That comparison retains primitive-pick
noise once, the original column-scale damping convention, and distinct assembly
and physical prediction responses.
