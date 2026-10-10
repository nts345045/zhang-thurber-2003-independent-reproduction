# Saved initial-ray comparison controls

These are invented saved tables and explicitly artificial stage/review ledgers. No reference formulas, numerical rays, or inversions are computed. The four small reference records are reused from the already saved invented initial-reference wrapper fixture.

`001/` preserves 41 passing checks. `002/` records the final 45 passing checks after adding corrupt reference-flag, time, derivative, and boundary-field rejection controls. Both directories retain input fixtures, source snapshots, terminal comparison outputs and commands. The final `comparison_pass.log` records the intentional refusal to overwrite the successful output directory; the original successful comparison remains in its unchanged terminal ledger and summary.

The checks cover native event/origin/SEED/FDSN/epoch joins with quoted and valid empty strings, original xyz derivatives, source-time exclusion, a vector whose components individually pass 3e-6 but whose Euclidean norm fails, all original stopping/initialization/domain/endpoint flags, invalid/tied references, nonfinite modeled values, exact initial-model hashes and review links, stage-0 command identity, independent sample-stage liveness, and exclusive output creation. Scientific failure records retain both native identity fields and an exact `comparison_row` join.

The maintained comparator is `diagnostics/compare_loma_initial_rays.py`. It requires a successfully completed `initial_matrix_preflight` ledger record and `full_initial_checks.json`; the unrelated sampled geometry check may still be active. It snapshots that atomic ledger rather than treating it as a final workflow result. Full initial events, stations, grid and simulation provenance must match the frozen reference byte-for-byte. The assessment configuration is separately pinned and intentionally need not equal the original simulation configuration.

Every original ray/status/native column is retained in `comparison.csv.gz`. Added reference columns preserve eligibility, branch/ties, original precise coordinates and source-time metadata, source derivatives and boundary flags. `time_error_s` uses pure propagation time. `source_error_euclidean_norm_s_per_km` uses all three original-axis derivative differences. The unchanged limits are 25 microseconds and 3e-6 s/km. Calculation completion, individual accuracy checks, original flags and combined scientific acceptance are distinct. No rays are removed from the table.

Reproduce controls in a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_initial_comparison.py --output data/development/loma_initial_comparison_checks/new_run
```

The eventual real comparison, only after its matrix stage completes, is:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_loma_initial_rays.py --data data/loma_lom_initial_preflight_001 --reference data/development/loma_initial_reference_001 --output data/development/loma_lom_initial_comparison_001
```

These controls do not establish actual Loma forward accuracy, sampled finite-difference accuracy, or inversion readiness.
