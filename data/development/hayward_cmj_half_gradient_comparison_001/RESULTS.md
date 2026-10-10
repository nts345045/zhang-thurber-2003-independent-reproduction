# Saved C++ gradient comparison on the accepted half-step polygons

The closed stage-3 C++ gradient rows agree with the independently bounded
available components to approximately 1e-15 s/km in Euclidean error norm.
This comparison uses the already saved benchmark rows and reviewed post-half
component bounds on identical geometry; it makes no C++ call, numerical
integration, trace or subprocess. The saved-only checker completed and was
reaped with exit code zero. The prepared README remains the pre-execution record.

| Event index | Available / unavailable components | Error-norm upper bound, displayed (s/km) | Largest component absolute-error upper bound, displayed (s/km) |
| --- | ---: | ---: | ---: |
| 981 | 3050 / 31 | 1.0199509462527773e-15 | 1.2017034291455752e-16 |
| 987 | 3055 / 32 | 1.0050045555334184e-15 | 9.985551257184704e-17 |

For each emitted binary64 value and saved raw component interval, the checker
retains the exact rational error interval and its contribution to the squared
error-norm bounds. The displayed values above are rounded. None of the emitted
available values lies inside its much narrower reference enclosure; these are
measured discrepancies, with no added accuracy threshold. The comparison is
of raw available components, without box projection. Unavailable ordinary
normal components remain separate and are not compared with a chosen supporting
vector. Source and receiver derivatives are outside this comparison.

The frozen benchmark oracle still records half-step derivatives as unavailable.
This separate evidence adds their available-component comparison without
changing that oracle or rerunning the kernel. Original convergence flags remain
zero, source partials remain blank, and candidate convergence remains null.
The result does not establish stationarity, first arrival, source-derivative
accuracy or an accepted production state.

## Native identities

Both cases use receiver index 160, SEED `NC.CMJ..EHZ` and derived FDSN source
identifier `FDSN:NC_CMJ__E_H_Z`, with the valid empty location. The metadata epoch
is `1996-11-12T23:45:00` through `1998-06-09T19:30:00`; station identifiers are
`NC.CMJ` and `FDSN:NC_CMJ`. The [summary](summary.json) and
[comparison sidecar](comparison.json.gz.identifiers.json) retain the full native
contexts and both-side receiver-epoch joins.

| Event index | Event resource ID | Origin resource ID | Pick resource ID | Association resource ID |
| --- | --- | --- | --- | --- |
| 981 | `quakeml:NC.anss.org/Event/NC/518943` | `quakeml:NC.anss.org/Origin/NC/4251144` | `quakeml:NC.anss.org/Arrival/NC/49639104` | `quakeml:NC.anss.org/AssocArO/NC/49639104` |
| 987 | `quakeml:NC.anss.org/Event/NC/519264` | `quakeml:NC.anss.org/Origin/NC/4252064` | `quakeml:NC.anss.org/Arrival/NC/49654119` | `quakeml:NC.anss.org/AssocArO/NC/49654119` |

All 18 original catalog row/side uses are retained (zero-based rows of
[observations.csv](../../hayward/observations.csv)):

- Event 981: `12568:i, 15081:j, 16943:i, 17559:j, 17871:i, 19525:i, 25283:i, 28675:i, 40595:i`.
- Event 987: `12672:i, 14638:j, 14683:j, 14830:j, 15239:j, 16943:j, 21423:i, 30903:j, 37879:i`.

The [source review](source_review.json), [execution receipt](execution_receipt.json),
[benchmark review](../hayward_cmj_fixed_polygon_kernel_001/review.json) and
[post-half review](../hayward_cmj_post_half_step_tangent_review_001/review.json)
bind the saved comparison. Summary SHA256:
`775754c10cad0f57bba55da4d21f05cea4a69d8f63586b881dfa4fdf765a736f`;
execution receipt SHA256:
`278294323bcab5cadd4ba2655248caad6264b9431116a09eb214e173dc63b156`.
