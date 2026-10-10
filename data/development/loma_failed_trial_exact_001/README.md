# Exact action of the 24 rejected LOM ray trials

Every actual rounded trial polygon from the neutral replay satisfies the
original Armijo decrease condition when its mathematical travel-time action
is enclosed using rational interval arithmetic. The original binary64 search
rejected all 24. The saved local-convergence flag remains false.

The first trial changes the exact action by
`-6.76195037950116008917e-15 s`; the final trial changes it by
`-3.36321220661717402301e-22 s`. These are calculated changes for the saved
coordinates, including coordinate rounding, rather than idealized displacements.
The independently enclosed full gradient gives a directional derivative of
`-6.763118143572066e-15 s`, close to the recorded
`-6.7631181427496004e-15 s`. Both derivatives classify every trial as passing;
the maximum component discrepancy in the full gradient is
`1.1644452495058955e-16 s/km`.

The calculation uses the unchanged positive, depth-only initial velocity model.
Each straight segment is split at depth-grid planes, and reciprocal-affine
slowness is integrated with rational enclosures of square roots and logarithms.
Identical segments cancel identically. Actual endpoints, path topology, all
24 step sizes, and the separate post-loop halved step are checked against the
recorded search. No aligned nonsmooth segment is admitted as an ordinary
gradient. The Armijo coefficient is the exact value of the original binary64
constant, and the original model box is preserved.

`summary.json` contains all interval endpoints as rational numbers, numerical
displays, saved decisions and full native identity. `source/` freezes the
helper, mathematical enclosure routines and consumed input tables/sidecars.
`execution_execution.json` records the terminal run and source/review hashes.
The reviewed helper first passed the 17 checks in
`../loma_failed_trial_controls_002/`; the earlier control run is retained in
`../loma_failed_trial_controls_001/`.

`review.json` independently checks the recorded classifications, hashes and
native identity. Its checker and two additional Decimal evaluations are in
`../loma_failed_trial_exact_review_001/`. The independent 80- and 100-digit
actions for trials 0 and 23 lie inside the saved intervals; this is a numerical
consistency check in addition to the enclosure calculation.

Run from the integration repository root with a new output directory:

```sh
python3 diagnostics/check_loma_failed_trials.py \
  --replay data/development/loma_failed_search_3426_001 \
  --controls data/development/loma_failed_trial_controls_002 \
  --review data/development/loma_failed_trial_controls_002/review.json \
  --output data/development/loma_failed_trial_exact_NEW
```

This establishes false numerical rejection for this particular saved search.
It does not establish convergence of a corrected ray optimizer, explain the
separate bottom-endpoint derivative failures, or validate an inversion. No
production arithmetic, threshold, path or scientific status changes here.
