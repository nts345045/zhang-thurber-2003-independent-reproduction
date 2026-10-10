# One-step continuous-action experiment on the native guide

This diagnostic tests two single steps from the same frozen row-5 guide polygon. It does not run an outer optimizer. One direction uses the negative midpoint of the interval supporting vector; the other removes its normal component at knots incident on the guide. The tangent projection supplies a feasible search direction only. It cannot certify stationarity for arbitrary normal displacements.

Both controls in `001` accept their twentieth attempted step (19 halvings), h=1/524288 km along the normalized direction. All 40 attempts are preserved. The action decreases, while the newly computed support-norm upper bounds increase from the original 6.82584832193e-6 s/km:

| Direction | Continuous F(d), s/km | Upper bound on action change, s | New support-norm upper bound, s/km | Exact aligned edges |
| --- | ---: | ---: | ---: | ---: |
| Negative support midpoint | -6.82584832193e-6 | -4.67324038198e-12 | 1.84175508076e-5 | 1872 |
| Tangent projection | -6.82583946604e-6 | -4.67335325645e-12 | 1.84174635279e-5 | 1874 |

These displayed values are rounded. The interval errors in the two new support vectors have norm bounds approximately 2.61e-37 and 2.55e-37 s/km. Armijo acceptance controls the action and does not require a decreasing gradient norm. The results establish valid isolated steps without a stationarity claim or an optimizer promotion.

The positive-part correction happens to be exactly zero for both native directions: the full direction's contact-normal components point into the constant-speed side. The invented control explicitly retains the distinct case where a negative supporting dot product accompanies a positive complete first variation. All 11 recorded controls passed, including six positive-part formulas, that insufficiency example, exact original-action interval parity, zero tangent correction and both strict action decreases.

The original polygon, model, full event/origin and channel/epoch metadata, and convergence flag are copied from `../native_interface_support/001`. The input is the previously saved retained reference-seed polygon, whose `original_updates` field is zero. The geometry is event `quakeml:NC.anss.org/Event/NC/20091683`, origin `quakeml:NC.anss.org/Origin/NC/2660124`, and `NC.BSL..EHZ` (`FDSN:NC_BSL__E_H_Z`), epoch `1989-08-25T19:45:00` through `1990-09-10T19:20:00`. No production input or flag is changed.

## Directional acceptance

Let m be the exact rational midpoint of the saved component intervals. Each direction is normalized by a positive rational upper enclosure R of its own Euclidean norm, so d=-m/R and ||d||₂<=1. Endpoint components are zero. The directions and their exact rational values are saved in `directions.csv`.

At the original x=0 guide, the normal slowness derivatives are 0 and 1/18 s/km². The complete continuous directional derivative is therefore

    F(d) = G·d + sum_edges [L/18 * I_plus(d_ax,d_bx)],

where G is the alpha=0 supporting vector and I_plus integrates the positive part of the linearly interpolated endpoint normal displacement. Its exact formula is given in `../interface_stationarity_bound/proof.md`. The correction is nonnegative and includes arbitrary coupled endpoint signs. A negative supporting dot product alone does not authorize a trial. The diagnostic requires the upper endpoint of the complete F(d) interval to be strictly negative.

The tangent direction has d_x=0 at every guide-incident knot, so its cusp correction vanishes exactly. All smooth components of the first variation remain present in both controls.

## Action acceptance and new polygons

Trial coordinates are exact rational values P+h*d. The initial normalized step is h=1 km and the trial budget is the existing 24 halvings. The original box and fixed endpoints are enforced without clipping or snapping. Zero-length trial segments are rejected. The coefficient c=1e-4 and the halving budget are checked against the frozen production header; the direction construction is an isolated experiment, not production-optimizer parity.

For each admissible trial, reciprocal-affine primitives enclose the continuous polygon action without quadrature. The conservative Armijo test is

    T_trial.upper <= T_original.lower + c*h*F(d).lower.

For c*h>0 this implies the usual inequality with the exact action and exact directional derivative. A certified negative derivative together with this test also implies strict action decrease. A trial at an aligned nonconvex face can still have its action evaluated; inability to construct a new convex supporting bound is recorded separately from action acceptance.

Every attempted action and rejection is written incrementally to `attempts.jsonl`, with native identifiers. The first accepted polygon for each direction is saved with exact rational coordinates and approximate decimal displays. Any newly computed support bound refers only to that new polygon. Fixed endpoint derivative fields stay blank, and original convergence flags retain their original meaning.

Reproduce with a fresh output directory from the integration repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
python3 diagnostics/check_native_interface_step.py \
  --output data/development/native_interface_step/reproduction
```

The recorded invocation uses `--output data/development/native_interface_step/001`. The output summary pins the diagnostic, both reviewed arithmetic helpers, original support evidence, native inputs, and the header containing the line-search constants. The recorded log is retained with the evidence.

`001/readback.py` checks the saved hashes, all 5410 identified new polygon rows, both exact coordinate updates and endpoints, interval norm bounds, and all 40 recorded Armijo inequalities. It performs no new action evaluation or optimization. Its recorded result is `001/readback.json`.

No source or model derivative is selected. These steps provide no convergence, inserted-knot, stationary-curve, or first-arrival certificate. Interval arithmetic bounds the saved geometry's integration and arithmetic errors; it does not bound physical model uncertainty. Only rational interval endpoints and rational polygon coordinates are authoritative.
