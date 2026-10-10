# Retained-node curvature diagnostic proposal

This proposal is unimplemented and does not authorize or imply a new optimizer. It concerns the fixed, identified native polygon already used by `native_interface_support/001` and `native_interface_step/001`: event `quakeml:NC.anss.org/Event/NC/20091683`, origin `quakeml:NC.anss.org/Origin/NC/2660124`, receiver `NC.BSL..EHZ` (`FDSN:NC_BSL__E_H_Z`), native epoch `1989-08-25T19:45:00` to `1990-09-10T19:20:00`. The original flag remains zero. No physical model, endpoint, polygon, threshold or production source is changed.

## What the saved secants establish

The saved interface-tangent direction d has zero x displacement at every guide-incident knot; this means tangent to the x=0 face, not necessarily tangent to each ray segment. Its fixed endpoints and global Euclidean normalization give a dimensionless direction with norm at most one. The step h has units km. The exact continuous directional derivative is enclosed near D=-6.825839466036318e-6 s/km. The saved actions enclose

    K(h) = [T(P+h d)-T(P)-h D]/h².

At h=2^-17, 2^-18 and 2^-19 km, K is approximately 2.294096988, 2.294101766 and 2.294104160 s/km². All twenty accepted/rejected trials are preserved in `interface_moment_set/001/native_tangent_curvature.csv`. They certify positive directional remainders at those finite steps, not a Hessian spectrum or the limiting second derivative. If T is twice differentiable along this particular variation, the limit is one half of its directional second variation.

Writing the Armijo inequality exactly gives

    h K(h) <= -(1-c) D,       c=1e-4.

The saved interval bounds, not a Taylor approximation, decide acceptance. Using the smallest-step displayed secant only as an illustration gives a crossing scale of about 2.97509e-6 km, between the rejected 2^-18 and accepted 2^-19 km trials. Thus the nineteen halvings in this normalized steepest-support experiment are consistent with the observed positive directional curvature. They are not nineteen production L-BFGS rejections: this diagnostic direction differs from the production search direction. The larger supporting-vector norm after the accepted step does not establish a failure of the action-decrease test or isolate its cause.

The exact moment-set evidence shows that alpha=0 already minimizes the Euclidean supporting-vector norm for the original polygon and the full-direction one-step polygon. For all three saved polygons, the fixed smooth/interface-tangent projection nearly accounts for the entire norm. More choices of normal support cannot remove this residual. This does not identify which curvature terms dominate it.

## Existing metric and stopping rules

`src/core.hpp:272-300` already uses the edge weight

    w_e = s(midpoint_e)/L_e

in an isotropic, fixed-endpoint weighted path Laplacian M. Its quadratic form is `sum_e w_e |d_b-d_a|²`. The inverse is the L-BFGS initial metric; its positive scalar multiplier is `(s_history dot y_history)/(y_history dot M^-1 y_history)` at lines 379-384. Feasible descent L-BFGS directions are retained; a direction altered by box projection, or a non-descent direction, is replaced by the cone-metric solve and the history is reset (lines 392-405). The principal solve retains incident-edge diagonals (`src/ray_metric.hpp:13-38`). This is already a segment-length preconditioner. A new claim that merely introducing 1/L weights would solve the conditioning problem would be incorrect.

`norm(Vec)` is Euclidean (`src/core.hpp:38`), and `projected_ray_gradient` applies the box projection before that norm (lines 264-270). The actual tests are projected norm <1e-7, or accepted action decrease <1e-11 together with projected norm <1e-5 (lines 369,472). These use the code's sampled one-sided ordinary gradient. The continuous supporting vector at an aligned interface is a different object. Its norm is not a replacement criterion. The original support norm exceeds 1e-7, while both one-step fixed-projection lower bounds exceed 1e-5; the original has no accepted-step action change with which to apply the combined criterion.

## Segment second variation from the unchanged action

For one nonzero edge let e=b-a, L=|e|, n=e/L, r=d_b-d_a and eta(u)=(1-u)d_a+u d_b. Put J=int_0^1 s(a+u e) du, where slowness s is in s/km. For a smooth medium and this fixed variation,

    Q_e = (J/L) [|r|²-(n dot r)²]
          + 2(n dot r) int grad(s) dot eta du
          + L int eta^T Hess(s) eta du.

The first term is the exact geometric length stiffness. The edge block is `(J/L)(I-n n^T)`, positive semidefinite with a longitudinal null direction. In a homogeneous medium, moving collinear interior knots along the same straight ray is a parameterization freedom: the travel time and curve do not change. Inverting this geometric block alone would therefore require an explicit treatment of its nullspace. The current isotropic metric supplies positive longitudinal search stiffness; it is not an extra term in the Fermat objective.

For the x-only native model the whole directional second variation can be calculated from the same exact reciprocal-affine antiderivative already used by the interval action, without quadrature or omission of internal transverse crossings. Let S'=s, D_x=b_x-a_x !=0, s_a=s(a_x), s_b=s(b_x), and

    J   = [S(b_x)-S(a_x)]/D_x,
    J_a = (J-s_a)/D_x,                 J_b = (s_b-J)/D_x,
    J_aa = 2(J-s_a)/D_x²-s'_a/D_x,
    J_ab = (s_a+s_b-2J)/D_x²,
    J_bb = s'_b/D_x-2(s_b-J)/D_x².

Then use

    J'  = J_a d_ax + J_b d_bx,
    J'' = J_aa d_ax² + 2 J_ab d_ax d_bx + J_bb d_bx²,
    Q_e = (J/L) [|r|²-(n dot r)²] + 2(n dot r) J' + L J''.

Here the endpoint subscripts on J denote normal-coordinate partials. These formulas include all interior x-layer crossings through S. At an endpoint kink, a nonzero normal displacement would require its declared one-sided s' value; zero normal displacement removes that derivative term. The proposed first diagnostic only admits directions for which every kink endpoint has zero normal displacement, and reports any unmet condition rather than inventing a side.

For D_x=0 inside a smooth interval, the nonsingular limits are J=s, J_a=J_b=s'/2, J_aa=J_bb=s''/3 and J_ab=s''/6. For a guide-aligned edge with d_ax=d_bx=0, J'=J''=0 exactly, including the kink: `Q_e=(1/(6 L))[|r|²-(n dot r)²]`. This is a restricted second variation along the saved face-tangent direction, not an all-direction smooth Hessian at the cusp. Tiny nonzero D_x must keep its exact rational value; use interval bounds and preserve an inconclusive result if cancellation prevents a useful enclosure.

## Smallest proposed computation

Freeze only the existing identified polygon, support intervals, saved tangent direction/trial actions, x-profile and source hashes. No new path optimization or line search is needed.

1. Verify fixed endpoints, nonzero edges, positive velocity, exact guide membership and the zero normal movement of every kink endpoint. Preserve the complete native context and original flag. Separate guide edges, smooth-leg edges and transverse layer crossings by exact geometry.
2. Evaluate the interval-enclosed scalar Q along the one saved direction using the endpoint formulas above. Save each edge's geometric, cross and medium contributions. Report whether the saved 2K(h) approaches this Q, with the existing finite h and interval errors stated; do not assert a limiting equality from three samples alone.
3. Evaluate the existing metric quadratic form, the exact-mean isotropic form `sum (J/L)|r|²`, and geometric stiffness on the same direction. Report longitudinal versus transverse contributions and the segment-length range. This tests what the current metric approximates and whether replacing midpoint slowness by the exact mean could materially change this particular scalar comparison. It does not compute a condition number or justify a new inverse.
4. Check the formulas on a homogeneous straight polygon (known transverse stiffness and exact longitudinal null variation), one reciprocal-affine segment with no crossing, and a split/unsplit transverse crossing whose exact action is the same. Controls test the analytic contractions, not an optimizer.

Only after that result is reviewed would a separate single direction from the existing reduced metric be informative. Fix the guide-normal search coordinates, solve the principal M_FF system for the smooth/interface-tangent midpoint gradient, and retain all incident-edge diagonals. This is a feasible trial direction, not an all-direction stationarity certificate. Its full continuous first variation and exact action would still require the existing descent/Armijo checks. That later step is not included in this proposal and has not been implemented.

## Pins and limits

- Current `src/core.hpp`: `7111f67c896b7b93d344372423259e288533210807392e7da2eec72f0c55caed`.
- Current `src/ray_metric.hpp`: `a282299431787361ff343dd71fc984fad0abcb675f7bf23b42189d1c61ba8732`.
- Saved one-step summary: `167bfd760019f461bdfcf373ce699575739bcc0704874c3ffde94044eedc23eb`.
- Saved tangent secants: `0bc560a2e48d5adb2dcf22cdad67809c0ace72dd1e8352375066f17c1c1861ed`.

No claim follows about a continuous stationary curve, inserted-knot variations, global first arrivals, endpoint/model derivatives, a full Hessian spectrum or the production optimizer's asymptotic rate. No new tolerance, smoothing, interface snapping or convergence label is proposed.
