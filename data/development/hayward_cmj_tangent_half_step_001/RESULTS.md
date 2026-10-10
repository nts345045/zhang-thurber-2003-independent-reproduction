# Both prescribed half-size trials decrease the action

Both alpha-one second trials were rejected. Reusing those exact saved
directions from the retained first accepted paths, the prescribed half-size
trials now pass the same conservative Armijo test. Each actual rounded
displacement has a resolved negative slope, and each action decrease is
resolved with the unchanged degree-eight, one-subdivision, 128-bit enclosure.

| Native event | Half-size trial minus retained action (s) | Bound width (s) | Maximum node move (m) |
|---|---:|---:|---:|
| 981 | -1.9271662414e-11 | 5.9914e-32 | 0.0455338 |
| 987 | -7.5767070934e-11 | 5.9046e-32 | 0.0249128 |

Only two binary64 rounding calls and 2,058 new edge-action evaluations ran.
No new direction, metric solve, gradient evaluation, trace, field or optimizer
loop was performed. The rejected full-size trials remain unchanged in
`../hayward_cmj_tangent_step_002/`. This batch ran from
12:53:14.227842 to 12:55:33.655615 UTC; root reaped session 40082 with code zero,
and both rounding helpers were reaped. Endpoints and unavailable normal
coordinates remained fixed.

The independently checked smaller-step decreases support the interpretation
that the preceding unit steps were too large. Both accepted action-change
magnitudes still exceed the combined stopping test's 1e-11 s scale. These
results alone do not establish local stationarity, source-derivative accuracy
or a first arrival. Original failure flags remain false, original source
partials remain blank, and candidate convergence remains null. A separate
post-half-step component calculation is needed; no gradient from the rejected
full-size paths is substituted.

The saved-only checker passed 132178 checks in 81 categories. It binds the
previously reviewed direction, then independently checks raw component sums,
full slopes, separate multiply/add rounding, ordered action-cache joins,
exact cancellation and Armijo classification. It performs no numerical
integration or new metric audit. Review SHA-256: `31a42fe26d47987e6afa065e60498ec8d3839793fe4f28d04657702db62f9c88`.

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

Each result and numeric-file sidecar retains all nine catalog row/side uses,
both DD endpoints, SEED/FDSN codes, resource IDs, authoritative epochs and
provider source hashes. `README.md` describes the frozen preparation; this
file records its terminal outcome.
