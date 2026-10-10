# Full initial-support continuous 1D comparison

This completed diagnostic compares all 14,262 saved initial rays in Hayward preflight `first_arrival_003` with the independently implemented continuous, monotone 1D branch reference. It uses the actual saved grid profile and native source/receiver coordinates. It does not rerun the numerical rays, change their stopping flags, or start an inversion. All reference enumerations completed and were valid, with no near ties.

The exact reference is conditional on this initial horizontally uniform profile. Its interval calculations certify the reported branch enumeration and distance closure; minimum-time ordering uses floating-point actions. This is not a certificate for subsequent three-dimensional models.

| Saved local flag | Rays | Time error <= 25 microseconds | Source vector error <= 3e-6 s/km | Both limits |
| --- | ---: | ---: | ---: | ---: |
| All | 14,262 | 2,326 | 1,842 | 603 |
| True | 14,123 | 2,326 | 1,782 | 603 |
| False | 139 | 0 | 60 | 0 |

These are the retained analytic component limits, applied without loosening. The source criterion is the Euclidean norm of all three derivative errors. The generated `summary.json` also retains the original component-wise descriptive statistics; those statistics are not the vector acceptance criterion.

The median travel-time error is 37.8031 microseconds, with RMS 53.7424 microseconds and maximum 2.232174 milliseconds. The source-vector error has median 5.765278e-6 s/km and maximum 0.03357077 s/km. Original observation row 14099 (event index 1079, native receiver epoch 314, `NC.JJR..EHZ`) has both largest errors despite its true local flag. Its complete event/origin/pick/arrival/channel identities and epochs are in the preserved row and `independent_review.json`. The path cause is investigated separately; this comparison alone does not distinguish branch selection, incomplete optimization, and polyline discretization.

Local stopping flags therefore do not certify forward accuracy. Refining only the 139 false flags cannot establish accuracy on the full support.

## Provenance and terminal status

The comparison started after the full initial linearization exited successfully but before the separate sampled raycheck finished. The captured execution ledger is retained as captured. The overall preflight later terminated with `failed_checks_preserved`: 139 full-support local flags failed. The independent review reconciles all 16 shared frozen file hashes with the terminal review in `../hayward_first_arrival_003_review/`, preserves all original row fields, verifies 57,048 source/origin sparse-matrix entries, and joins every saved reference by original row and native source/receiver indices. No success state is fabricated.

`summary.json` preserves the executed command, dependency versions, exact source/input/output hashes, and the reference module's limitations. `source/` preserves both Python helpers. `independent_review.py` checks hashes, identities, source columns, subtraction, vector norms, and the terminal reconciliation; it does not revalidate reference mathematics.

## Lossless table archive

`frozen_tables.tar.gz` contains `comparison.csv`, `references.jsonl`, and all 17 files under `inputs/`, including every original observation/metadata field, all linearization tables, run manifest, captured execution ledger and solver source snapshot. The archive changes packaging only. `packaging.json` records every original byte hash and the archive hash; every member was read back and verified. Tar owner/time metadata and gzip time are normalized, without changing member bytes.

Extract and rerun the saved-table review from this directory:

```sh
tar -xzf frozen_tables.tar.gz
PYTHONDONTWRITEBYTECODE=1 python3 independent_review.py
```

The archive keeps the repository compact; the expanded copies remain local and are ignored. Neither extraction nor review runs a ray solver or changes observational inputs.
