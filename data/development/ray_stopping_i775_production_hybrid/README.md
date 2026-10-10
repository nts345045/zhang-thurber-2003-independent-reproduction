# Direct audit of the promoted hybrid ray optimizer

The four controls reproduce the frozen final finite-guard diagnostic exactly.
`results.csv`, `paths.csv`, `history.csv`, `cone_metric.csv`,
`path_gradient_checks.csv`, and `identified_ray.csv` are byte-identical to
`../ray_stopping_i775_cone_hybrid_finite_guard/`. The source snapshot contains
the integration-worktree `trace` with the canonical `src/ray_metric.hpp`.
It does not represent a rerun or modification of the frozen field inversion.

The new `--production-hybrid` mode adds observation hooks to a copy of the actual
`trace` function, including its supplied-seed branch. It does not replace the
search direction or generate a separate seeded optimizer. The unobserved
control calls the actual `trace`. All four cases match exactly in time, path,
projected/raw gradients, source derivatives, every nodal velocity derivative,
path-length weights, update count, merged-node count, and stopping flag.
`instrumentation.diff` records the hooks; the optional cone-statistics pointer
only copies the computed certificate. Historical diagnostic modes explicitly
reject this promoted source and require their frozen pre-promotion snapshots.

The event is `quakeml:NC.anss.org/Event/NC/403533`, at solver event index 775.
The native receiver is `NC.CMO..EHZ` / `FDSN:NC_CMO__E_H_Z`, station-epoch index
184, valid from 1993-10-15T19:23:00 to 1995-07-06T22:27:00. The complete provider
event, origin, pick, arrival, channel and epoch records remain in
`identified_ray.csv`; every diagnostic CSV joins through observation index 9692.

| Initialization | Path spacing (km) | Accepted updates | Final projected gradient | Stopping rule met |
| --- | ---: | ---: | ---: | --- |
| Straight | 0.5 | 12 | 7.59059e-8 | Strict gradient |
| FMM | 0.5 | 4 | 1.03881e-7 | Combined action/gradient |
| Straight | 0.25 | 20 | 1.47547e-8 | Strict gradient |
| FMM | 0.25 | 4 | 2.15603e-8 | Strict gradient |

The FMM initializer uses auxiliary spacing 0.5 km, second-order updates and
closed source cells in both the reference and promoted calculations. Each
control has a budget of 1000 updates. All 40 accepted directions have finite,
negative directional slope and strictly decrease the original action, with one
line-search evaluation per update. There are 38 cone replacements and two
retained feasible L-BFGS directions. There are no line-search or quadratic
certificate failures. The maximum free-equation relative backward error is
2.02e-16, primal violation is zero, dual violation is 4.66e-18, and
complementarity error is 1.00e-19. Endpoints are exact.

These results establish observation neutrality and promotion parity for one
identified ray at two path spacings and two initializations. They do not certify
global first arrivals, all rays, or nonlinear inversion convergence. The coarse
FMM case retains the existing combined stopping rule and does not meet the
strict 1e-7 projected-gradient gate. The action, domain, Armijo and stopping
thresholds are unchanged. KKT certificates use a stated floating-point tolerance.
Raw source derivatives and accumulated nodal derivatives remain branch envelope
derivatives, subject to path/quadrature error, stopping residual and branch or
active-set switching.

## Reproduction and provenance

From the repository root, the executed commands were:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py --variant i775_production_hybrid --budgets 1000 --production-hybrid
PYTHONDONTWRITEBYTECODE=1 python3 data/development/ray_stopping_i775_production_hybrid/review.py
```

Choose a fresh variant to avoid overwriting evidence. `summary.json` records
relative compile/run commands, binary/input/source/output SHA-256 hashes,
`TMPDIR=tmp`, and one OpenMP thread. `source_snapshot.tar.gz` contains the exact
compiled sources with normalized archive owner/time metadata. Its core hash is
`854214388b7e3def3770a8d75f347ba747443b98bcc4d5ade8627fa4b7566940`;
the canonical metric hash is
`04d1f080ddc6253a988696706c7b1578e7637590d7ae5099a4cd3c60120839bf`.
Later finite-output or exception-context changes to the worktree are outside
this frozen comparison.

`review.py` verifies the source archive, evidence and observational-input hashes,
compares all six CSVs with the frozen reference, checks native identity joins,
finite modeled results, exact endpoints, accepted descent/action decrease and
KKT diagnostics, and confirms that the historical mode rejects the promoted
source before creating output. `review.json` preserves those checks and hashes.
Undefined endpoint gradient components and initial/final step fields are explicit
not-applicable `nan` values. No observation or model value is invented.
