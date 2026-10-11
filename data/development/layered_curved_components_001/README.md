# Continuous layered-ray components

This portable development package contains a continuous curve representation,
a limited affine branch constructor, and two completed sets of invented
controls. All 58 affine checks and all 24 independent full-nodal assertions
passed. [RESULTS.md](RESULTS.md) describes the observations and limits.

The four C++ files in [source/](source/) are the exact reviewed and executed
sources. [METHOD.md](METHOD.md) explains the curve and integral formulas;
[CONTROL_README.md](CONTROL_README.md) preserves the full-nodal control design
as written before execution. The latter's preparation wording is historical;
the completed results are in [results/](results/). Scientific hashes are in
[manifest.json](manifest.json). Original result bytes retain their long-double
decimal or hexadecimal values.

The kernel integrates action and every trilinear nodal velocity and length
kernel along a declared continuous curve, partitioned at every x/y/z face.
Display samples do not enter those integrals. Exact lateral nodal equality is
required for the base velocity field. The affine constructor covers homogeneous
or two-depth-node increasing affine profiles, including a finite-bottom guide.
It does not enumerate arbitrary piecewise profiles or replace the maintained
three-dimensional solver. Supplied branch-completeness and derivative-status
labels remain distinct from numerical integration results.

## Replay

Requirements are Python 3.6 or newer, a C++17 compiler supporting `long double`,
and a POSIX environment. The recorded run used GCC 8.5 with extended-precision
`long double`; another platform need not reproduce the same last bits and must
pass the actual controls on its own arithmetic.

From the repository root, choose an absent project-local output directory
outside this package:

```sh
mkdir -p tmp
python3 data/development/layered_curved_components_001/replay.py tmp/layered_curved_replay_001 --cxx g++
```

The script verifies the package hashes, compiles each control once, then runs
each once. It writes binaries, logs, commands, results and a replay status only
inside the new directory. Existing output paths, including dangling symlinks,
are refused. Failures retain their outputs and are not retried. The script
checks the resulting control summaries; it does not demand byte identity with
the bundled results. The documented replay completed successfully in a fresh
project-local directory: both programs passed, and all three scientific result
files matched the bundled bytes. The replay itself is separate from the
original control executions.

The scientific package excludes binaries, session logs, process identifiers,
machine-specific runtime records and the original execution receipts. No
catalog observation, real ray, inversion, production adoption, or general
first-arrival validation is included. Quadrature-rule differences are reported
diagnostics, not interval error bounds.
