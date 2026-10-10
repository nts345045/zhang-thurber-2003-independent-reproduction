# Full fixed-geometry layered reference, preserved first attempt

The isolated reference enumerated every one of the 37,648 pairs in the prepared 724-source, 52-receiver geometry. The four-worker calculation completed in 730.77 s. The controller reread both compressed streams, checked all native metadata and pair indices, and reverified the frozen source and input hashes. The mathematical reference module is unchanged from the 355-check validation and the earlier 104-sample comparison.

All 37,648 candidate enumerations are complete, but **11 references fail the unchanged distance-closure requirement of 1e-8 km**. Their first-arrival values and source derivatives remain blank; their full candidates and failed closure values are retained. The remaining 37,637 valid references comprise 25,713 direct paths, 5,951 turning paths, 5,474 critical-guide paths, and 499 flat direct paths. There are no near ties. Completion of the process is distinct from acceptance of every reference.

All 11 failures belong to source 357, event `quakeml:NC.anss.org/Event/NC/20091139`, origin `quakeml:NC.anss.org/Origin/NC/2650404`. Its normal coordinate is x = -0.011677621261526383 km, just inside the constant v = 6 km/s region. Each failed case has one direct candidate; distance residual magnitudes span approximately 1.01e-8 to 1.26e-7 km. The pair indices are listed in `summary.json`. Near-critical direct-root conditioning is a hypothesis for separate investigation, not a correction applied to this evidence.

`references.csv.gz` contains every pair in event-major/receiver-minor order, its reference flags and values, and every original source/receiver metadata string in prefixed columns. `certificates.jsonl.gz` preserves every branch, rejection reason, unresolved case, and certificate; its `pair_index` joins directly to the CSV. Exact original metadata tables and model/configuration inputs are in `inputs/`, and the executed reference sources are in `source/`. These are catalog-defined simulation geometry and a fixed receiver metadata snapshot; no provider pick identities or observations were invented.

The independent post-completion calculation in `check.py` verifies that the full reference dictionaries for all 104 earlier sample pairs are identical. Among valid references, the largest signed violation of the Euclidean/global-maximum-speed lower bound or independently integrated straight-path upper bound is 3.56e-15 s. The maximum source-gradient eikonal norm residual is 8.33e-17 s/km. These are physical consistency checks, not an additional completeness or interval time-ordering proof.

Commands, from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_layered_full.py --output FRESH_DIRECTORY --workers 4
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 data/development/loma_layered_full_001/check.py
```

The first command refuses an existing output directory. `execution.json` records the terminal process state, while `summary.json` records the separate reference validity result and source/input/output hashes. The maintained controller and invented-data checks were committed as `94f573a`; the mathematical reference and 104-sample evidence were committed as `cf54010`.

No observations, noise, simulation, inversion, production-ray substitution, or tolerance change occurred. Floating-point minimum-time ordering is distinct from interval-certified ordering; equal maxima can in general admit continuous families of paths. This failed-closure attempt is preserved unchanged before any later arithmetic investigation.
