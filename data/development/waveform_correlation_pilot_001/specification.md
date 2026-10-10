# Written method and one-pair diagnostic assumptions

The target study reports 17,955 P-wave waveform-derived differences, but the
exact original measurement roster and processing implementation are not
identified. The existing catalog-derived differences are a separate data type.
This diagnostic concerns one already selected event pair at `NC.JPR.02.EHZ`,
using the two authoritative records in
[pilot_001](../../authoritative/waveforms/pilot_001/README.md). It does not create
an inversion observation or establish a full waveform dataset.

## Verified written specifications

[Waldhauser and Ellsworth (2002)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2000JB000084),
section 2.2, paragraph 16, pages ESE 3-3–3-4, describes vertical-component
records at stations within 200 km of the pair centroid. Its tapered windows
contain 256 samples over 2.56 s. At least half the squared-coherency values
within 2–10 Hz must exceed 0.9. Delay is obtained from cross-spectral phase
slope following Poupinet et al. (1984). Section 2.3, paragraph 18, weights
waveform differences by squared coherence and distinguishes waveform-energy
timing from first-motion timing. This passage was checked against the locally
retained primary manuscript text, not inferred from its figures.

The inspected prose does not determine taper shape, exact window placement,
spectral averaging, phase unwrapping, phase-fit weighting, interpolation,
an additional time-domain filter, or response preprocessing. It therefore
does not fully specify a reproducible numerical measurement. The 2–10 Hz
coherence evaluation band does not by itself prescribe a particular bandpass
filter. These missing choices must remain explicit before broad measurements.

## Declared diagnostic choices

The primary calculation starts 0.5 s before each catalog P pick, removes the
window mean, and applies a symmetric Hann taper to 256 samples. It retains raw
digital counts: the two retrieved full response descriptions are identical,
so no differential response correction is introduced. There is no resampling,
fractional sample interpolation, additional bandpass, or time-domain lag search.

With the forward transform convention `exp(-i*2*pi*f*t)`, form
`C = conj(X_i)*X_j`, `A = abs(X_i)^2`, and `B = abs(X_j)^2`. Average each over
five neighboring frequency bins with equal weights (a Daniell average), then
compute squared coherence `abs(mean(C))^2/(mean(A)*mean(B))`. Evaluate the
20 original frequency bins whose centers lie in 2–10 Hz. The averaging kernel
also uses adjacent bins outside that evaluation band. No zero padding creates
extra nominal observations.

Unwrap the averaged cross-spectrum phase in ascending frequency using the
usual nearest-adjacent `2*pi` branch. Fit a straight line with a free intercept
to the bins with squared coherence above 0.9, using ordinary least squares.
At least half the evaluation bins must pass the written coherence criterion
before the primary estimate is labeled a candidate measurement. No formal
millisecond uncertainty is inferred from the correlated, smoothed bins.
Phase-unwrapping cycle ambiguity remains a limitation; the catalog-aligned
window supplies the initial phase association.

If event j's waveform feature occurs `delta` seconds later relative to its
catalog pick than event i's feature, the phase slope is `-2*pi*delta`.
Consequently the waveform-energy difference in the existing i-minus-j solver
convention is `catalog_difference - delta`. This sign is checked with invented
analytic delayed cross spectra. Both original event/origin/pick/association
identities and distinct receiver epochs remain attached; a derived local
diagnostic ID is never presented as a provider resource ID.

Predeclared sensitivity calculations vary the pre-pick interval over
0.25, 0.5 and 0.75 s and the averaging width over 3, 5 and 7 frequency bins.
All nine variants are retained. The primary choice stays fixed regardless of
which variants pass. An unsuccessful pair is preserved as rejected rather than
replaced with a different pair or relaxed coherence criterion.

These choices define an independent, inspectable signal-processing diagnostic.
They are not claimed to recover the undocumented details of the 2002/2003
processing or to validate later inversion use.
