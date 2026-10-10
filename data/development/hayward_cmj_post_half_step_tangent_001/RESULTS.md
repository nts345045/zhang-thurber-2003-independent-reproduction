# Tangent and support bounds on the accepted half-step polygons

The accepted half steps reduce the available internal tangent norms for both
CMJ paths. The bounded calculation completed all 2058 edges and the sign checks
on 61 aligned edges with 65 patches; the process was reaped with exit code zero.
The [independent saved-data review](../hayward_cmj_post_half_step_tangent_review_001/review.json)
passed, including geometry, native identities, component sums and support signs.
The prepared README remains the pre-execution record.

| Event index | Available / unavailable components | Available norm (s/km) | Ratio to first-step norm | One feasible full support norm (s/km) |
| --- | ---: | ---: | ---: | ---: |
| 981 | 3050 / 31 | 2.5528423362261987e-6 | 0.821181 | 4.405308330595466e-5 |
| 987 | 3055 / 32 | 6.747335154731096e-6 | 0.530563 | 2.2710668131114742e-5 |

These are decimal displays of the saved exact squared-norm bounds; ratios are
rounded. Both masks are unchanged from the accepted first-step geometry. Both
available norms are below 1e-5 s/km and above 1e-7 s/km. The preceding accepted
half-step action changes have magnitudes greater than 1e-11 s (approximately
1.92717e-11 and 7.57671e-11 s), so the combined small-change stopping condition
is not met. The unavailable normals also prevent interpreting the available
norm as a full ordinary-gradient test. No stopping flag is promoted.

Every aligned patch satisfies the one-sided sign conditions for the same
pointwise convex mixture to make both endpoint normal moments zero. The full
vector retains all ordinary entry and exit normal contributions. Its norm
encloses one feasible supporting vector, not the minimum support residual;
these larger witness norms are inconclusive about that minimum. Projection
uses only the exact physical box. Original convergence flags remain zero,
source partials remain blank, and candidate convergence remains null. There
was no new action integration, metric solve, trial, trace, field evaluation,
source/model derivative or support search.

## Native identities

Both cases use receiver index 160, SEED `NC.CMJ..EHZ` and derived FDSN source
identifier `FDSN:NC_CMJ__E_H_Z`. The empty location is valid. The metadata epoch
is `1996-11-12T23:45:00` through `1998-06-09T19:30:00`; station identifiers are
`NC.CMJ` and `FDSN:NC_CMJ`. Full provider records and both-side epoch joins
remain in [native_contexts.json](native_contexts.json).

| Event index | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| --- | --- | --- | --- | --- |
| 981 | `quakeml:NC.anss.org/Event/NC/518943` | `quakeml:NC.anss.org/Origin/NC/4251144` | `quakeml:NC.anss.org/Arrival/NC/49639104` | `quakeml:NC.anss.org/AssocArO/NC/49639104` |
| 987 | `quakeml:NC.anss.org/Event/NC/519264` | `quakeml:NC.anss.org/Origin/NC/4252064` | `quakeml:NC.anss.org/Arrival/NC/49654119` | `quakeml:NC.anss.org/AssocArO/NC/49654119` |

All 18 original catalog row/side uses are retained (zero-based rows of
[observations.csv](../../hayward/observations.csv)):

- Event 981: `12568:i, 15081:j, 16943:i, 17559:j, 17871:i, 19525:i, 25283:i, 28675:i, 40595:i`.
- Event 987: `12672:i, 14638:j, 14683:j, 14830:j, 15239:j, 16943:j, 21423:i, 30903:j, 37879:i`.

The closed [summary](summary.json), [execution ledger](execution.json),
[outer reaping receipt](outer_reaping.json),
[review receipt](../hayward_cmj_post_half_step_tangent_review_001/execution_receipt.json)
and [accepted half-step review](../hayward_cmj_tangent_half_step_review_001/review.json)
bind this geometry and its results. The independent review SHA256 is
`d16b1da181b06530ed283ee0cd90eecc642bdd6b65674905ab5863e1b176a818`.
