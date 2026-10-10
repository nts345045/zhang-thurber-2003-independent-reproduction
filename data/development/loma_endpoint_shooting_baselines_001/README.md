# Supplemental retention of four invented mixed baselines

This completed replay closes the original shooting package's omitted
unperturbed mixed trajectories. It uses the exact frozen original shooting
source and matching Python/NumPy/SciPy runtime, cell, initial guesses, ODE
settings and branch selection. Only four baselines are evaluated: mixed
one-cap and mixed both-bottom fixtures at the two original ODE settings.
No perturbed model, native geometry, production code or inverse calculation
is evaluated or changed.

All four selected candidates are retained with complete attempted candidates,
integrated actions, original-node kernels, endpoint momenta and sampled paths
in `baseline_candidates.json`. All 102 stored baseline components from the
[original comparisons](../loma_endpoint_shooting_controls_001/perturbations.json)
match exactly. Using the supplemental action with the original saved perturbed
actions reproduces all 18 old mixed boundary secants exactly. There are zero
component or secant mismatches. `comparison.json` retains every comparison.
The original six affine boundary secants already have full baseline paths in
the original package and were not replayed here.

`summary.json` pins this helper, the original frozen numerical source and
original input/execution/summary/comparison bytes, along with every supplemental
output. `inputs/` and `source/` preserve the consumed files. The two executions
remain distinct; the original summaries, finite-step failures and readback are
unchanged. This matching replay fills the retention gap but is not an
independent ODE implementation or an additional accuracy certificate.

The original limitations still apply: one matched root per topology, numerical
sampled-domain/reaction checks, no branch completeness proof, and no native or
production correction. All 24 original raw boundary discrepancies remain above
3e-6 s/km at their declared finite steps.

To reproduce, choose a fresh output directory from the integration worktree:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=tmp/matplotlib tmp/waveform_env/bin/python -u diagnostics/replay_endpoint_shooting_baselines.py --output data/development/loma_endpoint_shooting_baselines_NEW
```
