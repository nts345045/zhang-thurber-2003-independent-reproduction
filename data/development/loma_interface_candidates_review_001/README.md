# Independent saved-interface-candidate readback

This review checks the three explicitly prescribed candidate polygons in
`../loma_interface_candidates_002`. It verifies all input and frozen artifact
hashes, all native identity fields, the complete depth-only Cartesian grid,
fixed endpoints, unchanged coordinates, and the original B convergence flag.
The 1,134-node polygon is read from saved data; no ray is traced or optimized.

The reviewed rational segment helpers reproduce all three saved enclosures
exactly. A separate 80- and 120-digit implementation splits each changed
segment in its original xyz parameterization, integrates reciprocal-affine
velocity in depth, and checks the action difference against the bounds.
The remaining 1,131, 1,131 or 1,130 edges cancel identically. This independent
depth calculation checks the axis mapping; the 13 homogeneous controls alone
could not detect a mistaken depth-axis permutation.

Moving node 484 to z=7 km decreases action by about 1.4603753e-16 s; moving
485 alone increases it by 4.3171155e-17 s. Moving both decreases it by
2.1195795e-16 s. These are fixed candidate values, not accepted line-search
steps, a snapping rule, or evidence of stationarity or convergence. No aligned
interface support vector is interpreted as an ordinary gradient. No source
or model derivative, optimizer, or inversion is changed.

The full preserved native context identifies event
`quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, `NC.JSJ..EHZ`,
`FDSN:NC_JSJ__E_H_Z`, and epoch 1989-05-02T15:00:00 to
1990-09-14T21:50:00. Empty location is preserved. The initial numerical
coordinates remain explicitly distinguished from catalog geometry.

Run the readback from the repository root, writing a fresh review file:

```sh
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python \
  data/development/loma_interface_candidates_review_001/check.py \
  --output data/development/loma_interface_candidates_review_REPEAT.json
```

The original review was also attached as `../loma_interface_candidates_002/review.json`
using `--attach`; existing outputs are never overwritten. Decimal agreement is
a consistency check, not an additional interval proof. Unrecorded moment-set
or support-bound explorations are outside this review.
