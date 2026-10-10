# Discrete normalized waveform measurement controls

Attempt `002` passes 41 invented controls for the
[prospective method](../normalized_correlation_specification/README.md).
The checks cover extraction on the native sample grid, the i-minus-j lag sign,
biased catalog picks, local normalization, gains and offsets, complete search
support, masks, nonfinite and constant data, reversed polarity, boundary and
tied peaks, coherence screening, and the effect of cross-spectrum smoothing.
They do not read real waveform records or create inversion observations.

The first attempt passed its 37 ordinary controls. Independent source review
then identified cancellation in ObsPy's rolling variance calculation when a
large search-margin sample coexists with small variations inside other windows.
The saved int32 counterexample in `001` produces an undefined coefficient at
the true peak, which the old method correctly rejects. It does not demonstrate
an accepted wrong delay. The original source, arrays and ordinary-check result
remain preserved. Its additional review explicitly corrects an initial
finite-only error summary that overlooked the undefined coefficient.

The revised evaluator directly subtracts each comparison window's own mean and
rescales that window before the Pearson dot product. This evaluates the same
declared coefficient without subtracting large rolling moments. Four added
int32 controls put spikes from 100,000 to 2,000,000,000 outside the selected
window; all retain the known lag and agree with independent centered Pearson
coefficients within the fixed numerical comparison tolerance. No physical
window, acceptance screen or waveform threshold was changed.

Run into a fresh directory from the integration branch:

```sh
MPLCONFIGDIR=tmp/waveform_mpl PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
  tmp/waveform_env/bin/python diagnostics/check_normalized_waveform_measurement.py \
  --output data/development/normalized_waveform_measurement_checks/NEW
```

The raw-record decoder, full native-identity joins and any legacy `dt.cc` export
require separate checks. A ten-millisecond discrete lag spacing and a relative
correlation weight do not establish a statistical timing uncertainty.
