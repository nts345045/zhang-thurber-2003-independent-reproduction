# Invented trial-backtracking controls

This package tests the isolated candidate003, not an adopted solver or an observed earthquake. Every event, origin, pick, arrival and XX.MOCK..HHZ epoch is invented. Native-format fields exercise the actual loader and retain empty locations, quoted/newline metadata, a zero-weight observation and both differential receiver epochs.

Preparation does not compile or run the fixtures. Execution is a separate phase after source review. The copied `invert` loop is unchanged except for three explicit fixture seams shown in the saved diffs: the actual returned Rays pass through a wrapper into the actual gate; the actual LSQR solve runs before an optional prescribed test increment is returned; selected output streams can be redirected to `/dev/full` after freshness checks. No quality exception is fabricated. Pure/mixed failures alter actual returned Ray records. All-valid cases leave every seam inert and require byte-identical before/after output and status tables.

The independent half/quarter-step targets are homogeneous source-time offsets. Original fixed weights are reconstructed with sorted medians and the declared row-multiplier formula. Snapshot checks cover all source/model increments, LSQR status, original metadata and zero rows. Rejected states are checked against the original accepted source coordinates, source clamping and exponential model update at every fraction. No objective is assigned to rejected trials. Current/final/mixed/unexpected failures, no evaluable trial, valid-but-worse objectives, prior artifacts, incomplete snapshots and deferred stream errors remain distinct. Tiny homogeneous 5→6→5 field-cache checks compare actual cached and fresh results while preserving native receiver indices.

The I/O fixture uses the Linux full device to produce failure after a successful open. These checks exercise flush/close error propagation, not power-loss durability or all filesystem failure modes. A prescribed increment is explicitly a fixture input and is not presented as the actual LSQR solution; the actual solve result/status remain captured for inspection. Numerical comparison bounds here are roundoff/serialization controls, not changed scientific ray thresholds. No observational request, native ray, real inverse, production edit or acceptance-flag promotion is performed.

After review, from the integration checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_trial_backtracking_checks.py --phase run --variant 002
```

The runner requires unchanged prepared inputs and helpers, fresh build/results/execution paths, records commands before launch, preserves every failed output, and checks original inputs again after execution. It does not commit anything.
