# Loma initial inverse-forward plan

This is a plan, with no new forward run or inversion. `plan.json` pins the
completed `data/loma_lom_analytic_001` simulation ledger and exact initial
geometry/model/configuration. The separate exhaustive output audit was still
running when this plan was written and must pass before a forward preflight.
The 6,795,336,074-byte observation table's hash is taken from its terminal
execution ledger; this plan does not repeat the output auditor's full-file hash.

There are 724 perturbed sources, 52 native receivers at 52 distinct coordinates,
37,648 required rays, and 15,932,384 synthetic rows. The inverse grid has 288
velocity nodes and 2,896 source parameters, totaling 3,184 parameters. The
70 × 100 × 17 km box spans x=[−35,35], y=[−60,40], z=[−1,16]. Nine initial
sources are clamped at z=16; one has z<0. Their native event/origin IDs are
retained in the JSON. All initial positions lie inside the box. Initial origin
corrections span −0.157649 to 0.158168 s.

The saved LOM start is depth-dependent, with (z km, Vp km/s):
(-1,3), (0,3), (3,5.1606383), (7,5.9521387), (11,6.1139884),
(16,6.3163006). These are the exact grid's interpolation knots, not all knots
of the primary tabulated profile. The x-dependent continuous synthetic truth
and its unperturbed sources cannot supply references for this initial model.

## Field storage

The C++ field stores one binary64 time and one 32-bit parent per auxiliary node.
Each concurrent build also allocates binary64 slowness and one-byte accepted
flags. Heap/vector capacity, paths, allocator reservations, and inverse arrays
are additional. GiB below means 2^30 bytes; these are payload calculations,
not observed peak memory or guarantees about the 128 GiB address-space limit.

| FMM spacing (km) | Auxiliary shape | Nodes per field | All 52 persistent fields (GiB) | Four builds' temporary slowness/flags (GiB) |
|---|---|---:|---:|---:|
| 0.5 | 141 × 201 × 35 | 991,935 | 0.576 | 0.033 |
| 0.25 | 281 × 401 × 69 | 7,774,989 | 4.518 | 0.261 |
| 0.125 | 561 × 801 × 137 | 61,562,457 | 35.777 | 2.064 |
| 0.0625 | 1121 × 1601 × 273 | 489,958,833 | 284.737 | 16.427 |

The unchanged 104-ray sample visits all 52 receivers. Holding both complete
0.125/0.0625 caches would require 320.514 GiB before any temporary storage and
cannot fit the current limit. Optional `raycheck_receiver_batch 4` retains the
production cache and at most four refined receiver fields, giving approximately
74.107 GiB including four builds' slowness/flags, before queues and other costs.
Measure actual address-space/RSS headroom; reduce the receiver batch if needed,
preserving every sample, native index, h/2 spacing and finite difference. The
batching fixture's small measured RSS does not establish real-run headroom.

## Validation sequence

1. Require the simulation's complete output/identity audit. Freeze a separate
   initial-forward configuration and binary; preserve the actual simulation
   and failed polygon-truth evidence. Current run.cfg still contains candidate
   path/FMM spacings 0.5/0.5 km. Fine Hayward evidence makes 0.03125/0.125 km a
   possible assessment setting, not a validated Loma choice.
2. Enumerate independent continuous arrivals for every one of the 37,648
   initial source/receiver pairs using the saved monotone z-profile and actual
   perturbed coordinates. Retain full native event/origin/channel/epoch joins,
   branch inventories, unresolved cases and near ties. Compare pure travel
   times: simulated source.t is a separate additive prediction term. Require
   complete unique references and finite derivatives, then retain the existing
   controls |time error| ≤25 microseconds and source-gradient Euclidean error
   ≤3×10^-6 s/km. The earlier x-truth reference is not this calculation.
3. Compare identified production rays against all those initial references,
   with finite/domain/exact-endpoint checks and unchanged local-convergence and
   initializer-success flags. Keep the existing 104 samples and all 24 valid
   source central differences among their first eight samples; receiver
   batching changes cache lifetime only. These sample IDs were selected using
   truth-geometry nearest/farthest distances and must not be relabeled as new
   initial-geometry extrema. Additional boundary/near-tie cases can supplement
   them. Refine FMM branch selection and polygon spacing separately when a
   failure occurs; do not accept a small refinement difference as proof of the
   correct branch.
4. Stream native observation checks rather than materializing 15.9 million
   Python dictionaries. The Hayward helper also assumes a station_j column
   absent from this compact synthetic schema, so it cannot be reused unchanged.
   A combined full-support initial-ray export and matrix census should reuse
   the same rays rather than inadvertently repeating an expensive full trace.
   The existing matrix_preflight_only mode counts actual active rows/entries
   without allocating or solving the matrix; its status table alone does not
   replace the continuous time/source-derivative comparison.
5. Launch an inverse calculation only after those separate gates and memory
   checks pass. Preserve full iteration histories, accepted steps, LSQR
   diagnostics, native residual identities and final forward checks. Updated
   velocity models are three-dimensional; passing an initial 1D reference
   cannot certify their branch selection, derivatives or global first arrivals.

## Matrix and scientific limits

Keeping all rows and all 288 model entries per row gives an upper bound of
4,715,839,720 ordered entries and 52.941 GiB CSR payload including smoothing
and damping. Numeric observations, residual/weight vectors and three LSQR row
workspaces add approximately 0.594, 0.237 and 0.356 GiB before capacities and
paths. Actual path sparsity, DD length masks, robust weights and stages must be
counted. Among the fixed 152,834 truth-selected event pairs, 2,532 have initial
separation ≥20 km, giving zero distance weight to 263,328 catalog/precise rows;
these records remain in the cohort. No pair reselection is proposed.

The flat top layer, gradient breaks, finite bottom and nine bounded initial
sources require explicit branch/boundary interpretation. Existing Loma truth
diagnostics show that correct branch seeds and highly accurate polygon action
can still fail local stopping; source-derivative accuracy and stationarity are
separate checks. Central differences that leave the domain are omitted, not
evidence of smooth unconstrained derivatives. Neither initial ray validation
nor a small linear residual establishes nonlinear recovery. Synthetic catalog
and precise differences share underlying arrivals; resolution/noise analysis
must not invent independent differential errors. No waveform correlation or
published-cohort equivalence is implied by this experiment.
