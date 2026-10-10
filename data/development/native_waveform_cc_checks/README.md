# Identified waveform measurement controls

The offline runner `diagnostics/run_native_waveform_cc.py` joins the complete
original catalog-pair roster to reviewed native sample windows. It calls the
unchanged, independently reviewed normalized-correlation core. These controls
use invented miniSEED records and explicitly fictitious event, origin, pick
and association identifiers. No observed waveform is processed here.

The runner requires a completed sample assessment and a passed independent
review with `samples_summary_sha256` bound to that exact summary. It verifies
the pinned plan, reference origins, all raw requests and responses, and full
native metadata before measurement. The frozen acquisition decoder is used
only for its offline `decode` function; its request functions are never called.
The decoded metadata and little-endian native sample hashes must match saved
records. Catalog travel times are checked against each pick's own identified
reference origin, and original pair differences are checked against those
travel times.

Every reported-available requested window must be accounted for. The explicit
`explicit_record_no_samples_mode` permits only the separately reviewed decoder's
identified zero-return status. Decoded and missing windows must be disjoint,
and their union must equal the full requested set. A partial trace, overlap,
wrong channel or altered sample is a failure, not a missing-window replacement.

The primary measurement requires the same full SEED/FDSN channel and exact
reported receiver coordinates, provider-declared vertical orientation and
native 100 Hz samples. Distinct native metadata epochs remain separate.
Unavailable, nonvertical, unresolved-orientation, unsupported-rate and moved-
receiver pairs remain in the output with explicit reasons. These are processing
statuses, not claims of exclusion from the published study.

## Output contract

`identified_measurements.csv.gz` contains one row for every original catalog
pair in its original order. Each original column is copied verbatim with the
prefix `original_catalog_`; original value, uncertainty and weight fields
therefore remain explicitly distinct from waveform results. New fields include:

- `measurement_id`: a local identifier, never a fabricated provider ID.
- `measurement_status`, `cc_attempted`, and `cc_ineligibility_reasons_json`.
- `dt_cc_i_minus_j_s`, `cc_candidate_dt_i_minus_j_s`, and
  `cc_delay_j_minus_i_s` with the documented sign convention.
- `maximum_cc`, `maximum_cc_squared`, and accepted-only
  `cc_relative_weight_squared`. None is an estimated inverse variance.
- Blank `cc_formal_timing_uncertainty_s`, separate sample spacing and coherence
  counts, and `diagnostics_jsonl_row` for attempted measurements.
- Both original pick-row indices, sample statuses, raw and decoded-window
  hashes, sample indices and starts, orientation and response metadata.

`attempted_diagnostics.jsonl.gz` retains every attempted pair, including failed
screens. Each record contains the full `original_catalog`, `waveform_i`,
`waveform_j`, `receiver_epoch_i`, `receiver_epoch_j`, and numerical `diagnostics`.
The diagnostics retain all computed lag coefficients and coherence arrays.
Undefined entries are JSON null with the rejection status preserved. A pair
rejected before a numerical array is computed does not invent that array.

The summary freezes input/source hashes, source copies and output hashes. A
terminal execution record binds the summary. A passed measurement review must
use `measurements_summary_sha256` to bind that summary before the separate
`dt.cc` exporter consumes accepted rows. Export still requires collision-checked
event and station mappings and a complete native sidecar. This runner writes
neither `dt.cc` nor tomography observations.

## Recorded checks

The fresh `002` suite passes 48 checks. It covers actual integer-nanosecond
pick-relative offsets, sign, cross-epoch and empty-location identity retention,
complete row preservation, full lag/coherence arrays, undefined coefficients,
zero-return accounting, orientation/rate/position statuses, and rejection of
altered origins, epochs, channel identities, catalog values, raw bytes, decoded
timing and gaps. Rejected runs preserve a failed execution record and do not
publish a completed summary.

`001` preserves the initial 43/44 outcome. Its sole failure was a test expecting
51 candidate starts when a 3 ms grid offset actually leaves 50 native starts
inside the full closed ±0.25 s interval. The output was correct; the maintained
test expectation was corrected. The frozen failure and explanation remain.

Reproduce with a fresh output directory from the integration repository root:

```sh
MPLCONFIGDIR=tmp/waveform_cache/mpl XDG_CACHE_HOME=tmp/waveform_cache/xdg \
TMPDIR=tmp/waveform_cache/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
tmp/waveform_env/bin/python diagnostics/check_native_waveform_cc.py \
  --output data/development/native_waveform_cc_checks/reproduction
```

The core component tests remain separate. These native-I/O controls do not
establish real-data correlation quality, timing uncertainty, instrument phase
equivalence, or inversion fitness.
