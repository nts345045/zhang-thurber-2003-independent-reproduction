# Isolating the combined stopping rule for initial row 8147

This experiment retains the frozen Hayward preflight 003 model, event, native receiver epoch and both starting paths for original observation row 8147 (event index 671, receiver epoch 13, `NC.CBR..EHZ`). The event/origin/pick/arrival resource IDs, full SEED/FDSN channel identity and epochs accompany every comparison row; the complete original and geometry metadata are in each run's `identified_ray.csv` and `review.json`.

The control uses the unmodified frozen core. The isolated strict copy changes exactly one condition: it disables the combined action decrease below 1e-11 s and projected gradient below 1e-5 s/km. The original strict projected-gradient criterion below 1e-7 s/km remains. Objectives, quadrature, gradients, metric, updates, line searches, admissible paths and initial seeds are unchanged. This is a diagnostic source patch; production files, frozen preflight binaries and configurations were not modified.

Both straight and second-order FMM starts were tested with path spacings 0.125 and 0.0625 km, fixed FMM spacing 0.5 km, and budgets of 1,000 and 4,000 updates. Each observed trace was compared exactly with its unobserved counterpart: all 16 comparisons preserve path, time, source and model derivatives, lengths, reported gradients, update/merge counts and stopping flags. The selected controls also reproduce the previously saved 139-ray refinements at their 12-significant-digit output precision.

The independent continuous 1D reference has a unique valid turning arrival at 2.523685961203169 s, reaching depth 4.000222390889434 km. The source is at 3.985 km. The comparison uses the same actual grid-adapted profile as preflight 003, including its change in vertical velocity gradient at 4 km.

| Path spacing (km) | FMM-start condition | Accepted updates | Final projected gradient (s/km) | Time error (microseconds) | Source-vector error (s/km) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0.125 | Original combined stop | 13 | 2.1553e-6 | 8.8365 | 2.8722e-5 |
| 0.125 | Strict, 4,000 budget | 4,000 | 3.4747e-7 | 8.0598 | 3.2151e-5 |
| 0.0625 | Original combined stop | 16 | 2.0687e-6 | 2.2117 | 4.9224e-6 |
| 0.0625 | Strict, either budget | 597 | 3.0578e-7 | 2.0823 | 9.5955e-6 |

All eight strict runs fail the retained 1e-7 stopping criterion. Six exhaust their iteration budgets. Both repeats of the 0.0625 km FMM start exhaust the 24-trial line search after 597 accepted updates; the observation history records that failure explicitly. The original combined rule stops all eight controls at the same results for either budget.

Further optimization lowers the polyline action but does not repair the source derivatives for this ray. Halving the path spacing improves travel-time error by approximately a factor of four, consistent with a discretization contribution. Because strict stationarity remains unresolved, this experiment cannot isolate the error of a fully optimized fixed polyline. It does not establish the cause of all 16 earlier derivative failures or of rays in updated three-dimensional models. The unchanged analytic limits are 25 microseconds in time and 3e-6 s/km in the Euclidean norm of the three source derivatives; every time passes and every source vector fails in this experiment.

## Reproducibility

`check.py` validates every captured artifact hash, exact native geometry, the one-line core patch, all observer parities, prior-control parity, and the history evidence for termination. It recomputes the single continuous reference using the frozen module in `source/`, then writes `comparison.csv` and `review.json`. The table includes both starts and budgets; the prose table above only summarizes the selected FMM controls.

The sibling directories `../initial_ray_first_arrival_003_8147_strict_control001/` and `../initial_ray_first_arrival_003_8147_strict_gradient001/` preserve their source snapshots, patch and instrumentation diffs, original control core, exact paths, optimizer histories, metric diagnostics, finite-difference checks, native ray and model, and compiler/run output. Each is packaged without changing member bytes in `frozen_artifacts.tar.gz`; its `packaging.json` verifies every member against the executed run summary. Expand both archives in their respective directories before rerunning `check.py`.

The executed commands were:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_initial_strict_stop.py --run first_arrival_003 --observation 8147 --variant strict_control001 --spacings 0.125,0.0625 --budgets 1000,4000 --field-spacing 0.5
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_initial_strict_stop.py --run first_arrival_003 --observation 8147 --variant strict_gradient001 --spacings 0.125,0.0625 --budgets 1000,4000 --field-spacing 0.5 --strict-gradient-only
```

The launcher refuses to overwrite existing output directories. A rerun needs distinct variant names and the original frozen preflight inputs/source layout. The saved-table check does not run the optimizer or require the frozen executable.
