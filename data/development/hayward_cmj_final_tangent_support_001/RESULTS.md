# Small feasible full supports on both final polygons

The two prescribed final polygons admit complete coupled supporting vectors
with norm below the existing strict scale of 1e-7 s/km. Their continuous
Fermat-action enclosures also resolve a net decrease from the accepted
half-step polygons that started the bounded iteration. This is a first-order
residual result at fixed geometry, model, endpoints and topology. Original
ray convergence and derivative flags remain zero, source partials remain
blank, and candidate convergence remains null.

| Event index | Available norm (s/km) | Feasible full-support norm (s/km) | Final minus starting-half action (s) |
| --- | ---: | ---: | ---: |
| 981 | 8.1820915198e-8 | 8.1820915198e-8 | -3.3920599504e-11 |
| 987 | 9.6184022250e-8 | 9.6184022250e-8 | -5.8997178430e-11 |

These are rounded displays of rational interval bounds. The exact full-norm
upper bounds are strictly below 1e-7; conservative displayed upper bounds
are 8.183e-8 and 9.619e-8 s/km. The available vectors have 3,050 and 3,055
components, omitting 31 and 32 aligned normal slots. The full vectors retain
all 3,081 and 3,087 internal components. Fixed source/receiver sides remain
omitted, and projection uses only the physical model box.

One action/component pass covers all 2,058 final edges. All 65 patches on
61 aligned edges have positive continuous face velocity and a nonnegative
normal slowness-gradient jump over the complete patch. Four interval moments
per patch retain the two endpoint shape functions on both neighboring sides.
One binary64 coefficient, interpreted exactly as a rational, blends both
endpoint moments together. Every ordinary adjacent-edge contribution remains,
including two entry/exit normal contributions per event. This is a coupled
feasible support, not independent clipping of endpoint components.

The midpoint fit only proposes the coefficients. Event 981 reaches the
declared 10,000-sweep cap; event 987 stops after 1,894 sweeps because its
coefficients no longer change. Neither outcome proves an optimal mixture
or a minimum residual. Their finite coefficients lie in [0,1], and the
separate interval assembly supplies the feasible full-vector bounds above,
including the capped case. A small witness establishes existence; its lower
bound is not a lower bound on the minimum over all supporting vectors.

The three compact invented control groups pass all
[20 checks](controls/summary.json), with a separate
[root review](controls/review.json) and
[reaping receipt](controls/execution_receipt.json).
The [independent native saved-output review](../hayward_cmj_final_tangent_support_review_001/review.json)
passes 90,213 checks and verifies 378 file pins. It reconstructs exact final
geometry, original nodal face polynomials and quadratic extrema, moment
scaling, shared coefficients, every ordinary contribution, full-vector sums,
box projection and action-cache joins. It performs no integration or fit.
Final C++ available-vector errors are below 1.036e-15 and 1.028e-15 s/km;
the underlying action and component intervals remain tied to their reviewed
primitive and control evidence.

The net action comparison binds the final polygons to the saved half-step
edge enclosures. It does not independently certify every intermediate
approximate acceptance decision. Neither this audit nor the
[preceding bounded iteration](../hayward_cmj_tangent_iteration_001/RESULTS.md)
establishes first-arrival selection, a local/global action minimum, final
source/model derivative accuracy, inversion acceptance or a production
correction. No nodes move during this audit. It makes no trace, field,
metric, rounded-trial, ray-optimizer or inverse call.

## Native identities and catalog uses

Both paths use native receiver 160, SEED `NC.CMJ..EHZ` and derived FDSN source
identifier `FDSN:NC_CMJ__E_H_Z`, with a valid empty location. Station identifiers
are `NC.CMJ` and `FDSN:NC_CMJ`; the metadata epoch is
`1996-11-12T23:45:00` through `1998-06-09T19:30:00`. Full native records and
both-side epoch joins remain in [native_contexts.json](native_contexts.json)
and the event-output identifier sidecars.

| Event index | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| --- | --- | --- | --- | --- |
| 981 | `quakeml:NC.anss.org/Event/NC/518943` | `quakeml:NC.anss.org/Origin/NC/4251144` | `quakeml:NC.anss.org/Arrival/NC/49639104` | `quakeml:NC.anss.org/AssocArO/NC/49639104` |
| 987 | `quakeml:NC.anss.org/Event/NC/519264` | `quakeml:NC.anss.org/Origin/NC/4252064` | `quakeml:NC.anss.org/Arrival/NC/49654119` | `quakeml:NC.anss.org/AssocArO/NC/49654119` |

All 18 catalog row/side uses remain attached (zero-based rows of
[observations.csv](../../hayward/observations.csv)):

- Event 981: `12568:i, 15081:j, 16943:i, 17559:j, 17871:i, 19525:i, 25283:i, 28675:i, 40595:i`.
- Event 987: `12672:i, 14638:j, 14683:j, 14830:j, 15239:j, 16943:j, 21423:i, 30903:j, 37879:i`.

The [summary](summary.json), [terminal ledger](execution.json),
[outer reaping receipt](outer_reaping.json) and
[review execution receipt](../hayward_cmj_final_tangent_support_review_001/execution_receipt.json)
bind the completed calculation. Independent review SHA256:
`a6020400eb0d8fe33ed1a63f6668f6c042b6fccbcfc688442887d4f49e8612e3`;
review receipt SHA256:
`3b5b3ef63fe5f77a58a5ba7ef572d5af87010d00d2253b3dca753964c9ac9515`.
The [README](README.md) preserves the original preparation; this file records
the terminal outcome.
