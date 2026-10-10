# Controlled first-arrival initialization comparisons

These calculations separate two changes to the diagnostic travel-time field:
the switched second-order upwind stencil and symmetric seeding when a receiver
lies exactly on auxiliary-grid planes. The continuous velocity model, path
bending, iteration budget, and accuracy thresholds are unchanged. All endpoints
and media are invented numerical tests. No real observations or production
inversions use this prototype.

## Mechanism and controls

The original receiver initialization uses the corners of one half-open cell.
At a grid node, that places exact segment-action seeds in only one octant.
The optional corrected rule uses the union of corners from every closed cell
containing the exact receiver. Its final connection region uses the same union.
The seed values remain trial bounds which marching may improve. Off-grid
receivers retain the original unique cell and bitwise-identical fields/paths.

The [field-component tests](fmm_field_checks/README.md) preserve 28 failed
reflection comparisons for the original rule. The corrected rule has no
reflection failures in the 224 comparisons, whose maximum reflected time
difference is `4.44e-16 s`. The local mixed-order scalar solver is independently
checked against long-double bisection; its largest recorded root difference is
`4.44e-15 s`. These tests isolate discretization behavior, not continuum branch
completeness. The [stencil specification](fmm_second_order_specification.md)
states the assumptions and limitations of the higher-order switch.

The new first-order control exactly reproduces the historical experiment's
shared non-timing result columns, all 61 gate rows, and all saved path rows.
The source-seeding option and stencil order are then varied independently.

## Results

The table reports gates at the finest auxiliary and path spacing in each
experiment. Coarse experiments also contain homogeneous checks, giving 61
gates; the refined experiments retain 37 gates without repeating those checks.
The listed missed branches refer only to the sampled offsets in the flat-top
layer over a positive vertical gradient.

| Finest field/path spacing (km) | Stencil | Source cells | Failed gates | Missed diving-branch offsets (km) |
| --- | --- | --- | ---: | --- |
| 0.25 / 0.25 | First order | Original | 10 / 61 | 14.68, 15, 16 |
| 0.25 / 0.25 | First order | Closed union | 10 / 61 | 14.68, 15, 16 |
| 0.25 / 0.25 | Switched second order | Original | 9 / 61 | 14.68, 15 |
| 0.25 / 0.25 | Switched second order | Closed union | 9 / 61 | 14.68, 15 |
| 0.0625 / 0.0625 | First order | Original | 4 / 37 | 14.68, 15 |
| 0.0625 / 0.0625 | First order | Closed union | 4 / 37 | 14.68, 15 |
| 0.0625 / 0.0625 | Switched second order | Original | 2 / 37 | 14.68 |
| 0.0625 / 0.0625 | Switched second order | Closed union | 0 / 37 | None among tested offsets |

The combined refined experiment has 44 comparisons. All extracted candidates
succeed, and every selected bent path meets the original local stopping rule,
preserves exact endpoints, and stays inside the domain. Both source seeding
and stencil order matter in this test: neither change alone removes the
remaining near-crossover failures at the tested refinement.

The original and coarse controls also expose tiny endpoint discrepancies in
selected production straight-seed paths. Three first-order and four
second-order comparison rows have nonzero endpoint errors, at most
`8.90e-16 km`. These are reported separately in the comparison JSON because
strict endpoint equality was not part of the historical 61 gates. No variant
has a selected path outside its model. The refined experiments have zero
endpoint discrepancies. The production endpoint formula remains unchanged.

Passing these finite cases does not certify the general first arrival, establish
a globally second-order convergence rate, or measure the inversion effect.
The crossover sweep samples specific offsets rather than every neighborhood
of its nondifferentiable envelope. Three-dimensional heterogeneous cases and
field applications require separate validation before production integration.

## Rebuilding and evidence

Each new calculation requires a fresh `--variant` name and preserves its exact
compilation sources in `source_snapshot.tar.gz`. For example:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py --variant order2_closed_refinement_repeat --order 2 --refine --closed-seed-cells
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/compare_fmm_orders.py
```

The second command summarizes the recorded named experiments, not the new
repeat. [fmm_order_comparison.json](fmm_order_comparison.json) provides counts,
per-offset errors, endpoint checks, historical-control equality, and input
hashes. Each variant preserves all comparison rows, paths, gate values, and
failure lists. A diagnostic exits unsuccessfully when a retained gate,
extraction, or selected local convergence check fails; those failures are
scientific evidence rather than incomplete execution.

Archive ownership/timestamps and displayed machine-specific paths were
normalized before publication. The [packaging record](fmm_artifact_packaging.json)
preserves before/after hashes. Every archived source-member byte and every
scientific CSV byte is unchanged by that operation. Original packages and
summaries remain in ignored local `tmp` directories.
