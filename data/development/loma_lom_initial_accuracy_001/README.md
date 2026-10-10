# Full LOM initial-ray accuracy comparison

This completed comparison assesses the saved 37,648 rays from the LOM initial
matrix preflight against independently computed, frozen continuous references
for the same depth-only initial model and perturbed source geometry. It does
not recompute references, trace rays, solve an inverse problem, or assess the
still-separate sampled refinement/finite-difference stage.

| Unchanged check | Passing rays / 37,648 |
| --- | ---: |
| Unique, valid reference with a defined source derivative | 37,648 |
| Finite modeled values | 37,648 |
| Absolute time error at most 25 microseconds | 37,648 |
| Euclidean source-derivative error at most `3e-6 s/km` | 37,600 |
| Original local flag and all other path/initializer flags | 37,647 |
| All checks jointly | 37,599 |

The maximum absolute time error is `2.8983983377806055e-6 s`;
the maximum Euclidean source-derivative error is
`1.5850655663200005e-5 s/km`. All 49 rows that fail a check remain fully
identified in `summary.json` and `comparison.csv.gz`. No tolerance or
convergence flag changed.

The 48 derivative failures all have sources at the 16 km lower domain
boundary and a continuous `bottom_boundary` reference branch. They involve
seven event identities. Their errors are in the z component: maximum absolute
x and y errors are respectively `4.826694599557868e-14` and
`4.961309141293668e-13 s/km`. These patterns motivate a separate endpoint
discretization investigation; this table alone does not establish its cause.

The additional local-stopping failure is pair row 3426: event index 65,
`quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, receiver index 46,
`NC.JSJ..EHZ` (`FDSN:NC_JSJ__E_H_Z`), epoch
`1989-05-02T15:00:00` to `1990-09-14T21:50:00`. Its time and source derivative
pass their respective limits, but its original local flag is false. Accuracy
agreement does not replace that stopping requirement. The combined failures
prevent inverse acceptance at the assessed settings.

The preceding matrix-only command completed with return code zero in
1 h 35 min 16 s and measured peak RSS 40,377,956 KiB. Its census contains
15,932,384 observation rows, 15,669,056 active data rows, 625,217,505 ordered
augmented entries, and 7,753,377,620 bytes of nominal CSR payload. Completion
of a matrix census is not a successful inverse solve or an all-ray quality
pass. The production preflight controller continues its prescribed sampled
checks independently.

`inputs/` preserves the exact reference and completed-preflight evidence;
the full ray CSV is losslessly gzip-compressed with a verified decompressed
hash. The captured execution ledger explicitly records that the overall
preflight was still running. Source/grid/geometry/native joins and frozen
binary/source hashes are checked before comparison, and completed inputs are
rehashed afterward. `summary.json` and terminal `execution.json` bind the
complete output inventory. The summary SHA256 is
`72ed25dbde4bc14b1e0967f6a1880ff396683735c723b41f633e081a085fe6bb`.

Reproduce from the completed saved inputs with a fresh output directory:

```sh
python3 diagnostics/compare_loma_initial_rays.py --data data/loma_lom_initial_preflight_001 --reference data/development/loma_initial_reference_001 --output data/development/loma_lom_initial_accuracy_FRESH
```

Only pure propagation times are compared; saved source-time offsets remain
separate. Source derivatives use the original x/y/z order and Euclidean
vector norm. This validates or rejects particular initial 1D-model rays;
it does not certify later 3D models, branch completeness in an arbitrary
medium, or nonlinear inversion convergence.

The independent saved-table review passed. It verified every ordered row,
all original native/status fields, reference certificates and gradients,
error arithmetic, and all 49 failure joins without retracing or rerunning the
reference calculation. `review.json` binds that audit; its successful status
does not change the failed numerical acceptance.
`source/review_saved_tables.py` preserves the exact executed checker bytes,
originally run as `tmp/review_loma_accuracy_saved.py`. Its write-exclusive
review output intentionally prevents overwriting an existing review.
`publication_manifest.json` additionally pins this explanatory README, the
independent review, and its exact checker, leaving the original comparison
summary and execution ledger unchanged.
