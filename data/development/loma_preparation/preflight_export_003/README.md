# Identified initial-ray export with the matrix census

The matrix-only preflight now saves source travel-time derivatives, the separate
source origin correction, path-point count, domain membership, and exact endpoint
flags in `dd_preflight_ray_status.csv`. The export uses the same ray objects as
the matrix census. All native event/origin/channel/epoch fields remain present.
Pure travel time excludes the origin correction. Other status exports retain
their existing bytes.

The existing invented fixture checks four rays and eight synthetic observations.
Exported times and all source partials agree with the homogeneous analytic
solution within the 12-significant-digit output precision. Nonzero source times
remain separate. Empty paths, out-of-domain and nonfinite vertices, one-ULP
endpoint changes, false local flags, and sparse native-index order are retained
and distinguished. Native identities and empty epoch/location fields survive.

Against frozen commit `e097c11`, the matrix census, existing preflight status
fields, simulation status, observations, initialization, and arrival values are
unchanged. The preflight writes no inverted model or accepted-step history.
Local-convergence failures remain visible; completing a census does not accept
them or establish first-arrival accuracy. Full continuous-reference and sampled
refinement checks remain separate requirements.

Reproduce in a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_simulation_gate_checks.py \
  --variant preflight_export_NEW --baseline e097c11
```

`summary.json` records source, artifact hashes and commands. The first attempt
(`../preflight_export_001/`) failed to compile because the test used the wrong
CSV helper name. The second (`../preflight_export_002/`) passed the current
component checks but omitted `pair_distance` from the comparison configuration.
The third serializes the actual complete configuration and passes every check.
Both failed attempts remain preserved; neither was a real-data calculation.
