# Full-support 1D comparison helper checks

These are invented homogeneous geometry and CSV/matrix fixtures. They are not
provider observations or results from a field inversion.

`check.py` constructs two identified fixture rays with exact homogeneous travel
times and source derivatives. The nodal log-slowness kernels use two-point Gauss
integration, which is exact for the trilinear shape weights along these straight
paths. One source derivative is exactly zero and omitted from the triplet table.
The helper recovers that component as zero and preserves every identity column.
Time/source differences remain below the declared 12-significant-digit
serialization bound. The test then changes an event ID and removes an origin-time
column independently; both malformed fixtures fail before creating output.

Run from a clean checkout with Python 3.6+, NumPy and SciPy:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_1d_support_checks/check.py
```

The fixture refuses to overwrite `tmp/hayward_1d_support_checks`.
`results.json` records all three passing controls, executed commands, and hashes
of the fixture, helper and unchanged reference module. No production solver,
ray tracer, inversion, or provider query is invoked.

The real comparison command will be:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_hayward_1d_support.py --data data/hayward_first_arrival_003 --output data/development/hayward_first_arrival_003_1d_support
```

It requires a completed `preflight.json` and verifies the frozen geometry,
observations and linearization-table hashes. The helper preserves every original
linearization-row field and appends continuous-reference results. All reference
candidates and unresolved cases are saved in `references.jsonl`, joined through
row, observation, event and native station indices. The native provider IDs and
epochs remain directly in `comparison.csv`. Source derivatives come from the
saved unweighted Jacobian, with omitted entries interpreted as zero and verified
source-column mapping. Reference results apply only to the initial one-dimensional
profile. They impose no new inversion or field-accuracy threshold.
