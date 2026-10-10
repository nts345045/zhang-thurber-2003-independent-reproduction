# Launch status at the report checkpoint

The separately reviewed launch started the guarded catalog-DD solver on
2026-10-10 at 07:37:17 UTC. The process remains active at this checkpoint.
There is no accepted final model or scientific-success claim.

`plan.json` and `README.md` preserve the prepared plan. `launch_review.json`
records its acceptance after full and sampled initial accuracy review;
`launch_verification.json` records the actual startup checks.
`launched_run_manifest.json` is an unchanged copy of the live attempt's
immutable `dd_inversion_run_manifest.json`. It pins actual inputs, executed
sources, executable, compiler and runtime evidence. Mutable histories and
execution state remain in `data/hayward_first_arrival_guarded_001/` in the
integration worktree and are excluded from this completed-evidence delivery.

The later three-dimensional models still require local guards and separate
accuracy and nonlinear-convergence review. The 98 waveform differences are
not inputs to this attempt.
