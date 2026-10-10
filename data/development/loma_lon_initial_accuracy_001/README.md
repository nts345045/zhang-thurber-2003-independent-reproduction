# LON initial-model full-ray accuracy

The completed matrix-only stage supplied all 37,648 identified rays for 724
events and 52 receivers. This saved-table comparison uses the independently
reviewed continuous depth-profile reference in `loma_lon_initial_reference_002`.
It does not trace new rays, enumerate new references or solve an inverse problem.

All 37,648 references are unique and eligible, and all saved local, finite,
initialization, endpoint and domain flags pass. All propagation-time errors
pass the unchanged 25 microsecond limit; the maximum is 4.87665744 microseconds.
**50 source-vector errors exceed 3e-6 s/km**. The maximum is
9.86335730e-6 s/km. This is a failed scientific preflight criterion despite
the passing local flags; no inverse acceptance follows.

`failure_groups.json` preserves a full-identifier roster and descriptive
breakdown. Thirteen failures have sources at the 16 km bottom boundary and
bottom-guided reference paths, with error almost entirely in the normal
component. The other 37 are turning rays from 12 interior source events;
their maximum vector error is 4.80706014e-6 s/km. Those interior failures
require separate diagnosis. The LOM boundary-only interpretation cannot be
applied to the whole LON failure set.

The matrix stage completed at 08:42:53 UTC on 10 October 2026 with return code
zero. The comparison controller reaped its child with code zero at 08:45:10 UTC.
Its receipt and logs accompany the unchanged numerical summary. Completion
of the calculation is distinct from passing its scientific criteria. The
independent sampled refinement and finite-difference stage was still running
when these rows were captured.

These results belong to the original frozen kernel with `core.hpp` SHA-256
`7111f67c896b7b93d344372423259e288533210807392e7da2eec72f0c55caed`.
The later maintained-source curvature correction did not alter this running
preflight or its binary, and these results do not test that correction.

The roughly 37 MB package preserves the complete compressed ray table,
continuous references and certificates, native geometry, configuration,
simulation provenance, source snapshots and terminal-stage ledger capture.
The compressed ray table was verified against its original uncompressed
hash. The matrix census records 626,324,658 entries and a 7,766,663,456-byte
CSR payload estimate; the matrix itself is neither required nor included
in this comparison package.

The command recorded in `summary.json` reproduces the comparison from the
original completed input directories into a fresh output directory. Every
consumed source/input has an explicit frozen-copy mapping in that summary.
`source/controller.py` is the archival launch controller; its original path
is retained in `packaging_receipt.json`; its command and terminal status are
retained in `controller_completion.json`.
It is not a new launch entry point in its archival location.
