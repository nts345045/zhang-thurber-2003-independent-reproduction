# Refinement of identified initial Hayward failures

All four calculations preserve the same 139 failed rays, original native event/pick/channel identities and epochs, and frozen preflight003 executable. Each uses the unchanged 1,000-update budget. No station or event is excluded.

Every continuous layered reference is complete, valid, and unique for this subset. The limits below are the existing analytic controls: absolute time error <=25 microseconds and Euclidean source-derivative vector error <=3e-6 s/km. The local stopping flag is a separate measurement.

| Variant | Path km | FMM field km | Local passes /139 | Time passes /139 | Source-vector passes /139 | Both /139 | Max time error us | Max source-vector error s/km |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [001](hayward_initial_failure_refinement_001_reference/summary.json) | 0.25 | 0.25 | 134 | 122 | 114 | 114 | 54.041013 | 9.80324293e-05 |
| [002](hayward_initial_failure_refinement_002_reference/summary.json) | 0.125 | 0.5 | 139 | 139 | 123 | 123 | 13.074503 | 2.87222264e-05 |
| [003](hayward_initial_failure_refinement_003_reference/summary.json) | 0.0625 | 0.5 | 139 | 139 | 136 | 136 | 3.266713 | 4.92239021e-06 |
| [004](hayward_initial_failure_refinement_004_reference/summary.json) | 0.03125 | 0.5 | 139 | 139 | 139 | 139 | 0.818113 | 1.83424088e-06 |

The 0.25 km variant changes both path and field spacings. The other three change only path spacing relative to the 0.5 km initialization field. All results, including failed thresholds, are retained.

Each `hayward_initial_failure_refinement_NNN/` directory contains the completed execution record, identified observations, original failed rows, and saved Jacobian. Its corresponding `_reference/` directory freezes the inputs and Python sources, retains all reference candidates in `references.jsonl`, and adds errors to every original identified row in `comparison.csv`. `original_observation_row` maps back to the full preflight. The 002 comparison also contains an independent native-join and derivative-norm review.

Run the frozen solver subset with `PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/refine_initial_failures.py --run first_arrival_003 --variant NEW --spacing 0.03125 --field-spacing 0.5`. Then compare it using `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_refined_initial_failures.py --data data/development/hayward_initial_failure_refinement_NEW --output data/development/hayward_initial_failure_refinement_NEW_reference`. Choose fresh names; the helpers refuse to overwrite previous variants.

This evidence does not validate all14,262 rays, later three-dimensional models, or an inversion. The complete initial reference finds substantial errors outside this subset, including a locally converged row14099. See [the full reference](hayward_first_arrival_003_1d_support/summary.json) and [terminal preflight review](hayward_first_arrival_003_review/README.md).
