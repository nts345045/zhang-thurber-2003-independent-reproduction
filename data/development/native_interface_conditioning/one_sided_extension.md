# One-sided curvature at a moved transverse kink endpoint

This is a proposed extension of the preserved partial `001` calculation. It introduces no direction, solve, step, optimizer or stopping criterion. Root authorized deriving these conditions and obtaining independent mathematical review before a separate `002` implementation.

Let the existing endpoint motion be a(h)=a+h*d_a and b(h)=b+h*d_b, with h approaching zero from above. Assume a nonzero segment, D_x=b_x-a_x !=0, positive continuous piecewise-affine velocity on a finite profile, and a direction feasible in the finite model for sufficiently small positive h. The primitive S of continuous slowness s=1/v is continuously differentiable. At a grid kink x_0 its one-sided second derivatives are s'_-(x_0) and s'_+(x_0). Therefore, for the already fixed scalar normal displacement gamma,

    S(x_0+h gamma)
      = S(x_0) + h*s(x_0)*gamma
        + h²*s'_{sign(gamma)}(x_0)*gamma²/2 + o(h²),  h -> 0+.

For gamma>0 the coefficient is the slope on the right; for gamma<0 it is the slope on the left. For gamma=0 the second-order term vanishes exactly and no side needs to be chosen. This side is determined by the saved direction and the sign of h, not an incident-cell convention or tolerance.

The endpoint formulas in the original proposal then hold with those directional slopes:

    J = [S(b_x)-S(a_x)]/D_x,
    J_a = (J-s_a)/D_x,                 J_b = (s_b-J)/D_x,
    J_aa = 2(J-s_a)/D_x²-s'_{a,dir}/D_x,
    J_ab = (s_a+s_b-2J)/D_x²,
    J_bb = s'_{b,dir}/D_x-2(s_b-J)/D_x².

As before,

    J' = J_a*d_ax + J_b*d_bx,
    J''_+ = J_aa*d_ax² + 2 J_ab*d_ax*d_bx + J_bb*d_bx²,
    Q_+(d) = (J/L)(|Delta d|²-(n dot Delta d)²)
             + 2(n dot Delta d)J' + L J''_+.

This is the second derivative from h>0 along this fixed displacement. It is not a two-sided Hessian, a bilinear form in all directions, or a stationarity test. The first variation remains unique on a transverse segment because s is continuous. The second one-sided value can change when the direction is reversed. Interior moving crossings are already included by S; no crossing-location derivatives are discarded.

For the actual x=0 guide edges, D_x=0 and both normal displacements are exactly zero. Keep their existing exact restricted curvature. Continue to reject any aligned kink segment with nonzero normal movement; its first-order cusp requires the separate directional treatment, and this extension does not expand that case. Preserve the existing smooth D_x=0 limits. Preserve exact nonzero D_x without snapping it to zero.

Finite-domain eligibility is checked before evaluation. All original movable native knots are strictly interior and the endpoints are fixed, so some positive feasible h exists. For interpretation of the saved finite secants, record the first positive h at which an endpoint reaches another x plane or a nonzero D_x becomes zero, if either occurs. This is an exact rational geometry diagnostic, not a new step restriction or acceptance threshold. Finite secants outside this local expression's unchanged endpoint pieces remain recorded and are labeled accordingly.

Minimal added controls:

1. Put a single transverse segment endpoint at an internal gradient kink and use each sign of its normal displacement. Compare the appropriate one-sided formula with independent high-precision actions at h,2h,3h>0. The forward combination [2T(0)-5T(h)+4T(2h)-T(3h)]/h² has O(h²) truncation error. This numerical control does not certify an interval by itself.
2. Reverse segment endpoints and their displacement vectors; action and the same one-sided curvature must agree. Include two separately moving kink endpoints so each directional side is selected independently.
3. Verify zero normal displacement reproduces the original eligible curvature intervals exactly, and that moved aligned-cusp edges remain explicitly ineligible.
4. Retain the previous homogeneous, affine, fixed-normal split/unsplit, tiny nonzero-D_x and rejection controls. No existing gate or native flag changes.

Only after source/formula review would a fresh `002` freeze run. It would preserve the eight original excluded rows and identify which directional slope makes each newly eligible. Every edge contribution and all continuous-versus-metric comparisons would remain interval bounded, with incomplete or inconclusive results retained. `001` is not overwritten or promoted.
