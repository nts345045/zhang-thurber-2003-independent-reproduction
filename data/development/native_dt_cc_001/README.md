# Identified normalized-correlation differential times

This export contains 98 accepted P differential times from the separately
reviewed [native waveform calculation](../native_waveform_cc_001/README.md).
It adds no observations to a solver and changes no catalog values. The timings
are newly measured for the documented authoritative subset; they are not the
manuscript's original waveform-difference dataset.

Keep the following files together:

- `dt.cc`: 98 event-pair headers and 98 observations. Each observation gives
  station code, travel time for event i minus that for event j in seconds,
  CC squared as a dimensionless relative weight, and P phase. The header's
  additional origin-time correction is zero.
- `dt.cc.identifiers.csv.gz`: all 44,718 original pair rows in their original
  order, with every measurement field preserved. The 98 exported rows point
  to exact header/data line numbers. The other 44,620 rows remain present with
  their measurement statuses and blank legacy line numbers. Both event,
  origin, association and pick resource IDs, full SEED/FDSN channel identities,
  both native epochs, waveform hashes and original catalog uncertainties remain
  attached.
- `event_id_map.csv`: the 1,058 events referenced by the complete pair roster,
  with provider event/origin resource IDs. The positive legacy integer is the
  original event index plus one. The accepted subset references 103 events;
  integer IDs are local mappings, not new provider resource IDs.
- `receiver_epochs.csv.gz`: all 22 native epochs used by accepted observations,
  including full station/channel metadata, reported positions, source hashes,
  verbatim location codes and explicitly absent provider resource IDs.
- `summary.json` and `execution.json`: input/source/output hashes and the
  completed offline command. The independent export review verifies saved
  headers, numerical values and all identity mappings.

Literal legacy station codes are used only after checking that each identifies
one full channel and reported physical position among exported observations.
Different metadata epochs remain distinct. Ambiguous station/channel collapse,
event-origin ambiguity, and duplicate or reversed pair/station/phase rows are
errors; none is silently merged. Numeric fields use 17 significant digits to
retain stored binary64 values.

The format, travel-time sign and event mapping follow the documented
[EQcorrscan convention](https://eqcorrscan.readthedocs.io/en/latest/_modules/eqcorrscan/utils/catalog_to_dd.html).
No response correction, new correlation, uncertainty estimate, or change to
the measurement screen occurs during export. CC squared is not a formal
inverse variance. Importing it as a row multiplier would square it again in
a least-squares objective; solver weighting remains a separate decision.

The [serialization controls](../identified_dt_cc_export_checks/README.md)
pass 45 invented checks before this real export. Reproduce from the integration
repository root with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/export_identified_dt_cc.py \
  --measurements-summary data/development/native_waveform_cc_001/summary.json \
  --measurements-review data/development/native_waveform_cc_001/independent_measurement_review.json \
  --epochs data/authoritative/waveforms/cohort_plan_001/identified_used_epochs.csv.gz \
  --output data/development/native_dt_cc_reproduction
```

Raw authoritative samples, all 14,262 original picks, and five explicit
zero-sample outcomes remain in
[`cohort_samples_002`](../../authoritative/waveforms/cohort_samples_002/README.md).
Rejected and unavailable waveforms imply no exclusion from the original study.
