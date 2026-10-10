# Independent saved zero-support readback

Source prepared for review; not yet executed. Run only after a passed `source_review.json` binds `checker_sha256` and the native calculation has completed and been reaped:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 data/development/hayward_cmj_post_step_zero_support_review_002/check_saved.py
```

The checker uses only the Python standard library and saved files. It independently evaluates the original eight-node trilinear basis at three rational points on each face patch to reconstruct its degree-at-most-two velocity and one-sided normal-derivative polynomials. Exact endpoint and interior stationary-point extrema establish the whole-patch signs. Grid coordinates and velocities mean the exact recorded binary64 values. No project numerical module is imported; no reciprocal integration, ray trace, field, metric solve or new trial is performed.

For continuous positive velocity, `gm >= 0 >= gp` implies `s_minus,n = -gm/v² <= 0 <= -gp/v² = s_plus,n`. Where `gm-gp>0`, the common pointwise mixture uses `theta=gm/(gm-gp)`. Both weighted endpoint normal moments are then zero. If its denominator vanishes, the proved signs force both derivatives to vanish and any mixture, including one half, is valid. This is a shared pointwise selection, not independent clipping of two endpoint components. The normal length variation is zero on an aligned straight edge; continuity cancels moving cell-cut terms. Multiple aligned faces are outside this roster.

The readback joins both accepted first-trial paths at the time of this historical support calculation, every original catalog use and both native receiver epochs. It reconstructs every available component, retains all ordinary entry/exit contributions, substitutes zero only for normal contributions of proved aligned edges, and independently sums the full vector and exact physical-box projected squared norm. The saved primitive component enclosures remain inherited evidence; this checker does not reintegrate them. A large norm of this feasible vector is inconclusive about the minimum support residual. Original false convergence flags and blank source partials remain unchanged. The rejected second trials and later accepted half-size trials are not inputs; this is not a latest-geometry assessment.

The root-owned source review and later execution receipt are separate from the native package. `review.json` is written exclusively, with before/after input hashes, full identifiers, exact extrema locations and the reconstructed case results. No frozen native file is modified.

The executed first checker is preserved in [review001](../hayward_cmj_post_step_zero_support_review_001/), including its source review and [failed execution receipt](../hayward_cmj_post_step_zero_support_review_001/execution_attempt_001.json). It rejected equivalent C++/Python hexadecimal spelling before polynomial or support checks. This version changes only the comparison to canonicalize saved hexadecimal strings with `float.fromhex(...).hex()`, retaining signed zero; exact rational coordinate checks are unchanged. The one-line patch is saved beside the checker. No native result is recalculated.
