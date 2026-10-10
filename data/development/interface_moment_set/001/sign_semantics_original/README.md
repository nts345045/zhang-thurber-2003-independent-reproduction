# Preserved sign-certificate wording

These files preserve the first sign-only record and its source. The old boolean `alpha_zero_minimizes_euclidean_support_norm=false` could be mistaken for a proof of non-optimality in the tangent-step case. The maintained sign check now uses `alpha_zero_minimum_norm_certified`; false means only that the nonnegative-component criterion is inconclusive, as the unchanged `certificate_status` already stated. All arithmetic, counts and rational intervals are unchanged. The main 156-control component summary and proof are unchanged.

The package README also corrects an unrelated prose error: `norm(Vec)` in `src/core.hpp:38` is Euclidean, and the box-projected stopping tests use it. No componentwise-maximum stopping rule is implemented.
