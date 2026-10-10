# Normalized correlation and differential-time controls

The 37 invented controls in `001` pass. They compare the installed ObsPy
`correlate_template` result with a direct local-mean, local-variance definition
of normalized cross-correlation. This is the definition documented by
[EQcorrscan](https://eqcorrscan.readthedocs.io/en/latest/submodules/utils.correlate.html).
The maximum coefficient discrepancy is about 1.12e-15. These arrays contain no
real station or earthquake observations.

Subtracting a global mean and applying a positive scalar gain before correlation
improves numerical conditioning; each comparison window must still use its own
mean and variance. Controls cover small and large gains, DC offsets, signed
polarity, constant inputs, a peak at the search boundary, and repeated maxima.
A package value of zero for a constant window represents undefined normalized
correlation and cannot establish an arrival time.

Let `a` be the actual template start relative to event i's pick, `b` the actual
comparison-stream start relative to event j's pick, and `k` the peak index among
valid comparison-window starts. At sampling rate `f`, the feature delay relative
to the picks is `delta = b + k/f - a`. The differential time in the existing
i-minus-j convention is `catalog_dt - delta`. Controlled signals with biased
picks and unequal sample-start offsets check this sign. It agrees with
[EQcorrscan's travel-time convention](https://eqcorrscan.readthedocs.io/en/latest/submodules/autogen/eqcorrscan.utils.catalog_to_dd.write_correlations.html).

Run from the integration branch using the pinned waveform environment:

```sh
MPLCONFIGDIR=tmp/mpl_waveform_controls PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
  tmp/waveform_env/bin/python diagnostics/check_normalized_waveform_correlation.py \
  --output data/development/normalized_correlation_checks/NEW
```

Each run requires a fresh output directory and retains the invented arrays,
correlation coefficients, executed helper, package versions and source hashes.
`review_001.json` records separate source/result review. This diagnostic chooses
no real-data filtering, taper, interpolation, acceptance threshold, or timing
uncertainty. It creates no `dt.cc` observations. Those choices and adequate
waveform support remain prerequisites for broad measurements.
