# Bounded-memory Loma Prieta implementation

This design retains 724 authoritative source locations, 52 receiver placements,
all 152,834 unordered source pairs strictly below 20 km, 37,648 absolute rows,
and both 7,947,368-row differential types. Pair membership is fixed by the truth
geometry. No source, station, neighbor, data type, or zero-weight output row is
discarded to reduce memory. The scientific noise and rounding operations remain
those of the current generator, with their previously documented limitations.

## Concrete first change: stream numeric observations, share synthetic identities

The existing generator already writes observation CSV rows incrementally. Its
large-row memory failure arises later: `observations()` retains a complete
`CsvTable` while creating another copy of 18 metadata key/value pairs in each
`Datum`. The measured-layout lower bound is 57.59 GiB before rays or matrices.

Use one plain numeric `Datum`: four `int` indices, `double value`,
`double a_priori_weight`, and `int station_j`. Its measured size is 40 bytes.
A plain `ObservationSet` holds the numeric vector, original metadata column
names, and either full native metadata rows or a flag for the strictly validated
synthetic schema. Geometry metadata remain in the existing event/station tables.
This avoids two numeric record types and preserves existing prediction, weight,
and derivative formulas. It costs 607.77 MiB for the complete Loma numeric table;
the previously proposed 24-byte special record would save another 243 MiB but
requires a separate representation for prior weights and second receiver epochs.

The input path is concrete:

1. Factor the existing CSV header checks into a reusable function. Keep
   `csv_record` quoting, row-width, duplicate-header, integer, and finite-number
   validation. Count valid records in a first streaming pass, check size overflow,
   and reserve the numeric vector once. A second pass parses and validates them.
2. Enable shared synthetic metadata only for explicit authoritative-geometry
   input with the exact current synthetic schema. Validate every incoming field
   against `simulation_metadata`'s semantics: both provider event/origin IDs,
   complete NSLC/FDSN source ID, valid empty location, native channel epoch,
   synthetic marker, data-type basis, and geometry-table labels. Require unit
   prior weight and the existing same-placement receiver convention. Reject
   unexpected columns in this requested compact mode rather than silently omit
   them. Precomputed field references can avoid building a temporary metadata
   vector for each validation.
3. Retain the parsed `double value` unchanged. Do not reconstruct differences
   from serialized arrivals: current CSV precision makes that operation inequivalent.
4. Stream reconstructed metadata to every residual, sampled-ray association, and
   linearization output. Preserve input metadata column order and values exactly.
   Full provider records and source hashes remain in the pinned geometry tables;
   synthetic timing records acquire no provider pick/arrival IDs.
5. Keep the real-observation route explicit: stream its CSV rows but retain every
   original metadata value in its sidecar, including both native pick/arrival
   identities, weights, and receiver epochs. Shared synthetic metadata must never
   be inferred merely because some columns resemble the synthetic schema.

The CSV remains canonical and self-identifying. No new binary exchange format,
metadata framework, or observation reordering is needed. Replace `observed_rays`
push/sort/unique with a checked 37,648-byte presence array and ascending scan.
The scan retains the existing numerical ray indices and validation of cross-epoch
receiver geometry. The new data container's output accessors resolve metadata
against the supplied current event/station tables; they do not hold pointers into
an event vector that relocation can replace.

## Matrix memory is a separate, necessary follow-up

After removing repeated metadata, `Matrix` still allocates one vector per active
row and `solve(Matrix A,...)` copies the whole matrix. Replace its storage with
plain CSR arrays: 64-bit row offsets, 32-bit column indices, and double values.
Retain the existing `add`, `mul`, and `trans` interfaces. Count active entries in
a first assembly pass, reserve exactly, then fill in the same row and entry order.
Transfer ownership into `solve` at the inversion call site, where the matrix is
not used afterward. Small callers that need an unchanged matrix may still copy.

At mean row widths 32, 64, and 128, all-row CSR payloads are 5.82, 11.51, and
22.91 GiB. These are scenarios, not measured Loma support. With 288 model nodes,
the dense-support upper bound is 4,715,835,072 entries, or 52.82 GiB of CSR
arrays. The actual count and byte budget must be calculated by the preflight
rather than assumed from these scenarios. Report the active-row count, entry count, allocated capacities,
RHS/work vectors, and peak RSS before a full solve. A declared memory budget must
stop before oversized allocation, without replacing the data selection.

Preserve these operator details, confirmed by an independent source review:

- `Matrix::add` multiplies coefficients and RHS by the weight, and the objective
  uses its square. Freeze stage, robust, prior, and distance weights through the
  linear solve and model line search. Preserve the `weight < 1e-12` omission rule.
- Keep the signed source and origin-time coefficients and the second receiver
  index. For each velocity node retain the 0.005 km differential path-length mask,
  followed by the `abs(value) > 1e-14` rule.
- Preserve duplicate entries and their insertion order. Column scaling sums each
  stored coefficient squared; coalescing duplicates can change normalization and
  damping even when matrix multiplication would be unchanged.
- Include weighted smoothing before computing column norms; retain the `1e-20`
  fallback, then scale columns and append damping in scaled coordinates. Keep
  the current final-log-slowness smoothing RHS and `v *= exp(-q)` update.
- Retain Golub–Kahan LSQR, its 600-update limit, `1e-8` normal-residual test, and
  physical-variable back-transformation. Do not switch to normal equations.

CSR is the minimal initial implementation. If its measured footprint exceeds the
chosen run budget, a matrix-free operator is a second implementation, not a silent
fallback with different masks. It must use frozen ray derivatives/weights and the
same row ordering. The earlier estimate of roughly 2.29 billion dense node checks
per multiplication explains why that path needs measured timing before selection.
Sharing a catalog/precise stencil or sparse ray-support unions can reduce cost,
but is not necessary to remove the repeated-metadata blocker.

Robust-scale medians can use the already allocated per-type vectors in place;
they currently make an unnecessary copy before `nth_element`. Release those
vectors after constructing the fixed weights. Move LSQR work vectors after use
instead of copying them, while retaining operation order and stopping semantics.

## First-arrival field lifetime also needs an explicit budget

The integration branch currently keeps a field for each receiver. Its persistent
arrays are one double time and one integer parent per auxiliary node. For the
declared Loma box `70 x 100 x 17 km`, 52 fields consume approximately 0.58, 4.52,
35.78, and 284.74 GiB at spacings 0.5, 0.25, 0.125, and 0.0625 km, before temporary
build arrays, heaps, and allocation overhead. These are cost scenarios, not
choices of scientific accuracy. The saved probe reports the exact node counts.

Coordinate receiver batches with the first-arrival owner if required by the run
budget. Each receiver field can be built once, used for all of its source rays,
and released before the next batch; the final ray array retains native indices.
Do not enlarge FMM spacing to fit memory without a separately justified accuracy
decision. Batching can sacrifice cache reuse between evaluations but must leave
each field and bent ray unchanged.

## Code ownership and validation before a full run

Requested ownership after the first-arrival branch is available:

| Files | Change |
| --- | --- |
| `src/csv.hpp` | Reusable validated header and streaming row iteration. |
| `src/main.cpp` | Numeric `Datum`, metadata sidecar/container, streamed input, identity reconstruction, presence-array ray support, matrix ownership transfer, robust-vector lifetime. |
| `src/core.hpp`, matrix section only | CSR storage, preserved scaling/damping, LSQR workspace moves. Coordinate with the ray-optimizer owner. |
| `src/main.cpp` ray scheduling and `src/forward.hpp` | Receiver field batching only if needed, owned/coordinated with the first-arrival integration owner. |
| New diagnostic files | Metadata round trips, malformed/mismatched input failures, CSR/operator/LSQR comparisons, and complete-cohort memory measurements. |

Before using this route, compare every parsed value and metadata field against
the existing loader on a small identified synthetic fixture; include empty
locations, both row types, input extra-column rejection, and an existing real
cross-epoch case. Verify output schema/value equivalence. Compare CSR forward and
transpose products, column norms, smoothing/damping, adjoint products, and LSQR
steps against the current matrix, including mask boundaries, duplicates, and
zero-weight rows. Preserve failures and thresholds. These checks precede full
synthetic arrival generation or inversion.

## Structural prototype result

[bounded_memory_001/summary.json](bounded_memory_001/summary.json) freezes the
entire selected event and channel CSVs and relevant source files. All provider
IDs, epochs, SEED codes, and provenance columns are retained unchanged. The C++
probe allocates every structural observation slot in generator order, using NaN
for the absent timing value; it does not generate or save an observation table.
It validates 31,827,120 event-side identity links and all receiver links, recovering
all 37,648 ray indices and exactly the declared pair/type counts.

The measured 40-byte vector occupies 637,295,360 bytes. Linux peak RSS is
628,392 KiB (613.66 MiB), including the frozen geometry and lookup structures.
Allocation plus structural validation took 1.52 s in this measurement. This is
not a full CSV throughput, matrix, FMM, or inversion benchmark. Rebuild in a new
evidence directory with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_specification/run_streaming_memory.py --variant NEW_VARIANT
```

No `src` file, observation, inverse model, or first-arrival integration file was
changed while preparing this design and prototype.
