# Two reference-selected continuous-curve diagnostics

This is a source/design proposal only. No reference enumeration, curve
evaluation, new polygon, optimizer or real-data calculation has been run for
this proposal. The completed component remains separately packaged in
`data/development/layered_curved_components_001`.

## Fixed scope and evidence

Use only the original LOM24104 bottom-guide ray and LON8670 turning ray, with
their complete native identities, original binary64 grid and exact source and
receiver coordinates from the reviewed six-case input manifest. These are two
reference-selected geometries, not a test of independent branch selection.

- LOM24104: `tmp/lom24104_endpoint_reference_001/references.json`, SHA256
  `35abd5792e404fcb5e073aa30eb790af2d907b458cc94aedb3904dbf297964f9`,
  record 0. The unshifted source is on z=16 km. The exact phase speed is the
  bottom nodal value, `7111522232399261/1125899906842624`; the positive guide
  length has an existing interval enclosure. Preserve its analytic time and
  endpoint intervals without recalculation.
- LON8670: `data/development/loma_lon_initial_accuracy_001/inputs/reference/certificates.jsonl.gz`,
  SHA256 `9e9b2ab541bd97b539d016aa0b229d3192cf8d18110ccd3e0bd470369c28e51b`,
  pair 8670 / event 166 / receiver 38. Use the saved `first_arrival.u_rational`
  and its separately saved root enclosure, not the reciprocal of the rounded
  displayed slowness. The exact representative is
  `944310683079866513903143259526759563753/170141183460469231731687303715884105728`.
  Retain the saved rational turning depth and floating time/source comparison
  as their actual types. The existing floating distance residual is about
  -1.32e-12 km; it is not a new high-precision closure bound.

Any future small input preparer must bind each selected record to the already
reviewed reference artifact and full original native case before writing the
two-case input. It must retain both the rational phase-speed representative
and its enclosure. No reference function import is needed.

## Curve construction

Keep the existing `lcr::Grid`, `Curve`, `Piece::line`, `Piece::arc_increment`,
and `integrate` interfaces. Construct a meridional curve with the original
source as horizontal origin and the source-to-receiver horizontal unit vector
as azimuth. Each positive-gradient depth interval contributes an affine arc;
the constant top interval contributes a straight leg. Split a turning layer
into incoming and outgoing pieces at the saved turn. A bottom-guide piece
remains exactly at the physical bottom. Display samples remain separate.

For phase speed u and layer endpoint speeds va <= vb, define
`qa=sqrt((u-va)*(u+va))`, and similarly qb. The increasing-depth angular sweep is

```
delta = atan2(vb*qa - va*qb, va*vb + qa*qb).
```

When cancellation matters, use the algebraically equal numerator

```
u*u*(vb-va)*(vb+va)/(vb*qa + va*qb).
```

The latter requires a positive denominator; a zero-length interval is omitted,
and a known turn has q=0 explicitly. The initial angle uses `atan2(v,q)` on a
deeper-going leg and `atan2(v,-q)` on a shallower-going leg. For the outgoing
leg, compute the same positive sweep with `va=v_end <= vb=v_start` and begin
at `atan2(v_start,-q_start)`; traversal-ordered decreasing speeds must not be
inserted into the increasing-speed numerator. Pass delta directly to
`arc_increment`; do not recover it by subtracting rounded endpoint angles.
Curvature is g/u, with g the layer's positive velocity slope.

For g=0, a nonhorizontal leg has `dr=abs(dz)*v/q` and its signed depth change.
The case q=0 with nonzero dz is inadmissible; a guide instead requires dz=0
and the selected branch's positive horizontal extent. The vertical p=0 limit
uses a vertical line. These limits are explicit even though neither selected
native case is expected to require the vertical limit.

## Representation and interpretation limits

Working-long-double reconstruction can miss an intended depth interface or
receiver by roundoff. Record each intended join, stored join, tangent mismatch
and final closure. Keep exact stored piece continuity. Do not snap an endpoint,
clamp a velocity, silently move a guide or substitute an adjusted phase speed.
If the current representation cannot simultaneously preserve the required
join, physical box and resolved turn, record an explicit construction failure.
Such a failure would motivate a separately reviewed representation change;
it is not authority to weaken a guard in this diagnostic.

Use `branch=reference_selected_bottom_guide` or `reference_selected_turning`,
`completeness=not_assessed_by_this_component`, and
`derivatives=selected_curve_only`. The consumed reference's branch evidence is
reported separately. Full xyz face cuts and every nodal dv/length kernel stay
unchanged. No polygon residual or production Ray convergence flag is invented.

The proposed finite evaluation is one integration per successfully constructed
curve, with the existing 16-point result and 8-point discrepancy on the same
partition. Save all pieces, full kernel vectors, closure/join diagnostics,
partition and sample counts, action versus the existing reference, basis-sum
and velocity-homogeneity residuals, and separate display samples. These test
whether the completed curved component can represent and integrate the two
selected paths. They do not provide an independent native nodal-kernel oracle,
an interval certificate or a production first-arrival implementation. Concrete
source and finite call inventory require review before either evaluation.
