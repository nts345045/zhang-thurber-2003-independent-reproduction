# Separate field and path refinement

These commands record the historical refinement at commit `88b60b5`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py --refine
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/plot_first_arrival_audit.py
```

The current audit runner requires a fresh `--variant` name. For a separate
first-order repeat, add `--variant refinement_repeat --order 1` to the first
command; its outputs go to `data/development/fmm_initialization_refinement_repeat/`.
The plotting command above continues to read the preserved historical results.

This extends the [first-order baseline](../fmm_initialization_audit/README.md)
without changing the FMM algorithm, continuous optimizer, or accuracy gates.
Auxiliary spacings are 0.125 and 0.0625 km; path spacings are independently
0.125 and 0.0625 km. The 44 comparisons use the same invented layer and
constant-gradient cases. Homogeneous checks are retained in the baseline
rather than repeated here. All extractions and selected local convergence
flags pass. Of 37 accuracy/consistency gates, 33 pass and four fail.

At 0.0625 km path spacing, the recovered 20 and 40 km diving rays have time
errors below 1.8 microseconds and source-gradient errors below
`3e-7 s/km`. The earlier constant-gradient accuracy failures also disappear.
This isolates path discretization as a resolvable part of the earlier error.

Auxiliary refinement to 0.0625 km finds the correct diving branch at 16 km,
where the baseline missed it. It still selects the late direct branch at
14.68 and 15 km, with unchanged errors 0.000176503 and 0.003189637 s.
Those two time failures and their two source-gradient failures remain explicit
in `consistency.csv`. All comparison rows, paths, and hashes are saved.
The diagnostic exits with status 1 because these four gates fail.

The first-order method therefore needs more than path refinement near a
branch crossover. A finer auxiliary field, an independently justified more
accurate field scheme, or a separately validated branch search must address
that error. Neither this experiment nor a selected grid agreement certifies
the continuum first arrival. Production inputs and code remain unchanged.

The [diagnostic figure](../../../figures/diagnostics/first_arrival_audit.pdf)
shows an admissible faster path and the remaining branch errors. It is a
forward-solver validation figure, not a reproduced manuscript panel.
