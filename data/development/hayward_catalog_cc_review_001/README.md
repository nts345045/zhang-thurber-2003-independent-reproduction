# Independent prepared-input readback

`check.py` reads the terminal `data/hayward_catalog_cc_001` artifacts without
calling the adapter, waveform calculation, ray tracer or solver. It verifies
the reviewed source, execution and preserved controller-failure hashes; every
original catalog cell and its byte copy; all 98 appended export/native fields;
both receiver epochs; copied geometry; the literal CC-squared prior; and blank,
explicitly unestimated CC uncertainty.

The review checks 58,980 unchanged catalog rows plus 98 added rows, spanning
103 accepted events and four channels. It independently compares the original
and combined sets of 14,262 native event/receiver pairs. The review records
both counts and a deterministic SHA-256 of the sorted pairs, tied to the
byte-identical event and station identity tables. Different metadata epochs
use their separate `station` and `station_j` indices.

The terminal result is `data/hayward_catalog_cc_001/independent_review.json`.
All used hashes are checked before and after readback. `first_readback/`
preserves the preceding successful full native/cell review and its exact
source, before adding the canonical pair hash and explicit controller-artifact
checks. Neither review alters scientific inputs.

From the integration repository root, with no existing destination review:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  data/development/hayward_catalog_cc_review_001/check.py \
  --data data/hayward_catalog_cc_001
```

This verifies preparation and provenance. It does not establish CC timing
variance, a covariance model, forward accuracy or an inverse result. The adopted
row multiplier gives CC to the fourth power in the squared objective; later
stage weights and numerical acceptance remain separate decisions.
