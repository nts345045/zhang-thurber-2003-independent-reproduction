# Bounded control plan — not executed

Review this source and a small concrete harness before compiling either copied
tree. Use the existing absolute compiler and flags pinned in `prepared.json`.
Keep assertion checks enabled. All inputs below are invented; no authoritative
geometry, live run input, or field reference is needed.

## Actual before/after export parity

Use one tiny constant-velocity cube with two events and two colocated receiver
rows having different metadata epochs. Preserve an empty location code, an open
epoch end, full invented event/origin/channel/pick identities, and a quoted
metadata field. Include absolute and cross-epoch DD observations, plus a
zero-prior row whose native ray pair occurs nowhere else. This last pair must
remain in both new files even though its matrix row is omitted.

Freeze identical saved event/grid/observation/config bytes for `before` and
`after`. Select a small positive FMM spacing and one explicit stage; the same
config is used by both executables. Run only the full-linearization command,
not inversion. Compare all eight original files byte for byte. This includes
the matrix, row weights, suppressed terms, smoothing, scaling/damping metadata,
native rows, and 12-digit ray table. The test fails if any original file differs.
The existing `diagnostics/check_full_linearization.cpp` supplies the fixture
and exact assembly conventions; no covariance-algebra suite needs to be repeated.

Read the two additional files independently. Require complete unique native
support, sequential zero-based node indices, exact point counts, every native
metadata string, and numeric 17-digit round trips. Recompute closed-box and
endpoint flags from the paths and parsed input tables. Compare all common
numeric/status fields with the original ray table at its existing 12-digit
serialization. Match new source partials to the corresponding signed source
entries of the original matrix export. Require attempted/successful
initialization according to the saved config, without inferring first arrivals.

## Supplied-Ray controls, with no additional tracing

Call the actual copied array writer on a small explicitly constructed Ray
inventory. Preserve the same native metadata and distinguish these arrays from
computed physical rays. Read every resulting status and path record.

- Valid finite arrays cover both receiver epochs and the zero-weight-only pair.
  Add a straight-config case with unattempted initialization to demonstrate the
  existing conditional policy. Repeat its saved flags under an FMM config only
  in the readback control: missing required initialization must be refused.
- Change only the local flag; then only attempted-initializer success. The
  writer must retain the complete diagnostics and unchanged false flags, while
  the config-aware readback refuses them. Finite arrays retain the original
  exporter's permissive diagnostic behavior; this patch adds no gate.
- Set one interior point just outside a grid face using `nextafter`, alter each
  endpoint separately, empty a path, and introduce a nonfinite path coordinate,
  travel time, or source partial. Verify the corresponding existing flags and
  complete retained node records. For nonfinite/empty Rays the original
  finite-ray rejection must still occur after both new files are closed.
- Shorten `dv` and `length` separately. Each case must retain
  `ray_derivatives_evaluated=0`, blank source-partial fields, and the original
  dimension error before matrix assembly. A wrong total Ray-array size remains
  an early error with no invented rows.

For the independent saved-table reader, mutate one copy at a time: missing or
duplicate support, changed event/origin/channel/epoch metadata, dropped or
duplicated path node, wrong node order/count, changed endpoint, changed domain
flag, or false evaluated flag. Each mutation must fail the exact relevant join
or existing status predicate. Do not introduce a new gradient-magnitude cutoff,
path smoothness criterion, or minimum link length.

## Evidence preservation and I/O

Precreate each new suffix separately as a regular file and as a dangling
symlink. Call the actual CLI with otherwise missing inputs: refusal must occur
before input reading, ray work, or modification of the existing artifact. Also
exercise the direct array writer's refusal.

Use a declared fixture-only output-opening seam to direct each new stream to
`/dev/full`, after the fresh-path check, while leaving the actual writer and
`finish_output` body unchanged. This tests a real write/flush/close failure,
not merely the prior-file refusal. The thrown failure must prevent a successful
export claim. Preserve any partial diagnostics and exact seam diff.

Save the exact harness, sources, config, commands, compiler/runtime pins,
before/after files, checks and failures in a fresh control package. No source
adoption or field export follows merely from these controls. A later field
diagnostic must use a copied terminal saved model and keep the original run
unchanged. Its final accuracy acceptance is a separate decision.
