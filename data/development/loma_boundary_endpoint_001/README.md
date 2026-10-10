# Source derivative at the lower model boundary

This completed diagnostic evaluates the saved polygon for LOM initial pair
24104, event `quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`
(`FDSN:NC_HQR__E_H_Z`), epoch `1989-07-11T19:55:00` to
`1990-03-24T19:55:00`. The full authoritative context, current perturbed source
coordinates, original catalog coordinates and source hashes remain in
`inputs/identified_ray.csv` and `subdivision.csv.identifiers.json`.

The source and its first interior knot both lie at the 16 km lower boundary.
The leading segment has length L = 0.031257257325715639 km. In the initial
depth-only model its local slowness slope is
s'_z = −0.0010142064287980456 s/km². For a horizontal segment, with the other
endpoint held fixed, differentiating the segment integral gives

    ∂T_edge/∂z_source = L s'_z / 2.

This predicts −1.5850655663167804e−5 s/km, agreeing with the saved polygon
derivative −1.5850655663167801e−5 s/km. The independent continuous boundary
reference has zero normal source derivative. This calculation explains the
captured polygon's nonzero value; it does not establish the leading-segment
geometry of all 48 source-derivative failures.

The diagnostic divides only this leading segment into 1, 2, 4, 8 and 16
equal collinear pieces. The saved binary64 action remains exactly
13.315128114663265 s at every level; maximum inserted collinearity error is
3.103e−16 km. Holding inserted knots fixed decreases the normal endpoint
partial approximately as 1/n, reaching −9.906659789478292e−7 s/km at n=16.
This changes the family of endpoint perturbations. If an inserted knot at
fraction u instead moves by (1−u) times the source displacement, contraction
of all raw knot derivatives recovers the original source derivative. The
largest component discrepancy of that tied-knot chain rule is 2.776e−17 s/km.
These are different derivatives of different parameterized path families,
not conflicting derivatives of a single family.

Twenty-five invented closed-form checks pass before the native evaluation.
They use a horizontal unit segment in v(z)=5+z km/s at z=1 km and test its
action, tangential source derivative, fixed and tied normal derivatives, and
the analytic expression at each subdivision. Their arithmetic allowances
are recorded separately from the unchanged scientific accuracy thresholds.
The native calculation performs no tracing, optimization or inverse solve.
The original successful local flag remains unchanged; the separate failed
source-accuracy result also remains unchanged. No production correction is
implemented or justified by simply choosing a subdivision level.

Run from the integration repository root, using fresh output/build paths:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_boundary_endpoint_check.py \
  --observer data/development/loma_initial_failure_24104_001 \
  --output data/development/loma_boundary_endpoint_FRESH \
  --build tmp/loma_boundary_endpoint/FRESH
```

`source/` preserves the executed helpers and frozen C++ headers; `summary.json`
records the compiler command, input/output hashes, all controls and all five
native results. The original observer is independently reviewed in
`../loma_initial_failure_review_001/`.

The separate source/math and saved-table readback passes in `review.json`;
`review_saved_result.py` preserves its executed checker. It verifies all
25 controls, five native rows, 16 input and 27 output hashes, copied observer
summary, identities and unchanged flags without rerunning numerical code.
The bottom-face normal derivative is interpreted from the admissible
interior side of the original model domain.
