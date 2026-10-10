# Internal velocity ridge beside two rejected paths

The preserved Hayward trial paths for events `NC518943` and `NC519264` at
`NC.CMJ..EHZ` contain 31 and 32 internal nodes within one millimetre of the
internal grid plane `x=0`. The smallest distances are approximately
`3.34e-11` and `1.54e-10` km. These are numerical path coordinates, not
observational position accuracies. Both original local convergence flags
remain false.

At the projection of each of these 63 nodes onto that face, the rejected
model's velocity increases toward the face from the left and decreases
away from it on the right. The adjacent x coordinates are -3, 0 and 5 km.
At fixed y and z, bilinear interpolation on each face gives velocities
`v_minus`, `v_zero`, and `v_plus`. The one-sided slopes are
`(v_zero-v_minus)/3` and `(v_plus-v_zero)/5`, in inverse seconds.
All left slopes are positive and all right slopes are negative. Thus the
reciprocal-velocity integrand has a cusp minimum across this face.

[analyze.py](analyze.py) calculates these slopes with exact rational arithmetic
on the recorded binary64 coordinates and velocities; [summary.json](summary.json)
records the results and input hashes. [near_face_nodes.csv](near_face_nodes.csv)
retains every selected original node, all native source/receiver metadata,
and the added face slopes. The one-millimetre selection is a descriptive
inventory, not a solver tolerance or a snapping operation. No path, model,
status flag or solver input changes.

This calculation identifies a nonsmooth model feature beside two failed
paths. It does not establish that this feature caused either stopping
failure, that the paths are stationary, that their travel times are first
arrivals, or that all 181 rejected rays share a mechanism. It uses no new
field, ray, optimization, endpoint derivative or inversion evaluation.

Inputs are the immutable prepared copies in
`../hayward_trial_cmj_old_D_replay_001/inputs/`, themselves taken from the
preserved first rejected Hayward trial. To repeat the calculation, copy the
script to a fresh sibling package below `data/development/` and execute it
with `PYTHONDONTWRITEBYTECODE=1 python3 NEW_PACKAGE/analyze.py` from the
repository root. It refuses to overwrite either numerical output.
