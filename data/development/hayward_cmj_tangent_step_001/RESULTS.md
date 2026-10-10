# One tangent step from each CMJ face candidate

Both prescribed trial steps decrease the continuous trilinear travel-time
action. These are diagnostic paths at the saved rejected inversion state;
neither is an accepted inversion result or a certified stationary ray.

| Provider event | Native event | Nominal slope (s) | Trial minus starting action (s) | Largest node movement (m) |
| --- | ---: | ---: | ---: | ---: |
| NC518943 | 981 | -6.438533022288699e-10 | -2.4665526755737916e-10 | 0.0516890940731366 |
| NC519264 | 987 | -1.5336547183016366e-9 | -4.672764875478615e-10 | 0.140947377249843 |

The dimensionless step is one for both paths. Displayed slopes and action
differences round exact rational enclosures in `event_981/result.json.gz` and
`event_987/result.json.gz`. Difference widths are 5.9914812e-32 and
5.9051326e-32 s. The actual rounded-displacement slopes are also strictly
negative, approximately -6.438533022437405e-10 and -1.5336547183278632e-9 s.
Both full actions satisfy the predeclared conservative Armijo inequality.

## Model and interpretation

The starting paths are the separately identified exact-face candidates from
`../hayward_cmj_face_action_001/`. The model, physical box, node order and
source/receiver endpoints are fixed. The positive edge metric uses the
existing midpoint velocity and edge length. Its principal system retains
incident diagonal weights when an unavailable face-normal coordinate is held
at zero. This restriction defines the trial direction's search subspace; it
does not impose a physical constraint or provide a reduced convergence test.
Every available tangent component contributes to the nominal and actual
rounded-displacement slope bounds. Coordinates are formed by separate
binary64 multiplication and addition.

The two complete actions use exact grid-plane splitting, degree-eight
reciprocal expansions, one subdivision and 128-bit outward bounds. The run
evaluated 1,028 and 1,030 new edge actions, two metric solves and two rounding
calls. It performed no post-step tangent integration, trace, field solve,
optimizer iteration, endpoint derivative or model derivative. The original
convergence flags remain false, and new convergence status remains null.
Post-step stationarity and source accuracy therefore remain unresolved.

## Authoritative identities

Both paths terminate at receiver 160, `NC.CMJ..EHZ`,
`FDSN:NC_CMJ__E_H_Z`, station `NC.CMJ` / `FDSN:NC_CMJ`.
The location code is valid and empty. The authoritative metadata epoch is
1996-11-12T23:45:00 through 1998-06-09T19:30:00.

| Native event | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| ---: | --- | --- | --- | --- |
| 981 | quakeml:NC.anss.org/Event/NC/518943 | quakeml:NC.anss.org/Origin/NC/4251144 | quakeml:NC.anss.org/Arrival/NC/49639104 | quakeml:NC.anss.org/AssocArO/NC/49639104 |
| 987 | quakeml:NC.anss.org/Event/NC/519264 | quakeml:NC.anss.org/Origin/NC/4252064 | quakeml:NC.anss.org/Arrival/NC/49654119 | quakeml:NC.anss.org/AssocArO/NC/49654119 |

`native_contexts.json` retains the complete original context, nine catalog uses
per ray, both differential endpoints, pick/association IDs, epoch joins and
source hashes. Each numerical helper file has an identifier sidecar. Provider
responses and original catalog records are unchanged.

## Execution and independent review

Root-owned native session 31175 completed with code zero and was reaped.
Calculation time was 12:10:29.943729–12:12:48.954016 UTC on 2026-10-10.
All four helper processes were reaped. `outer_reaping.json` binds the observed
tool completion to the execution and summary hashes.

The saved-only checker in `../hayward_cmj_tangent_step_review_001/` passed
121,658 checks in 89 categories; root-owned session 52198 was reaped with code
zero. It reconstructs exact slope, metric-accounting, rounding, action-sum and
Armijo identities and verifies all identifiers and terminal hashes. It does
not independently reintegrate velocity or action. The frozen primitive source
and invented controls support those evaluations. Review SHA-256:
`f2072cb53dd03df7c33e471ba1356d5209bb9b67e28ce061ea9fa38a0ada6f62`.

The preceding invented control failure is preserved in
`../cmj_tangent_step_source_001/`: decimal `-0` was parsed as integer zero,
breaking decimal/hex agreement before any trial. The separate 002 package
preserves signed zero as a floating token and passes all 50 checks. The
numerical direction, action and acceptance rules were unchanged.
