# Normalized waveform correlation: acquisition checkpoint

The user clarified that normalized raw-waveform cross-correlation should
produce identified `dt.cc` inputs. Instrument response correction is not
required. The historical CMW1 calibration and orientation remain unknown;
no later metadata are backdated. The earlier failed cross-spectral pilot and
the complete catalog observations remain unchanged.

This package resumes the immutable [full-cohort plan](../cohort_plan_001/README.md):
14,262 picks, 44,718 catalog differences, 62 NSLCs and 372 native receiver
epochs. It uses the exact planned P−1 to P+4 second requests. The earlier
plan's paused-state strings describe that historical checkpoint; current
requests and outcomes are recorded separately here. Nothing in this package
changes the pair graph or replaces a rejected pair with another.

## Authoritative retrieval

Initial discovery used USGS/ComCat and EarthScope, then the routed NCEDC
archive. [EarthScope fedcatalog](https://service.earthscope.org/irisws/fedcatalog/1/)
accepts selection-list POST requests. Its routing output is channel discovery,
not evidence that samples exist. The prior pilot shows whole-second output
even for a request with fractional-second endpoints; exact native window
times remain in every request and identifier attachment.

`acquire.py` first checks dataselect routes in batches of at most 25 used-epoch
intervals, then queries [NCEDC availability](https://service.ncedc.org/fdsnws/availability/1/)
in batches of at most 100 pick windows. Batch sizes bound requests without
reducing the selection. Missing routes, missing spans, unexpected identities
or access errors are preserved and stop acquisition for clarification.
No automatic retries or guessed aliases are used.

Raw POST bodies and provider responses are exclusive-created. Each response
has URL, UTC, HTTP status, hash, request-body hash and full native request
identifiers, including both the provider pick identity and its event/origin/
association context. Derived FDSN channel identifiers are distinguished from
provider IDs. Valid empty locations remain empty in metadata and become `--`
only in request syntax. Missing provider waveform IDs remain missing.
Parsed routing and availability records link back to these identified
requests. Availability quality, rate and overlapping spans remain distinct.

No full-response request is an acquisition prerequisite. Subsequent miniSEED
retrieval will use the established NCEDC route and pinned standard ObsPy
environment, preserving raw bytes and checking exact NSLC, timing, sample
rate/grid and gaps/overlaps before processing. This checkpoint does not yet
claim complete coverage or create any waveform differential observation.

## First request outcome

The first 25-epoch EarthScope POST returned HTTP 400 on 2026-10-10 UTC.
Its error identifies `format=request` as invalid for the requested target
service. The original planned POST included `targetservice=dataselect` and
`format=request`; the same options had succeeded in earlier GET probes, but
the bulk POST had not previously been submitted. The exact body, raw error,
HTTP provenance and all request identities are retained under `raw/`.
`routing_001.json` records the stop before any availability or waveform query.
No missing station or waveform is inferred from this syntax rejection.

The [official POST example](https://service.earthscope.org/irisws/fedcatalog/docs/1/help/)
uses channel/time selection lines without those two option headers. Any
corrected request must be saved separately, keep the same 25 original
channel/time lines, and preserve this failed attempt. `source/acquire_initial.py`
pins the exact helper used for the first request.

## Processing basis established before broad measurements

The official [EQcorrscan normalized correlation definition](https://eqcorrscan.readthedocs.io/en/latest/submodules/utils.correlate.html)
subtracts the template mean and the comparison window's local mean at each
lag and divides by both window norms. The
[`write_correlations` API](https://eqcorrscan.readthedocs.io/en/latest/submodules/autogen/eqcorrscan.utils.catalog_to_dd.write_correlations.html)
uses event resource IDs to associate waveform streams and defines differential
times as travel time for event i minus that for event j. Correlation-squared
weights are an optional data convention, not a calibrated timing uncertainty.
Its [preprocessing source](https://eqcorrscan.readthedocs.io/en/latest/_modules/eqcorrscan/utils/catalog_to_dd.html)
detrends and uses a four-corner Butterworth filter in forward and reverse
directions; no response removal is included in that path. These primary pages
were checked on 2026-10-10 UTC.

The written precursor provides 2.56-second tapered windows and a 2–10 Hz
squared-coherency criterion; it does not prescribe a normalized-CC threshold
or the missing preprocessing details. The prospective normalized-CC diagnostic
uses a 2.56-second template starting 0.5 seconds before the catalog pick,
a ±0.25-second lag search and a 2–10 Hz zero-phase filter. Window placement,
lag range and filter are declared methodological assumptions, not recovered
paper parameters. Interpolation, correlation acceptance and uncertainty will
be declared and tested before broad measurements; no choice is selected from
the prior failed pilot. In particular, a time-domain correlation coefficient
is not equated with the paper's squared spectral coherence.

Scalar amplitude normalization does not establish identical instrument phase
response. Missing response and orientation information remains an explicit
limitation of the authorized raw-waveform workflow, without becoming a
calibration gate or a station-exclusion rule.
