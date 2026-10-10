# Invented contact and release results

All 30 declared checks passed. The terminal run used 10 C++ helper calls, 22 combined action/component edge evaluations, 22 independent affine edge references and 24 directional edge evaluations. One compiler, the control driver and all helpers exited zero and were reaped; stderr was empty. These are invented polygons, with no native event or receiver identities and no ray tracing, field solve or inversion.

The [saved summary](results/summary.json), [execution ledger](execution.json), [outer receipt](outer_reaping.json) and [independent saved-data review](review.json) preserve the results. The review verified 73 distinct hashes and 1,136 readback checks without importing or rerunning either evaluator. The [preparation README](README.md) remains the unchanged pre-execution specification.

## Exact contacts and true release

For `v = 6 - |x|`, both prescribed contact events were accepted at the full event fraction, without halving. The first internal node reached exactly `(0, 1, 0)`; its normal coordinate was retained for one subsequent proposal, which placed the second node exactly at `(0, 2, 0)`. Coordinates were formed by exact rational addition followed by one binary64 rounding. The fractions below are exact; action changes are rounded displays of the saved enclosing intervals.

| Proposal | Accepted fraction | Action change (s) |
| --- | --- | ---: |
| First fast contact | `281474976710656/5734045185933537` | −4.25687521669 × 10⁻⁴ |
| Second fast contact | `8563139535726023/95752925142182864` | −1.96505395055 × 10⁻⁴ |
| Slow-face positive normal release | `1/64` | −8.25541424823 × 10⁻⁴ |

Each accepted trial passed a negative true directional bound for its actual rounded displacement, conservative interval Armijo, and the recorded binary64 action comparison. After the first contact, its isolated normal remained an ordinary derivative: a unit negative-normal release had derivative approximately −0.0239696241463 s/km. Temporary retention therefore demonstrates contact construction, not stationarity or a physical constraint. The final positive-length aligned edge has unavailable ordinary normal components; neighboring ordinary contributions remain saved. No full supporting vector or convergence claim was made for this formed face.

For `v = 6 + |x|`, the initial three unit edges had exactly zero available tangent derivatives in the affine oracle. Both simultaneous unit-normal release signs had true directional derivative `−2/36 = −1/18` s/km. The declared positive release moved both internal nodes to `x = 1/64` and reduced the action from 0.5 s to approximately 0.499174458575 s. Zero in the branch-gradient convex hull at this slow face is not a supporting-vector certificate for its true first variation.

## Frozen cut-rule errors

The four two-node controls compare all six ordinary endpoint-gradient components with the independent split-affine log oracle. Values below are approximate norms from the saved error intervals, in s/km. The existing cut rules were observed unchanged.

| Case | Exact crossing parameter | Cut omitted? | Six-component error norm | Largest component error |
| --- | --- | --- | ---: | ---: |
| Below displacement cutoff | `1/2` | Yes | 1.132162752 × 10⁻⁴ | 8.005599593 × 10⁻⁵ |
| Above displacement cutoff | `1/2` | No | 6.108503523 × 10⁻¹⁷ | 4.317534012 × 10⁻¹⁷ |
| Below endpoint cutoff | `1/17179869185` | Yes | 3.234152609 × 10⁻¹² | 3.234152609 × 10⁻¹² |
| Above endpoint cutoff | `1/4294967297` | No | 5.093800095 × 10⁻¹⁸ | 4.031901867 × 10⁻¹⁸ |

The first omitted crossing has action error only about 5.24272 × 10⁻¹⁷ s despite its much larger gradient error. Passing the declared controls records this failure mode; it does not certify that evaluator's generic gradient accuracy. No cut rule, tolerance, production algorithm or native status was changed. These finite examples establish neither general contact convergence nor first arrival.
