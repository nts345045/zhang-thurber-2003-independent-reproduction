# Invented catalog-plus-CC input controls

These controls exercise the proposed adapter and the existing C++ observation
loader and matrix assembly. All records, identities, coordinates and supplied
ray values are invented. No real observations are imported, no travel times
are calculated, and no inverse solve is invoked.

Variant `002` is the final source snapshot: 70 Python checks and 36 C++ checks
pass. Variant `001` preserves the preceding successful 70/34 checks. The only
subsequent change adds an explicit C++ case with nonunit stage and distance
factors; the adapter and production code are unchanged between variants.

The fixture has two events, two epochs of one channel with an empty location
code, two absolute catalog rows and one catalog differential row. One accepted
CC row is appended. Its original event, origin, pick, association, both epochs,
source hashes and quoted multiline metadata remain attached. The controls
verify every original catalog value and its uncertainty string, original row
order, unchanged geometry and preserved original catalog bytes. They reject
changed native associations, missing or replaced mappings, source-row changes,
an invented CC timing uncertainty, a changed sign or origin correction,
unreviewed acceptance, stale hashes and nonfresh or overlapping output paths.
Rejected measurements do not become solver rows.

The C++ component loads the adapter's invented output through the actual
`observations`, `validate_identities` and `observed_rays` functions. Both epochs
survive; appending CC adds no new native source/receiver pair. Metadata survives
the actual writer/loader round trip. Supplied arbitrary ray values distinguish
the two native receivers and check prediction and all eight source/origin
derivative signs without calling a ray tracer.

The selected literal legacy convention is tested through `observation_weight`
and `Matrix::add`, rather than only a separate Python formula. With CC = 0.5,
the prior row multiplier is 0.25. A residual/cutoff ratio of 0.5 gives a robust
factor of 0.5625. Unit stage and distance factors give a combined multiplier of
0.140625 and a weighted residual of 0.0703125; its squared-objective contribution
relative to a unit prior is 0.0625 = CC to the fourth power. A second case uses
stage 0.5 and distance taper 0.5625, yielding multiplier 0.03955078125 and weighted
residual 0.019775390625. Both Jacobian and residual are checked. Catalog-only
configuration still rejects type 2, and derived CC uncertainty remains blank.

Each variant saves frozen adapter, harness and canonical C++ sources, complete
invented CSV/JSON inputs and outputs, compiler/component logs, source and
artifact hashes, and a summary. The temporary executable is identified by hash
and command. The invented export-review envelope tests the adapter's byte and
status gates; it is not evidence for real waveform acceptance. Independent
real-data measurement/export reviews remain prerequisites for any later import.

Rebuild from the integration repository root into a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python \
  diagnostics/check_hayward_cc_input.py \
  --output data/development/hayward_cc_input_checks/FRESH
```

No run configuration, solver weighting calibration or CC covariance is selected
by the adapter. A later isolated run must explicitly specify `catalog_only_dd=0`
and all nine stage factors. CC squared is not a formal inverse variance; the
existing catalog shared-pick covariance must continue to reject type 2.
