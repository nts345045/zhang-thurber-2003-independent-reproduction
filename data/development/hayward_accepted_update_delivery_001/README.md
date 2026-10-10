# Accepted update 1; run incomplete

This delivery preserves the verified saved-state figure and exactly the files consumed by its plotting script. It contains 54 regular archive members: 39 pinned inputs, 14 closed plot artifacts (including the authored script and README), and the plot's execution receipt. Original repository-relative paths and full scientific identifiers are preserved. `members.json` records every member's size, permission bits, SHA256 and role. `packaging.json` binds the archive, verifies a second deterministic reconstruction and records the byte-identical copies at `figures/hayward_accepted_update_001.pdf` and `.png`.

The figure shows the 77 saved grid nodes at z = 8 km and all 1,092 event displacements, with an unamplified native-coordinate detail. Complete event/origin, receiver/channel/epoch, pick and association mappings and the authoritative observations are archived. Figure sidecars point to those full mappings. The accepted-state meaning and exact statistics remain in the original plot README/summary; no postupdate RMS or final-convergence claim is added.

Only the actual plotting dependency maps are followed. Hash references inside historical receipts may describe other inverse-run evidence that this plot does not consume; the archive is not a solver replay package. No growing ledger, cache, home directory, runtime database, Python environment or installed binary is included. The only history/trial prefixes are already closed, explicitly labelled saved snapshots. Original files and receipts remain unchanged.

## Restore safely

Run from the checkout root using Python 3.6 or newer. The destination must not exist, its parent must exist, and no destination ancestor may be a symlink. All archive contents are verified before creation; regular files are written exclusively without `extractall` or overwrites.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_accepted_update_delivery_001/restore.py --destination tmp/hayward_accepted_update_restore_001
```

The archived PNG/PDF and their original sidecars are then under `tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_001_figures/`. `restore_receipt.json` records the verified member count and archive hash.

## Replot without replacing evidence

The archive supplies saved inputs and source, not plotting software. The original run used Python 3.11, Matplotlib 3.11.2 and NumPy 2.4.6 in `tmp/waveform_env`; its exact runtime details are in the archived summary. With that environment available, run the following from the checkout root after restoration. The new plotting folder is a sibling of the archived one, so the unchanged script resolves the restored inputs correctly. The `mkdir` command requires a fresh location.

```sh
mkdir tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_replot_001
cp tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_001_figures/plot_accepted_update.py tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_replot_001/
cp tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_001_figures/README.md tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_replot_001/
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python tmp/hayward_accepted_update_restore_001/tmp/hayward_accepted_update_replot_001/plot_accepted_update.py
```

The plotting script places Matplotlib/XDG/temp files inside its new project-local directory before importing plotting libraries. It verifies all 39 restored input pins, reconstructs the full catalog joins, and refuses to overwrite generated files. No fit, interpolation, solver, ray, field, Jacobian or integration is called. Exact statistics and the saved input geometry can be compared directly; renderer metadata and PDF timestamps mean regenerated plot bytes need not match. The archived and delivery-copy figure bytes remain authoritative.

Packaging and restore/replot verification receipts are delivery evidence only. This task does not compile, push, alter reports or adopt a solver change.
