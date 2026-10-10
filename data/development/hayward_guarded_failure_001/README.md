# Preserved guarded Hayward failure

The guarded catalog-DD run stopped at iteration 0, line-search trial 0, before accepting an update. All 14,262 initializers succeeded, but 181 selected rays failed the existing local stopping test. The saved history has no accepted rows; the last-accepted source and velocity tables equal the starting state numerically. These files contain no accepted inverse solution.

[classification/summary.json](classification/summary.json) and the [identified failure roster](classification/identified_failures.csv) retain the 181 failures across 152 events and 61 native receiver epochs. The saved-table audit checked 14,262 status rows, 240,003 path nodes and 18,051,404 native metadata cells. All saved paths were finite, inside the model and attached to their exact endpoints. The inferred termination counts are 106 update-budget exits and 75 exhausted searches; individual iteration histories were not saved. Candidate source derivatives and its objective were not evaluated. This census establishes neither a common failure mechanism nor that the later D kernel would resolve it: the run used its frozen earlier kernel.

## Archive contents and identity

[archive/failed_run.tar.gz](archive/failed_run.tar.gz) is one ordinary gzip tar, **18,775,402 bytes**, SHA-256 `aea609c985ae0e8c447510b3ecc78968a38f0777977ffa7c36b5b55139e504e3`. Its 61 regular-file members preserve **541,489,704 bytes**: every one of the original run's 57 files, the executed binary, and three inherited initial-ray sample tables. The 432,260,494-byte failed-path CSV and 29,975,831-byte status CSV are unchanged inside it. No published file reaches 100 MB.

[manifest.json](manifest.json) records every member's original path, size and SHA-256, the complete compressed-stream hash, 13 exact readable copies, and the inherited-evidence mapping. [archive_verification.json](archive_verification.json) records complete member readback, gzip completion and unchanged original files. [restore_check.json](restore_check.json) additionally binds the classification and resolves all its 68 input hashes to restored members or the nested frozen source archive; all 12 inherited evidence pins also resolve.

The archived `run/initial_events.csv`, `run/stations.csv` and `run/observations.csv` retain the authoritative event/origin/pick/arrival identities, full NSLC (including empty location), receiver epochs and raw-source hashes. The trial status, failed-path and failure-roster rows carry the same native context directly. `run/dd_failed_forward_events.csv` is the rejected candidate; `run/dd_last_accepted_events.csv` and its grid companion describe the starting state. The archive does not reinterpret either as a recovered model.

The two external pins are existing repository files [packaging.json](../hayward_first_arrival_004_1d_support/packaging.json) and [frozen_tables.tar.gz](../hayward_first_arrival_004_1d_support/frozen_tables.tar.gz), containing the earlier initial-state reference evidence. Their exact hashes are in this manifest. Initial-state validation is not a continuous 3D accuracy reference for the rejected trial.

## Verify or restore

Run from the root of a published project checkout containing this package and those two external files:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_guarded_failure_001/package.py verify
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_guarded_failure_001/package.py verify --restore tmp/hayward_guarded_failure_restore_NEW
```

The second command requires a fresh destination and writes the archived members under it. It rejects existing destinations, parent traversal and symlinked ancestors. It verifies every extracted byte and never runs the archived executable. The local test used a separate scratch directory and retained refusal checks for existing, symlinked, escaping and outside-project destinations. `initial_attempt/` preserves the first helper, manifest and successful member readback before the parent-traversal check was added; only the helper hash changed in the final manifest, and the archive bytes remained identical.

The frozen source is nested at `run/guarded_source.tar.gz` (14 verified source files); the executed binary is `execution_provenance/dd`. Original compiler/version output, flags, runtime-library hashes and small build-provenance files remain in `run/`. The generated CMake build tree is not included. The binary is environment-specific: these instructions restore evidence, not rebuild or rerun the failed inversion. Historical absolute project paths in raw logs, context and ledgers are preserved as evidence; use the relative commands above for extraction. No credentials or session transcripts were added.

The original run and all frozen numerical artifacts were left untouched. Scientific classification and byte-preservation checks are separate, and neither promotes the failed trial to an accepted model.
