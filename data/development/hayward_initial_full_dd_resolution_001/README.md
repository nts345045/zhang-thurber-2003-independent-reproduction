# Initial-model full-DD resolution and shared-pick noise

This package contains a completed **initial-model, stage-0, catalog-only** linear
resolution calculation. It is not a final inverse result, a nonlinear covariance
estimate, or a manuscript-panel promotion. [RESULTS.md](RESULTS.md) gives the
scientific outcome and limits; [PLOT.md](PLOT.md) documents the separate display.

The 58,980 observations comprise 14,262 absolute picks and 44,718 catalog
differences. There is no normalized cross-correlation input. The chosen initial
stage multipliers are 1 for absolute rows and 0.1 for catalog DD rows, before
the saved robust/distance factors. The calculation retains the exported 0.005 km
path-length-difference mask, coupled source parameters, smoothing and damping
with the original column scales. The provider's symmetric timing uncertainties
are assumed to be one standard deviation; this assumption concerns uncertainty
scale, not instrument-response calibration.

`scientific_manifest.json` binds the six closed result/identifier files in
`data/`. `replay_inputs.tar.gz` contains the twelve original CSV inputs needed by
the unchanged numerical script, plus the export config and native-ID marker.
`replay_inputs.json` records every member's exact bytes, mode and SHA-256.
The complete identifier companion preserves all event/origin, pick/arrival and
channel SEED/FDSN/epoch records, including valid blank locations and distinct
second-side epochs. Both matrix axes follow its saved model-node order; pick
columns follow its explicitly recorded primitive-pick order.

## Replay the matrix calculation

Use a Python environment with NumPy and SciPy. The recorded calculation used
Python 3.11.9, NumPy 2.4.6 and SciPy 1.17.1. From the repository root, with that
environment's interpreter available as `python`:

```sh
python -B data/development/hayward_initial_full_dd_resolution_001/replay_resolution.py \
  --output tmp/FRESH_initial_full_dd_resolution
```

The helper refuses existing destinations and symlink traversal, verifies the
archive and exact member roster, restores all fourteen inputs, and copies both
full identifier companions. It then replaces itself with one invocation of the
unchanged, hash-checked `resolution_full_hayward.py --mode initial`. OpenMP and
OpenBLAS use one thread; caches and temporary files stay in the fresh tree.
The four results appear under `tmp/FRESH_initial_full_dd_resolution/data/`.
No ray tracing, waveform request, reference enumeration or inversion is run.
Any failed attempt remains in its fresh destination; choose a different name
for an independently justified later attempt.

Compare numerical arrays, native IDs and node/pick ordering when replaying.
The result manifest retains the actual input paths, so its bytes change with
the fresh destination; archive-container metadata and numerical libraries may
also affect file hashes. The closed original files are never overwritten.

The documented packaged-input command was executed once successfully in a
fresh destination. Both CSVs, the matrix archive and both identifier companions
were byte-identical to the original results; all four arrays were also checked
bit-for-bit. Only the twelve input-path keys changed in the result manifest.
[The scientific replay comparison](evidence/numerical_replay.json) records the
bindings and outcome. No ray or reference calculation was repeated.

## Regenerate the omitted ray-path evidence

The 19.7 GB table repeating full identities for 11,506,620 path nodes is
preserved locally and bound in `scientific_verification.json`; it is not needed
for matrix replay. Its regeneration is a separate ray calculation, not part of
the command above. The exact exporter source snapshot is
`data/development/hayward_full_dd_geometry_adoption_002/source/`; all eleven
source hashes are recorded in the scientific verification file. A fresh export
can be built and run as follows, without using the maintained solver source:

```sh
mkdir -p tmp/FRESH_initial_ray_export/data
tar -xzf data/development/hayward_initial_full_dd_resolution_001/replay_inputs.tar.gz \
  -C tmp/FRESH_initial_ray_export/data \
  initial_events.csv initial_grid.csv observations.csv stations.csv run.cfg authoritative_ids_required
cmake -S data/development/hayward_full_dd_geometry_adoption_002/source \
  -B tmp/FRESH_initial_ray_export/build
cmake --build tmp/FRESH_initial_ray_export/build -j2
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 tmp/FRESH_initial_ray_export/build/dd \
  linearize_full tmp/FRESH_initial_ray_export/data/run.cfg \
  tmp/FRESH_initial_ray_export/data initial 0
python -B diagnostics/review_full_dd_geometry.py \
  --data-dir tmp/FRESH_initial_ray_export/data \
  --config tmp/FRESH_initial_ray_export/data/run.cfg --mode initial \
  --output tmp/FRESH_initial_ray_export/geometry_review.json
```

Use a genuinely fresh export directory. This is potentially expensive and its
own outputs require review; the original scientific checks do not automatically
certify a different build or new trace. The all-ray time/source comparison in
`evidence/time_source_comparison.csv.gz` refers to the closed original export and
the unchanged published 1D reference evidence identified in the verification
file. Runtime logs and process receipts remain local.
