# Hayward second accepted update relative to the first

The figure compares two closed accepted states of the ongoing catalog-only Hayward inversion. Iteration 1 accepted trial 4 at fraction **1/16**. Its fixed-weight objective decreased from **1410.9617357448938 to 1250.1138773364614**, or 11.3999%. This is an intermediate update, not a final inversion, recovery result or first-arrival accuracy claim.

The left panel shows second-minus-first velocity at the **77 saved grid nodes at z=8 km**, without interpolation. The center and right panels show the second accepted event displacement from the first state, at actual scale in native x/y kilometres. Gray points mark the first state; the red rectangle bounds the 4 km × 4 km detail. Both states retain 1,092 events and 462 model nodes. Colors and exact descriptive differences are defined in `statistics.json`; square-root display values are descriptive arithmetic.

The two new tables in `inputs/` are byte-exact accepted-state snapshots from the uniquely named iteration-2/trial-0 rejection prefix. The executed source copies accepted `e/g` separately from rejected trial coordinates. The 288 rejected rays belong to that attempted next update. Iteration 2's recomputed-weight objective of 1253.1810003788601 is not directly comparable to the prior accepted objective. History RMS and ray metrics remain pre-update diagnostics; no successful-trial full status table was emitted.

`scientific_manifest.json` binds the new tables, the source contract, and ten exact members of the already published first-update archive. The plot reads those members directly and verifies their hashes; it does not restore runtime files or require the active inversion directory. First-state tables, station metadata and native maps are reused rather than copied into this package. The derived identifier table retains all three event states and full receiver metadata. Its exact archive references preserve all 14,262 event/receiver pairs, 103,698 catalog side uses, both pick/association identifiers, SEED/FDSN codes, epochs and valid blank locations.

From a checkout containing this package and the prior tracked archive, use Python with Matplotlib and NumPy:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_second_accepted_update_figure_001/plot_second_update.py --output tmp/FRESH_hayward_second_update
```

The output directory must be fresh and inside the checkout. Matplotlib/XDG/temp caches stay inside it. The existing project plotting environment is `tmp/waveform_env/bin/python`; software installation is separate from these scientific inputs. PNG/PDF, exact statistics, identifier mapping, figure sidecars and `summary.json` are written once. Renderer/PDF metadata may change figure hashes on replay. Process observations, machine identifiers, execution receipts, logs and caches remain local and are excluded from this scientific package.

The renderer is adapted from the first-update plotting source already stored in the prior archive; `source_delta.patch` records the exact change. No solver, ray, field, Jacobian, inversion, fit or interpolation is called. Prior figures and scientific evidence remain unchanged.
