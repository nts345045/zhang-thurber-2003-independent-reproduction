# Lossless simulation packaging checks

Seventeen checks passed using the completed two-event/two-receiver invented
launcher002 simulation and an independent numerical/native output review.
No real Loma archive was produced by this suite.

The preserved positive package contains every byte of all 39 original files,
including full native identities, across 16 artificially small 4 KiB parts.
The normal publication bound is 50 MiB per part. Stream readback and a fresh
restore verified every filename, size, and SHA-256. A separate invented member
larger than 2 MiB crossed many part boundaries and restored exactly; that larger
fixture stays under the project-local temporary test directory.

Negative checks reject live/interrupted simulations, failed or stale reviews,
changed observations, an existing output/restore directory, parts over 50 MiB,
corrupt/missing compressed parts, wrong member hashes, unsafe member paths,
and changed publication manifests. A failure after output reservation records
an explicit failed execution and the failure report hash. Partial artifacts
remain inspectable. All original invented fixture bytes remain unchanged.

`summary.json` pins the actual helper, test, and package outputs. The package's
readable manifest and evidence link binary parts to exact native event/origin
and channel/epoch tables. The review used here is
[fixture_review.json](../loma_simulation_packaging_001/fixture_review.json).
The first smoke package/source are preserved under `../loma_simulation_packaging_001`;
`../loma_simulation_packaging_002` preserves the earlier 14-check result before
the failure-state and publication-manifest guards were added.

Rebuild the final test in fresh directories:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_loma_simulation_packaging.py \
  --output data/development/loma_simulation_packaging_NEXT \
  --work tmp/loma_packaging_checks_NEXT
```

Only after the real independent simulation review passes and its raw outputs
are frozen, the intended publication command is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/package_loma_simulation.py package \
  --data data/loma_lom_analytic_001 \
  --review data/loma_lom_analytic_001/independent_simulation_review.json \
  --output data/published/loma_lom_analytic_001
```

The helper refuses a nonterminal run, failed/mismatched review, or populated
publication directory. It retains local originals, streams one level-1 gzip
tar into bounded parts, performs complete member/part/CRC readback, and rehashes
all originals before reporting success. Compression changes no record IDs,
values, CSV formatting, pair selection, or precision. Publication preserves
synthetic observations; it does not claim that native provider IDs represent
new observed picks or that an inverse forward operator is accurate.

Publish only the helper and reviewed package directory. Stable `readable/*.log`
files require explicit force-add because the repository ignores logs; verify
all manifest-referenced files are tracked. Do not stage the original large CSV
files. Restore requires a new directory and verifies the complete stream again.
