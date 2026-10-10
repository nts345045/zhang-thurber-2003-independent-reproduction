# Streaming observations and ordered sparse storage

This checkpoint removes the repeated-string observation loader and copied sparse
matrix as memory blockers. It does not generate the full Loma Prieta travel-time
table, perform its inversion, or establish that the forward model finds global
first arrivals. The Loma selection remains 724 sources, 52 receiver placements,
37,648 absolute rows, and 7,947,368 rows of each differential type. All 152,834
source pairs strictly below 20 km remain selected. The generator and its random
number ordering are unchanged.

`src/csv.hpp` now exposes the existing validated CSV header and row reader.
`observations()` counts records, reserves its numeric vector once, and parses one
record at a time. `Datum` occupies 40 bytes on the tested platform. The full Loma
numeric vector therefore occupies 637,295,360 bytes (607.77 MiB), plus shared
identities and short-lived parsing buffers. The prior 57.59 GiB lower bound came
from two simultaneous copies of repeated metadata strings; it was not the size
of the numeric data themselves.

Shared metadata is enabled only for explicitly identified synthetic geometry
with the exact current 18-column synthetic metadata schema. Every incoming
metadata value is checked against the event/origin IDs, eight channel/epoch
fields, and synthetic labels. The dictionary owns its strings independently of
mutable relocated event coordinates. Extra fields, altered identities, invalid
indices, and claimed provider pick IDs fail rather than disappear. Ordinary real
inputs keep every native metadata field, including prior weights and both
receiver epochs. All saved residuals, linearizations, and ray associations retain
the canonical inline metadata columns. Numeric observed values are parsed from
the input CSV; they are never reconstructed from rounded arrivals.

Observed-ray discovery uses a presence array and ascending scan. It preserves
native receiver indices and the existing exact-coordinate cross-epoch checks.
The matrix uses ordered CSR arrays with `size_t` row offsets, integer columns,
and double coefficients. Duplicate entries and their insertion order remain
intact. Weight multiplication, column scaling, smoothing, scaled damping,
LSQR stopping, and update arithmetic are unchanged. The inversion transfers
matrix ownership into `solve`; LSQR work vectors also transfer ownership.

## Allocation preflight

Every outer iteration freezes its usual weights, counts actual retained rows and
coefficients, and writes `<mode>_matrix_preflight.csv` before allocating the full
matrix. Counts include smoothing and the damping rows appended in `solve`.
The second assembly pass uses the same rows and weights and checks both counts.
The report distinguishes CSR array payload, numeric observation storage,
residual/weight vectors, and a conservative LSQR row-workspace allowance. These
are not total-process RSS estimates: ray paths/derivatives, FMM fields and heaps,
native metadata on ordinary inputs, vector bookkeeping, and small work arrays
are additional. Row offsets and NNZ counts support more than 2^32 entries.

Set `matrix_preflight_only 1` in a copied run configuration to compute the first
iteration's actual count and stop before full matrix allocation or any linear
solve. This still computes the required forward rays. It writes a header-only
history and the preflight table, with no model/event update. A normal run then
requires this setting to be absent or zero. Use a fresh output directory; this
option does not invalidate old model files that may already be present.

Full Loma NNZ and total-process memory remain unmeasured because the full arrival
and derivative computation has not been started. There is no hidden neighbor
cap, automatic data exclusion, alternate operator, or memory-triggered change
to the scientific selection. Receiver-field cache lifetime is a separate memory
cost and is unchanged here. The additional counting pass trades assembly time
for bounded allocation; it does not retrace rays.

## Checks and provenance

The reproducible suite freezes current source, baseline source at `deeae0e`, and
the saved identified Hayward inputs. Run it in a new directory with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_streaming_checks.py --variant NEW_VARIANT
```

The suite compares ordered multiplication, transpose multiplication, and 27
LSQR systems byte for byte against the legacy solver, including duplicate
columns, zero weights, and uneven scales. It preserves both native cross-epoch
input checks and end-to-end manufactured fixtures. The identified synthetic
fixture exercises all three observation types and DD, standard, and fixed-model
location modes. A separate preflight-only call must match the assembled matrix
counts without producing a model update.

The initial baseline external-input run failed because it required
`diagnostic_row` to be the final ray-convergence column; integrated first-arrival
columns now follow it. Only that positional assumption was replaced with a
named-column presence check, retaining the row count and every numerical gate.
The same correction is applied to the frozen baseline driver. Preliminary
failure evidence is retained separately from successful comparisons.

The full-cohort structural probe and its frozen authoritative identities remain
in `../loma_specification/bounded_memory_001/`. It allocated all 15,932,384 slots
without generating times, and measured 613.66 MiB peak RSS. The streaming fixture
uses 100,000 explicitly invented numeric rows; its measured RSS must not be
interpreted as a full forward/inverse calculation. No provider query was made.

The saved [storage comparison](storage_001/summary.json) passed: 27 LSQR systems,
22 external-input CSVs, 19 forward-fixture CSVs, and 36 identified synthetic
CSV files match the frozen legacy results exactly. All 58,980 saved Hayward
rows and 2,064,300 metadata values survive unchanged; the support set remains
14,262 native rays. The 100,000-row streaming fixture measured 10,672 KiB peak
RSS before loading the real-data fixture. Its numeric vector is 4,000,000 bytes.
These tiny solver fixtures validate storage equivalence, not manuscript results.

[Schema checks](schema_001/summary.json) additionally reject reordered, missing,
and duplicate metadata columns before ray evaluation. They are reproducible
using the fixture and executable produced by the main suite:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_streaming_schema.py \
  --fixture data/development/loma_streaming/NEW_VARIANT/streaming_observations \
  --executable tmp/loma_streaming_checks/NEW_VARIANT/current_check_forward_integration \
  --output data/development/loma_streaming/NEW_SCHEMA_VARIANT
```

Independent read-only reviews found no material defect in either ordered
operator arithmetic or metadata admission/export. The unchanged mathematical
constraints remain: each weight multiplies the row and RHS, duplicate entries
contribute separately to column norms, and the existing masks and thresholds
are preserved. Full run allocation and scientific convergence remain separate
checks after integration with the forward solver.

Compiler and run streams use the repository's ignored `.log` files. They remain
in the local evidence directory and are regenerated by the runner; their hashes
are recorded, but they are excluded from the committed changes. The omitted
large invented CSV and real roundtrip are also rebuildable. The unchanged real
input snapshot, source snapshots, comparison summaries, fixture/result CSVs,
and schema failure summaries are committed for review.
