# Final execution preparation

The replay evaluates pair 8670 and passing control pair 8674, both from source 166 (NC event 10090456, origin 2644764). The receivers are NC.JHL..EHZ and NC.JRG..EHZ. Complete native identifiers, epochs and full-precision initial coordinates are preserved in `inputs/native_context.json` and the selected tables.

Each variant calls the archived public `trace` entry twice, using spacing 0.03125 km, at most 1000 updates, full derivatives and a null seed. That entry constructs the original straight initialization. No receiver field or iteration instrumentation is introduced. Source origin-time corrections remain metadata and are excluded from propagation time. The original FMM diagnostics remain separately labeled saved metadata.

The old implementation must reproduce all original physical scalars, status, counts and native fields at their 12-significant-digit serialization before the D variant runs. Final paths and model partials are saved at 17 digits with full native metadata on every row. D changes both outer action accumulation and usable-curvature handling, so a difference is not attributed to either change alone. The 37 interior failures retain their original flags and unchanged 25 microsecond time and 3e-6 s/km Euclidean source-error limits. Neither this pair selection nor a local flag establishes global 3D first arrivals or inversion readiness.

Preparations 1 and 2 are immutable, superseded and unexecuted. Version 2 added complete process-group termination accounting; version 3 also places post-launch PID/ledger bookkeeping inside the child cleanup handler. No numerical driver, source, setting or input changed in those corrections. `prepare_revision_v3.py` verifies the preceding preparation before writing `prepared_v3.json` exclusively.

The final command, after an independent passed `prelaunch_review.json` bound to `prepared_v3.json`, is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 run_v3.py
```

Use a fresh package for any repeat. An existing execution ledger forbids restart. No files from an unsuccessful attempt should be removed or overwritten.
