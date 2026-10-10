# Prescribed CMJ face-polygon results

The two bounded action calculations completed successfully, and the
[saved-record review](review.json) passed without new integration. These are
new prescribed polygons. The original old-kernel ray flags remain false;
neither candidate has a convergence flag. No displacement step, optimizer,
field, ray trace, or source/model sensitivity calculation was performed.

Both pairs use receiver 160, `NC.CMJ..EHZ`, `FDSN:NC_CMJ__E_H_Z`, with the
preserved empty location code and channel epoch
`1996-11-12T23:45:00`–`1998-06-09T19:30:00`. Source 981 retains event
`quakeml:NC.anss.org/Event/NC/518943` and origin
`quakeml:NC.anss.org/Origin/NC/4251144`; source 987 retains event
`quakeml:NC.anss.org/Event/NC/519264` and origin
`quakeml:NC.anss.org/Origin/NC/4252064`. Full original native context, raw
coordinate text, binary64 hex values, and exact rational mappings accompany
the results.

| Source index | Changed / unchanged edges | Candidate minus original action, display (s) | Exact-face edges / patches | Available tangent norm, display (s/km) |
| --- | --- | --- | --- | --- |
| 981 | 32 / 996 | −4.38905247026464e−11 | 30 / 32 | 3.46366520377062e−5 |
| 987 | 33 / 997 | −8.16495236718789e−11 | 31 / 33 | 4.13062167445887e−5 |

The exact rational action-difference intervals are strictly negative. Their
widths are approximately `3.75e-34` and `3.26e-34` s. These bounds concern only
integration and arithmetic for the recorded numerical model; they do not
represent observational or model uncertainty. Identical edges cancel before
subtraction. The fixed degree-8, one-subdivision, 128-bit budget was retained.

All 65 single-face patch jump polynomials have nonnegative minima over their
whole intervals. The independent review reconstructed each quadratic from
exact trilinear slopes and included interior extrema. This is a convex-jump
eligibility result, not a stationarity certificate.

The review assembled all free-node tangent intervals and projected them using
the true physical box. There are 3050 and 3055 available components, with 31
and 32 unavailable face-normal components; no available component is at an
exact physical boundary. The squared norm intervals, in `s^2/km^2`, display
approximately `1.199697664381134e-9` and `1.7062035417509354e-9`. Their exact
lower bounds exceed both `(1e-7)^2` and `(1e-5)^2`. Thus normal support choices
alone cannot reduce the full support residual below these fixed tangent
lower bounds. The displayed square roots are informational; the rational
squared bounds in the [identified norm table](../hayward_cmj_face_action_review_001/tangent_norms.json)
are authoritative. These are diagnostic comparisons, not stopping decisions;
the production combined exit also requires an accepted action change.

The deterministic first tangent witnesses are at node 1, along x, outside
both selected near-face sets. Their full directional intervals are negative,
displaying approximately `−6.8149863e-9` and `−7.7949856e-9` s per dimensionless
perturbation. Both adjacent edges are included, and positive geometric
feasibility bounds are saved without taking a step. These small witnesses
elsewhere do not explain the original face-normal failure. The full tangent
norms also show that computing only a normal support certificate would not
resolve the remaining residual at these prescribed polygons.

The review checked 2123 cached action records, 2056 free-node component
assemblies, all 63 selected original-node joins, and all 65 patch quadratics.
It used only saved intervals, geometry, exact algebraic slope checks, and
native/provenance joins. It did not recompute action or directional integrals.

- Native [summary](summary.json): `56c51845fa8ee9a2cefe1be09c78819b7eef6e79b4f7c0b4f7ca2b3580fe77d9`.
- [Independent saved review](review.json): `447091d4ec796691e7c3cfe8f852d0ae23a11cc7be74e11fcded101f6a37afc2`.
- Reviewer [execution receipt](../hayward_cmj_face_action_review_001/execution.json): `36a81d6f249045158cc57a6affe49dbb783c90b77c2656344d024ce3ba0a3ec7`.

No minimum, first arrival, cause of the original failure, or production remedy
follows from this static comparison. All consumed sources, inputs, flags, and
terminal records remain unchanged.
