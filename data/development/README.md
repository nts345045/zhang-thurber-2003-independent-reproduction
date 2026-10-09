# Development evidence

The current external-input checks, native cross-epoch receiver tests, all 48
numerical validation results, and Hayward initial-ray preflight are described in
[`external_input_checks.md`](external_input_checks.md). Their result files and
provenance distinguish completed checks from the superseded histories below.

## Superseded numerical histories

These saved iteration histories document an interrupted development run. Rejecting a
whole update if any source left the domain prevented progress for other
sources once an event reached a boundary. The final implementation projects
individual trial source coordinates to the declared rectangular domain.
The standard and DD runs were stopped deliberately to apply this correction.
The preliminary loc1d run finished, but its results are excluded from final
figures. Final files are regenerated under `data/synthetic/` by `rebuild.sh`.

## Source-derivative numerical diagnostic

`source_derivative_step_sweep.csv` records a diagnostic after the paired-difference
interpolation-gradient correction. It is not a manuscript-panel input. The
sandwich-medium ray connects (-10,-20,8) to (20,15,0) km, uses 0.6 km initial
segments, and varies ray iteration limit and source finite-difference step.
The independent reference integrates the conserved-transverse-slowness ray
through constant/linear velocity segments; its implementation is
`sandwich_snell_reference()` in `src/ray_checks.hpp`.

At 600 iterations the 0.1, 0.03, and 0.01 km finite differences agree with
the source derivative within 0.000153 s/km, while a 0.001 km perturbation
amplifies finite ray-discretization/optimization errors to 0.00350 s/km.
Increasing the iteration limit does not guarantee convergence of that small-step
finite difference because optimized path-node distributions can differ.
The validation source perturbation is therefore 0.01 km, with its original
0.003 s/km acceptance tolerance; the velocity perturbation remains 0.001 km/s.
Direct checks against the independent Snell reference also test the source
derivative without subtracting nearly equal numerical travel times.

Regenerate this optional diagnostic from the project root with the current
implementation and reference helper, without changing archived or final data:

```bash
mkdir -p tmp
TMPDIR="$PWD/tmp" g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic diagnostics/source_step_sweep.cpp -o tmp/source_step_sweep
./tmp/source_step_sweep tmp/source_derivative_step_sweep.csv
```

The generator writes all 12 iteration-limit/source-step combinations with
17-digit output. The archived diagnostic was transcribed from 12-digit
numerical output, so comparisons should allow for that output rounding.
