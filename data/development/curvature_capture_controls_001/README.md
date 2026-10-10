# Invented neutral curvature-capture controls

All 38 controls passed. The harness reads no authoritative geometry or ray table. It checks the frozen logging hooks using invented telemetry and six small invented homogeneous, affine, and kink-model rays, each with a straight or supplied curved initial path. All returned `Ray` fields, including paths, derivatives, flags, and floating-point bit patterns, agree with the same frozen unobserved trace. This establishes logging parity for these controls; it is not an accuracy or convergence certificate.

The manual records test quoted identifiers and multiline text, 17-digit binary64 and signed-zero round trips, supplied curvature values that differ from exact sums, separate rounded coordinate displacements, strict threshold neighbors, eight-pair eviction and ages, reset events, selected-iteration frames, both adjacent-edge inventories, strict cut predicates, disabled hooks, dimension/memory rejection, and output preservation. Invented telemetry intentionally need not satisfy ray dynamics. The real native context in `prepared.json` identifies the eventual proposed replay and is not used as an invented test input.

The existing `prepared.json` and `source/` were not changed. The maintained harness and runner are copied under `fixture/`; `controls_summary.json` pins those sources, all prepared inputs, compiler, binary, commands, logs, and result tables. Source-map keys are repository-relative; output-map keys are relative to this directory. The independent `controls_review.json` is required separately before a native launch.

Executed from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_curvature_capture_controls.py data/development/curvature_capture_controls_001
```

This command deliberately refuses an existing fixture/results directory. For a fresh reproduction, copy the unchanged prepared snapshot to a fresh variant, use a fresh build directory in a separately frozen runner, or run the recorded compiler and binary commands with fresh output paths. Do not overwrite this evidence. `TMPDIR` was the repository `tmp/`; `OMP_NUM_THREADS=1`. No production source, stopping condition, or physics changed.

Compiler warnings are retained in `fixture/compile_stderr.log`. The fixture has four misleading-indentation warnings from adjacent statements, and the unused renamed frozen driver entry point has a missing-return warning inherited from renaming `main`. The fixture invokes neither that entry point nor authoritative input loading. Compilation and all controls returned zero; warnings are not presented as a clean compiler log.
