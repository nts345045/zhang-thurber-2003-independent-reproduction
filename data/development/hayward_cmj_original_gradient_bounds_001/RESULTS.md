# Original CMJ component audit

The independent bounds support the large ordinary gradients on both unchanged
original failed polygons. The saved C++ component errors are about 12 orders of
magnitude smaller than the gradient norms; they do not explain those large
residuals. This conclusion concerns these two saved geometries, not arbitrary
segments or the cause of the optimizer's stopping failure.

| Event index | Edges | Ordinary internal components | Reference gradient norm (s/km) | C++ minus reference error norm (s/km) | Largest component error bound (s/km) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 981 | 1,028 | 3,081 | 4.96490350e-4 | 1.05642761e-15 | 1.17927169e-16 |
| 987 | 1,030 | 3,087 | 4.93786227e-4 | 1.04362055e-15 | 1.06325659e-16 |

Displayed values round the saved rational enclosures; full bounds are in
[the summary](summary.json) and [independent review](../hayward_cmj_original_gradient_bounds_review_001/review.json).
The gradient norm measures the reference vector's magnitude. The error norm
instead measures the vector of saved raw C++ values minus those reference
bounds. `raw_available_squared_norm` in the native records contains the former
reference magnitude despite its name. All internal ordinary components are
available, and none lies on the physical box boundary, so exact-box projection
leaves this reference vector unchanged. The saved C++ vector projected under
that same rule and the historical activity-band norm remain separate records;
small differences between their displayed scalar norms also include their
summation/rounding conventions.

The native calculation completed all 2,058 declared edge evaluations using the
unchanged reviewed interval primitive (series degree 8, nine retained powers, one subdivision, 128 bound bits).
The [saved-only checker](../hayward_cmj_original_gradient_bounds_review_001/check_saved.py)
then passed 59,290 checks and 131 distinct hash bindings, including every original
path/raw-gradient row, exact model and physical-box joins, both-side catalog
associations and all component sums/error intervals. Its
[execution receipt](../hayward_cmj_original_gradient_bounds_review_001/execution_receipt.json)
records reaped exit 0; it made no evaluator or integration calls. The native
[outer receipt](outer_reaping.json) separately records the completed calculation.

These are the original failed forward evaluations, not the later modified CMJ
polygons or a final inversion. Both convergence flags remain `0`, derivative-status
flags remain `0`, and source partials remain blank. Fixed source/receiver
components are omitted. No source/model sensitivity accuracy, first-arrival
selection, production correction, accepted model or new convergence flag is
claimed. Complete crossing inventories and this gradient agreement hold on the
two original polygons only; the separate invented cutoff counterexamples remain
valid.

## Native identities

Both paths use receiver index 160, `NC.CMJ..EHZ` (valid empty location), derived
FDSN channel identifier `FDSN:NC_CMJ__E_H_Z`, and channel/metadata epoch
`1996-11-12T23:45:00` through `1998-06-09T19:30:00`. Full provider and coordinate
provenance, each original observation row and both receiver-epoch joins remain
in [native_contexts.json](native_contexts.json), both event outputs and their
identifier sidecars.

| Index | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| --- | --- | --- | --- | --- |
| 981 | quakeml:NC.anss.org/Event/NC/518943 | quakeml:NC.anss.org/Origin/NC/4251144 | quakeml:NC.anss.org/Arrival/NC/49639104 | quakeml:NC.anss.org/AssocArO/NC/49639104 |
| 987 | quakeml:NC.anss.org/Event/NC/519264 | quakeml:NC.anss.org/Origin/NC/4252064 | quakeml:NC.anss.org/Arrival/NC/49654119 | quakeml:NC.anss.org/AssocArO/NC/49654119 |

All nine zero-based catalog row/side uses are retained for each event:

- 981: `12568:i`, `15081:j`, `16943:i`, `17559:j`, `17871:i`, `19525:i`, `25283:i`, `28675:i`, `40595:i`.
- 987: `12672:i`, `14638:j`, `14683:j`, `14830:j`, `15239:j`, `16943:j`, `21423:i`, `30903:j`, `37879:i`.
