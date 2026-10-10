# Tangent gradients after one CMJ trial step

Both accepted diagnostic steps reduce the available tangent-gradient norm.
Neither resulting path meets the strict gradient scale. The second path also
remains above the looser gradient scale used in the existing combined stop.

| Provider event | Native event | Before step (s/km) | After step (s/km) | After / before |
| --- | ---: | ---: | ---: | ---: |
| NC518943 | 981 | 3.4636652e-5 | 3.1087443408142793e-6 | 0.0897530263 |
| NC519264 | 987 | 4.1306217e-5 | 1.2717301388716515e-5 | 0.3078786292 |

These displays round exact rational squared-norm enclosures. The available
coordinate sets are unchanged: 3,050 and 3,055 components, with 31 and 32
unavailable face-normal components. No free coordinate lies on the physical
box boundary. The calculation sums both incident-edge contributions at every
available free-node coordinate; source and receiver endpoints remain fixed.

The complete lower bounds exceed the stated strict scale of 1e-7 s/km.
Event 987's lower bound also exceeds 1e-5 s/km. Any full supporting residual
that retains these tangent components must have at least their norm, so
choosing normal support values cannot remove the resolved tangent obstruction.
For event 981, a tangent upper bound below 1e-5 is only a necessary partial
check. Its preceding accepted action decrease, 2.4666e-10 s, exceeds the
combined stop's 1e-11 s change scale. Event 987's preceding decrease is
4.6728e-10 s. Neither combined criterion has been established.

The scale comparisons use the exact stated decimals as diagnostics, consistent
with the preceding norm review. They do not change the kernel's binary64
constants or stopping flags. The original convergence flags remain false,
source partials remain unevaluated, and candidate convergence remains null.
One further separately bounded tangent trial addresses a remaining measured
residual. This result does not certify a stationary polygon, continuous ray,
source derivative, recovered model or first arrival.

## Calculation and verification

The two inputs are exactly the rounded trial polygons saved in
`../hayward_cmj_tangent_step_001/`. The unchanged frozen primitive evaluates
each of their 2,058 edges once, with degree-eight reciprocal bounds, one
subdivision and 128-bit outward rounding. The availability mask is derived
anew from the actual trial geometry. Only exact physical-box boundaries
activate the normal-cone projection. No action, metric solve, trial move,
trace, field solve, optimizer iteration or source/model derivative was added.

Root-owned session 45371 completed with code zero and was reaped. The process
ran from 12:23:32.983551 to 12:37:17.235348 UTC on 2026-10-10 and spawned no
children. All 2,058 attempted edge evaluations completed. The terminal receipt
is `outer_reaping.json`.

The independent saved-only checker reconstructs the actual face mask, complete
adjacent-edge sums, projected vectors, squared-norm bounds and ratios. It also
checks all input/output hashes, full native/catalog identities and terminal
receipts. It passed and was reaped with code zero; no numerical primitive was
reevaluated. Review SHA-256:
`cfc98e5904193702941410d7e29afb32c7ccb6b632622db14f4099c87ef6a3ed`
in `../hayward_cmj_post_step_tangent_review_001/review.json`.

## Authoritative identities and coordinate provenance

Both paths end at receiver 160, `NC.CMJ..EHZ`,
`FDSN:NC_CMJ__E_H_Z`, station `NC.CMJ` / `FDSN:NC_CMJ`.
The valid location code is empty. The metadata epoch is
1996-11-12T23:45:00 through 1998-06-09T19:30:00.

| Native event | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| ---: | --- | --- | --- | --- |
| 981 | quakeml:NC.anss.org/Event/NC/518943 | quakeml:NC.anss.org/Origin/NC/4251144 | quakeml:NC.anss.org/Arrival/NC/49639104 | quakeml:NC.anss.org/AssocArO/NC/49639104 |
| 987 | quakeml:NC.anss.org/Event/NC/519264 | quakeml:NC.anss.org/Origin/NC/4252064 | quakeml:NC.anss.org/Arrival/NC/49654119 | quakeml:NC.anss.org/AssocArO/NC/49654119 |

Every result retains the full original native context and nine catalog uses,
including both differential endpoints, epoch joins and source hashes. Saved
coordinate provenance includes the first trial's decimal tokens, binary64
hexadecimal values and exact rationals. These are diagnostic ray coordinates
at a rejected inversion state, distinct from provider catalog coordinates.
Provider responses and original catalog observations are unchanged.
