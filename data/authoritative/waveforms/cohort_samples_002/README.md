# Native samples with explicit provider omissions

This continuation retains the same 14,262 picks and 44,718 catalog differences.
It assesses all 464 non-CMW1 windows for which the reviewed authoritative
[availability inventory](../cohort_cc_002/README.md) reported covering spans.
The first [failed attempt](../cohort_samples_001/README.md) remains unchanged.
Its 100-window dataselect response contains 96 complete windows and no samples
for four exact requested windows. Those omissions are preserved, not retried.

`cached_first_response.json` pins the original response, request, native
identifier attachments, provenance and decoder source, as well as identical
local copies. `offline_reuse_execution.json` records an end-to-end run without
`--fetch`; `samples_001.json` retains 96 decoded rows, four explicit omitted
rows, and all original catalog records. The later `acquisition_execution.json`
records the bounded continuation. Batch 0 reuses those exact bytes; batches
1–4 request the other 364 original windows at the official NCEDC endpoint.
There are no alternative-source lookups or replacement records.

The only new decoder mode is explicit `--record-no-samples`. A native window
receives `provider_returned_no_samples` only if no complete trace exists and
no returned sample from its exact NSLC intersects the entire half-open
request interval. Any partial, gapped, overlapping, ambiguous, wrong-identity,
wrong-rate or wrong-quality support still fails. A sample exactly at the
start belongs to the interval; a sample exactly at the end does not.
`decode_checks_001.json` preserves 40 invented controls: the original 17
cases in both modes plus six absent/partial/boundary cases. The independent
source review is limited to its pinned source and controls.

Each decoded batch has `windows` with complete native metadata, trace and
sample indices, actual sample-grid offsets and little-endian sample hashes.
Its additive `missing_windows` entries retain `original_observation_index`,
the entire `native_pick`, and the explicit omission status. Both decoded and
omitted rows in the normalized full-cohort CSV retain the raw response path
and hash. The two disjoint identity sets must cover the complete requested
set. Missing sample values and waveform public IDs remain missing; no provider
identifier, gap sample, calibration or timing uncertainty is invented.

The final summary distinguishes `all_reported_available_non_cmw1_windows_assessed`
from `all_reported_available_non_cmw1_windows_acquired`. The first means every
planned request has an explicit decoded or no-returned-sample outcome. The
second is false whenever any such window lacks samples. The mode is recorded
as `explicit_record_no_samples_mode`; counts appear separately as
`decoded_native_windows`, `provider_returned_no_sample_windows`, and
`assessed_native_windows`. Availability omissions and the pending CMW1 access
clarification remain separate statuses in the unchanged full pick roster.

The saved command uses the project-pinned ObsPy environment:

```sh
MPLCONFIGDIR=tmp/waveform_cache/mpl XDG_CACHE_HOME=tmp/waveform_cache/xdg TMPDIR=tmp/waveform_cache/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python data/authoritative/waveforms/cohort_samples_002/acquire.py --fetch --record-no-samples --batches 5 --summary samples_002.json
```

Do not rerun this completed/fresh-name command over existing evidence. The
controller records source/review hashes and the child PID before execution,
then terminal return status and output hashes; interruption terminates its
process group. Raw bytes, requests and native attachments remain immutable.
This package establishes sample identity and support only. It makes no
correlation measurements, does not establish historical archive absence,
and does not infer original study membership or exclusions.

The bounded acquisition completed with code 0. All 464 selected windows were
assessed: 459 have decoded native samples and five have an explicit
`provider_returned_no_samples` outcome. No partial or ambiguous window was
accepted. The full pick table also retains 13,681 windows without a reported
availability span and 117 CMW1 windows pending the separate access
clarification. The five raw replies total 1,978,368 bytes; the first reply was
reused, so only four new requests were made in this continuation.

Decoded support comprises 348 windows on `NC.JPR.02.EHZ`, 47 on
`NC.CBR.10.EHZ`, and 32 each on `NC.JSB.10.EHZ` and `NC.JSF.10.EHZ`. Every
decoded window has 500 samples at 100 Hz. The four originally omitted JPR
windows remain omitted. The fifth is original pick row 8103, event
`quakeml:NC.anss.org/Event/NC/320692`, pick
`quakeml:NC.anss.org/Arrival/NC/38629844`, requested on `NC.JPR.02.EHZ` from
1992-10-18T13:42:25.710000Z to 13:42:30.710000Z. Its full native epoch and
resource context remain in batch 2 and the normalized pick table.

Joining the unchanged pair roster through both native event/pick/channel/
epoch identities gives 1,195 catalog differences with decoded support on
both sides, all with provider-declared vertical orientations. The five
omitted picks affect 38 original pairs, including 37 whose two availability
spans were reported. All 44,718 original pairs remain; these support counts
are not accepted correlation measurements. The terminal summary and later
independent sample review bind the exact raw, decoded and normalized files.

`independent_samples_review.json` passes the terminal identity and accounting
audit: 898 pinned inputs, all 30 raw/request/decoded artifacts, all 459 decoded
traces and independently extracted sample hashes/timestamps, and zero exact
sample intersections for each of the five omitted windows. It verifies the
unchanged full pick roster and the disjoint 464-window union. Correlation
quality and timing uncertainty remain outside this audit.
