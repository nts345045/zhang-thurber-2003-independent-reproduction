# Independent saved LON comparison review

The saved readback passes for all 37,648 rows. It verifies every original
output hash, all 37 frozen input mappings, the reaped controller and completed
matrix command, complete native metadata joins, reference uniqueness flags,
all time and source-vector differences, and the recorded failure roster.
Numerical ray coordinates retain the frozen C++ writer's 12-significant-digit
format; provider metadata and empty location codes are compared exactly.

All local/path and 25-microsecond time checks pass. Fifty source-vector errors
exceed 3e-6 s/km: 13 at bottom sources and 37 at interior sources. The maximum
time error is 4.87665744 microseconds, and the maximum source error is
9.86335730e-6 s/km. All original failure flags remain visible.

This checks saved evidence without rerunning a ray solver or continuous
reference calculation. The prior independent reference review remains the
basis for the reference solutions. These rays used the earlier frozen
optimizer; they do not validate the later curvature correction. Sampled
preflights and the guarded inversion are separate runs.

The executed command was:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_lon_initial_accuracy_review_001/check.py
```

The checker creates `review.json` exclusively. To repeat it, use a fresh
scratch copy with the comparison package available and no existing review.
