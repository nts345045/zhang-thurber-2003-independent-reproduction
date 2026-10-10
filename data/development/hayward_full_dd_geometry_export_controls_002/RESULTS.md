# Same-ray geometry export: 82 invented checks pass

The frozen controls completed with **82/82 passing** on 2026-10-10 at
11:14:08 UTC. All 34 compiler/fixture/reader children were reaped, and the outer
controller reaped the runner with code zero. The three builds used the pinned
compiler and original optimized flags; their stderr logs are empty. Closed
outer logs and the executed controller are preserved in `controller_provenance/`.
The controller copy is execution provenance; the fresh-package replay entry is
`run.py`, following its hash-bound preparation and review gates.

The original and candidate commands each evaluated only three used native
event/receiver-epoch pairs in the same invented homogeneous cube. **All eight
original export files are byte-identical**, including the matrix, weights,
smoothing, ordered-entry scaling, and 12-digit ray table. The candidate adds
the two reviewed geometry/path files without changing those results.

The standalone reader verifies all four original observation rows, three
native pairs, 24 saved path nodes, and 20 signed source-matrix entries. The
zero-prior-only pair remains present. Both receiver epochs, empty location,
open epoch end, quoted metadata, and all native event/origin associations are
preserved. The 17-digit coordinates match the parsed 12-digit input point,
which deliberately differs from the earlier unrounded fixture coordinate.

The remaining checks comprise 17 supplied-Ray cases, 44 malformed saved-table
cases, eight export-path preservation cases, and two reader-output preservation
cases. False local/initializer/geometry flags remain false. Empty or nonfinite
paths and short derivative vectors remain inspectable before the original
assembly refusal. Straight initialization allows unused NaN seed diagnostics;
the FMM config rejects an absent required initializer. Both real `/dev/full`
faults reached checked flush/close rejection. Prior files and dangling links
were preserved, with no second new diagnostic emitted before refusal.

The earlier `../hayward_full_dd_geometry_export_controls_001` is preserved
**unexecuted**. Independent source inspection found that mutually consistent
observation/exported-row metadata could bypass a direct native association
join. This variant adds those joins and eleven coordinated corruption cases;
the exporter candidate and C++ fixture remained unchanged.

Passing these controls establishes the tested export/readback behavior only.
It does not certify first arrivals, final three-dimensional accuracy, source
or model derivative accuracy, nonlinear convergence, or the earlier internal
inversion state. A field copy still needs an exact source/binary/config/terminal
export record and separate final accuracy acceptance. No field ray, inverse,
covariance calculation, data retrieval, maintained source, live input, or Git
state was changed. The existing covariance algebra was not rerun.

Terminal evidence:

- `summary.json`: `f090766ef2bafd6aeaeb049506800d566386fffaac2e2feacd6762f94a1428a2`
- `execution.json`: `34255a4ca3fa9a3551b922ea9aed94fbbbe07b5dcb91c5f394793d447b2ebaeb`
- `controller_provenance/completion.json`: `f7f496ef5ea38db6495545cc8b59a8b4bdce9781c2d7fee3ad8fbb309080fa0f`

The summary pins 1,031 generated artifacts. The independent terminal readback
is reserved for root in `review_saved.py` and `review.json`; this document does
not claim that separate review has occurred.
