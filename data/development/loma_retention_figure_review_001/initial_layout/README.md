# Saved retention-figure review

The existing PNG/PDF and all saved plotted arrays pass independent readback. The checker reconstructs the full B/C accepted-update sequences, projected gradients, cumulative retained pairs and equal approximate-action counts directly from reviewed native tables. It checks all twelve input hashes, the source and figure hashes, full 199-field native context, unchanged straight-start result and PDF identity/labels. The PNG was viewed directly and is readable. No plot, ray, action or optimizer was rerun.

B has 1,000 updates / 40 retained pairs / flag 0; C has 145 / 145 / flag 1. The dashed line is only the gradient bound of the combined criterion, which also requires small action change. The published metadata states this condition and excludes a general positive-retention or exact-action claim. The plot keeps the original local flags and refers to this one identified ray.

Executed from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_retention_figure_review_001/check.py > data/development/loma_retention_figure_review_001/review.json
```

For a later read-only repeat, omit the redirection to preserve the frozen review. Exit code was zero; `receipt.json` pins the reviewed artifacts and checker.
