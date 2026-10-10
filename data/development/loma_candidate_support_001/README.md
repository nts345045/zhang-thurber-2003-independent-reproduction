# Support existence on a prescribed interface polygon

This static calculation uses the reviewed candidate that places vertices
484 and 485 of the saved B polygon exactly at z=7 km. All other vertices,
both endpoints, and the original B result remain unchanged. There is no ray
solve, optimizer step, source update, or inversion.

The 1,134-node candidate has positive segment lengths and strictly interior
movable vertices. Its actual Cartesian grid is depth-only. Exactly one edge,
484 to 485, lies along a nonzero convex jump in the normal slowness derivative.
Smooth-segment endpoint derivatives and that edge's lower-side support are
summed with exact rational outward intervals in the original xyz axes.

Write c=L(s'_plus−s'_minus), A=−G484z and B=−G485z, where G includes all
incident contributions. The lower bounds on the two feasibility margins are
approximately 5.87264e-9 and 2.21668e-9 (s/km)²:

    2cA − (A+B)² > 0,
    2cB − (A+B)² > 0.

The pinned moment-set proof therefore supplies a bounded density whose
endpoint moments cancel both normal components exactly. These strict tests
use the entire outward enclosures, so unknown correlations among the exact
values do not invalidate the conclusion. A rational approximation to that
density is not substituted for the exact existence statement.

Only the two certified components become zero. All other 3,394 internal
components retain their enclosed values. The complete internal support norm
is enclosed near **5.579028738881561e-6 s/km**, compared with
6.889365618534295e-5 s/km for the lower-side support on this same candidate.
The rational bounds in `summary.json` are authoritative; these displays are
rounded. Neither number is the original B ordinary gradient or a modified
convergence flag. No minimized dual solution or global minimum is claimed.

All 25 invented controls pass. They exercise moment signs, asymmetric
moments, strict versus boundary feasibility, conservative interval rejection,
an explicit bounded density, norm enclosures, a depth-dependent aligned-edge
case, and supporting inequalities. The reviewed candidate's action change
is reproduced exactly from its three changed edges; all remaining edges
cancel. The original B flag remains false after its recorded 1,000 updates.

`candidate_support.csv` retains every node, exact rational coordinates, the
lower-side intervals and the existence-based support intervals. Fixed
endpoint components are blank because source/receiver derivatives are not
selected. Its identifier sidecar and `identified_ray.csv` preserve all 199
native fields, including event `quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, channel `NC.JSJ..EHZ`,
`FDSN:NC_JSJ__E_H_Z`, and epoch 1989-05-02T15:00:00 to 1990-09-14T21:50:00.
The current perturbed numerical geometry remains distinct from the catalog
geometry. All used sources, proofs, reviews and native inputs are frozen and
hashed under `inputs/`.

Reproduce from the repository root into a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python diagnostics/check_loma_candidate_support.py \
  --output data/development/loma_candidate_support_REPEAT
```

This is a supporting-vector existence bound for one prescribed polygon and
fixed positive-length topology. It supplies no ordinary derivative at the
aligned kink, arbitrary trilinear-model result, inserted-knot certificate,
first-arrival proof, or production adoption. Independent review passed:
`review.json` binds the summary and records the separate physical-xyz
80- and 120-digit readback of all 1,133 edges, all 3,396 internal components,
the complete action, both strict moment margins and both norm enclosures.
