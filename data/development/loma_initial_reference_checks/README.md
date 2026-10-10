# Initial-depth reference wrapper checks

These are invented integration fixtures, not observations or additional validation of the continuous ray formulas. The numerical helper is unchanged at SHA-256 `13020fef85113c302b27d846e1b4286c13576348a10710ba8a4c6fbd999e1c98`.

`001/` preserves the original 29 passing wrapper checks. `002/` records all 38 final checks after adding disjoint input/output paths and explicit reference-comparison usability. Each directory freezes the check/helper sources and records their hashes, command, small invented inputs, terminal ledgers, and saved reference streams. The two full invented runs use one and two workers and produce byte-identical compressed tables and certificates.

The final checks cover complete Cartesian native support, quoted/empty metadata, exact boundary flags, original-coordinate derivative mapping, saved perturbed geometry, exclusion of nonzero source-time corrections from propagation time, z-only positive nondecreasing model eligibility, reviewed-input hash/status gates, deterministic worker ordering, exclusive output creation, and preservation of unresolved arithmetic. A near tie, undefined coincident-source derivative, or nonfinite reference cannot be labeled ready for source-derivative comparison. No numerical-reference tolerance changes.

Reproduce with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_initial_reference.py --output data/development/loma_initial_reference_checks/new_run
```

The full initial-geometry calculation is a separate evidence run. These invented results do not certify forward-ray or inversion accuracy.
