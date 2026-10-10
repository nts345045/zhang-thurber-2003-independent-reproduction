# LON initial matrix and forward preflight

The separate LON preflight uses the unchanged, independently audited simulation
in `data/loma_lon_analytic_001`. It retains all 724 events, 52 receivers,
37,648 source–receiver rays and 15,932,384 synthetic observations. The 104
diagnostic sample IDs retain their original truth-geometry selection; their
preflight coordinates are the saved perturbed initial coordinates. There are
24 valid central-difference components for the selected initial geometry.

`eligibility.json` pins the complete terminal simulation and independent
simulation review, and verifies the separately completed continuous initial-
profile reference and its independent review in
`../loma_lon_initial_reference_002/`. All 37,648 references are valid and
comparison-ready. This reference result does not establish accuracy of the
yet-uncomputed polygon rays.

The maintained `run_loma_initial_preflight.py` is unchanged from its validated
LOM launch. The current C++ main includes the separately reviewed inverse
forward guard. All numerical headers and CMake are byte-identical to the
running LOM preflight. For matrix-only mode, the main function takes the same
ray and matrix-census path and deliberately retains false local flags for
diagnostic review. The geometrycheck function is unchanged. It performs no
inverse solve or accepted update.

`check.py` compares existing frozen O3 binaries on copied invented inputs.
All seven controls passed. The earlier live-LOM binary and the guarded binary
produce byte-identical history, matrix-census and full ray-status files at
one and four threads. One fixture deliberately has false local flags; another
uses the declared path/FMM spacings and iteration budget. No inverse result
files are produced. The exact sources, inputs, commands, raw outputs and
hashes are preserved in `controls/` and `summary.json`.

The actual preflight settings are path spacing 0.03125 km, FMM spacing
0.125 km, 1,000 local updates, refined receiver batch size four, four threads
and a 128 GiB address-space limit. It uses `iterations=1` and
`matrix_preflight_only=1`, followed by the ordinary factor-two sampled
refinement. These settings are unchanged from the LOM assessment. A failed
local flag remains a scientific failure; hard finite/domain/endpoint/
initializer failures stop the launcher. The original simulation and the
other live jobs remain unchanged.

The authorized separate run command is:

```bash
python3 run_loma_initial_preflight.py \
  --simulation data/loma_lon_analytic_001 \
  --output data/loma_lon_initial_preflight_001 \
  --build tmp/loma_initial_preflight_runs/lon_001
```

The launcher freezes its own source, configuration, compiler, runtime
libraries and new executable before the full matrix preflight. Its terminal
ledger and independent numerical review determine the outcome. This adoption
record does not authorize a LON inverse solve or certify later 3D models.
