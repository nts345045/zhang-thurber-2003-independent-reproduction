# Rejected one-pair waveform diagnostic

The fixed pilot pair fails the written coherence screen. Only 2 of 20 frequency
bins exceed squared coherence 0.9 in the primary calculation; at least 10 are
required. All nine predeclared window/smoothing variants fail (0–4 passing
bins), and every candidate waveform difference is null. No waveform-derived
observation was added, the pair was not replaced, and the criterion was not
relaxed.

The existing catalog-difference row is 15108 (zero-based): event NC238035 and
event NC30083101 at `NC.JPR.02.EHZ`, with distinct 1991 and 1995 metadata epochs.
`summary.json`, all 180 rows of `identified_spectra.csv`, and the figure sidecar
retain both provider event/origin/pick/association identities, complete channel
identity, epochs, and raw-source hashes. The independent local diagnostic ID is
not a provider measurement ID.

The primary window begins 0.5 s before each P pick, contains 256 samples at
100 Hz, is demeaned and Hann tapered, and uses five-bin spectral averaging.
The [specification](../waveform_correlation_specification/README.md) separates
written method from assumptions. The plotted dashed phase line fits only two
coherent bins with two free parameters. Its near-zero residual is algebraic;
it is not timing precision, uncertainty, or an accepted delay. The signed
phase slope is retained for diagnosis only.

The analytic phase-delay controls and an invented identical finite-window
control passed. A separate closed-form check in `review.json` confirms the
expected coherence acceptance/rejection for all 15 analytic spectra. The
scientific auditor independently checked the sign, native joins, and rejection
logic and found no material defect. Phase unwrapping through low-coherence
bins remains a candidate-stage limitation. This failed pair does not determine
whether other retained pairs have usable waveform coherence.

The frozen script, numerical summary, spectra, and figures are unchanged from
the completed diagnostic. Rebuild into a fresh output directory with the pinned
project environment:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$PWD/tmp/waveform_mpl" \
XDG_CACHE_HOME="$PWD/tmp/waveform_cache" TMPDIR="$PWD/tmp/waveform_tmp" \
OPENBLAS_NUM_THREADS=1 tmp/waveform_env/bin/python \
  diagnostics/check_waveform_correlation.py --output data/development/waveform_correlation_pilot_NEW
```

The raw observations and exact dependency versions are preserved in
[the acquisition pilot](../../authoritative/waveforms/pilot_001/README.md).
No new provider request was made by this calculation.
