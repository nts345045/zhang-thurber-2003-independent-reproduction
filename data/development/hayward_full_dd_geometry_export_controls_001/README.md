# Invented same-ray geometry export controls

This package is prepared for source/harness review. No control has yet run.
`prepare.py` copies the reviewed isolated exporter candidate, writes invented
inputs, and records source/runtime hashes. `run.py` refuses execution without
a passed `prelaunch_review.json` bound to its exact `prepared.json`. The runner
owns and reaps each compiler or fixture child, retains return codes and logs,
and preserves failed checks rather than changing their expectation.

The planned 71 checks comprise eight original-file byte comparisons, an actual
geometry readback, zero-prior-only native support, the parsed saved-model point,
17 supplied-Ray cases, 33 malformed saved-table cases, eight new-export-path
preservation cases, and two reader-output preservation cases. `cases.json`
lists the case names before execution. Compilation uses the exact pinned
absolute compiler and original `-O3`, OpenMP, assertion-enabled flags.

Only two tiny physical exports run: the original and candidate binaries each
evaluate the same three used event/receiver-epoch pairs in a homogeneous cube.
This exercises the actual `linearize_full` CLI and its FMM dispatch. The two
receiver rows are colocated but retain distinct epochs. One otherwise unused
pair belongs only to a zero-prior observation. Every identifier is explicitly
invented; quoted metadata, an empty location, and an open epoch end are retained.
The four input observations include a cross-epoch DD row.

The supplied-Ray cases do not evaluate rays. Their prescribed partials and
local flags are test values, not claimed physical derivatives or stopping
results. They exercise the actual array writer and its original failure
behavior. Empty/nonfinite/short-derivative arrays retain both new diagnostics
before the original rejection; finite local/initializer/geometry failures
remain exported and are refused by readback. Unattempted initialization is
accepted only under the straight config; unused seed diagnostics remain NaN.

The I/O variant changes only the file-opening line of the copied `output`
helper, using the declared `fixture_output_suffix` to redirect one new stream
to `/dev/full`. The writer, freshness checks and checked flush/close remain
unchanged. `io_seam.patch` exposes this fixture-only change. Regular-file and
dangling-link controls are separate, and test refusal before CLI input reads
or array assembly. The dangling links are removed after their unchanged target
and refusal are recorded; no runtime link is intended for publication.

`review_geometry.py` is a standalone standard-library reader. It streams the
large path and matrix tables, retaining only native inputs and per-ray counts.
It checks all original observation support, both native epochs, every metadata
field, 17-digit geometry at the parsed saved point, closed-box membership,
exact endpoints, existing local/derivative flags, the saved config's initializer
policy, old/new status serialization, unchanged original observation metadata,
and the signed source entries of the actual exported matrix. It hashes all
15 used files before and after a successful review. It does not repeat
covariance algebra or assign a scientific accuracy tolerance.

After a reviewed successful export, a later saved-copy review can use:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 review_geometry.py --data-dir SAVED_COPY --config SAVED_COPY/run.cfg --mode dd --output FRESH_REVIEW.json
```

This command alone does not attest which binary produced the files or its
terminal status. A field wrapper must separately bind source/binary/command,
config and final saved inputs to completed export evidence. Passing the reader
does not certify first arrivals, final three-dimensional accuracy, accurate
source/model derivatives, or nonlinear convergence. The evaluation point is the
parsed 12-digit saved model; its earlier internal precision is unavailable.
No native ray, inverse, covariance, observation query, maintained source, live
run, or Git state is part of these controls.

The preparation command is `PYTHONDONTWRITEBYTECODE=1 python3 prepare.py`.
Following independent source/harness review, the bounded execution command is
`PYTHONDONTWRITEBYTECODE=1 python3 run.py`. Preserve this package after either
success or failure; repeats require a fresh package.
