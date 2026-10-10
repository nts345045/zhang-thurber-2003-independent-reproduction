# Exact storage for the Loma Prieta synthetic observations

Reviewed 2026-10-09. This is an implementation plan, not a generated data set or solver change. Counts come from [pair_cost.json](pair_cost.json): 724 sources, 52 receivers, 152,834 unordered pairs at strictly less than 20 km, and **15,932,384 observation rows**. All 37,648 absolute rows and both 7,947,368-row differential types remain present. Pair membership is determined from the declared simulation geometry and is not recomputed from relocated sources.

## Remove repeated strings first

`observations` in `src/main.cpp` currently loads every CSV field into `CsvTable`, then constructs a second representation with 18 metadata key/value pairs per synthetic row. The estimated simultaneous payload exceeds 57.5 GiB before matrix assembly. Stream records with the existing `csv_record` parser instead; retain its quoting, finite-number, header, and row-width checks.

For the existing identified synthetic schema, retain a plain record containing four 32-bit indices `(i,j,station,type)` and the parsed 64-bit value: 24 bytes per row, **0.356 GiB** total. Vector position preserves the original row number. Reserve the checked row count to avoid capacity growth. Keep event and receiver metadata once in the identified geometry tables. Validate every incoming identity and constant metadata field against those tables before discarding its repeated string. Require the existing synthetic marker and schema; reject unrepresented extra fields or retain them explicitly. The existing real-data path still needs its pick/arrival IDs, per-row weights, second receiver index, and both native epochs.

The full CSV remains the canonical synthetic input, with its current inline identifiers. Reconstruct those same fields when streaming residuals or sampled-ray associations. Preserve provider event/origin IDs, NSLC including empty location, derived FDSN identifiers, metadata epochs, and the distinction between provider and derived IDs. Retain all additional provider fields and provenance in the geometry tables, pinned by hashes. Synthetic timing records must never acquire fabricated provider pick IDs. No new binary format or string-interning framework is needed.

Store the parsed observation value itself. Reconstructing differences from `arrivals.csv` is not exactly equivalent: `output` writes 12 significant digits, while differential values are computed before that serialization. Lossless archive compression preserves the full CSV but does not solve the current loader's memory problem.

## Reuse rays and numerical derivatives

`rays` already traces each used source–receiver combination once per model evaluation. Preserve this cache: only **37,648 rays** exist. Replace the repeated index collection and sort in `observed_rays` with a 37,648-entry presence array followed by an ascending scan. Validate every observation while marking it. Do not trace rays inside LSQR multiplication.

`observation_row` has an important exactness condition. A differential velocity coefficient is suppressed when `abs(length_i-length_j) < 0.005 km`; surviving coefficients also require absolute value greater than `1e-14`. Therefore, multiplying a simple event-pair incidence matrix by per-ray derivatives would change the current operator. Retain both conditions, source derivatives, signs, and column order. Catalog and precise rows for one pair/receiver share the unweighted derivative stencil, but remain separate observations with separate residuals and weights.

## Matrix storage choices

Let `N` be the active row count and `k` its mean number of stored entries. The table assumes all 15,932,384 rows are active; the widths are scenarios, not measured ray support. CSR means separate arrays of 32-bit columns, 64-bit values, and 64-bit row offsets.

| Mean entries per row | Current entry and row payload, one matrix | CSR payload, one matrix |
| --- | ---: | ---: |
| 32 | 7.95 GiB | 5.82 GiB |
| 64 | 15.55 GiB | 11.51 GiB |
| 128 | 30.74 GiB | 22.91 GiB |

These use `16*N*k + 24*N` and `12*N*k + 8*(N+1)` bytes. They exclude RHS, allocation overhead, and vector spare capacity. Each additional full row-length double vector costs 0.119 GiB. `solve(Matrix A,...)` currently copies the complete matrix; transferring ownership at its call site eliminates that copy because the original matrix is no longer used. A contiguous CSR representation can then retain existing row construction and multiplication order with limited changes. Use 64-bit entry counts even though model columns fit 32 bits.

An optional second reduction stores each pair/receiver stencil once and references it from its two observation rows. There are 7,985,016 absolute-or-pair/receiver stencils. Apply each row's weight separately; do not merge the data or change robust-weight estimation. This nearly halves differential derivative storage but requires a row-to-stencil map.

A matrix-free alternative stores only observations, current rays, fixed weights, active-row indices, and LSQR vectors. Compute the exact masked coefficients from cached ray arrays in both forward and transpose operations. For a 288-node grid, dense ray `dv` and `length` arrays total 0.162 GiB. Numeric observations, those two arrays, a 32-bit active-row map, and eight full row-length vectors total **1.53 GiB**, excluding paths, ray objects, temporary capacities, and other work. This is a component budget, not measured peak RSS. In-place median selection and reusing row workspaces would avoid further copies.

The matrix-free cost is repeated coefficient work: even sharing the two differential types entails approximately 2.29 billion node checks per multiplication for 288 nodes. Iterating a rigorously constructed union of nonzero ray supports could reduce this work. CSR amortizes it over the LSQR iterations. Measure support and timing on an unchanged small case before choosing; no neighbor cap or observation thinning is needed for either representation.

## Preserve the solve and verify equivalence

Start with the streaming numeric loader, presence-array ray indexing, ownership transfer, and CSR. Consider matrix-free multiplication only if the measured CSR requirement warrants its extra computation. Keep the field-data workflow isolated during implementation.

Both operators must preserve the existing weighted column norms, including smoothing rows; the `1e-20` scale fallback; column scaling; and damping rows appended **after** scaling. Freeze robust, stage, distance, and a priori weights throughout each linear solve and line search. Keep all observations on disk and in residual reports, including rows currently assigned zero weight. Preserve the current active-row ordering and smoothing objective. Continue Golub–Kahan LSQR; replacing it with normal equations changes numerical conditioning.

Before a large run, compare every parsed value and reconstructed identity on a small expanded input; compare forward and transpose products, column norms, RHS, and fixed-weight LSQR solutions against the current matrix. Include derivative-mask boundary cases, zero weights, and a real-data cross-epoch identity case. Check the adjoint dot product and unchanged objective evaluation. Require exact row/pair counts and identity joins; numerical operator/solution comparisons should use reported roundoff tolerances rather than claiming bitwise equivalence after accumulation order changes. Stream complete output rows with their identities. No production file or observation was changed during this review.
