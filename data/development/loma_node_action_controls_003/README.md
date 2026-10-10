# Two-segment action controls

This final control run passes 25 invented checks for
`diagnostics/check_loma_node_action.py`. The independently reviewed
reciprocal-affine action arithmetic is unchanged. The source applies the
explicit `(x,y,z)` to `(z,x,y)` permutation and sums the adjacent endpoint
gradients at the middle node. High-precision Decimal differences are
independent consistency checks; the rational series remainders and
square-root enclosures provide the action/gradient bounds.

Controls 001 and 002 each passed the original 22 arithmetic checks. The
subsequent source review of 002 found that its unexecuted native selector
matched three original finite-difference step sizes and then required one.
The issue is preserved in 002. Version 003 explicitly selects the declared
`1e-6 km` row and adds multiple-step, missing-row, and duplicate-row controls.
No native run occurred before the corrected source and controls were reviewed.

`review_at_native_launch.json` is the exact review consumed by native 001.
`review.json` is the later wording-only version; `review_revision.json`
records the three prose-spacing changes, exact hashes, and observed timing.
All numerical/source pins and review status are identical. Both files are
now immutable. The native run preserves its exact consumed version and
passed its original final input/source hash gate.
