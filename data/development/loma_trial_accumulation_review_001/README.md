# Independent saved-arithmetic review

`check.py` verifies the completed saved-path comparison without executing a ray
solver or recomputing quadrature. It checks input, frozen source, and artifact
hashes; native identity and unchanged-edge joins; all 25 sequential binary64
totals from the 28,325 saved segment records; exact sums of binary64 segment
differences; and all six comparisons with the certified action changes.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_trial_accumulation_review_001/check.py
```

The saved review is `../loma_trial_accumulation_001/review.json`. It confirms
the approximate pass counts `0, 17, 17, 17, 17, 21` in the order recorded by
the native summary. It does not certify the extended approximations or change
the original false convergence flag.
