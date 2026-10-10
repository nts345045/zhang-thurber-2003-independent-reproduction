# Identified native waveform measurements

This completed, offline calculation preserves all 44,718 original catalog
pair rows. It attempts 1,195 pairs for which both requested records were
decoded from authoritative NCEDC MiniSEED and passed the native identity,
continuous-sample, 100 Hz, and provider-declared vertical-component checks.
The independently reviewed acquisition assessed 464 windows: 459 supplied
samples and five returned no samples. Missing and rejected records remain
identified; they are not inferred exclusions from the published study.

## Fixed method and results

The calculation uses the previously declared
[normalized correlation specification](../normalized_correlation_specification/README.md):
256 samples, a template beginning at the native sample nearest 0.5 s before
pick i, and complete candidate-start support within 0.25 s of that start
relative to pick j. It maximizes the signed, separately demeaned Pearson
coefficient. No extra bandpass, response correction, sample interpolation,
or amplitude calibration is applied. Undefined, nonpositive, boundary, and
numerically tied maxima are rejected. The discrete aligned windows then
receive the Hann/FFT/five-bin equal-weight spectral screen: at least 10 of
the 20 bins centered in 2–10 Hz must have squared coherence strictly above
0.9. These parameters were fixed before this calculation.

| Measurement status | Pair rows |
| --- | ---: |
| Accepted discrete measurement | 98 |
| Failed coherence screen | 1,086 |
| Maximum at search boundary | 10 |
| Nonpositive maximum | 1 |
| Not attempted | 43,523 |
| Total preserved | 44,718 |

The 98 accepted measurements involve 103 distinct event resource IDs and
the following channels. Full event, origin, pick, arrival, receiver, and
metadata-epoch identities remain in the saved rows and diagnostics.

| SEED channel | Derived FDSN source identifier | Accepted rows |
| --- | --- | ---: |
| `NC.JPR.02.EHZ` | `FDSN:NC_JPR_02_E_H_Z` | 75 |
| `NC.CBR.10.EHZ` | `FDSN:NC_CBR_10_E_H_Z` | 19 |
| `NC.JSB.10.EHZ` | `FDSN:NC_JSB_10_E_H_Z` | 3 |
| `NC.JSF.10.EHZ` | `FDSN:NC_JSF_10_E_H_Z` | 1 |

`identified_measurements.csv.gz` retains original catalog fields under
`original_catalog_*`, with the measured delay and differential time in
separate columns. For the declared sign convention,
`dt_cc_i_minus_j = original_catalog_value - delay_j_minus_i`.
`attempted_diagnostics.jsonl.gz` preserves the full lag/coherence arrays and
both native waveform and receiver-epoch records for every attempted pair.
The 10 ms sample spacing is not a formal timing uncertainty. `CC^2` is a
declared prospective relative weight, not an inverse variance or an adopted
solver row multiplier.

## Provenance and validation

`summary.json` binds all inputs, frozen numerical sources, and outputs;
`execution.json` records terminal completion without network requests.
The runner source is `diagnostics/run_native_waveform_cc.py` at SHA256
`54cd6533bac62a7f8d6b7b433fbd7782c14fd743b2d20b6f2059a1d71a255837`.
The summary SHA256 is
`8a97e3c31d4a8db25c2c63b448addbfbfe258d94a17ecfa1663e5facb5772021`.
Python 3.11.9, NumPy 2.4.6, and ObsPy 1.5.1 were used. The native-I/O
implementation passed its separate 48-control suite before this run.

`independent_measurement_review.json` records the independent saved-output
audit: all original rows, 1,195 attempted diagnostic/native joins, and the
accepted lag, differential-time, coefficient-square, and coherence arithmetic
pass. Its reproducible audit source is in
[native_waveform_cc_review_001](../native_waveform_cc_review_001/check.py).
This audit reads saved arrays; it does not repeat the CC/FFT calculation.

The external launch metadata originally mislabeled the sample-review hash
as the sample-summary hash. The command itself used the correct separate
paths, and the numerical runner independently verified and recorded both
correct hashes. `run_controller.json` and `run_controller_source.py`
preserve the original bookkeeping; `run_controller_correction.json` binds
the correction to the unchanged numerical summary and execution ledger.
No numerical input or result changed.

This directory contains measurements only. No catalog value was replaced,
no tomography observation was imported, and no figure's reproduction status
is advanced by this calculation. Legacy serialization and any subsequent
catalog-plus-correlation inversion require their separate identity and
weighting contracts. The accepted subset is an independently selected,
availability-limited counterpart, not the original study's waveform cohort
or cross-spectral phase-slope estimator.
