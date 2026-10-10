# Independent saved readback of the B seed-load replay

The terminal replay passed its neutrality check. `check.py` performs only saved-file/hash, identity, source-diff and reference-error arithmetic checks. It constructs no field, ray or action and changes no optimizer. The exact command and code0 are recorded in `execution.json`; `checks.json` is byte-identical to `../loma_seed_loaded_b_native_001/review.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_seed_loaded_b_review_001/check.py
```

All five numerical tables—results, history, paths, path-gradient checks and cone-metric records—are byte-identical to both the reviewed B baseline and neutral capture. Their hashes are listed explicitly in the review. The full 199-field event/origin/channel/epoch context, native row joins, full Candidate metadata, 568-node raw seed and 1,134-node resampled frame match the captured inputs. The original driver resampling remains in force; the loader returns the raw seed, not the previously resampled polygon.

The guarded source snapshot, reviewed control inputs, compiler, executable, runtime libraries, terminal ledger and reaped-child controller/log hashes all pass. Every B numerical source and the original observed optimizer remain byte-identical. The only driver change is the reviewed Candidate loader replacing field construction. `sy > 1e-14` remains unchanged; no positive-only retention variant was executed.

The straight start preserves 54 updates, 54 retained pairs and local flag 1. The selected FMM start preserves 1,000 updates, 40 retained pairs and local flag 0. Both retain the prior 25-microsecond time and 3e-6 s/km source-vector accuracy classifications. The complete source-vector norm is independently recomputed from the saved reference; no reference is enumerated again.

This establishes neutrality for loading this captured Candidate. It supplies no convergence remedy, new retention result, later-model accuracy certificate or production adoption. The in-process observed/unobserved path-and-array comparison is an exact numeric comparison made by the frozen driver, not a new independent bit-pattern ray execution. Native timing is preserved by the execution ledger and is not used to claim a general performance improvement.
