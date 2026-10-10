# Identified geometry in the full DD export

The integration exporter now saves `MODE_full_linearization_ray_geometry.csv`
and `MODE_full_linearization_ray_paths.csv` from the same ray array used for
the matrix. Both files use 17 significant digits and retain native event,
channel, and metadata-epoch identities. They include used pairs that occur only
in zero-prior observations. Failed returned rays retain their diagnostic flags
and paths before the existing finite/dimension rejection. Existing diagnostic
files and dangling links are refused before ray evaluation.

The [82 invented controls](../hayward_full_dd_geometry_export_controls_002/RESULTS.md)
passed using the frozen old-kernel source. All eight original export files were
byte-identical. Independent [saved readback](../hayward_full_dd_geometry_export_controls_002/review.json)
verified the terminal files, native joins, and failure records without importing
the tested reader or ray code.

The first integration compile failed because its main file lacked the reviewed
I/O helpers. That [attempt](../hayward_full_dd_geometry_adoption_001/RESULTS.md)
is retained. This adoption adds those exact helper bodies and the checked close
to the status writer. The complete status-writer function and export header
match the reviewed candidate. Removing the helper insertion and reversing that
one close call restores the prior main file exactly. The
[independent source review](source_review.json) records this comparison.

The fresh [compile](compile.json) passed with the existing integration D kernel.
No numerical evaluation was run in either adoption attempt. Inversion
arithmetic, trial acceptance, and the kernel remain unchanged. The running
old-kernel Hayward attempt uses its separately frozen binary and sources.

The maintained reader is
[`diagnostics/review_full_dd_geometry.py`](../../../diagnostics/review_full_dd_geometry.py),
byte-identical to the reviewed control reader. For a future completed export,
use:

```sh
python3 diagnostics/review_full_dd_geometry.py \
  --data-dir SAVED_EXPORT_DIRECTORY --config SAVED_EXPORT_DIRECTORY/run.cfg \
  --mode dd --output FRESH_REVIEW_JSON
```

The reader checks complete native support, identifiers, path order, endpoints,
domain membership, configured initialization, and signed source-matrix entries.
It reads the parsed saved model, whose coordinates were previously written at
12 digits. Agreement does not attest the executing binary, first arrival,
derivative accuracy, nonlinear convergence, or covariance assumptions. A field
export and final-model accuracy assessment remain separate work.
