# Identified catalog-plus-CC input preparation

This isolated input dataset contains 59,078 rows: all 58,980 original catalog
rows, unchanged in their original fields and order, followed by 98 accepted
normalized waveform differences. The types are 14,262 absolute arrivals,
44,718 catalog differences, and 98 waveform differences. No configuration,
forward calculation, or inversion was run for this preparation.

`observations.csv` keeps both event/origin/pick/arrival identities, full channel
SEED/FDSN names, both native metadata epochs, and original source hashes.
All 98 added rows retain their complete identified export sidecars inline.
Their provider pick IDs describe the reference catalog picks; the derived
measurement has its own local identifier. The complete accepted and rejected
44,718-pair correlation roster remains pinned through the export provenance.
The copied geometry, initial grid, stations, and authoritative-ID marker are
byte-identical to their catalog inputs. `catalog_provenance/observations.csv`
is an exact byte copy of the original catalog file.

The adopted empirical prior is the literal legacy `CC^2`, multiplying the
residual and Jacobian row. It contributes `CC^4` to the squared data
objective before the squared stage/robust/distance factors. Derived CC
uncertainty remains blank and explicitly unestimated; original reference-pick
uncertainties are not CC uncertainties. See the separate
[adoption decision](../development/catalog_cc_weight_adoption_001/README.md)
and the retained earlier weighting proposal.

The accepted measurements cover 103 events and four channels. All 98 event
pairs have only one accepted channel; their graph has 32 components, with
largest component seven events. Those counts describe only this CC subset,
not the rank or recovery of a combined catalog-plus-CC inversion. The full
identified graph evidence is retained in
`data/development/native_cc_connectivity_001`.

`preparation_manifest.json` pins the original inputs, derived export,
processing provenance, adapter source, and generated files. `execution.json`
records the exact command, terminal return code zero, reviewed-controls
hashes, and logs. A controller-only first attempt referenced a nonexistent
optional review filename and stopped before invoking the adapter or creating
output; its exact source and failure record are preserved in
`execution_logs/initial_launch_*`. The corrected controller uses the existing
hash-bound controls summary and root review. No scientific input or adapter
computation changed.

The independent terminal readback is recorded separately in
`independent_review.json`. Input preparation and review do not imply that
the pending forward or inversion gates passed. A future run must explicitly
declare all nine stage factors and disable `catalog_only_dd`; the existing
catalog covariance code must continue to reject type 2 until its noise model
is extended and independently justified.

The completed independent readback verifies all original fields and order,
all 98 full accepted sidecars, and both receiver epochs. Of the added rows,
38 pair different native metadata epochs at the same physical receiver.
The original and prepared datasets each require exactly 14,262 native
(event index, receiver epoch index) rays, with identical sorted sets; adding
the CC measurements introduced no new forward pair. The review records the
canonical set hash and verifies 994 source, data, output, and execution pins.
The new measurements span 22 native epochs across the four channels.
