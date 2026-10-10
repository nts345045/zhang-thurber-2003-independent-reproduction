# One tangent metric trial on each prescribed CMJ polygon

This package is **source and preparation only**. It has not evaluated a native
metric, direction, trial or action. Execution requires an independent
`prelaunch_review.json` with `status: passed` bound to `prepared.json`.

The only cases are events 981 and 987 at receiver 160 (`NC.CMJ..EHZ`), starting
from the independently reviewed exact-face candidate polygons in
`../hayward_cmj_face_action_001`. Their 1029 and 1031 nodes, endpoints and
31 and 32 unavailable x-normal slots remain identified in the saved inputs.
The full failed-state source and receiver metadata are distinct from provider
catalog coordinates. `native_contexts.json` attaches every original catalog
row/side use, including both epoch indices and the shared DD row 16943.

## Fixed calculation and limits

The unchanged reviewed 002 binary supplies one metric solve per eligible case
and at most one rounded trial. There is no compilation. The unchanged Python
helpers use all available saved tangent intervals, exact zero displacement
on unavailable normals, fixed endpoints and the full principal metric
diagonals. This is a feasible search subspace for one experiment, not a new
physical constraint or definition of stationarity.

The complete interval contraction must be strictly negative before choosing
the single geometry-bounded step. The actual separately rounded displacement
must also have strictly negative contraction before action evaluation. The
full trial action uses the original trilinear velocity with exactly 8 series
terms, 1 subdivision and 128-bit dyadic interval rounding. It reuses identical
ordered starting edges and evaluates at most 1028 + 1030 = **2058** new edges.
No tangent integral is recomputed. The conservative Armijo comparison retains
the existing binary64 coefficient `1e-4`, nominal slope and actual rounded
trial action. Nominal slope and actual displacement are reported separately.

Every unresolved interval, ineligible start or arithmetic failure is retained.
There is no second direction, line search, retry, integration escalation,
resampling, trace, field construction, source/model partial, inverse update,
normal-support optimization or stopping decision. Original convergence flags
remain zero and candidate convergence remains null. A decrease applies only
to the newly recorded diagnostic polygon.

## Joins, outputs and lifecycle

Before numerical imports, `run.py` checks original text through binary64 into
exact rationals, all model nodes, complete contexts, both fixed endpoints,
ordered candidate edge/action joins and the complete starting-action sum.
Each available tangent interval must equal the sum of both incident saved
edge contributions and match the directly pinned sparse `tangent_norms.json`.
Its exact availability mask is also rechecked by the unchanged helper against
the actual candidate geometry. Every one of the nine catalog uses per event
is preserved with original row text, pick/association IDs and both epoch joins.

Per-case output is `event_EVENT/result.json.gz`, embedding all native context,
catalog uses, coordinate provenance, starting evidence and the complete
single-trial result or failure. Raw helper files are
`event_EVENT/metric/{input.txt,stdout.json,stderr.log}` and, only if reached,
`event_EVENT/round/{input.txt,stdout.json,stderr.log}`. Every numeric file has
an identifier sidecar **before its helper starts**. Expected output paths are
declared first; actual byte hashes are recorded only after the child is reaped
and its streams are closed. No prelaunch output hash is invented.

The wrapper owns each child process group, reaps normal and failed children,
and refuses to freeze output hashes while a group can still write. It refuses
any existing execution, summary or case directory. `execution.json` records
commands, return codes, reaping, environment and terminal hashes;
`summary.json` keeps complete identities and the bounded calculation status.
Root owns and reaps the outer wrapper process separately.

The exact command and runtime hashes are in `prepared.json`. From the project
root, after review, the sole intended command is:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 data/development/hayward_cmj_tangent_step_001/run.py
```

All referenced inputs are immutable existing project files. The wrapper
directly reuses the reviewed 002 binary and frozen mathematical sources.
Preparation performs no native numerical calculation.
