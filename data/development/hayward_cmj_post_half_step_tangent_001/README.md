# Tangent and support bounds after the accepted CMJ half steps

This package is prepared source only. An independent, hash-bound
`prelaunch_review.json` is required before the command in `prepared.json`.

Use the exact saved rounded half-step polygons for events 981 and 987 at
receiver 160. The reference vector is the reviewed **post001** vector on the
retained accepted first-step geometry. The rejected second full-size trials
remain separate evidence. No prior path, result or convergence flag changes.

## One bounded component pass

Call the unchanged frozen `trilinear_action_bounds.edge_tangent_components`
once per edge, with terms 8, subdivisions 1 and bits 128. The fixed maximum is
1028 + 1030 = **2058** edge evaluations. There is no new action, metric, rounded
trial, trace, field, optimizer, source partial or model partial. The primitive
internally evaluates its two-endpoint formula; fixed source and receiver
components are omitted from the saved arrays and interpretation.

Recompute aligned internal faces from the actual half-step geometry. Any
zero edge, outside-box coordinate or edge aligned with multiple internal
faces produces an identified ineligible case. Sum both incident contributions
for each available free-node coordinate. A normal slot remains unavailable
if either incident edge is face-aligned; the old mask is never imposed.

Project only at the exact physical box: `min(g,0)` at a lower bound,
`max(g,0)` at an upper bound, and `g` in the interior. Square each projected
interval conservatively and sum exact rational lower and upper bounds, in
**s²/km²**. Compare pre/post masks and available norms. The stated decimal
`1e-7` and `1e-5` scales are squared exactly for diagnostic comparisons only;
the production `1e-10` boundary activity band is not used. No square-root
routine or stopping decision is added.

## Same-pass zero-normal support

Import the unchanged, independently reviewed zero-support module from
`../hayward_cmj_post_step_zero_support_001/run.py` and call only its pure
`zero_normal_support` and `supporting_vector` functions. This adds exact
partition and quadratic sign algebra, with **no aligned-normal moment
integration**. On every patch of each single-face edge, require positive
continuous velocity and complete one-sided ranges `gm >= 0`, `gp <= 0`.
The same pointwise mixture then makes both coupled endpoint normal moments
zero. Store each patch polynomial, exact extrema, sign result and selection.

Assemble one full vector from the newly computed edge records, substituting
zero only for the proved aligned-edge normal terms. Retain every ordinary
entry and exit normal contribution. A failed sign condition remains
inconclusive; there is no alternative support search. The feasible vector's
upper squared norm is an upper bound for one choice, not a minimum. Its lower
bound is not a lower bound for the minimum support residual. Neither bound
certifies a local minimum, first arrival or source derivative.

## Identified evidence and lifecycle

`event_EVENT.json.gz` will retain full event/origin and channel/epoch context,
all nine original catalog row/side uses, exact rounded-coordinate provenance,
pre/post component and mask records, patch proofs and the full support vector.
An identifier sidecar precedes numerical work. Original false flags and blank
source partials remain intact; candidate convergence remains null. Provider
catalog, original failed-state, first-step and half-step coordinates stay
distinct. The accepted half-step action is copied solely for geometry binding.

The wrapper preserves the reviewed post001 single-process lifecycle. Root
owns and reaps the command; it spawns no children. Exceptions retain the
identified completed record prefix and attempted/completed edge counts.
`summary.json` and `execution.json` bind terminal files; root attaches a
separate outer-reaping receipt. No retries, budget escalation or subsequent
step follow automatically. `post001_to_posthalf.patch` records the adaptation.
