# Fixed selected-path gradient decomposition

This diagnostic evaluates the two old and two D selected polygons from the completed [CMJ replay](../hayward_trial_cmj_old_D_replay_001/RESULTS.md). It makes exactly four `path_eval` calls against the respective frozen source snapshots. No trace, field, optimization, perturbation, inverse or path change occurs. The replay's derivative-disabled status, blank source partials and false flags remain unchanged. Recomputed quantities are explicitly diagnostic free-knot gradients, not source or model partials.

For each saved polygon, the unchanged `path_eval`, `norm` and `projected_ray_gradient` must reproduce both recorded norms at 17 digits before analysis continues. The per-node table retains every original path field and native identifier. Fixed endpoints have blank gradient fields because the original free-knot vector omits them. Projected components follow the original box-direction projection and sign convention exactly.

The descriptive selection is all free nodes with `abs(x)<1e-6 km` beside the internal x=0 face. With exported binary64 components interpreted as exact rationals, the reported fraction is

`sum_selected gx^2 / sum_all_free_nodes (gx^2 + gy^2 + gz^2)`.

Raw and projected versions, separate axis contributions, all-axis near-face contributions and the largest 20 components under each norm are retained. Exact squared sums of the recorded components need not equal the square of the rounded production norm. The selection does not snap a path or introduce a stopping tolerance. A large fraction would localize the reported norm; it would not certify nonsmooth stationarity, prove a cause of failure or establish first-arrival accuracy.

Pairs are event 981 (`quakeml:NC.anss.org/Event/NC/518943`, origin `quakeml:NC.anss.org/Origin/NC/4251144`) and event 987 (`quakeml:NC.anss.org/Event/NC/519264`, origin `quakeml:NC.anss.org/Origin/NC/4252064`) at receiver 160, `NC.CMJ..EHZ` / `FDSN:NC_CMJ__E_H_Z`, blank location, epoch 1996-11-12T23:45:00–1998-06-09T19:30:00. Full native fields and original statuses accompany the outputs.

`prepared.json` pins this source and the completed replay's exact paths, grid, statuses, source snapshots, terminal review, compiler and runtime. `run.py` requires an independent passed preparation review and refuses an existing execution ledger. It uses the previously reviewed process-group cleanup, verifies pins before and after evaluation, and preserves any failure. In a fresh copy of this prepared package under the project root, execute `PYTHONDONTWRITEBYTECODE=1 python3 run.py` from its directory. The referenced completed replay package must also be present unchanged.
