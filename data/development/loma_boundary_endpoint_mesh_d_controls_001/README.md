# Invented endpoint mesh repeated with D

The reviewed D optimizer does **not** change the saved endpoint-mesh outcomes.
All 836 analytical/parity checks pass, while the same two optimized rays retain
false local flags and the same 32 optimized source-vector comparisons fail.
This supplies no new native endpoint correction or reason to repeat the native
mesh ladder merely with D.

| Invented case | Optimized rows | False local flags, old / D | Source failures, old / D |
|---|---:|---:|---:|
| Positive guide | 25 | 2 / 2 | 24 / 24 |
| Homogeneous oblique | 25 | 0 / 0 | 0 / 0 |
| Near-zero guide | 30 | 0 / 0 | 8 / 8 |

Across all 240 fixed/tied/optimized evaluation rows, every stored field except
`time_s` is exactly unchanged. The three complete final-path CSV files are
byte-identical, covering 5,058 point rows. This includes source derivatives,
gradient norms, update counts, flags, merge counts and the saved final geometry.
All 18 ordinary-versus-explicit-mesh parity checks pass and their tables are
byte-identical to the old run. Intermediate optimizer histories were not
captured; final-path equality does not claim equality of every internal step.

Only 85 reported times differ, by at most 1.11023e-16 s. Changes in derived time
errors and secants follow from those stored totals; their largest secant change
is 1.19210e-7 s/km at a very small perturbation. The exact polygon references,
continuous affine references, source errors and scientific pass/fail fields are
unchanged. These accumulation differences do not resolve the old secant defects.

The positive-guide cases at epsilon=0 still stop with zero updates. Their fixed
first-element source partial remains -1/(288*n), including -2.17014e-4 s/km at
n=16. It is the correct fixed-knot polygon partial L*s'_z/2, not the continuous
guide sensitivity. The two finite-epsilon failures are still n=1 and n=2 at
epsilon=2^-10 km; both exhaust 1000 updates. The near-zero-guide baselines still
take two updates and satisfy the existing combined test with projected norm
about 6.9824e-6 s/km, not the strict 1e-7 test. The homogeneous oblique normal
derivative remains nonzero and accurate. Nothing is zeroed or relabeled.

## Frozen scope

`preparation.json` pins the reviewed integration candidate core/helper, its
independent integration review, the original endpoint plan, unchanged C++
harness and old controls. The numerical source is exactly
`usable_curvature_integration_prepared_001/after/src`, including the normalized
helper include. No maintained production file is changed.

`runner.diff` changes only the copied Python runner's repository-root depth,
numerical-source directory and added helper dependency/copy routing. All three
models, levels 1/2/4/8/16, perturbation ladders, compiler flags, maximum 1000
updates, stopping/Armijo rules, 80-digit reference formulas and check tolerances
are unchanged. The initialization-only preview was inspected before compiling;
the generated optimizer/derivative suffix matches D byte for byte and the
executed explicit trace matches the preview exactly. The D package changes
outer accumulation as well as guarded positive curvature relative to old001;
this comparison cannot attribute effects to retention alone.

`results/summary.json` preserves all four completed commands, source/binary
hashes, copied sources, raw output and analytical checks. `compare.py` performed
a saved-only comparison of all input/path/parity/evaluation/reference table
records and checked 91 pins before and after reading. `comparison.json` retains
every changed scalar field, old/new hashes, case counts and zero-epsilon rows.
The original [old001 package](../loma_boundary_endpoint_mesh_controls_001/README.md)
is unchanged. No native geometry, field trace or inverse was run.

## Repeat

From the integration worktree, choose fresh project-local directories:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_boundary_endpoint_mesh_d_controls_001/run_endpoint_mesh_d.py --output data/development/loma_boundary_endpoint_mesh_d_controls_NEW --build tmp/loma_boundary_endpoint_mesh_d_controls_NEW
```

The runner requires the pinned original plan/compiler and freezes the selected
numerical files again. Preserve this terminal package and use the unchanged
recorded source for comparison. The accompanying asymptotic shooting readback
is a distinct action-consistency question; it does not alter these raw mesh
failures or support production adoption.
