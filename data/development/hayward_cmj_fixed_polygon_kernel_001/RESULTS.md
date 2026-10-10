# Fixed-polygon kernel benchmark: completed

The frozen C++ kernel evaluated eight saved polygons: prescribed face, accepted first step, rejected full second step, and accepted half step for events 981 and 987 at receiver 160. It performed eight `path_eval` calls and 8,232 additional segment checks, with no tracing, field construction, optimization, or new reference integration. Both children completed and were reaped. The [independent saved readback](review.json) passed 194,162 checks with 189 pinned files; [its execution receipt](review_execution.json) records exit zero. Exact source, runtime, input and output hashes are bound by [prepared.json](prepared.json), [summary.json](summary.json), and [outer_reaping.json](outer_reaping.json).

Against the existing rational action enclosures, the largest saved absolute-error upper endpoint was approximately **1.17476247e-15 s** for the returned `path_eval` value and **3.51707565e-18 s** for one segment. The separately recorded ordinary binary64 path sum has a largest error upper endpoint of approximately **1.08634301e-14 s**. The largest available-component Euclidean error-norm upper endpoint was approximately **1.05603502e-15 s/km** across the four face/first derivative comparisons. These are rounded displays of exact bounds retained in [the detailed comparisons](results/comparison_details.json.gz). Unavailable face-normal components and fixed endpoint/source derivatives are excluded. The second and half polygons have no derivative oracle in this frozen benchmark; the separate post-half calculation was still pending at preparation.

All four C++ paired-difference Armijo decisions agree with the saved action-oracle decisions. Both methods use the same exact binary64 `1e-4` coefficient. The checker independently parsed the complete emitted hexadecimal significands and reconstructed the recorded 53-/64-bit scalar sums, products, narrowing, and comparisons; it did not call the segment evaluator.

| Event | Trial from first polygon | Fraction | C++ paired change (s; rounded) | Oracle decision | C++ decision |
|---|---|---:|---:|---|---|
| 981 | Full second | 1 | +3.02123615188e-10 | Reject | Reject |
| 981 | Half | 0.5 | -1.92716584878e-11 | Accept | Accept |
| 987 | Full second | 1 | +2.70199266607e-10 | Reject | Reject |
| 987 | Half | 0.5 | -7.57670532217e-11 | Accept | Accept |

The eight timed `path_eval` calls sum to **18.754649 ms**; the additional segment checks and their edge-table output sum to **34.979390 ms**. These are single-batch measurements in the pinned `-O3` environment, without repetitions or a timing uncertainty estimate. They exclude compilation, input loading and the Python oracle comparison, and do not predict a field or inversion runtime.

The calculations concern identical fixed polygons and original nodal model values. They do not establish ray stationarity, first-arrival selection, source-partial accuracy, or a production correction. Original `ray_converged=0` and `ray_derivatives_evaluated=0`, blank source partials, and null candidate convergence statuses remain unchanged. No source adoption occurred in this benchmark.

## Native identities and complete catalog uses

Both cases use native receiver index **160**, SEED **`NC.CMJ..EHZ`**, FDSN **`FDSN:NC_CMJ__E_H_Z`**, with a valid empty location and metadata epoch **1996-11-12T23:45:00–1998-06-09T19:30:00**. [native_contexts.json](native_contexts.json) retains all original source/receiver fields, every raw catalog row, and both receiver-epoch joins. Each numeric input and output has its full identifier sidecar; [oracle.json.gz](oracle.json.gz) binds the exact geometry and reference records.

| Native event index | Event resource ID | Origin resource ID | Reference catalog pick ID | Association ID |
|---:|---|---|---|---|
| 981 | `quakeml:NC.anss.org/Event/NC/518943` | `quakeml:NC.anss.org/Origin/NC/4251144` | `quakeml:NC.anss.org/Arrival/NC/49639104` | `quakeml:NC.anss.org/AssocArO/NC/49639104` |
| 987 | `quakeml:NC.anss.org/Event/NC/519264` | `quakeml:NC.anss.org/Origin/NC/4252064` | `quakeml:NC.anss.org/Arrival/NC/49654119` | `quakeml:NC.anss.org/AssocArO/NC/49654119` |

All nine uses per case are retained below as **zero-based row:side** in the original [observations.csv](../../hayward/observations.csv), whose bytes are pinned in the preparation. Shared row 16943 legitimately uses both events on different sides.

- **981:** `12568:i`, `15081:j`, `16943:i`, `17559:j`, `17871:i`, `19525:i`, `25283:i`, `28675:i`, `40595:i`.
- **987:** `12672:i`, `14638:j`, `14683:j`, `14830:j`, `15239:j`, `16943:j`, `21423:i`, `30903:j`, `37879:i`.

The [initial preparation attempt](input_preparation_attempt_001/execution.json) failed on relative-path bookkeeping before reading data or creating numeric inputs. Its exact source and correction are preserved. The [completed preparation/readback receipt](input_preparation_execution.json) verifies all 11 numeric files, 8,240 nodes, 8,232 edges, original flags, and complete identities without an evaluator call.
