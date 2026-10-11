# Guarded catalog-only Hayward comparisons

The two comparisons use the original 58,980 catalog rows, 1,092 sources,
372 receiver epochs and 14,262 native rays. They reuse the frozen C++ source
in `../hayward_corrected_rebuild_sources_001/source/` and the exact preparation
and child-process handling in `../../../rebuild_hayward_corrected.py`.
No production numerical source is changed. The additional entrypoint prepares
the catalog, checks its original scientific bytes, compiles a fresh copy and
attempts one selected mode. It appends no waveform measurements.

`standard` uses absolute observations and solves for event and velocity
parameters. `loc1d` retains the initial velocity grid and solves only for event
parameters. Its three six-iteration stages use the original catalog-only
absolute/catalog multipliers `(1, 0.1)`, `(0.1, 1)` and `(0.1, 1)`.
Standard tomography excludes differential rows and uses unit stage factors.
Robust weighting, damping, smoothing where applicable, twelve trial fractions,
the 1,000-update ray budget and current/trial/final ray guards remain unchanged.

The [full initial reference comparison](../hayward_first_arrival_004_1d_support/README.md)
passed all 14,262 original rays. The same native inputs, effective configuration
and mathematical kernel apply here. The accepted-state export in the frozen
main program only adds output. This initial evidence does not certify later
moved sources, three-dimensional velocity updates or nonlinear convergence.

From the repository root, run each mode with its own fresh destinations:

```sh
python3 -B run_hayward_catalog_comparison.py --mode standard \
  --preparation-python /path/to/compatible/python3.6 \
  --output data/FRESH_hayward_standard --build tmp/FRESH_hayward_standard
python3 -B run_hayward_catalog_comparison.py --mode loc1d \
  --preparation-python /path/to/compatible/python3.6 \
  --output data/FRESH_hayward_loc1d --build tmp/FRESH_hayward_loc1d
```

Use the preparation runtime documented in the shared source package, with
NumPy and Requests. CMake, C++17/OpenMP and Linux process groups are required.
Each attempt uses four OpenMP threads and the existing 128 GiB address-space
limit. All caches and generated process records stay in the fresh build tree.
Existing output/build destinations are refused. There is no automatic retry.

After actual child closure, `comparison_outcome.json` records the observed
exit, any failed stage, exact source/input/output hashes and whether outputs
are stable. It always leaves scientific success unclaimed. The method prefix
is `standard_` or `loc1d_`: inspect its history, accepted event/grid snapshots,
trial ledgers, preserved failures and any conventional final tables. History
metrics describe the pre-update state. A separate saved-output review is
required before an accepted state or final model is reported. This entrypoint
does not calculate covariance or compile a report.

The new entrypoint is pending source review and has not been executed at this
preparation checkpoint. Existing lifecycle tests belong to the exact shared
helper; they are not new comparison outcomes.
