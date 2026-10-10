# LON initial-depth reference with one preserved invalid case

The full independent reference calculation completed all **37,648 pairs** (724 saved perturbed sources × 52 native receivers) in 416.1 seconds. **37,647 references are valid; one fails the unchanged distance-closure limit.** Therefore `reference_comparison_ready` is false. Execution completion and correct artifact preservation do not imply numerical validity of every reference.

Pair **8156**, event index 156 and native receiver index 44, retains its sole turning candidate but exposes no selected time or derivative. The event is `quakeml:NC.anss.org/Event/NC/255127`, origin `quakeml:NC.anss.org/Origin/NC/2644594`; the receiver is `NC.JSC..EHZ`, `FDSN:NC_JSC__E_H_Z`, epoch `1989-05-10T21:40:00` to `1990-10-04T20:15:00`. Its candidate turns at 11.000000000888981 km and has a distance residual of **1.0783892889776325e-8 km**, exceeding the existing **1e-8 km** limit. The full candidate and all native fields are retained in `invalid_cases.json`, extracted without new numerical evaluation by `extract_invalid.py`. This package neither corrects nor accepts that candidate.

All 37,752 candidate records and their certificates remain in `certificates.jsonl.gz`. Among valid selected references there are 19,651 turning, 17,982 direct, 13 finite-bottom, and one flat direct path. There are no near-tied first-arrival branches. The unchanged numerical helper is pinned at SHA-256 `13020fef85113c302b27d846e1b4286c13576348a10710ba8a4c6fbd999e1c98`; root and closure limits are unchanged.

This LON calculation uses its own exact saved initial grid:

| Depth (km) | Velocity (km/s) |
|---:|---:|
| -1 | 2.53 |
| 0 | 2.53 |
| 3 | 5.50640625 |
| 7 | 6.03765625 |
| 11 | 6.345629139072848 |
| 16 | 6.478079470198676 |

The saved initial-event and station tables are byte-identical to the LOM variant. The initial grid and configuration differ. No LOM travel-time reference, x-dependent simulation truth table, or observation values were reused for this calculation. `inputs/inverse_plan.json` records those exact relationships and the completed LON simulation/review links.

The finite domain is x ∈ [-35,35], y ∈ [-60,40], z ∈ [-1,16] km. Candidate depth bounds and exact endpoint boundary flags are retained. Horizontal paths move monotonically between their endpoints within the convex horizontal rectangle. Coordinates and source derivatives use the **original xyz axes**, with no x-truth permutation. The saved nonzero `source_t` remains metadata and is excluded from pure propagation time.

`references.csv.gz` is ordered by `pair_index=event*52+station` and preserves every original source/receiver field verbatim, including provider resource IDs, SEED/FDSN identifiers, metadata epochs and valid empty fields. Invalid selected values remain blank. `check.py` verifies every native join, hash, candidate-validity flag, derivative mapping and boundary flag without rerunning references. On valid selected paths, time is no greater than an independently integrated straight-path action; maximum excess is zero. The maximum endpoint slowness-norm discrepancy is 1.11e-16 s/km. These are necessary consistency checks, not an independent completeness or time-ranking proof. `review.json` and `independent_review.json` distinguish correct evidence preservation from the one numerical failure.

Frozen inputs and sources, the terminal execution ledger, and controller output are retained. No ray tracing, observations, forward preflight or inversion was run here. A subsequent isolated conditioning investigation must use a separate directory and preserve this failed original package.

Review/extract the saved evidence:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 data/development/loma_lon_initial_reference_001/check.py
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_lon_initial_reference_001/extract_invalid.py
```

Reproduce the unchanged batch with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_initial_reference.py --data data/loma_lon_analytic_001 --output data/development/loma_lon_initial_reference_new --plan data/development/loma_lon_initial_reference_plan_001/plan.json --workers 4
```
