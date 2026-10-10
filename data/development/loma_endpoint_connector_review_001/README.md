# Independent fixed-endpoint component review

The review passes for `../loma_endpoint_connector_native_001`. It verifies
40 input hashes, 52 original output hashes, all frozen copies, and the full
199-field native context. The separately attached formula sidecar identifies
the coordinates in `exact_baseline_formulas.json` and is pinned by this review.

The source and first two internal vertices lie exactly on the original
16 km bottom face. The saved nodal speeds define the last-layer velocity
gradient as an exact rational ratio. No rounded replacement model is used.
For these horizontal components, the constrained curved connector is a
positive bottom guide, with exactly the same mathematical action as the
first straight element. Its inward normal endpoint derivatives are zero.

An independent generic segment calculation integrates first variations in
physical xyz coordinates at 120 decimal digits. It agrees with the saved
100-digit displays for both original straight elements and all source and
first-vertex component combinations. The display allowance is 1e-95; it is
an arithmetic readback allowance, not a scientific acceptance threshold.

The source normal derivative changes from approximately -1.58506556632e-5
to zero s/km. The complete first-vertex normal derivative changes from
-3.17013113251e-5 to -1.58506556619e-5 s/km because the second straight
element remains. Thus the calculation does not zero the full vertex
gradient. The connector source vector differs from the saved continuous
reference by about 7.831e-17 s/km. This component comparison does not assign
new whole-ray accuracy or convergence flags.

No perturbed action, reoptimized path, general trilinear-medium connector,
nodal model Jacobian, or inverse calculation is supplied. The affine
component cannot be substituted selectively into a production forward
function that changes definition under nodal perturbations.

The complete identities remain attached: event
`quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`, identifier
`FDSN:NC_HQR__E_H_Z`, and epoch 1989-07-11T19:55:00 to
1990-03-24T19:55:00. Current simulation coordinates remain distinct from
the authoritative catalog geometry.

From the integration worktree, write a fresh readback with:

```sh
python3 data/development/loma_endpoint_connector_review_001/check.py \
  --output data/development/loma_endpoint_connector_review_REPEAT.json
```
