# Prescribed CMJ face polygons: prepared action comparison

This package contains source and a concrete plan only. No new polygon has been
evaluated, no tangent component calculated, and no native command launched.
Independent review must precede the proposed calculation. The source is
[check_cmj_face_action.py](../../../diagnostics/check_cmj_face_action.py).
It imports the unchanged, frozen arithmetic from the
[80-check invented package](../trilinear_action_controls_001/RESULTS.md).

## Exact roster and geometry

Use only the two **original old-kernel** paths in the reviewed
[CMJ replay](../hayward_trial_cmj_old_D_replay_001/RESULTS.md), both ending at
receiver 160, `NC.CMJ..EHZ`, `FDSN:NC_CMJ__E_H_Z`. Preserve the empty location
code and channel epoch `1996-11-12T23:45:00` to `1998-06-09T19:30:00`.

| Original event | Event resource ID | Origin resource ID | Path nodes | Selected original nodes |
| --- | --- | --- | --- | --- |
| 981 | `quakeml:NC.anss.org/Event/NC/518943` | `quakeml:NC.anss.org/Origin/NC/4251144` | 1029 | 724–754 inclusive (31) |
| 987 | `quakeml:NC.anss.org/Event/NC/519264` | `quakeml:NC.anss.org/Origin/NC/4252064` | 1031 | 726–757 inclusive (32) |

The selected rows must join byte-for-byte to their original path fields and to
the frozen [near-face inventory](../hayward_cmj_interface_geometry_001/README.md).
The loader does not select nodes using a new distance threshold. It requires
the exact previously reviewed indices. Both original `ray_converged=0` flags,
unevaluated source partials, statuses, native context, source/receiver tables,
and endpoint coordinates are preserved. This is not a D-path calculation.

A separately labeled candidate replaces only the selected x coordinates by
exact rational zero. It keeps y and z, node order, endpoints, and all other
coordinates unchanged. It must remain in the original finite box with positive
edge lengths; no merging is permitted. An ineligible candidate is retained
with all coordinates and explicit reasons, while its action and variation
remain unevaluated. An invalid original input or hash mismatch remains fatal.
The x=0 selection defines a prescribed
trial polygon, not a physical constraint, stopping tolerance, or new solution.
Candidate convergence status is absent, rather than copied from the old ray.

Raw inputs are copied without modification. Every coordinate and grid value
used by the proposed loader retains its original text, parsed binary64 hex
value, and exact rational value. Candidate records retain the full original
coordinate mapping and identify each exact-zero replacement. Full native
context appears in each per-ray output and in the shared model provenance.
The raw grid has an identifier sidecar applying it to both identified rays.

## Fixed calculation budget

The target is the continuous trilinear interpolant of the 462 recorded
binary64 velocity nodes. The finite polynomial settings are degree **8**, one
subdivision per exact cell/sign interval, and **128-bit** outward bounds.
The series proof applies to this degree; the degree-32 invented run does not
promise that every native bound at degree 8 will resolve a sign. No budget
increase or precision escalation is allowed in this attempt. A bound
containing zero remains unresolved.

Cache each original edge action once. Candidate edges with identical ordered
endpoints reuse the exact same record. Sum full original and candidate action
bounds, and separately sum differences only for changed edges. Thus identical
edges cancel exactly, including their uncertainty. The maximum action roster
is 2058 original edges plus 65 changed candidate edges, or 2123 distinct edge
evaluations. The record table retains exact endpoints, piece cuts, velocity
polynomials, explicit tails, and the mapping of both polygons to those records.

For every exactly single-face-aligned candidate edge, save the reviewed
`face_jumps` result on each complete face patch. Its quadratic extrema include
interior vertices. This checks the whole interval rather than reusing the
older knot-only slope signs. Any edge aligned with more than one internal face
leaves the first variation explicitly unsupported; its action remains a
separate defined calculation. A reversed jump is preserved and does not become
a convex-support certificate.

At most 2058 candidate edge tangent-component evaluations assemble all free
node components, including both adjacent edges. Normals incident on an aligned
face are explicitly unavailable as ordinary tangent components. Fixed source
and receiver components are omitted from outputs. No source/model derivative
of a minimized travel time is computed.

Select only the first sign-resolved, physically feasible coordinate component
in node/axis order. This is the deterministic coordinate rule from the reviewed
tangent helper, with an additional bound of one candidate direction per ray.
Independently enclose its complete directional variation using its two adjacent
edges; all other endpoint directions are zero, so their full length and medium
terms vanish exactly. There are at most four nonzero-edge directional
evaluations across both rays. If this full interval is not strictly negative,
record the unresolved outcome without trying another direction.

Save every free-node tangent interval and the witness node, axis, sign,
selected-set membership, exact-face incidence, distance in node indices to the
selected set, and directional magnitude. Also save the positive geometric
step bound while taking no step. A tangent witness elsewhere in the polygon
does not explain the recorded face-normal stopping failure. Neither a negative
witness nor an unresolved witness establishes all-direction stationarity,
local optimality, global first arrival, or a common mechanism for other rays.

## Review, outputs, and lifecycle

`prepared.json` binds all original inputs, unchanged arithmetic, passed controls
and root review, copied sources, native metadata, and this plan. The command
requires a fresh `prelaunch_review.json` with `status="passed"` and the exact
preparation hash. It checks the original and copied hashes before and after a
successful calculation. There is no subprocess, field, ray, inverse, search,
or optimizer call in the loader.

After independent review, the proposed command from the integration root is:

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python3 diagnostics/check_cmj_face_action.py \
  --output data/development/hayward_cmj_face_action_001
```

An owned external controller must record the command, PID, terminal return
code, and reaping. Signals inside the calculation preserve a failed summary
and any partial files. Existing or partial outputs cannot be overwritten. The
two per-ray JSON files are losslessly gzipped and read back, with their native
context attached. `model_provenance.json` preserves raw model values and their
exact mapping; `summary.json` reports completion separately from action signs
and witness eligibility. An interrupted partial gzip is retained and hashed,
not reported as successfully read back.

Only source syntax parsing and file-copy/hash preparation are authorized at
this stage. There are no numerical outcomes in this package yet.
