# Geometry diagnostic

[geometry.pdf](geometry.pdf) and [geometry.png](geometry.png) show two views
of the saved failure. The left panel uses fixed y and z at each path's
closest recorded node to x=0; velocity is linear in x within either adjacent
cell. The right panel shows all 63 nodes in the declared one-millimetre
inventory on a symmetric logarithmic axis. Colors identify the same events
in both panels. Numerical offsets are not observational accuracies.

[normal_sections.csv](normal_sections.csv) preserves the six plotted
section vertices and their full native context. The path points are in
[near_face_nodes.csv](near_face_nodes.csv). [plot_receipt.json](plot_receipt.json)
binds the script, inputs, output files and Matplotlib version. No ray is
recomputed and no manuscript panel status changes.

From a fresh copy of this package with its geometry calculation present,
run the following with a Python environment containing Matplotlib:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=tmp/matplotlib python3 data/development/NEW_PACKAGE/plot.py
```

The plotting script refuses existing output products. Root visually checked
the final PNG: labels, legends, points and the zero line are legible, with no
overlap or clipping. An earlier plot layout is retained locally under
`tmp/cmj_geometry_plot_initial_001`; only the final layout is in this package.
