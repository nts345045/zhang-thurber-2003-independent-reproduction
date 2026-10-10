# Same-ray full-DD geometry export: source-only candidate

This isolated candidate adds the saved path evidence missing from the existing
full-DD export. It has not been compiled or evaluated. No field export, ray
calculation, inverse solve, covariance calculation, or maintained-source change
was made in preparing it. The live old-kernel backtracking run is separate.

`before/` is the complete frozen `after/` source from the reviewed
[old-kernel backtracking candidate](../hayward_old_kernel_trial_backtracking_candidate_001/README.md).
In particular, its main is `a10dcdc3…`, core is `7111f67c…`, and original full
export header is `b32e9583…`. `after/` changes only `src/full_linearization.hpp`.
`candidate.patch` records every change; `prepared.json` pins both source trees
and this plan. The numerical kernels, inverse, ray dispatcher, config parser,
original eight export writers, and covariance analysis are unchanged.

## Two additional files

The existing `dd linearize_full CONFIG DIRECTORY MODE [STAGE]` entry point
would also write these files, using the same `const traced` array and
`observed_rays` inventory as the matrix:

- `MODE_full_linearization_ray_geometry.csv`: the existing
  `write_ray_status(..., &used, &g, 17, true)` output. It records source/receiver
  coordinates, pure travel time, origin-time offset, source partials, path count,
  domain and exact-endpoint flags, local/initializer flags, derivative-dimension
  availability, and every native event/channel metadata field.
- `MODE_full_linearization_ray_paths.csv`: every saved point of every used ray,
  with `event,station,node,x,y,z` and the same complete `source_` and `receiver_`
  metadata. Indices use the native receiver epoch; colocated epochs remain
  distinct. Empty location codes and open epoch ends remain empty.

Both files use 17 significant digits. No ray is retraced, resampled, selected,
or removed to create them. Support includes observations omitted from the
weighted matrix. The original eight files retain their existing schema and
precision, including the 12-digit `_rays.csv`; byte parity is a planned control,
not an executed result.

Fresh-file refusal for both new names runs before CLI input reads/tracing and
again in the array writer. It includes dangling symlinks. Both new streams use
the existing checked flush/close helper. A write failure propagates; a partial
file is preserved and must not be called a completed export. These changes do
not alter the older eight writers' existing I/O behavior.

The new tables are written before the original finite-ray/derivative-size
rejection. Thus returned nonconverged, failed-initializer, malformed, or
nonfinite Rays remain inspectable. An empty path has a status row with zero
points and no fabricated node row. Wrong derivative dimensions yield
`ray_derivatives_evaluated=0` and blank source-partial fields; the original
exporter still refuses to assemble them. An incomplete entire Ray array remains
an error. Exceptions that prevent `rays()` from returning are not converted
into fabricated diagnostic records.

## Interpretation and subsequent readback

The evaluation point is the parsed saved `MODE_events.csv` and `MODE_grid.csv`.
The inverse writes those files with 12 significant digits. New 17-digit fields
retain the parsed binary64 evaluation values; they do not recover the previous
internal inversion state. Original metadata strings are copied unchanged;
the explicit numeric coordinate fields refer to this saved evaluation point.
Any eventual export receipt must pin those input bytes, observations, stations,
saved config, stage, source, binary, command, and terminal return code.

A later readback must reconstruct all observation support using the existing
`station_j` semantics, join native identities and epochs, and check every
ordered path point against the 17-digit status row and saved grid. The existing
definitions use the closed grid box (`Grid::contains` with zero pad) and exact
binary64 endpoint equality. No coordinate, stationarity, or accuracy tolerance
is introduced here. The old eight-table validation and all covariance algebra
remain separate and unchanged.

The status writer preserves initialization flags but does not require an
attempt when FMM was requested. A config-aware readback must apply the existing
policy `auxiliary_spacing(config) > 0`: an attempt and success are required in
that case; an attempted initializer must succeed in either mode. An unattempted
straight initialization remains admissible under a straight config, with its
usual first-arrival limitation. The derivative flag checks vector dimensions,
not derivative accuracy.

Passed geometry and local flags would establish a numerical/provenance
prerequisite only. They would not establish first-arrival selection, final-model
accuracy, source-derivative accuracy, or nonlinear convergence. Final accuracy
diagnostics remain necessary. Conditional fixed-weight/mask covariance still
uses shared original-pick noise and excludes active-bound/nonlinear effects;
CC timing uncertainty remains unestimated.

The bounded, unexecuted checks are in [CONTROL_PLAN.md](CONTROL_PLAN.md).

