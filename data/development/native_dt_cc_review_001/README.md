# Independent identified dt.cc readback

`check.py` parses the terminal legacy text directly, without calling the
exporter. It verifies every header and observation line against the complete
native sidecar and reviewed measurements, including event/origin mappings,
both receiver epochs, the i-minus-j convention, zero additional origin
correction, and CC-squared relative weights. Stored values roundtrip through
the declared 17-significant-digit text serialization.

The audit passed for 98 exported observations in 98 event-pair headers.
All 44,718 original measurement rows and their order remain unchanged in
`dt.cc.identifiers.csv.gz`; 44,620 rows are explicitly unexported. The event
map retains all 1,058 events represented in the original pair roster, of
which 103 have an exported measurement. The receiver map retains 22 exact
native epochs. Accepted observations use `NC.JPR.02.EHZ` (75),
`NC.CBR.10.EHZ` (19), `NC.JSB.10.EHZ` (3), and `NC.JSF.10.EHZ` (1).
No legacy station token collapses different NSLC identities or positions.

The audit command was:

```sh
tmp/waveform_env/bin/python data/development/native_dt_cc_review_001/check.py --export data/development/native_dt_cc_001
```

The saved
[`independent_export_review.json`](../native_dt_cc_001/independent_export_review.json)
binds the exact export/measurement summaries, independent measurement review,
execution, sources, logs and native files with hashes checked before and after
readback. The helper refuses to overwrite an existing review. It performs no
correlation, export rerun or solver import. Keep the native sidecars with the
legacy text: its station field alone cannot represent full channel identities
and epochs. CC squared is a declared relative weight; this audit establishes
neither a timing variance nor a solver row multiplier.
