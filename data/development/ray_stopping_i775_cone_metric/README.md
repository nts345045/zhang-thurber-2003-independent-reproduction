# Preserved first full-cone run

This is the first complete four-case full tangent-cone metric comparison for identified event NC403533 / NC.CMO..EHZ (observation 9692). Complete native provider IDs and epoch metadata are in `identified_ray.csv`; all tables join through `observation_index`. Source and input hashes, the exact generated optimizer snapshot, raw histories, KKT records and unobserved-control equality checks are preserved.

All four cases reach the unchanged ray stopping rule, and all 40 observed directions are negative. The subsequent guarded variant adds an explicit outer strict-descent check and produces byte-identical final `results.csv`. Its complete scientific interpretation, limitations and reproduction commands are in `../ray_stopping_i775_cone_metric_descent_guard/README.md`. This earlier evidence remains unchanged. No production integration follows from these isolated comparisons.
