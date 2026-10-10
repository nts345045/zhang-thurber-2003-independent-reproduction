# Saved LOM path-node action and derivative

The bounded two-segment calculation confirms the saved local depth derivative
at node 484 of the failed FMM-seeded initial ray 3426. Its value is
`1.0312081489734001e-5 s/km`, differing from the saved binary64 derivative by
approximately `-4.5805230979014685e-21 s/km`. The local stopping flag remains
false. This is a derivative with respect to an internal polygon node, not a
new source derivative or a continuous-ray stationarity certificate.

The native event is `quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`; the receiver is `NC.JSJ..EHZ`
(`FDSN:NC_JSJ__E_H_Z`), epoch `1989-05-02T15:00:00` through
`1990-09-14T21:50:00`. All current initial coordinates, original catalog
metadata, and the full failed-ray context remain in the frozen inputs and
`summary.json`. Every probe carries the event/origin/channel/epoch identities.

The node is `9.505292908329466e-8 km` above the 7 km velocity-gradient break.
Only its depth is perturbed; the two neighboring nodes and every other
polygon node remain fixed. Thus the change in the two adjacent segment
actions equals the change in the complete fixed polygon's exact action.
The unchanged positive depth-only initial velocity profile is permuted from
physical `(x,y,z)` to `(z,x,y)` for the previously reviewed reciprocal-affine
segment arithmetic. Gradients are mapped back to physical coordinates.
Exact rational coordinate values and outward square-root/logarithm bounds
are retained; displayed decimal bounds are rounded.

Representative binary64-rounded downward probes give:

| Actual node-depth change (km) | Bounded action change (s), rounded display |
| ---: | ---: |
| `-4.752646454164733e-8` | `-3.25506110531873e-13` |
| `-2.3763232270823664e-8` | `-2.1187071196410106e-13` |
| `-3.7130032382037825e-10` | `-3.822009299306127e-15` |
| `-2.3206325749924872e-11` | `-2.392787452079425e-16` |

The negative intervals certify residual descent of this saved polygon. The
smallest rounded probes leave the coordinate unchanged and retain
inconclusive interval differences; they are not promoted to descent.
Exact rational perturbations and rounded binary64 perturbations are labeled
separately in all 40 records, using each pair's actual central span.

The original `1e-6 km` central difference crosses the depth break. Its
exact two-segment central quotient is approximately
`-1.5556203261650846e-5 s/km`, opposite in sign to the derivative at the saved
point. Both sides of that larger probe increase action; the downward side
increases it by about `5.4605828121542987e-11 s`. This crossing probe does not
validate the derivative at the original node. The original saved numerical
difference and all three original step sizes remain in the input artifact.

The failed optimizer's recorded full-step linear decrease is about 7.615
ULPs of its cached total time; its full-step Armijo decrement is about
0.0007615 ULP. These are scale comparisons only. The last L-BFGS direction
and its rounded trial paths were not exported by that observer, so the new
probes cannot replay or establish the cause of the failed line search.
Capturing those actual trials is the next bounded diagnostic; no production
action evaluation, optimizer, tolerance, or stopping flag changes here.

The final invented controls passed 25 checks before native evaluation.
They cover homogeneous and affine actions, coordinate permutation,
crossings, very small nonzero depth differences, equal-depth segments,
reversal, and the original finite-difference row selection. Earlier controls
001 and 002 remain preserved. Source review caught a native selector that
matched three saved step sizes before any native calculation; 003 selects
the declared `1e-6 km` row and rejects missing or duplicate matches. No
mathematical formula or tolerance changed.

`review.json` independently checks the 40 saved records, coordinate mapping,
native joins, interval subtractions and quotients, and all frozen hashes
without reevaluating actions. The consumed controls review was frozen at
SHA `16acd46c7d22e1550a165018c5fd9110bdc53c4d091ca03799c21d2b0b523717`.
After the native run passed its final hash gate, three prose-spacing strings
were edited in the controls review. Both exact versions and their recorded
timing are preserved in
`../loma_node_action_controls_003/review_revision.json`; no source, numerical
pin, status, native result, or frozen review was changed.

The exact command and source/review hashes are in `execution_receipt.json`.
Reproduction requires a fresh output directory and the exact consumed review
version, retained as `review_at_native_launch.json` in controls 003. This
diagnostic performs no ray tracing or inverse solve and changes no source
derivative or convergence flag.
