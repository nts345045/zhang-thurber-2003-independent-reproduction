# Available tangent bounds after the two saved CMJ trials

This is source and preparation only. No post-step tangent has been evaluated.
An independently approved, hash-bound `prelaunch_review.json` is required
before the one owned command in `prepared.json` can run.

## Fixed scope

Use exactly the rounded trial polygons already saved for events 981 and 987
at receiver 160 in `../hayward_cmj_tangent_step_001`. Reuse the unchanged frozen
`trilinear_action_bounds.edge_tangent_components` with terms 8, subdivisions 1
and bits 128, once per edge: at most 1028 + 1030 = **2058** calls. Do not repeat
any action, metric, rounding, trace, field, optimizer, source or model partial.

The loader checks the reviewed terminal result and decimal/hex/exact-rational
coordinates, fixed endpoints, full native contexts and all nine original
catalog row/side uses per ray. Original false flags and blank source partials
remain intact; diagnostic candidate convergence stays null. Coordinate
provenance describes the saved rounded trial, distinct from provider catalog
coordinates and the original failed polygon.

## Available components and comparison

Determine aligned internal faces anew from the **trial** coordinates. A node
coordinate is unavailable if either incident edge lies on that internal face.
Do not reuse the old mask. Multiple aligned faces, a zero edge or an outside-box
coordinate produce an explicit identified ineligible case before integration.

Sum both incident endpoint contributions for every available free-node axis.
Fixed source/receiver slots are omitted from saved edge and nodal arrays.
The unchanged primitive internally evaluates its ordinary two-endpoint edge
formula; no fixed-endpoint value is exported or interpreted as a source partial.

Project only at an exact physical-box boundary: at the lower boundary use
`min(g,0)`, at the upper boundary use `max(g,0)`, and in the interior retain `g`.
There is no `1e-10` activation band. A projected interval `[l,u]` contributes
zero to the lower squared norm when it contains zero, otherwise
`min(l*l,u*u)`; its upper contribution is `max(l*l,u*u)`. Add these exact
rational bounds over available components, with units **s²/km²**. No square
root routine is added.

Reconstruct the saved pre-step squared norm by the same exact algebra and
compare the two available vectors. Preserve availability counts and every
newly available/unavailable slot. If masks differ, the numbers refer to
different coordinate subsets. Compare to the unchanged stated `1e-7` and
`1e-5` gradient scales through their exact rational squares, **diagnostically
only**. These are neither new stopping flags nor all-direction, minimum or
first-arrival certificates. Normal-support existence is not evaluated.

## Evidence and lifecycle

Output per ray is `event_EVENT.json.gz`, with full native/catalog identities,
rounded-coordinate provenance, geometric face/mask inventory, each edge's
available components, the complete free-node vector, projected entries and
exact pre/post squared-norm bounds. Its sidecar is written before numerical
work and declares expected output identity; terminal hashes are bound later.
Any interrupted or failed case retains its identified completed edge prefix,
attempted/completed counts and error. No retries or budget escalation occur.

The Python process spawns no children. Root owns and reaps the one command;
the wrapper records signals, terminal status and hashes in `execution.json`
and `summary.json`. Existing inputs and reviewed numerical sources are read
directly and remain unchanged. New work stays separate from the completed
one-step publication.
