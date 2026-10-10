# Normalized waveform differential-time method

This prospective method specifies an independent normalized time-domain
cross-correlation calculation, as requested by the user. No real waveform
measurement informed these choices. It is not the original study's
cross-spectral phase-slope estimator. Instrument calibration and response
removal are not required. Missing historical responses remain explicit.

## Written basis and declared choices

The [written precursor specification](../waveform_correlation_specification/README.md)
provides the 2.56 s duration and the spectral quality criterion: at least half
the squared-coherence bins in 2–10 Hz must exceed 0.9. The
[EQcorrscan workflow](https://eqcorrscan.readthedocs.io/en/latest/submodules/autogen/eqcorrscan.utils.catalog_to_dd.write_correlations.html)
provides a reference for normalized time-domain correlation, pick-relative
lag searches, event-resource mapping, and i-minus-j differential times. Neither
source supplies all choices below. These are declared independent assumptions.

Use the existing, identified catalog pair roster. Preserve every pair's status,
including unavailable records and failed screens. Require the same full SEED
channel identity and physical receiver position, with both native metadata
epochs retained. The written vertical-component selection is applied using
provider orientation metadata. Unknown orientation remains unresolved;
nonvertical and unknown records remain available for a separate comparison.
No station is designated excluded from the original study on this basis.

The primary calculation uses native 100 Hz records, 256 samples per comparison
window, and a template beginning at the native sample nearest 0.5 s before
event i's catalog P pick. An exact half-sample tie chooses the earlier sample.
Event j's candidate starts cover delays within 0.25 s of the template start
relative to its own pick. Require complete coverage of the template and the
entire declared candidate-search support; a gap does not narrow the search.
Require continuous,
finite, unmasked samples with verified NSLC and timing. Preserve other sample
rates as unprocessed, without silently resampling. There is no extra bandpass,
response correction, fractional interpolation, or amplitude calibration.

For each candidate window, compute the signed Pearson coefficient after
subtracting the template's mean and that candidate's own mean. A positive
scalar rescaling may condition the calculation; it does not change the
coefficient. The longer search array and the template are not tapered for this
calculation. Applying unlike tapers would distort the lag comparison. Retain
all lag coefficients and actual sample-start offsets.

## Candidate delay and quality screen

Select the largest signed coefficient. Undefined zero-variance coefficients,
nonpositive maxima, a maximum at either search boundary, or numerically tied
maxima do not supply an accepted delay. Numerical ties mean coefficients within
`64 * machine_epsilon` of the maximum; this is a floating-point ambiguity
check, not a waveform-quality threshold. Retain all such candidates and reasons.
No minimum normalized-correlation coefficient is inferred from coherence.

After this discrete alignment, demean each of the two selected 256-sample
windows and apply a symmetric Hann taper. Compute the forward real FFT,
cross spectrum `conj(X_i) * X_j`, and the two power spectra. Average each
over five adjacent frequency bins with equal weights. At each original FFT
bin centered in 2–10 Hz, compute squared coherence as the squared magnitude
of the averaged cross spectrum divided by the product of averaged powers.
Adjacent smoothing bins outside 2–10 Hz remain included. Zero-power or
nonfinite bins make the screen unresolved. At least 10 of the 20 evaluation
bins must exceed 0.9. No phase slope is fitted for the delay.

Screening after alignment is intentional: averaging a rotating cross spectrum
can suppress estimated coherence even for exact delayed copies. For flat
spectral power, five-bin smoothing gives
`[sin(5*pi*delta*df)/(5*sin(pi*delta*df))]^2`, where `df = 100/256 Hz`.
An exact 0.1 s delay gives about 0.885 before alignment. This is a controlled
spectral example, not a real-data result. The earlier failed phase-slope pilot
and its catalog-aligned screen remain unchanged and separately labeled.

Let `a` be the actual template start relative to pick i, `b` the search start
relative to pick j, and `k` the accepted window-start index. Then
`delay_j_minus_i = b + k/100 - a` and
`dt_cc_i_minus_j = catalog_dt_i_minus_j - delay_j_minus_i`.
Store the catalog value, delay, result, sample spacing, coefficient, squared
coefficient, screen values, and complete processing configuration. Ten-millisecond
sample spacing is not a formal uncertainty; no millisecond precision is claimed.

## Saved identities, weights, and checks

Every saved real-data row carries both event/origin/pick/association resource
IDs, the complete SEED and FDSN channel identities, both metadata epochs,
raw waveform and metadata hashes, and the original catalog-row mapping.
Derived measurement IDs are explicitly local; absent provider IDs stay absent.
A legacy `dt.cc` export requires a full-identity sidecar and an explicit
resource-ID-to-integer mapping. Export collisions must be resolved before a
file is labeled usable.

Report `CC` and `CC^2`; a prospective `dt.cc` export uses `CC^2` as the declared
relative weight following EQcorrscan. It is not an estimated inverse variance.
The current tomography code multiplies both residual and matrix row by its
input weight, so importing `CC^2` there would contribute `CC^4` to the squared
objective. Solver import and the relative weighting of catalog and waveform
observations therefore require a separate explicit decision. A measurement
screen alone does not authorize an inverse update.

Before real measurements, check known delayed copies, gain/offset invariance,
sample-grid offsets and biased picks, incomplete/constant records, reversed
polarity, boundary/tied peaks, and the exact spectral smoothing identity.
Existing normalization controls are in
[normalized_correlation_checks](../normalized_correlation_checks/README.md).
The combined extraction, screening, and export implementation still requires
these component checks and independent review.
