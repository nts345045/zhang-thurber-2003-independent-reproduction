# Saved-record review of the CMJ face candidates

`review_saved.py` is prepared for independent source review. It has not run.
It imports only Python standard-library modules. It does not import the action
implementation, recompute any reciprocal integral, trace a ray, construct a
field, change a polygon, or search for a supporting vector.

After root approves this checker, it will require the terminal, reaped,
successful controller and calculation records. It will verify all original,
frozen, output, runtime, and controller hashes before reading both completed
gzip outputs, and recheck the pinned artifacts afterward. It then checks:

- Exact original/native/status/selection joins and every raw text, binary64 hex,
  and rational coordinate/model mapping. Ineligible candidates remain explicit.
- Original and candidate mappings to unique edge records, complete exact cell
  cuts, positive square-root enclosures, and recorded series-tail formulas.
  It sums the saved action bounds independently and cancels identical edges.
  It does not reevaluate the finite polynomial integrals inside those bounds.
- Both adjacent-edge tangent contributions at every free knot, blocked normal
  slots, omitted fixed-endpoint slots, and complete single-face jump records.
  Jump coefficients are independently reconstructed from exact bilinear slope
  values at three points per quadratic patch; extrema include interior vertices.
- The first eligible coordinate witness, its location relative to the selected
  nodes and exact faces, the sum of its two saved edge variations, and a positive
  geometric feasibility bound. Zero contributions from all other edges follow
  from their zero endpoint directions, not from an integration approximation.

For a witness step bound `h`, exact rational checks require its displaced knot
to remain in the physical box. On each incident edge they require
`h^2 |delta_d|^2 <= |e|^2/4`, which gives positive edge length throughout the
declared interval by the triangle inequality. This verifies feasibility only;
no displacement is taken and no action along that displacement is evaluated.

## Projected tangent norm

Every available free-node tangent component has a saved rational interval
`[l,u]`. At an exact physical lower face apply `min(g,0)` to both endpoints;
at an exact upper face apply `max(g,0)`; in the interior retain the interval.
Unavailable internal-face normal components are excluded. The square has
lower bound zero if the projected interval contains zero, otherwise the
smaller endpoint square; its upper bound is the larger endpoint square.
Summing gives exact rational lower and upper bounds on the squared Euclidean
norm of this projected tangent subset, in `s^2/km^2`.

Any coupled support vector with these same tangent components has a full
physical-box residual norm at least this subset's lower bound. This statement
does not assert support eligibility or existence when a face jump is nonconvex
or a multiple-face variation is unsupported. The subset upper bound is not an
upper bound on the unknown full support residual. The physical normal cone
uses exact boundary coordinates; the old solver's `1e-10` activity band is
irrelevant to this bound.

The checker compares squared intervals to `(1e-7)^2` and `(1e-5)^2` only as
diagnostic scales. A square-root display is informational; rational squared
bounds are authoritative. These comparisons cannot invoke the production
combined stopping test, which also requires an accepted action change, or
promote an original or candidate flag.

Each per-ray report and each norm table carries full native context, including
event/origin IDs, channel SEED/FDSN identity, empty location, and metadata epochs.
After a successful readback, `tangent_norms.json` will retain every projected
component and `review.json` will bind the source, terminal records, and results.
An identical review will be attached to the native output directory.

Proposed saved-only command after source approval:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  data/development/hayward_cmj_face_action_review_001/review_saved.py
```

The native calculation remains fixed. This review adds no native action or
directional evaluation and no optimizer or support search.
