# Complete Loma geometry reference after direct-root correction

All **37,648 native source/receiver pairs** have complete, valid references and
no reported near ties. The run took 752.95 s with four independent workers and
deterministic source-major/receiver-minor output. It uses exactly the same 724
catalog-defined sources, 52 receiver epochs and finite x-only model as full001.
No observations, simulation, noise or inversion were produced by this run.

The isolated change solves a direct branch using the exact rational offset
`delta = u - vmax`, preserving the small positive difference before evaluating
layer integrals. The existing **1e-8 km** closure requirement is unchanged.
The eleven previous invalid pairs are now valid; full001 and its failed
certificates remain untouched. The conditioning study and guarded 355/355 plus
65/65 controls are separate evidence in `../loma_layered_direct_conditioning_001/`
and `../layered_reference_checks/`.

| Selected branch | Pairs |
| --- | ---: |
| Direct | 25,724 |
| Turning | 5,951 |
| Critical maximum/plateau guide | 5,474 |
| Flat direct | 499 |

All 66,302 candidate distances satisfy closure; the largest absolute residual
is 3.12518e-9 km. All 104 corrected sample reference dictionaries match exactly.
For the 37,637 pairs valid in both full batches, the selected branch kinds are
unchanged, the maximum time change is 1.55205e-9 s, and the maximum source-vector
change is 9.98472e-14 s/km. Every native geometry and metadata field matches the
previous full batch. The maximum signed violation of the Euclidean/global-vmax
lower bound or independently integrated straight-path upper bound is
3.55e-15 s; the maximum endpoint eikonal-norm residual is 8.33e-17 s/km.
These are consistency results, not newly imposed scientific thresholds.

Run from the repository root with a **fresh** output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_layered_full.py --output data/development/loma_layered_full_002 --workers 4
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_layered_full_002/check.py
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_layered_full_002/compare_prior.py
```

The first command refuses an existing output directory. `execution.json`
records the terminal result and exact summary hash. `summary.json` pins source,
input and generated artifact hashes. `references.csv.gz` retains every native
source/receiver field, while `certificates.jsonl.gz` preserves all candidate
families, closures and rational parameters. `check.py` and `compare_prior.py`
only reread frozen artifacts; their results are in `review.json` and
`prior_comparison.json`. `controller_stdout.log` is copied after completion,
with its digest and terminal links in `log_provenance.json`.

Candidate-family completeness refers to minimum time in the declared finite
piecewise-linear model. Equal maxima can admit a continuum of geometries;
this is not enumeration of every path. Time ranking remains ordinary
floating-point evaluation, not an interval-certified ranking. Endpoint
derivatives belong to the selected branch. This independent reference does
not validate the production polygon optimizer or its inverse calculations.

`independent_review.json` records a separate read-only audit by
`earthscope_discovery`: all 37,648 ordered native CSV/certificate joins,
derivative-axis mappings, 17 output hashes and 13 source/input hashes pass;
all 104 corrected sample dictionaries and native fields match. No material
issue was found, and no reference arithmetic was rerun for that review.
