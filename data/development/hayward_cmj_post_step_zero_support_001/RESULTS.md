# Feasible zero aligned-normal support on the first accepted paths

This historical assessment uses the first accepted tangent trials, before
the later accepted half-size trials. Every one of 65 complete patches on
61 aligned edges has nonnegative minus-side and nonpositive plus-side
velocity-normal derivative. Positive continuous velocity therefore permits
one pointwise convex mixture with zero normal first-variation density. The
same mixture gives zero for both coupled endpoint normal moments.

All ordinary contributions remain, including the normals at face entry and
exit. The constructed full vectors have larger norms than the available
tangent subsets. Rounded displays are shown below; saved files retain exact
rational squared-norm enclosures.

| Native event | Available tangent norm (s/km) | Constructed full-vector norm (s/km) | Ordinary normal contributions at blocked nodes |
|---|---:|---:|---:|
| 981 | 3.1087443408e-06 | 4.4155230390e-05 | 2 |
| 987 | 1.2717301389e-05 | 2.4963052073e-05 | 2 |

The full-vector upper bound describes one feasible supporting vector. Neither
its upper nor its lower norm bound is a lower bound for the minimum over all
valid support choices. These large witnesses are therefore inconclusive
about that minimum. The available tangent lower bounds remain valid residual
obstructions, and both exceed the strict 1e-7 s/km scale. No original flag,
source/model partial, stationarity or first-arrival result is promoted.

The calculation used saved post-first-step components and exact one-sided
polynomial signs only. No gradient, normal moment or action was integrated;
no metric, rounding, trace, field, optimizer or subprocess ran. It completed
12:53:15.163728 to 12:53:25.896217 UTC. Root reaped session 98053 with code zero.
Each proof records the original side cells, global cut intervals, local
polynomial coefficients and exact endpoint/vertex extrema.

Independent readback reconstructed all side polynomials directly from the
eight original cell nodes, using three exact local evaluations to determine
each degree-at-most-two polynomial. It checked complete cuts, extrema,
pointwise mixture, ordinary incident terms, vectors, true-box projections,
native identities and all 18 catalog uses. The corrected review passed
49,956 checks and 94 file pins; root reaped session 84199 with code zero.
Review SHA-256: `784f1b4d4ac732819d4848625c812da5c6df0bd7c78f541187e66dfc1b3098f4`.

The first saved checker failed because it compared C++ hexadecimal strings
with omitted trailing zero digits to Python's padded spelling. Decoding both
forms gives the same binary64 values; signed-zero and exact-rational checks
are retained. Its executed source, source review and failure receipt remain
in `../hayward_cmj_post_step_zero_support_review_001/`. The one-line correction
and successful readback are in `../hayward_cmj_post_step_zero_support_review_002/`.
No scientific calculation was rerun or altered for this correction.

## Native identities

Both rays use station 160, `NC.CMJ..EHZ`, `FDSN:NC_CMJ__E_H_Z`, station
`NC.CMJ` / `FDSN:NC_CMJ`, valid empty location, and channel epoch
1996-11-12T23:45:00 through 1998-06-09T19:30:00.

- Native 981: event `quakeml:NC.anss.org/Event/NC/518943`,
  origin `quakeml:NC.anss.org/Origin/NC/4251144`,
  pick `quakeml:NC.anss.org/Arrival/NC/49639104`,
  association `quakeml:NC.anss.org/AssocArO/NC/49639104`.
- Native 987: event `quakeml:NC.anss.org/Event/NC/519264`,
  origin `quakeml:NC.anss.org/Origin/NC/4252064`,
  pick `quakeml:NC.anss.org/Arrival/NC/49654119`,
  association `quakeml:NC.anss.org/AssocArO/NC/49654119`.

Every result and identifier sidecar carries the full original catalog rows,
both DD endpoints, metadata epochs, provider hashes and original failed statuses.
