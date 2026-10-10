# Independent readback of the prescribed interface support

The review passes for `../loma_candidate_support_001`. It checks 14 input
hashes, 18 artifact hashes, 25 recorded controls, the complete 199-field
native context, and all 1,134 candidate vertices. Only the depths of vertices
484 and 485 differ from the saved B polygon; both are exactly 7 km.

An independent calculation integrates the action and both endpoint first
variations of all 1,133 segments directly in physical xyz coordinates at 80
and 120 decimal digits. Every one of the 3,396 internal components lies inside
its saved rational enclosure. The independent action and complete vector
norms also lie inside their enclosures. This checks the depth-axis mapping
without using the numerical helper being reviewed. Decimal agreement is a
consistency check, not an additional interval proof.

The exact rational readback verifies positive segment lengths, strictly
interior movable vertices, a complete positive depth-only grid, and precisely
one aligned convex kink at edge 484. The two outward moment margins have
positive lower bounds. The pinned moment-set result therefore allows both
normal components to vanish simultaneously for the actual enclosed values.
Every remaining component is retained in the complete norm, approximately
5.57902873888e-6 s/km. The alpha-zero choice on this same candidate has norm
6.88936561853e-5 s/km. Neither norm is the saved original B gradient.

This is an existence result for a supporting vector of the prescribed
polygon at fixed topology. It does not find a minimum-norm vector, establish
global stationarity, or justify a stopping or vertex-snapping rule. The
original B ray keeps its false convergence flag. No source or model
derivative is changed and no ray or inverse problem is solved.

The complete native identifiers remain in the input record and result
sidecar: event `quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, channel `NC.JSJ..EHZ`, identifier
`FDSN:NC_JSJ__E_H_Z`, and channel epoch 1989-05-02T15:00:00 to
1990-09-14T21:50:00. The current perturbed geometry remains distinct from
the authoritative catalog coordinates.

From the integration worktree, write a fresh readback file with:

```sh
python3 data/development/loma_candidate_support_review_001/check.py \
  --output data/development/loma_candidate_support_review_REPEAT.json
```

Regenerate the shared diagnostic figure from the reviewed saved calculation:

```sh
python3 plot_loma_interface_candidate.py \
  --support-review data/development/loma_candidate_support_review_001/review.json \
  --support-review-sha256 6ff8fad97ff9fec28163f625a54b16db305f713aaf476fb89f29f7bc9597e202
```

The plot command replaces its generated PDF, PNG and metadata in
`figures/diagnostics/`; it does not modify numerical inputs or reviews.
