# Neutral curvature capture for LOM initial ray 3426

This completed diagnostic records the existing long-double outer-accumulation
variant B without changing its action, gradients, optimizer, seeds, retention
threshold, line search, stopping conditions, or 1,000-update budget. It concerns
event `quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, and receiver `NC.JSJ..EHZ`
(`FDSN:NC_JSJ__E_H_Z`, epoch 1989-05-02T15:00:00 through
1990-09-14T21:50:00). `identified_ray.csv` and the per-file identifier sidecars
retain the complete native context and distinguish catalog coordinates from the
perturbed simulation source.

The compiler, copied sources, original inputs, control reviews, controller,
binary, and runtime libraries are pinned in `prepared.json`, `summary.json`,
`execution.json`, and the independent `review.json`. The native observer finished
with code 0 at 07:10:52 UTC on 2026-10-10; exact saved-value postprocessing finished
at 07:21:45 UTC. The controller reaped the wrapper. These are execution outcomes,
not convergence claims.

All five original B tables are byte-identical: `results.csv`, `history.csv`,
`paths.csv`, `path_gradient_checks.csv`, and `cone_metric.csv`. The FMM-seeded ray
still exhausts 1,000 updates with convergence flag 0 and projected gradient
4.720002826341664e-5 s/km. The straight-seeded ray retains its original 54 updates
and flag 1. The selected FMM ray is not accepted for an inverse calculation.

The capture preserves 1,000 curvature pairs and all 1,132,000 component records.
Forty pairs were retained and 960 rejected by the unchanged absolute
`s.y > 1e-14` rule. Every rejected dot product is positive in the computed sum,
the exact rational sum of stored binary64 S/Y values, and the exact rational sum
using actual rounded node displacement. There are no threshold-classification
differences in the independent readback. Every stored `step*q` displacement
differs somewhere from the actual rounded movement. This establishes what the
rule discarded; it does not establish that each discarded pair is informative
or that a different retention rule would converge.

The 436 recorded decreases and 564 equal recorded action totals are unchanged.
Exact rational evaluation of the recorded totals gives 564 failures of the
declared Armijo inequality, although the original rounded binary64 decision
accepts all recorded steps. Those rational calculations concern approximate
saved totals, **not exact Fermat actions**. They do not determine the true action
signs of the equal-value steps. Nineteen selected complete pre/post states,
3,040 adjacent-segment cut records, stable memory creation IDs, raw FMM seed,
resampled seed, and all candidate metadata support further bounded diagnostics.

`curvature_components.csv.gz` is the full losslessly verified table
(100,494,158 compressed bytes; 273,739,890 raw bytes), not a reduced sample.
`packaging_receipt.json` additionally pins the identifier sidecar attached to the
retained local raw copy after execution. The independent readback in
`../loma_curvature_capture_review_001/` checks all component rows and identities,
all selected states and cut records, seed resampling and memory joins, and exact
rational reconstruction at 22 representative iterations. No production source,
live run, optimizer flag, or input was changed.
