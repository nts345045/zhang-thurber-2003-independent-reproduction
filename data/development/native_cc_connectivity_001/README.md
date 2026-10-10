# Accepted CC-only event connectivity

The independently reviewed measurement table contains 98 accepted rows over
103 events. These are 98 distinct event pairs: **each pair has exactly one
accepted channel**. Their undirected event graph has 32 connected components;
the largest contain seven events, and the largest unique-pair degree is six.
The complete component-size inventory is in `summary.json`.

`accepted_measurements.csv.gz` preserves every column of all 98 accepted
source rows exactly, including original row mappings, event/origin/pick/arrival
resource IDs, full channel identities, both native epochs, and waveform hashes.
`event_membership.csv` identifies every graph node by its original numerical
index, event and origin resource IDs, degree, and component membership.
`cc-component-*` labels are explicitly local derived identifiers.

This calculation introduces no filter, threshold, or measurement. The complete
44,718-row source table remains unchanged. It describes the CC-only graph;
it does not test the rank or recoverability of the combined catalog-plus-CC
inverse problem. A single receiver per pair does not by itself determine a
three-dimensional relative location. Any combined experiment retains catalog
constraints and must report the uneven support of these measurements.

The frozen source and input/output hashes accompany the summary. Reproduce
with a fresh directory:

```sh
python3 diagnostics/check_native_cc_connectivity.py --output data/development/native_cc_connectivity_FRESH
```

The source checks the independent measurement review, all original status
counts, exact table hash, one-to-one event/origin/index mappings, complete
membership, the undirected degree-sum identity, and exact accepted-row
readback. It makes no numerical waveform or inversion calls.
