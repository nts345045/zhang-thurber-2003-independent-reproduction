# Reviewed curvature correction adopted in integration

The integration source now exactly matches the tested candidate: extended
outer accumulation of path action, returning binary64, and the shared usable
positive-curvature checks. These checks reject nonfinite or unrepresentable
reciprocals, metric scaling and two-loop arithmetic, while preserving the
original fallback and its exception if no usable descent direction remains.
The two diagnostic runners also include the new header in their frozen source
lists. `adopted.patch` records all four maintained-file changes.

`adoption.json` binds the prepared candidate, independent review, exact source
mapping and unchanged files. Validation reuses the exact bytes already tested
in `usable_curvature_integration_checks_001`: 48 core checks, the inversion
guard and external-input components, 37 declared finest-grid layered checks,
72 oblique checks, and 64 production-entry comparisons. The separate native D
replay preserved all five C numerical tables byte-for-byte. No numerical test
or inversion was launched during adoption.

The saved coarse layered case at distance 14.68 km and field/path spacing
0.125 km still has source-vector error **3.24035291764176e-6 s/km**, exceeding
3e-6 s/km. It lies outside the unchanged finest-grid gate inventory and is
retained as a failure of that accuracy comparison. The correction does not
certify exact curvature sign, arbitrary 3D first arrival, nonlinear inverse
convergence, or resolution of the separate bottom-boundary representation
error.

The running guarded Hayward inversion and LOM/LON preflights retain their old
frozen sources, configurations and binaries. All 52 recorded immutable run
files and the original main-worktree sources were verified unchanged before
and after adoption. Their results must retain their original kernel
attribution. Historical preparation and validation documents remain immutable
records of their earlier stages; this receipt records the later adoption.

The [replay guide](REPLAY.md) reconstructs the historical source prerequisites
in a fresh scratch checkout before rerunning the bounded validation.
