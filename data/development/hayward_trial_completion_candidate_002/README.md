# Prospective completion reviewer: three closure corrections

This fresh candidate preserves the maintained launcher under `before/` and the prospective completion-only change under `after/`. Nothing is adopted into maintained source. `correction.patch` shows the entire five-line difference from immutable candidate001; `candidate.patch` shows the full proposed launcher/helper change. The launcher itself is byte-identical to candidate001.

The approved saved-table controls001 completed 186/189: three malformed completions were wrongly accepted. Their summary, execution, recipes and mutated files remain preserved. This candidate adds only:

1. The numeric accepted source/model state in an iteration-zero solve snapshot must equal the actual initial input state.
2. Every recorded iteration must be below the configured iteration limit.
3. A stage-2 no-update iteration must be the last recorded iteration, matching the existing loop's break.

There is no new ray/gradient/objective tolerance, no strict-improvement requirement, and no change to weights, covariance, state updates or scientific eligibility. Seventeen-digit binary64 joins and the original twelve-digit history serialization remain unchanged. A zero-step completion after objective-evaluable nonimprovement remains legitimate. Later iterations without solve snapshots still prevent complete independent intermediate-state reconstruction.

The inherited proposal's complete scope and limitations are retained in `proposal001.md`. In particular, the final all-success gate is enforced by the exact audited C++ main and successful child return, not an independently emitted full final ray table. Initial source/numerical eligibility stays unchanged and is deliberately separate from this completion reviewer. A reviewed old7111-kernel plus exact candidate003-main bridge remains necessary before a new real attempt.

This package has only been parsed and prepared. The fresh controls002 will retain the original 189 recipes and add the independently reviewed actual joint-DD positive fixture from the old-kernel integration suite. That fixture supplements, rather than retrospectively replaces, controls001's explicitly hypothetical table ending. No C++ compilation, ray or inverse call is part of the saved readback.
