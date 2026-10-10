# Geometry-export evidence archive

This lossless archive preserves exactly three completed source/evidence directories:

| Directory under `data/development/` | Preserved status | Files |
| --- | --- | ---: |
| `hayward_full_dd_geometry_export_candidate_001` | Reviewed source-only exporter candidate | 25 |
| `hayward_full_dd_geometry_export_controls_001` | Unexecuted preparation; its observation/native-identity join gap is preserved | 43 |
| `hayward_full_dd_geometry_export_controls_002` | 82/82 invented checks passed; independent saved-output review passed | 1,086 |

All source copies, invented inputs, intermediate malformed tables, results, compiler/test logs, terminal controller provenance, `review_saved.py`, `review.json`, and `RESULTS.md` remain byte-exact. The original eight exported tables matched before/after in the small invented control. This package adds no field export, covariance calculation, numerical accuracy criterion, or final-model acceptance. The saved 12-digit model is the export evaluation point; equality to an earlier internal 17-digit state is not asserted.

`evidence.tar.gz` contains 1,154 regular files, 4,747,041 uncompressed bytes, and no links. Its compressed size is 1,482,511 bytes. `members.json` records every path, byte count, SHA-256 and permission mode. `packaging.json` records the archive hash, hard-pinned reviews, and three intentional compiled ELF fixture files (`controls_002/build/{before,after,after_io}`, each 623,632 bytes and mode `0755`). Those binaries are numerical provenance, not installed software; restoration never executes them. No process lock, interpreter cache, live run, or unrelated state is included. Archived logs are closed compiler/control evidence, not session transcripts.

## Restore and inspect

Run from the matching published `first-arrival-integration` checkout. To inspect without touching the original evidence trees:

```sh
python3 data/development/geometry_export_evidence_001/restore.py \
  --destination tmp/geometry_export_evidence_inspection
```

The restore helper is byte-identical to the reviewed helper in `trial_backtracking_evidence_001` (SHA-256 `0427f73f66b99530e7ffdcd103297e99199ab1b61a1596a997bc31cb8f39fc36`). It checks the archive/member hashes, gzip completion, safe paths, file kinds and modes before writing. It skips byte-and-mode-identical existing files and refuses differing files, modes or unsafe paths. It creates no processes from the archive and does not resume a completed experiment.

`check_restore.py` exercised a fresh project-local restore, exhaustive file/mode/roster readback, idempotent restoration, and refusal of deliberately changed scratch bytes and permissions. It restored the two scratch changes afterward and rehashed every untouched original. The terminal receipt is `restore_check.json`; the original scratch destination is `tmp/geometry_export_evidence_restore_001`. Repeating this one-use receipt-producing check requires a fresh copy of this archive package and a fresh scratch destination; ordinary `restore.py` inspections do not alter the receipt.

## Dependencies and provenance

`dependencies.json` binds all 38 distinct original input paths and ten recorded compiler/runtime hashes from the three preparations. Twenty-four original paths are inside this archive. The fourteen historical paths outside it are already tracked in the matching integration checkout: ten old-kernel source files, that old candidate's preparation record, the previous full-DD ray-input review, `diagnostics/check_full_linearization.cpp`, and `resolution_full_hayward.py`. The ten source files also have byte-identical copies inside this archive, listed explicitly in that manifest. Historical source provenance still refers to its original paths; restoration does not rewrite them. The prior `trial_backtracking_evidence_001` package also preserves the old candidate.

System compiler/libraries and Python are recorded by their original hashes and are not copied into the archive or overwritten. Complete frozen source trees and the exact compilation commands/flags remain available. Original receipts retain their historical absolute project paths and process IDs as inert provenance, not current runtime state. The main branch deliberately retains a different legacy solver source, so it must not be substituted for the pinned integration source when reproducing the controls.

The compressor and streamed member readback reuse the earlier reviewed archive algorithm; only the explicit three-package roster, prerequisite checks, and compiled/dependency inventories were adapted. Original archive members were unchanged before and after packaging and restoration. No Git mutation, native ray call, inverse solve, or network request was performed for packaging.
