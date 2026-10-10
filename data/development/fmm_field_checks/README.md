# Diagnostic FMM field checks

These invented component cases test an auxiliary eikonal initializer. Its field
times are not production ray actions. No inversion, real-data selection, or
production source change is part of these checks. Analytic first-arrival branch
and continuous bending errors are measured separately by the root audit driver.

The prototype API is
`Field(grid, receiver, spacing, order=1, closed_seed_cells=false)`.
Order 2 uses accepted monotone two-neighbor stencils when available and first
order otherwise. The local solve retains the maximum of both opposite
directional operators on each axis, including mixed stencil orders. Its
piecewise quadratic solve has a bracketed bisection fallback. Causality is
checked against positive active directions only. The field records stencil
evaluations, ineligible second-order directions, whole-update causal fallbacks,
scalar bisections, second-neighbor revisits, and seed-node counts. These counters
count update evaluations, not unique accepted nodes. The formula and limitations
are described in `../fmm_second_order_specification.md`.

The optional seed rule uses vertices of every closed cell containing an exactly
aligned receiver. It also uses those cells for the final exact-receiver
connection. This restores reflection symmetry at auxiliary-grid faces, edges,
and nodes. Off-grid receivers retain the same unique seed cell. No geometric
tolerance or tuned source radius is introduced; the default rule is unchanged.

| Evidence directory | Result and scope |
| --- | --- |
| `results.csv`, `summary.json` | Frozen first-order field baseline. |
| `closed_cell_before`, `closed_cell_after` | Invented extraction regression: 7 of 8 reflected seed-corner cases fail before the closed-face termination fix; all 8 pass after. Field times are unchanged. |
| `closed_cell_full`, `closed_cell_hayward` | Root-recorded full fixture and identified single-ray verification of that separate extraction fix. |
| `order2` | Initial optional-order field fixture: 39 paths and 26 invalid-input checks pass. |
| `order2_mixed_complete` | 100,000 local roots, 60 operator-switch/common-time-offset cases, and 384 affine travel-time stencils pass; 8 inherited on-grid field-reflection comparisons fail across both orders. An exact source snapshot and manifest preserve this state. |
| `closed_seed_rules` | 224 comparisons across both orders and seven receiver geometries. The optional rule has zero reflection failures (maximum difference 4.44e-16 s); 28 default-rule reflection failures remain recorded. Off-grid nodal fields and candidate paths are bitwise unchanged between rules. |
| `order1_control`, `order2_current` | Current header passes 39 paths and 26 invalid cases for each order. All non-timing columns match their respective saved baseline CSVs; see `default_behavior_comparison.json`. |

The historical `order2_mixed` and `order2_mixed_complete` summaries used the
misleading key `maximum_scalar_error_s` for the maximum over scalar and field
comparisons. Their numerical values and CSV bytes remain unchanged; each `interpretation.json` separates
the scalar-root maximum (4.44e-15 s) from the inherited field-reflection maximum
(0.074474 s). Future summaries use separate keys.

Rebuild a suite into a new directory; existing evidence cannot be overwritten:

```sh
python3 data/development/fmm_field_checks/run_checks.py --variant NEW_FULL --order 2
python3 data/development/fmm_field_checks/run_checks.py --variant NEW_ROOTS --suite mixed-order --order 2
python3 data/development/fmm_field_checks/run_checks.py --variant NEW_SEEDS --suite seed-rules
```

The mixed-order suite intentionally returns failure while the default half-open
source rule retains its known reflection errors. The seed-rule suite records
those default-rule failures and tests the separate optional rule. Every summary
records commands, source/result/binary hashes, and compiler output. `TMPDIR` is
set to the repository's `tmp` directory. Python 3.6 is supported.

The latest full-domain fixture uses 733,623 auxiliary nodes. One concurrent
measurement gave 2.00 s for order 1 and 2.39 s for order 2; these are not timing
guarantees. Arithmetic allowances in the component tests are floating-point
checks, not altered ray convergence tolerances. Passing these components does
not establish a global first arrival at finite auxiliary spacing, global
second-order convergence, or readiness for production integration.
