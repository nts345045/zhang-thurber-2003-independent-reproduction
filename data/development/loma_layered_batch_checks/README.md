# Full layered-reference batch controls

These are invented geometry and metadata fixtures, not observational or Loma results. The maintained helper is `diagnostics/check_loma_layered_batch.py`.

`001/` records 14 passing serial controls. `002/` adds direct source-gradient permutation and corrupted-gradient readback controls, with 16 passes. `003/` adds an ordered four-worker calculation whose compressed results and certificates match the serial calculation byte for byte: all 17 controls pass. Each directory preserves the exact helper, batch runner, and reference modules used in its `source/` directory and their hashes in `results.json`. Earlier evidence is unchanged.

The checks cover complete Cartesian pair support, arbitrary quoted/newline metadata, valid blank receiver location/end epoch, deterministic compressed files, preservation of an injected arithmetic failure, repeated native/output indices, finite-domain and full-grid validation, gradient mapping, startup failure records, and refusal to reuse a failed output directory. The small `invented_repository/` directory is deliberately labeled and undersized; invoking the real controller there must fail before reference enumeration because it is not the declared 724-source/52-receiver cohort.

Run from the repository root, choosing a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_layered_batch.py --output data/development/loma_layered_batch_checks/NEW
```

These IO controls supplement the independent 355-case layered-reference mathematical checks. They do not establish global ray-solver convergence or generate simulated observations.
