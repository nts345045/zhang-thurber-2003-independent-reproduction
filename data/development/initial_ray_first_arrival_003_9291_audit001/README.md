# Initial Hayward ray 9291: interface approach and refinement

The completed initial linearization in `hayward_first_arrival_003` has 139
failed local stopping tests among 14,262 rays. This diagnostic selects the
largest reported projected gradient: absolute observation row 9291, event
`quakeml:NC.anss.org/Event/NC/390228`, channel `NC.CCY..EHZ`.
`identified_ray.csv` retains the complete observation identities, native
metadata epochs, source and receiver records, and coordinates. Calculated
path and history rows join it through `observation_index=9291`.

The frozen original executable's core is instrumented with observation hooks.
All eight comparisons against the uninstrumented trace agree exactly in
action, path, source/model derivatives, path lengths, stopping flags and
iteration counts. The selected 0.5 km, 1,000-update result matches the
completed full-cohort initial linearization at its saved output precision.
No original run, input, or convergence flag is changed.

At 0.5 km field/path spacing the FMM-started candidate rejects its next line
search after 208 accepted updates, at time 3.645674500808567 s and gradient
0.002799002283 s/km. Raising the maximum from 1,000 to 4,000 changes nothing.
The straight-started candidate exhausts both budgets. Its action changes by
only about 1.1e-11 s between those budgets, despite a gradient above 0.001 s/km.

Two adjacent FMM-path knots approach the 4 km grid-depth interface to within
2.18e-13 km. Their approximately 1.01 km connecting segment is almost
horizontal. The saved gradient is evaluated on one side of the velocity-gradient
change, while finite differences at ordinary steps cross it. These central
finite differences do not estimate the same limiting derivative as the
one-sided ordinary gradient. The history shows very small quasi-Newton steps
and the unchanged line-search rejection.

With both field and initial path spacing reduced to 0.25 km, the FMM-started
candidate meets the unchanged **combined** stopping criterion after 41 updates;
the straight-started candidate takes 163. The FMM action is
3.645534035367894 s, 0.140465 ms below the coarse selected action. Its projected
gradient is 5.45916e-6 s/km, above the separate strict 1e-7 criterion.
The 1,000- and 4,000-budget results agree because they stop earlier.

This is a discretization and optimizer diagnostic for one identified ray,
not a claim that all 139 failures or all first arrivals are resolved.
The neighboring `initial_ray_first_arrival_003_9291_midpoint001` control
inserts free midpoints without changing the curve and tests an exact
depth-directed variation. An independent continuous layered reference
comparison is a separate artifact.

`summary.json` records the command arguments, recorded child exits, input and
source hashes, all eight results, and matching checks. `source/` contains
the frozen implementation and observer. `instrumentation.diff` and
`driver_adaptation.diff` show every diagnostic adaptation.
Reproduce with `diagnostics/run_initial_ray_diagnosis.py --run first_arrival_003
--observation 9291 --variant NEW_NAME` from the repository root, preserving
the frozen parent run and using a fresh output name.
