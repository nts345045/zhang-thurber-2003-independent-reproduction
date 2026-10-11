# Endpoint-mesh results for LOM24104

This scientific bundle preserves six independent reoptimizations of the same identified ray with 8 or 16 prefix subdivisions and bottom, 10 m inward, or 2.5 m inward source positions. Every run uses the closed 16-pair solver policy and the same 1000-update cap. Three returned polygons pass the final interval full-witness, time and fixed-polygon source checks; three remain unresolved at the update budget. See [RESULTS.md](RESULTS.md) for the six dispositions and limits of the result.

`inputs/` contains the exact numerical starts and their complete original identity sidecars. `final/` contains full returned coordinates and ordinary-gradient components; `summaries/` contains unchanged solver scalar/vector summaries. Their new sidecars retain the complete scientific case and remove only execution-specific absolute path/preparation wrappers. `cases.json` joins these files to the exact closed three-depth records in `references/references.json`.

`saved_results.json` preserves checked geometry, history totals, reference comparisons and finite-offset values. `final_projected_components.json` contains exact dyadic true-box projection arithmetic from the final tables. Square roots are rounded displays. All six saved fixed-polygon source and time comparisons pass; this does not certify optimized-source derivatives or first arrival. `intervals/` contains the complete exact edge, vector, projection and endpoint bounds for the three selected final polygons, plus all six dispositions. Starting action and net decrease were not assessed.

All generated source overrides remain explicit alongside Event NC20091537, Origin 2658134, event 463, receiver 28, NC.HQR..EHZ with empty location and the selected channel epoch. The original full QuakeML/StationXML-derived fields remain in every case. Units are km, seconds, km/s and s/km as declared by each numerical field.

`local_history_inventory.json` records the retained large histories without copying them. No process receipts, executables, session logs or machine runtime files are part of this bundle. `manifest.json` pins the delivered scientific files. The exact solver sources and GMP notices are described in [SOURCE.md](SOURCE.md); `interval_source_manifest.json` identifies six byte-identical interval modules. The two removed historical evidence maps and the reference-path change in the public interval records are documented in `intervals/summary.json`; no mathematical bound or native identity changed.

## Portable commands

Run from the repository root with Python 3.6 or newer, using fresh names under `tmp/`. These three entrypoints have been source-reviewed and syntax-checked but **have not been executed**. The numerical results above come from the separately completed original executions and saved readbacks, not from these new wrappers.

```sh
mkdir -p tmp
python3 -B data/development/lom24104_endpoint_mesh_results_001/summarize.py \
  tmp/FRESH_endpoint_mesh_summary.json
```

This stdlib-only command reads the six final tables and exact reference intervals. It recomputes the full ordinary-vector physical-box norm, residual concentration, first-edge length, and fixed-polygon time/source comparisons. It does not rescan optimization histories or replace the completed independent history/witness readback. Exact fractions are retained; square roots are display values.

```sh
python3 -B data/development/lom24104_endpoint_mesh_results_001/replay.py \
  tmp/FRESH_endpoint_mesh_replay --cxx c++
```

This compiles the unchanged observer once and runs the six supplied starts independently, in roster order, with limits `1000 24 10000`. It prewrites complete identity companions and preserves every bounded result, including nonconvergence. Failures stop the sequence without retry. A final-table summary follows the six helpers. Linux `/proc`, POSIX process groups and signal masks are required for child/group closure. The strict GMP 6.1.2/x86-64 extended-arithmetic requirements in SOURCE.md remain enforced; no runtime library is bundled. Accepted histories remain uncompressed in the fresh output tree and can be large. A new compiler/runtime is not assumed to reproduce the original trajectory bit for bit.

```sh
python3 -B data/development/lom24104_endpoint_mesh_results_001/regenerate_intervals.py \
  tmp/FRESH_endpoint_mesh_intervals
```

This separate command evaluates only the **three bundled final geometries**, not outputs of a new optimization replay: exactly 9,949 final edges, zero starting edges and zero aligned normal moments. It uses the unchanged series degree 8 (nine retained powers), one subdivision and 128-bit outward rounding. The six copied modules include their original NumPy/SciPy import dependencies; those packages must be installed even though no branch enumeration, fitting or optimization is called. The fixed three-depth reference intervals are inputs; this command does not regenerate them. Full mathematical results and partial failure records are preserved in the fresh output tree. No local minimum, net-descent, optimized-source derivative or first-arrival conclusion follows from this final-only assessment.
