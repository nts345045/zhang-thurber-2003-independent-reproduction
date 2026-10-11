# Hayward third accepted update relative to the second

This figure compares two closed accepted states of the ongoing catalog-only Hayward inversion. Iteration 2 accepted trial 3 at fraction **1/8**, reducing its fixed-weight objective from **1253.1810003788601 to 978.00644322787343**. The objective includes weighted data residual squares and final log-slowness smoothing; damping enters the solve only. This is **accepted update 3; run incomplete**, with no final convergence, recovery, first-arrival accuracy or post-update RMS claim.

The planned three panels retain the second-update display convention: third-minus-second velocity at the **77 saved nodes at z=8 km**, an overview of all **1,092** event displacements, and a 4 km × 4 km detail. Arrows use actual native x/y kilometres without amplification. Gray dots mark the second accepted state. Differences use exact rational arithmetic on the saved binary64 values; displayed square roots are descriptive. No interpolation, ray evaluation or inversion is performed.

Both uniquely named third-state event/grid snapshots are retained in `inputs/`. Their numerical states agree, while their original `coordinate_basis` labels distinguish the rejected-trial accepted-state copy from the iteration-3 solve copy. The executed source saves accepted `e/g` separately from rejected trial coordinates. The closed iteration-2 trial ledger, iteration-3 solve context and iteration-3 rejected-trial context are also retained. Exactly four known local checkout-root prefixes are removed from path references in the public ledger/rejection context; every non-path field is unchanged. The manifest records original and delivered hashes and the exact transformation. Raw originals remain in the closed local preservation.

Iteration 3 recomputes weights and records **973.55329487224935**; it is not directly comparable to the preceding fixed-weight accepted objective. The **394** failed rays belong to rejected iteration-3 trial 0, not to the accepted geometry. History RMS and ray metrics are pre-update diagnostics; there is no successful-trial full ray-status table.

`scientific_manifest.json` binds all new tables and the existing second-state package. The renderer reuses the two published second-state tables and five pinned members of the first-update archive: initial event metadata, receiver metadata, full native-pair and catalog-side maps, and the executed source contract. The output identifier mapping retains the initial, second and third event states, both third-state basis variants, all 372 receiver epochs, and exact archive references for 14,262 native pairs and 103,698 catalog-side uses. Event/origin/pick/association identifiers, SEED/FDSN channel identifiers, epochs and valid blank locations are preserved.

From a checkout containing this package and those existing scientific dependencies, using Python with Matplotlib and NumPy:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_third_accepted_update_figure_001/plot_third_update.py --output tmp/FRESH_hayward_third_update
```

The output directory must be fresh and inside the checkout. Missing parent directories are created; Matplotlib, XDG and temporary caches remain inside the new output directory. The existing project plotting environment is `tmp/waveform_env/bin/python`. PNG/PDF, exact statistics, full identifier mapping, figure sidecars and `summary.json` are written once. Rendering/PDF metadata may change figure hashes on replay. Process observations, execution receipts, logs and caches are local evidence, excluded from the scientific package.

`source_delta.patch` records the exact change from the published second-update renderer. Existing packages, plots and accepted-state preservation receipts remain unchanged. No solver, field, Jacobian, covariance, fit or interpolation is called.
