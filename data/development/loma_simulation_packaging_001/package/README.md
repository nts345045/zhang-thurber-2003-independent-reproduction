# Lossless simulation publication

The original local run is retained unchanged. `manifest.json` records each tar
member and each part's SHA-256 and byte count, reviewed completion hashes,
synthetic observation counts, and native identity-table mappings. `readable/`
keeps manifests, configuration, logs, and native event/channel tables accessible.
`independent_output_review.json` is the accepted numerical/native review.
All observations are synthetic; authoritative resource IDs identify geometry,
not new provider picks. This package does not establish inversion accuracy.

Parts are consecutive bytes of one gzip-compressed tar stream, each at most
50 MiB. Keep every part in order. Verification and restore use bounded memory:

```sh
python3 diagnostics/package_loma_simulation.py verify --package PACKAGE
python3 diagnostics/package_loma_simulation.py restore --package PACKAGE --output FRESH_DIRECTORY
```

Replace PACKAGE with this directory. The restore directory must not exist.
Restore verifies member paths, sizes, hashes, part hashes, and gzip integrity;
a failed restore leaves its partial directory for inspection. No record IDs,
CSV formatting, or numerical precision are changed by compression. Publish
this directory and the helper, not the multi-gigabyte original CSV files.
