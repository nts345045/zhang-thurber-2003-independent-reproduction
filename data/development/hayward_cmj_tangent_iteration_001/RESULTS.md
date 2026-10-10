# The bounded tangent iteration reaches its diagnostic target

Starting from the accepted half-step polygons, both paths reach a computed
available-component norm below 1e-7 s/km. The iteration uses the existing
segment evaluator and metric in the retained face-tangent search subspace;
it does not change the physical admissible variations or set a converged-ray
flag. The closed wrapper and both subprocesses were reaped with exit zero.

| Event index | Accepted updates | Evaluated trials | Accepted fraction at each update | Final computed available norm (s/km) | Fixed normal slots |
| --- | ---: | ---: | ---: | ---: | ---: |
| 981 | 16 | 32 | 0.5 | 8.1820915206700628e-8 | 31 |
| 987 | 38 | 152 | 0.125 | 9.6184022232540597e-8 | 32 |

Every event-981 update rejects fraction one before accepting one half. Every
event-987 update rejects one, one half and one quarter before accepting one
eighth. These are the recorded paired Armijo decisions using the unchanged
binary64 coefficient. Both cases stop with `diagnostic_available_norm_reached`,
within the declared limits of 1000 updates and 24 trials per update. The initial
path, action, edge and gradient arrays match the saved benchmark half polygons
bit for bit. Fixed endpoints and the search-normal slots remain unchanged.

The [independent saved-output review](../hayward_cmj_tangent_iteration_review_001/review.json)
reconstructs all 184 rounded trial geometries, accepted-state transitions and
recorded scalar inequalities. It checks the initial/final arrays, native joins,
lossless direction archive and terminal pins, with 676,006 pure scalar checks.
The sum of recorded accepted paired changes equals the exact sum of the saved
final-minus-initial binary64 edge values for each case. The checker makes no
compiler, evaluator, gradient-integration or metric call.

Intermediate gradient and edge arrays were not retained. Their contractions
and paired changes therefore remain recorded approximate values tied to the
reviewed source; this readback is not an independent certificate of every
intermediate action decrease or of the net continuous Fermat-action change.
The final available norm is a computed diagnostic quantity in the fixed search
subspace. A separate final interval action and complete supporting-vector
assessment remains necessary. Ordinary full gradients at aligned faces do not
supply that nonsmooth residual, and no minimum-support claim follows here.
Source-derivative accuracy and first-arrival selection remain untested.

Original convergence and derivative flags remain zero, source partials remain
blank, and candidate convergence remains null. There is no FMM, field, trace,
source/model derivative, inversion or production-source change. The original
failed state and all earlier prescribed trials remain preserved. The
[README](README.md) records the preparation; this file records the closed
iteration outcome, separately from any subsequent final assessment.

## Native identities and catalog uses

Both paths use native receiver 160, SEED `NC.CMJ..EHZ` and derived FDSN source
identifier `FDSN:NC_CMJ__E_H_Z`, with a valid empty location. Station identifiers
are `NC.CMJ` and `FDSN:NC_CMJ`; the metadata epoch is
`1996-11-12T23:45:00` through `1998-06-09T19:30:00`. Full native records and
both-side epoch joins are retained in [native_contexts.json](native_contexts.json)
and the numeric-file sidecars.

| Event index | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| --- | --- | --- | --- | --- |
| 981 | `quakeml:NC.anss.org/Event/NC/518943` | `quakeml:NC.anss.org/Origin/NC/4251144` | `quakeml:NC.anss.org/Arrival/NC/49639104` | `quakeml:NC.anss.org/AssocArO/NC/49639104` |
| 987 | `quakeml:NC.anss.org/Event/NC/519264` | `quakeml:NC.anss.org/Origin/NC/4252064` | `quakeml:NC.anss.org/Arrival/NC/49654119` | `quakeml:NC.anss.org/AssocArO/NC/49654119` |

All 18 catalog row/side uses remain attached (zero-based rows of
[observations.csv](../../hayward/observations.csv)):

- Event 981: `12568:i, 15081:j, 16943:i, 17559:j, 17871:i, 19525:i, 25283:i, 28675:i, 40595:i`.
- Event 987: `12672:i, 14638:j, 14683:j, 14830:j, 15239:j, 16943:j, 21423:i, 30903:j, 37879:i`.

The [summary](summary.json), [execution ledger](execution.json),
[outer reaping receipt](outer_reaping.json) and
[review execution receipt](../hayward_cmj_tangent_iteration_review_001/execution_receipt.json)
bind the terminal result. Independent review SHA256:
`4bba5bf6122237776c7478780da0619f6c531d714d717372c60b062772fdc57b`;
review receipt SHA256:
`286b6e6c230227c9beb59ba90fda8fafc3fe939d48336da3528cb4867c9aa0cd`.
