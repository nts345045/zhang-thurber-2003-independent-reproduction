# Prospective completion-review saved-table controls

This package tests the immutable `hayward_trial_completion_candidate_001` Python reviewer using the completed, independently reviewed invented outputs in `hayward_trial_backtracking_controls_002`. It makes no compiler, ray, field, reference or inverse call. Source preparation and control execution are separate. The original candidate, C++ controls and native tables are never changed.

`check.py --prepare` copies the reviewer, minimal launcher and their three import dependencies, the selected original fixture files and source/review receipts, then freezes their hashes and the complete prospective roster in `prepared.json`. It only parses Python syntax. `check.py --run` verifies those pins, makes a fresh `results/` directory, creates each declared copy/mutation, calls the saved reviewer, and retains every result, rejection reason, file hash and intentional symlink. A failed expected rejection is a failed control; it is never silently accepted or used to change the frozen candidate. A correction would require a new candidate and control package.

From the integration worktree, the prospective command is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_trial_completion_checks_001/check.py --run
```

The exact executing Python path, version and binary hash are in the preparation receipt. The reviewed source and tests are held for approval before this command is executed.

## Actual saved-loop evidence and invented schema fixtures

Five positive fixtures are complete, unaltered C++ table sets: `valid_dd`, `valid_loc1d`, `half`, `quarter` and `worse`. They cover all-valid iterations, one/two quality rejections followed by objective acceptance, and a quality rejection followed by eleven valid but nonimproving trials with a legitimate zero-step ending. The terminal failed `all`, `state` and `mixed_invalid` sets must remain rejected. Their original inventories and bytes are frozen under `fixtures/`. The runner reserializes only a working copy's configuration numerically; positive fixture CSV bytes remain identical to the saved originals.

Additional positive table-contract fixtures are explicitly hypothetical, not successful C++ executions. The joint DD fixture retains the actual `state` first rejected polygon, clamped source/model state and full original delta, but supplies a declared hypothetical half-step objective ending and history. This lets the reviewer exercise nonzero model columns and the unchanged exponential update; it says nothing about that hypothetical step's forward validity. Separate fixtures declare no-update stage skips, stage-2 termination, an all-invalid-model ending without a quality rejection, objective equality, legacy absent `station_j` semantics, and successful initialization flags. These table constructions are recorded as mutations, not measured outcomes or status promotions. In particular the real failed `state` output remains a separate negative control.

The malformed roster covers each of the eight rejection and five solve files, missing/orphan ledgers and convenience copies, full source/model delta/reference rows, both native epochs and empty location, original metadata names colliding with diagnostic names, zero-weight ray support, local versus nonlocal reasons/flags, native paths and finite-box/endpoints, snapshot dimensions/LSQR/basis, objective inequalities and 17-/12-digit history joins, configured iteration bounds, stage skips, symlinks and duplicate/malformed headers. Coordinated iteration-zero origin-time changes explicitly test the known initial-state anchor. No new numerical accuracy tolerance is introduced.

The seven child/source tests call the actual patched `check_inverse` entry, replacing only its first `rows(initial_events.csv)` call with a deliberate stop marker. They therefore test the completed-child and exact-main prerequisites without fabricating full guarded final outputs from the legacy-initialized invented fixtures. They do not exercise source eligibility, final full-table completion or independently prove the final ray gate. The unchanged launcher still requires a separately reviewed old-kernel/main bridge before a real attempt; no such bridge is adopted here.

The reviewer does not recompute saved current-model residuals or fixed weights from unavailable rays. It has no independently emitted all-success final ray table. Its successful saved-table result is evidence closure only, not first-arrival, final-model accuracy, optimization convergence, or an accepted scientific correction.
