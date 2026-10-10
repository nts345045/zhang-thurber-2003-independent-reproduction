# Identified dt.cc serialization controls

The frozen `001` suite passes 45 invented serialization and file-I/O checks
with the repository's default Python 3.6.8. It does not export real
observations or import anything into the tomography solver.

The controls exercise signed i-minus-j values and 17-significant-digit
readback, zero additional origin correction, positive event integer mapping
with event/origin resource IDs, both native receiver epochs and empty
locations, and complete rejected-row sidecars. They reject station/channel
or moved-position collisions, duplicate or reversed pair/station/phase
records, missing identities, nonfinite or invalid coefficient/weight
values, changed formal uncertainties, stale hash-bound reviews, incomplete
or nonoffline execution ledgers, modified receiver/measurement tables,
incorrect counts, and reused output directories. Original catalog sigmas
remain unchanged in the full sidecar. An all-rejected roster produces an
empty text file while retaining its identified rows and event mapping.

`001/summary.json` pins the exact exporter and harness sources and 69 saved
artifacts. The exporter SHA256 is
`256d11036f5273d26ec8a7159671d08f1375e1be02b6dc98fd89a2240849dd44`;
the harness SHA256 is
`26b3b275ef324a7cae6639d8c1ba72b808a6c5adcadf13a75a16f8a4c43856a7`.
Reproduce with a fresh output directory:

```sh
python3 diagnostics/check_identified_dt_cc_export.py --output data/development/identified_dt_cc_export_checks/FRESH
```

These controls establish serialization and provenance behavior on invented
inputs. Real export additionally requires the terminal, independently
reviewed measurement summary. `CC^2` remains a declared relative legacy
weight; this suite does not select a solver row multiplier or establish a
timing uncertainty.
