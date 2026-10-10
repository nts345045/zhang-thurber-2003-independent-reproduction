# Bounded backtracking and ridge evidence

This package preserves the independent trial-backtracking candidates, their before/after loop controls, the old-kernel integration checks, the saved-output completion checks, the separate launcher checks, and the invented internal-ridge calculations. `members.json` gives the exact roster. Source-only drafts and failed checks remain in the record with their original outcomes; their inclusion does not imply execution or acceptance.

Original preparation records and README files retain their pre-execution wording because they are part of the pinned inputs. Read each package's `RESULTS.md`, terminal execution record and independent review for its completed outcome.

The archive contains repeated small fixtures and their complete outputs. Selected source, documentation and review files are also readable directly in the repository. The archive does not include a new real-data inversion, the live LOM/LON preflights, or changes to the original Hayward baseline or maintained ray kernel.

This is not the entire historical launch dependency set. Use the published `first-arrival-integration` checkout for the new launcher: its reviewed `diagnostics/check_external_inputs.cpp` differs from the preserved main-branch baseline. The launcher also requires the original Hayward004 inputs, provenance, sampled checks and executed binary at `tmp/hayward_runs/first_arrival_004/compiled/dd`, its source archive, the prior guard-parity evidence, the full-reference archive, and the preserved failed-run inputs/source archive. Their exact paths and hashes are recorded in `hayward_old_kernel_backtracking_launcher_001/prepared.json`, including `original004_required_sha256`. Restore those separately from their existing packages before invoking the launcher; this archive does not replace missing historical evidence with a new run.

From the repository root, restore the evidence at its recorded relative paths:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/trial_backtracking_evidence_001/restore.py --destination .
```

To inspect a separate copy within the project instead:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/trial_backtracking_evidence_001/restore.py --destination tmp/trial_backtracking_inspection
```

The script checks the archive, member inventory and every file before writing. It leaves identical existing files in place and refuses to overwrite differing evidence. Intentional symbolic-link test inputs are preserved as links to local filenames, including missing targets; they are test cases, not runtime dependencies. The exact link count is recorded in `packaging.json`.

`package.py` documents how the archive was produced from the explicit roster. It requires the original completed packages and writes fresh outputs only. `packaging.json` records full archive readback against the original files. A separate fresh restoration check accompanies publication. Neither operation reruns a ray, inversion, or scientific accuracy check.

The old-kernel source bridge preserves the initial Hayward operator and its existing accuracy evidence. Backtracking allows the existing smaller trial fractions to be evaluated after a pure local-stopping rejection; it does not make a failed ray acceptable. Completed invented controls and saved-record consistency do not certify convergence or first-arrival accuracy in an updated field model. The exact-face ridge examples likewise do not change any native failed flag.
