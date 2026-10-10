# Replot from a checkout

All twelve pre-existing plotting inputs are tracked and byte-identical to the
recorded integration commit; [checkout_dependencies.json](checkout_dependencies.json)
lists their hashes. They contain the closed accepted-pair, catalog-event,
receiver-epoch and review records. No live inversion file, external waveform
request or untracked native input is needed. Include this entire small figure
package in the checkout as well. The saved PDF/PNG and their identifier
sidecars are already available under `render_002/`.

Plotting requires Python 3.11 and Matplotlib; the recorded render used
Matplotlib 3.11.2 and NumPy 2.4.6. These software packages are external
dependencies and are not supplied by Git. The script imports no project
evaluator, ObsPy or SciPy. If a suitable environment is unavailable, the
following commands create one inside the project; installation was not repeated
for this dependency check:

```sh
mkdir -p tmp
python3.11 -m venv tmp/cc_spatial_plot_env
tmp/cc_spatial_plot_env/bin/python -m pip install matplotlib==3.11.2 numpy==2.4.6
```

From the checkout root, render into a fresh destination:

```sh
PYTHONDONTWRITEBYTECODE=1 tmp/cc_spatial_plot_env/bin/python -B data/development/native_cc_spatial_support_001/plot_cc_spatial_support.py --output tmp/cc_spatial_replot_001
```

An existing project environment with those packages can replace the Python path.
The output directory must be absent. The script verifies the closed input hashes
and full native joins, then saves new source, tables, sidecars, PDF/PNG and a
summary without overwriting the archived renders. Caches remain under project
`tmp/`. Coordinates and identifiers should match exactly; PDF creation dates,
font/rendering dependencies and platform differences can change image bytes.
The recorded runtime is in [the final summary](render_002/summary.json).

This is a plot replay, not a repeat correlation, graph analysis or inversion.
The initial layout and its correction remain preserved; no prior receipt was
edited to add these instructions.
