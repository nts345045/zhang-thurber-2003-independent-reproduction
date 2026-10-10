# Identified raw waveform samples

This package is prepared for the existing 14,262-pick Hayward cohort. It
requests only original windows with a reported covering span in the completed
[availability inventory](../cohort_cc_002/README.md), after an independent
review binds that inventory's exact summary hash. CMW1 sample and alternative
retrieval remain paused for the access clarification. Every original pick and
all 44,718 catalog differences remain in the identified input tables.

Requests use the official NCEDC dataselect POST endpoint established through
EarthScope routing. Batches contain at most 100 unchanged P−1 to P+4 second
windows. Empty SEED locations remain empty in metadata and use `--` only in
the request syntax. Each response is saved unchanged as `.response`, including
HTTP errors, with its exact request, UTC timestamps, URL, hash and full native
event/origin/pick/association/channel/epoch identifier attachments. No provider
waveform public ID is invented. No calibration or response removal is required.

ObsPy 1.5.1 decodes the miniSEED bytes. The helper checks returned NSLC, rate,
quality and finite unmasked samples, then maps each half-open native window
to exact sample indices. Sample-grid offsets remain explicit rational Unix
nanoseconds. It requires one continuous trace for the whole window and rejects
overlapping returned traces; it does not interpolate gaps, resample, or select
between overlapping qualities. Decoder metadata and every native pick field
remain in the decoded record and normalized full-cohort table. MiniSEED timing
quality and calibration fields retain the decoder's values, including `False`
for unavailable fields. Those fields are not calibration gates.

The current [measurement specification](../../../development/normalized_correlation_specification/README.md)
uses raw windows without added filtering. These acquisition checks establish
sample identity and continuity, not correlation quality or an accepted delay.
The helper makes no waveform measurements and changes no catalog observation.
Unexpected access, identity or sample-support difficulty stops retrieval and
preserves the raw evidence before any alternative is attempted.

`decode_checks.json` preserves the first 15 invented miniSEED controls, including empty
location, a 3 ms native-grid offset, provider padding, standard decoding of
contiguous records, and rejection of gaps, overlaps, wrong identity/rate/quality,
incomplete windows, epoch crossing and nonfinite samples. `pilot_decode_checks.json`
replays the same two previously archived authoritative pilot records, retaining
their original identities and 500 samples each. `environment.json` verifies all
24 package versions in the existing pilot requirements file. No network request
was made for these checks.

Independent source review then identified an omitted edge case: an alternate
trace could contain a sample inside the requested window but outside the
chosen trace's first/last sample times. `edge_counterexample_001.json`, its two
invented miniSEED files, and `source/*_before_edge_fix.py` preserve both accepted
but ambiguous leading/trailing examples and the old source. The corrected
overlap check tests sample-index intersection with the entire requested
half-open interval. `decode_checks_002.json` passes all 17 controls, including
both new rejections; `pilot_decode_checks_002.json` confirms the two original
pilot decodes remain exactly unchanged. The original source review remains
bound to the old hash; the correction has its own review.

After terminal inventory review, use the pinned project environment and fresh
summary names. An initial request remains bounded to one batch:

```sh
MPLCONFIGDIR=tmp/waveform_cache/mpl XDG_CACHE_HOME=tmp/waveform_cache/xdg TMPDIR=tmp/waveform_cache/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python data/authoritative/waveforms/cohort_samples_001/acquire.py --fetch --batches 1 --summary samples_001.json
```

The source is frozen before requests. Cached replies are checked against the
exact request and native context. A later bounded continuation uses a fresh
summary name and revalidates cached replies without replacing their bytes.
The completed summary distinguishes the requested batch count from complete
coverage of all reported-available non-CMW1 windows.

The first real batch returned HTTP 200 and 393,216 unchanged miniSEED bytes,
then stopped at the unique continuous-support gate. No second request ran.
`acquisition_execution.json`, the raw response and its `decode_failure.json`
preserve that failed attempt. The offline `diagnose_batch_000.py` readback,
saved in `batch_000_offline_diagnosis.json`, finds 96 complete native windows
that pass the unchanged decoder and four windows with no returned sample
anywhere in their requested half-open interval. There are no partial or
ambiguous windows in this response. The four absent windows are:

| Original pick row | Provider event ID | Channel | Requested UTC start (five seconds) |
| --- | --- | --- | --- |
| 2275 | `quakeml:NC.anss.org/Event/NC/68937` | `NC.JPR.02.EHZ` | 1986-03-29T17:11:48.570000Z |
| 2335 | `quakeml:NC.anss.org/Event/NC/68936` | `NC.JPR.02.EHZ` | 1986-03-29T18:31:13.320000Z |
| 2466 | `quakeml:NC.anss.org/Event/NC/69426` | `NC.JPR.02.EHZ` | 1986-04-03T11:51:26.790000Z |
| 3248 | `quakeml:NC.anss.org/Event/NC/100229` | `NC.JPR.02.EHZ` | 1987-05-11T06:45:51.210000Z |

The diagnosis preserves full event/origin/pick/association/epoch identities,
all 96 decoded trace grids and sample hashes, the four original availability
records, and all 34 affected catalog differences. Thirty-three of those
differences have reported availability for both picks. The cause of the
availability/dataselect discrepancy remains unresolved; this response does
not establish historical archive absence. No gap filling, alternate lookup,
replacement pair or waveform measurement was performed.

Continuation is authorized within the documented subset only through an
explicit missing-window status in a separate acquisition variant. The four
no-sample cases and all catalog records must remain present. Their original
requests must not be repeated; partial, overlapping or ambiguous returned
support must still stop acquisition. This package remains the unchanged
failed-attempt evidence.
