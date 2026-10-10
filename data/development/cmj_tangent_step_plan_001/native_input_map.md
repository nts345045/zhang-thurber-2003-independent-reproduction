# CMJ tangent-step native input map

Read-only schema/identity derivation for a later reviewed wrapper. No native
direction, trial, action integration, source edit, or wrapper execution was
performed. Existing numeric files and reviews remain unchanged.

Paths below are relative to the integration checkout. Define
`N=data/development/hayward_cmj_face_action_001` and
`R=data/development/hayward_cmj_face_action_review_001`.

## Pinned starting records

| File | SHA-256 |
| --- | --- |
| `data/development/cmj_tangent_step_plan_001/README.md` | `d0cc467da8e4d597f45e9b7e9a2d3b90f648afbe9099c4f1fc1e8f3aace2460d` |
| `data/development/cmj_tangent_step_plan_001/provenance.json` | `0f96724f68b0858c8df05871c8e867d92ab92ce780e3e540b87f813a43f385e8` |
| `N/event_981.json.gz` | `365f7c9b338404203335bacc7c46db59389b1d45df64ea51ab4be812bfd5819d` |
| `N/event_987.json.gz` | `800763cae8c46d1d41a8e6d6bf9998a631f8f3a7c183f72ddf5012bae4e5ddf4` |
| `N/model_provenance.json` | `b2aaf8e17597cdcd00db18df0d50cc95502d34f1d81f7443d39b438823fb520c` |
| `N/inputs/native_context.json` | `606c12da50bd8e79b753cecf6619882eced59e455896eb8b13bad46296788103` |
| `N/inputs/trial_grid.csv` | `b85a7ff605674f46ac26d3953b7ab149092f1bd218fe82076d595bfc50c62d4c` |
| `N/inputs/trial_grid.csv.identifiers.json` | `61a8c62eb0dab2d98447842fe65b411d55ad34ddfbcf0c9c035d10126174a020` |
| `N/summary.json` | `56c51845fa8ee9a2cefe1be09c78819b7eef6e79b4f7c0b4f7ca2b3580fe77d9` |
| `N/execution.json` | `c3655f6e72c7c99eeca6dc3724be4978d5bcd48ddc9773f035bfa7b373c4c933` |
| `R/review.json` (identical to `N/review.json`) | `447091d4ec796691e7c3cfe8f852d0ae23a11cc7be74e11fcded101f6a37afc2` |
| `R/tangent_norms.json` | `72b0c6cc9ce3dcb5acd15c537bbc6076a13361537e92a1ed9d5f1ccc6c70eaa0` |

The original plan provenance does not directly pin `tangent_norms.json`;
the independent review does. The later wrapper must add that direct input pin.
The newly frozen invented-source preparation already pins/copies it, but has
no native loader.

## Geometry, action and component joins

- Join cases by `(event, station)`, not list position. In each event gzip,
  `coordinate_provenance[*].node` must be contiguous and unique; take physical
  xyz from `candidate_exact_rational`. The original raw-text/hex/rational
  mapping must agree with the frozen path CSV. Only declared selected x values
  are replaced by exact zero. Node counts are 1029/1031; selected ranges are
  724..754 and 726..757, inclusive. Source/receiver remain fixed.
- `candidate_edge_record_ids[e]` selects `unique_action_edge_records` by
  `cache_id`. Require its ordered `a_exact,b_exact` to equal candidate nodes
  `e,e+1`. Sum `record.action` interval endpoints exactly and compare with
  `candidate_action.exact_rational_bounds`. Keep `original_action` and
  `original_edge_record_ids` distinct. Cancel only identical ordered edges.
- `candidate_free_node_tangent_components` contains every internal node and
  three physical xyz slots. Reconstruct each available interval from
  `candidate_edge_tangent_records[node-1].components[1]` plus
  `candidate_edge_tangent_records[node].components[0]`. Preserve unavailable
  normal slots as null, including a node with one incident aligned edge.
- `R/tangent_norms.json` has `cases[*].components`, a sparse list keyed by
  `(node,axis)` with `axis` equal to `x`, `y` or `z`. Do not use a flat array
  offset. Match `coordinate_exact` to candidate geometry and `component_bounds`
  to the complete adjacent-edge sum. Check exactly 3050/3055 available slots
  and 31/32 unavailable x slots, no duplicates or missing available slots.
  All `physical_box_position` values are `interior`, so `projected_bounds`
  equal `component_bounds`; recheck the exact box independently.
- The model record has `axes_exact_rational`, `nodes[*].csv_row` and
  `values.{x,y,z,v}.{raw_text,binary64_hex,exact_rational}`. Its
  `recorded_grid_sha256` must match the grid CSV and identifier sidecar.
  Original decimal text denotes binary64: reconstruct `Fraction(float(text))`,
  not the exact decimal fraction. Preserve all 462 nodes and their ordering.
  Every starting action/component record uses the same model and
  `settings={terms:8, subdivisions:1, bits:128}`.

## Full identities and catalog pick joins

Each existing `native_context` contains `event`, `station`, `native_flat_index`,
`source_native`, `receiver_native` and `original_status`. Compare those complete
dictionaries across the event gzip, model, tangent file, summary and input
context; also join to `inputs/trial_events.csv` and `inputs/stations.csv`.
The flat indices are 365092 and 367324; derive them using the actual 372-row
receiver inventory rather than assuming an index formula alone proves identity.

| Event | Event resource suffix | Origin resource suffix | Absolute observation row (zero-based) | Pick suffix | Association suffix |
| --- | --- | --- | --- | --- | --- |
| 981 | `Event/NC/518943` | `Origin/NC/4251144` | 12568 | `Arrival/NC/49639104` | `AssocArO/NC/49639104` |
| 987 | `Event/NC/519264` | `Origin/NC/4252064` | 12672 | `Arrival/NC/49654119` | `AssocArO/NC/49654119` |

All resource suffixes above use prefix `quakeml:NC.anss.org/`.
Receiver index 160 is `NC.CMJ..EHZ`, `FDSN:NC_CMJ__E_H_Z`, with the valid empty
location and channel/metadata epoch `1996-11-12T23:45:00` through
`1998-06-09T19:30:00`. Keep station and network resource fields, raw metadata
source hashes, epoch-basis text, and unknown/empty provider fields intact.

**The existing CMJ context has no pick/association fields.** Their authoritative
catalog-observation source is `data/hayward/observations.csv`, SHA-256
`8c270875d675f07a5aa66d0471cd8f8a17c8f25b041e0eb6d2eb165784546a2c`.
The identical bytes are also retained as `run/observations.csv` in the reviewed
`data/development/hayward_guarded_failure_001` archive. A later wrapper must
explicitly pin this additional input and attach its original rows; do not
modify frozen CMJ metadata or synthesize provider IDs.

Join `i` and `station` to `event_i_resource_id`, `origin_i_resource_id`,
`pick_i_resource_id`, `arrival_i_resource_id`, `pick_i_time_utc`,
`pick_i_source_sha256`, channel IDs and first metadata epoch. For second sides
use `j`, the loader's `station_j` semantics, the `_j_` resource/pick fields and
`metadata_epoch_j_start/end`; never collapse epochs by coordinates. The absolute
rows have type 0, `j=-1`, and `station_j=-1`.

Each ray has one absolute and eight catalog-DD uses, all with the same native
pick/association/source-hash triplet. Preserve these zero-based row/side joins
if carrying the complete usage roster:

- Event 981: `12568:i, 15081:j, 16943:i, 17559:j, 17871:i, 19525:i,
  25283:i, 28675:i, 40595:i`. Pick-source hash
  `2817729c211254fdf0429f80ed43c243357db374019b293a43216d29f5077615`;
  pick time `1997-08-28T00:12:39.300000Z`.
- Event 987: `12672:i, 14638:j, 14683:j, 14830:j, 15239:j, 16943:j,
  21423:i, 30903:j, 37879:i`. Pick-source hash
  `f8cfe8dc188c51819f1d79520a8542c4c4671c575dfedf86456031af4dfc7363`;
  pick time `1997-08-31T00:29:41.540000Z`.

These picks identify catalog observations; they do not make the saved failed
trial coordinates an accepted model or turn a derived step into a new provider
measurement. Preserve `ray_converged="0"`, `ray_derivatives_evaluated="0"`,
blank saved source partials and `candidate_convergence_status=null`.

## Sidecars before a future launch

Every plain numeric metric input/output, direction, rounded trial and action
file must have an identifier sidecar **before** its helper is launched. Include
the full contexts and catalog joins above, expected filename/role, ordered
node/axis/edge mapping, source and candidate/model/component/review hashes, and
the exact input-file hash. For an output that does not yet exist, declare its
expected path and inherited identities beforehand; bind its actual bytes only
after the child is reaped and the stream closed, in a terminal receipt. Never
pretend an output hash was known before execution. Rehash consumed evidence
before/after execution. This memo creates no wrapper or launch authorization.
