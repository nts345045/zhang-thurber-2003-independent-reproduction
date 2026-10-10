# Corrected authoritative bulk routing request

This continuation preserves the exact cohort and prospective processing scope
in [cohort_cc_001](../cohort_cc_001/README.md). The first POST attempt and its
HTTP 400 response remain there unchanged.

The [official EarthScope POST example](https://service.earthscope.org/irisws/fedcatalog/docs/1/help/)
submits only the channel/time selection lines. This helper removes the two
GET-style `targetservice` and `format` headers from routing POST bodies,
retains every native selection line byte for byte, and uses the documented
default request-format response. It preserves original and corrected body
hashes and both request-line numbers in identifier attachments. All returned
service declarations remain in the raw reply; only the authoritative NCEDC
dataselect endpoint is used for waveform routing checks.

The first corrected request is limited to the same 25 used-epoch intervals.
The full 14,262 picks and 44,718 catalog differences remain in the pinned
plan. This is a client syntax correction, not a data-selection change. Any
remaining access or identity difficulty stops the affected request stage
and is reported before an alternative is attempted. Supported no-span
replies remain recorded inventory findings, as authorized below. No calibration correction,
waveform measurement or catalog replacement is performed by this helper.

The corrected POST succeeded. Through batch 7, EarthScope returned 195 of
200 requested used-epoch intervals. The five absent intervals are exactly
the known historical `NC.CMW1..EP2`, `EP3`, `HN1`, `HN2` and `HN3` records,
covering 117 picks and 199 catalog differences. They have authoritative NCEDC
operation identities but no corresponding historical StationXML routing
entries. This is a metadata-routing omission, not a statement of waveform
absence. `routing_all_001.json` preserves the initial stop at this point.

The user's calibration clarification authorizes investigation of these same
117 windows directly at the documented NCEDC availability service using the
already recovered historical identities. `cmw1_availability` divides them
into 100 and 17 exact windows, without renaming channels or backdating epochs.
`--allow-known-cmw1-routing-gap` permits the remaining routing batches while
retaining these five omissions explicitly. Any different missing route or
failure of the supported direct request still stops and is reported.
`source/acquire_routing_initial.py` preserves the exact earlier helper.

The complete routing continuation in `routing_all_002.json` returned 367 of
372 requested epoch intervals. Only those five historical CMW1 intervals
remain absent. The first direct CMW1 availability batch returned HTTP 200
with an empty `datasources` array for its 100 exact windows. That response
and the initial stop remain in `cmw1_availability_001.json`. A separate
supported-POST check of the two already retrieved pilot windows returned
their expected `NC.JPR.02.EHZ` spans at 100 Hz. This was a request-capability
check, not a replacement measurement pair. No CMW1 samples or alternative
sources have been requested while the availability clarification is pending.

The authorized inventory continues all original 14,262 windows: 14,145
non-CMW1 picks in 142 batches and all 117 CMW1 picks in two batches. A
supported empty response records a gap and does not discard its pick or
catalog differences. Access errors or unexpected channel identities still
stop the request stage. `run_inventory.py` saves each command before its
child starts, captures the terminal return code and file hashes, and leaves
the immutable response/request/identifier files in `raw/`. The controller
does not implement process-group interruption cleanup; inspect its recorded
child state before any recovery rather than restarting a potentially live
request process.

The inventory completed all 144 batches. `summarize_inventory.py` verified every raw response,
request, native identifier attachment, and reported span. It rederives
coverage directly from provider JSON, then retains every original column
in the pick and pair tables with added availability fields. The requested
windows are half-open; provider span ends are last-sample times, so the
reported span must reach the requested end minus one sample interval.
This establishes reported coverage only. Actual sample-grid alignment,
continuity, overlaps and decoding remain unchecked until samples are
retrieved. `summary_raw_coverage_checks.json` records an intermediate offline
check of 3,100 windows plus two rejected invented corruptions.

The terminal `inventory_summary.json` and `independent_inventory_review.json`
retain all 14,262 picks and 44,718 catalog differences. Covering spans are
reported for 464 windows from 402 events: 353 on `NC.JPR.02.EHZ`, 47 on
`NC.CBR.10.EHZ`, and 32 each on `NC.JSB.10.EHZ` and `NC.JSF.10.EHZ`. Every
reported span uses 100 Hz and quality code D. The other 13,798 windows,
including all 117 CMW1 windows, have no reported covering span. Both picks
have reported spans for 1,232 catalog differences; 43,486 lack one or both.
These counts describe this service inventory. They do not establish
historical waveform absence or membership in the original study.

The independent terminal audit rederived coverage from raw provider JSON
using exact rational times, checked all 144 requests and native attachments,
and verified 879 input hashes plus both normalized table hashes. Every
original pick and pair column remains unchanged. Actual sample retrieval has
its own [saved evidence](../cohort_samples_001/README.md); a reported span is
not treated as proof that the corresponding dataselect request returns samples.

The inventory makes no correlation measurements. The subsequent
[declared method](../../../development/normalized_correlation_specification/README.md)
uses normalized raw-window correlation without added filtering or response
removal, then applies a separate spectral-coherence screen. This supersedes
the earlier prospective filtering discussion without changing these five-second
requests. The paper's squared spectral-coherence criterion is distinct from
a normalized time-domain correlation coefficient.
