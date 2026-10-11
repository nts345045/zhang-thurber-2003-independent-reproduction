# Replot the initial-model full-DD result

The saved figure shows seven cross-fault sections. The left column interpolates
nodal masked-resolution diagonals for display. The right column propagates the
full saved covariance to each interpolated velocity, using `sigma=sqrt(w Cv w)`
and `Cv=diag(v) Cq diag(v)`. It does not interpolate nodal standard deviations.
Every section row retains the eight node indices and weights; complete
contributor event/origin/pick/channel/epoch identifiers accompany the outputs.

From the repository root, use Python with NumPy and Matplotlib installed and
choose an absent project-local output directory:

```sh
mkdir -p tmp/hayward_initial_full_dd_plot_runtime
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
TMPDIR="$PWD/tmp/hayward_initial_full_dd_plot_runtime" \
MPLCONFIGDIR="$PWD/tmp/hayward_initial_full_dd_plot_runtime/matplotlib" \
XDG_CACHE_HOME="$PWD/tmp/hayward_initial_full_dd_plot_runtime/cache" \
python3 -B \
  data/development/hayward_initial_full_dd_resolution_001/plot_initial_resolution.py \
  --data-dir data/development/hayward_initial_full_dd_resolution_001/data \
  --manifest data/development/hayward_initial_full_dd_resolution_001/scientific_manifest.json \
  --output tmp/hayward_initial_full_dd_replot_001
```

The cache and temporary directories stay inside the project. The plotter checks the published scientific inventory and all six input hashes,
then checks node ordering, matrix dimensions and identity joins before creating
its output directory. Two-variable covariance and tensor-basis controls run
first. This replot does not rerun the ray export or resolution calculation.

The original local rendering required a successfully completed numerical
execution record. This portable version instead consumes the published
scientific inventory, omitting machine process/session metadata. Covariance,
interpolation, controls and rendering equations are unchanged. The initial
rendering succeeded and was visually inspected. The documented portable replot
also completed successfully, using the project-local Python 3.11.9 runtime
with NumPy 2.4.6 and Matplotlib 3.11.2. The section table, both identifier
companions, PDF and PNG all matched the original rendering byte for byte.
[plot_replay.json](plot_replay.json) records the scientific comparison;
[figure/](figure/) contains the portable rendering and its manifest.
This checks the documented plotting procedure without repeating the resolution
calculation.

The result concerns initial sources/model and stage-0 catalog-only weights.
Neither this display nor a successful replot establishes final-model
resolution, full nonlinear uncertainty, or reproduction of Figure 11.
