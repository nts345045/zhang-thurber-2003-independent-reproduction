# Arithmetic comparison on the saved LOM trial paths

The original outer sum rejects all 24 trials. Exact summation of its unchanged
binary64 segment values recovers 17 Armijo passes, including the full first
step. Evaluating the same segment formula in extended arithmetic and adding
paired segment differences recovers 21. The exact action calculation certifies
all 24. These are saved-path comparisons, not new ray optimizations.

For trial 0, the original recorded change is `+1.2434497875801753e-14 s`.
Exact summation of original segment differences gives
`-6.7107777668162782e-15 s`; the exact mathematical action change is
`-6.7619503795011601e-15 s`. Thus outer accumulation is sufficient to explain
the erroneous first rejection. Segment arithmetic also matters for smaller
steps: extended paired changes for trials 21--23 are zero, zero and
`+8.470329472543003e-22 s`, despite their certified negative action changes.

`segments.csv` retains every segment evaluation for the original path and
all 24 trials (28,325 rows). `totals.csv` compares ordinary accumulation,
extended accumulation, and paired differences. Both tables have full native
identity sidecars. `summary.json` joins each result to its recorded decision
and exact action enclosure, preserves the original false flag, and records
input/output hashes. No scientific threshold changes.

The templated double evaluator must match the original kernel for every
segment, and each original path total must match both the original evaluator
and the neutral replay. All checks passed. Extended arithmetic has a 64-bit
significand on this platform, compared with binary64's 53 bits. It retains
the original binary64 Gauss coefficients and threshold constants while
recomputing coordinates, lengths, cuts and interpolation at higher precision.
These are approximations, not new certified action enclosures. Differences
of displayed extended totals also include final decimal display rounding.

The nine invented controls test homogeneous and depth-affine actions, reversal,
and cancellation. Their 64-binary64-epsilon allowance accommodates the frozen
Gauss coefficient representation; it is not an optimizer tolerance.
`controls_execution.json` saves exact compiler/control commands and pins;
`controls_review.json` and `launcher_review.json` were completed before native
evaluation. `run_native.py` records the native command, joins and error bounds.

To rebuild only this diagnostic, create a fresh build/output directory and
use the recorded compiler flags with
`source/diagnostics/check_saved_trial_accumulation.cpp`. Run the executable
first as `CHECK --controls OUTPUT.csv`, then as:

```text
CHECK GRID BASE_DIRECTIONS TRIAL_PATHS SEGMENTS_OUTPUT TOTALS_OUTPUT
```

The consumed grid, base directions, trial paths and decisions are frozen under
`inputs/data/development/loma_failed_search_3426_001/`. Copy the complete
`source/` tree when moving the diagnostic. The native controller refuses to
overwrite a completed run. No production source file is part of this experiment.
