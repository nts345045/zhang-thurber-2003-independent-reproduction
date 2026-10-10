# A depth variation missing from the retained coarse path

This is a fixed-path variation, not another optimizer. It uses the saved
0.5 km FMM-started Hayward observation 9291 path from the neighboring
`initial_ray_first_arrival_003_9291_audit001` experiment. The unchanged
`identified_ray.csv` sidecar carries the event, origin, pick, channel SEED
and FDSN identifiers, metadata epochs, and coordinates. Every output row
joins that sidecar through `observation_index=9291`.

A midpoint is inserted into each of the 38 straight segments in turn.
This represents the same physical curve with one extra degree of freedom.
The exact integrated action changes by at most 3.04e-18 s from insertion.
The new midpoint is then moved in positive depth by declared amounts;
neither original knot nor any endpoint moves, and no point is snapped to
an interface. All tested points remain in the original model box.

Segment 15 connects knots at depths 4+2.18e-13 and 4+1.38e-13 km. Its
inserted midpoint has depth gradient −0.001645448839 s/km. A 1e-7 km depth
perturbation gives an exact action-difference slope of −0.001645412695 s/km;
a 0.001 km perturbation lowers travel time by 1.283941 microseconds.
Thus the retained coarse edge omits a feasible descent variation.

The physical reason is that velocity increases on the deeper side of the
interface. A small midpoint depth tent has zero first-order length cost
at a horizontal segment but lowers slowness over a finite length. A stopping
certificate restricted to the old knots would not address this variation.
The actual saved segment is slightly off the interface; the calculation
uses its exact saved coordinates and evaluates the variation directly.

The depth-only field permits independent exact straight-segment integrals.
A coordinate permutation maps depth to the exact helper's x coordinate;
Euclidean length and the model are unchanged. Across all 190 insertion and
perturbation cases, production quadrature and the exact action agree within
1.06e-15 s. This excludes an action-integration discrepancy at the tested
scale; it does not certify all ray derivatives or global branch selection.

`midpoints.csv` retains all segments and perturbations, not only the selected
counterexample. `summary.json` records input/source hashes, commands and child
exits; `source/diagnostics/check_initial_ray_refinement.cpp` is the frozen
control. Compile with C++17, OpenMP and `-lstdc++fs`, then call the executable
with `initial_grid.csv input_paths.csv fmm_0.500000_1000 NEW_OUTPUT.csv`.
Preserve `identified_ray.csv` alongside the calculated output.
