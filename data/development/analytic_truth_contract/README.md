# Explicit identified analytic truth

The optional command is:

```sh
dd simulate CONFIG OUT --analytic-truth BUNDLE
```

The default command retains its production polygon-ray gate. The explicit
alternative requires `BUNDLE/references.csv` in the existing full layered
reference schema and the exact reference inputs under
`BUNDLE/inputs/{truth_grid,truth_events,stations}.csv`. It is intended for the
exactly x-dependent synthetic truth model. The initial inverse model may vary
with depth and is neither replaced nor assumed homogeneous.

The C++ consumer checks a positive finite x-only grid, all model coordinates
and nodal values, every source/receiver position and native metadata field,
zero reference origin times, and the full ordered event-major pair inventory.
Every reference must be complete and valid, have one uniquely selected
minimum at the reference's stated near-tie scale, and retain a known branch,
finite nonnegative time, finite signed source derivatives and an admissible
turn when applicable. A positive-speed travel-time bound supplies an additional
consistency check. These checks do not independently prove the reference
mathematics. The Python preparation/execution wrapper must verify immutable
artifact and mathematical-source hashes immediately before use and recheck
inputs afterward; C++ adds no cryptographic or JSON dependency.

Accepted reference times enter the existing C++ rounding, station-bias,
picking-noise and differential-observation code in exactly the original order.
The analytic mode creates `simulation_truth_status.csv`, preserving every
identified reference row, and `simulation_truth_mode.txt`. Its arrivals carry
the explicit `continuous_layered_snell_reference` mode and reference-pair
indices. Ray-status columns are empty: no path or convergence flag is
fabricated. The compact 18-field synthetic observation metadata remains
unchanged and includes no invented provider pick IDs.

This optional source does not relabel a failed polygon preflight or lower any
ray tolerance. Existing simulation outputs cannot be overwritten. Inverse
forward-ray validation remains necessary. Reference time ordering uses
floating-point actions; an accepted identified table is distinct from a
general 3D first-arrival certificate.

## Preserved checks

`001` retains a Python runner failure caused by applying `Path.relative_to`
to a relative `__file__`. It occurred before source copying, compilation or
numerical execution. The failing runner and its hash are saved.

`002` uses an invented homogeneous truth and a depth-varying initial grid.
All 55 named checks pass. They cover actual CLI dispatch; complete and rejected
table inventories; wrong native IDs, epochs and geometry; malformed values;
nonzero reference origins; unsupported models/branches; explicit truth status;
blank ray fields; preservation of an earlier failed geometry marker; and
unchanged synthetic noise/observation identities. Six default-mode outputs
match a frozen pre-change solver byte for byte. Analytic and ordinary modes
also produce identical noisy observations and initial perturbations in this
controlled fixture. Both compilations complete without warnings.

The independent review verifies 80 output hashes, 19 frozen source hashes,
all 55 check results, the six legacy comparisons and the full analytic/native
status joins. It runs no additional solver. These fixtures use no actual
Loma arrivals and generate no production observations.

Reproduce with a fresh variant:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_analytic_truth_checks.py --variant repeat
```
