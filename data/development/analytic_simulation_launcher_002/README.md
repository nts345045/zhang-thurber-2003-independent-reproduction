# Frozen analytic simulation launcher: interruption and replay guards

Fourteen checks passed. Twelve repeat the first invented smoke test after
the interruption-handler correction. Two additional checks send SIGTERM to
the actual driver during a separate CMake compilation: the terminal ledger
records interruption and the reaped child return code, all prepared inputs
remain byte-identical, and no synthetic output is written. The intentionally
interrupted build is preserved, not reported as a completed simulation.

The positive fixture runs the actual frozen C++ executable with two invented
events, two invented receivers, and eight synthetic observations. No real
Loma observations or inversions are produced. `summary.json` pins the
sources, original prepared bytes, completed simulation, and interrupted
attempt. Both source versions received an independent read-only review;
the corrected exception handler had no remaining review issue.

Reproduce in fresh project-local directories:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_analytic_simulation_launcher.py --output data/development/analytic_simulation_launcher_NEXT --build tmp/analytic_simulation_launcher_NEXT
```

For a separately prepared and independently reviewed real geometry bundle,
the maintained launcher is:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 run_loma_analytic_simulation.py --data data/FRESH_PREPARED_BUNDLE --build tmp/FRESH_SIMULATION_BUILD --threads 4
```

It reserves `simulation_execution.json` exclusively, freezes source and build
provenance, rechecks prepared hashes immediately before consumption, retains
both mutable originals, and checks immutable files after simulation. A
completed ledger explicitly awaits independent output review. It does not
start an inversion or accept the inverse forward operator.
