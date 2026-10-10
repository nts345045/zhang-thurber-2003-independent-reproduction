# Independent saved-measurement audit

`check.py` audits the terminal `native_waveform_cc_001` records without
importing or rerunning the correlation core. It checks all 44,718 original
catalog rows and their order, both event/origin/pick/association and native
receiver epochs, waveform raw/sample hashes, and the complete diagnostic
line mapping. All 14,262 original pick records remain present.

For every attempted pair, the audit reconstructs the template/search indices
and actual lag grid from native timestamps. It verifies the peak and tie
selection from the saved coefficient curve, CC squared, catalog-minus-delay
sign, and the strict coherence-bin threshold/count calculation from the saved
coherence array. It checks that rejected or unattempted rows have no accepted
delay/weight and that no formal timing uncertainty or solver observation was
added. It does not recompute normalized correlations or FFT spectra.

The saved audit passed: 1,195 attempted pairs have unique attached diagnostic
records; 98 are accepted discrete measurements, 1,086 fail coherence, 10 have
boundary peaks and one has a nonpositive peak. The other 43,523 original
pairs remain explicitly unattempted. The launch controller's mislabeled
summary hash is preserved with its exact correction; the independent
numerical ledger and unchanged command use the correct input files.

The audit command was:

```sh
tmp/waveform_env/bin/python data/development/native_waveform_cc_review_001/check.py --measurements data/development/native_waveform_cc_001
```

The resulting
[`independent_measurement_review.json`](../native_waveform_cc_001/independent_measurement_review.json)
binds the exact terminal summary, execution, sources, inputs, outputs and
controller correction with hashes before and after the readback. The helper
refuses to overwrite an existing review. The result establishes preserved
identities and consistent saved-array arithmetic; it does not establish
formal timing precision, instrument phase equivalence or exact reproduction
of the manuscript's waveform estimator.
