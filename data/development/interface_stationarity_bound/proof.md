# Supporting bounds and exact coupled interface controls

## Constant face coefficients

Let a retained segment of nonzero length L>0 lie in a face. Zero-length segment variations are outside this derivation. Its endpoint normal displacements are a,b and q(u)=(1-u)a+ub. Denote the two one-sided normal slowness derivatives by g_minus and g_plus. The normal length variation vanishes. For constant coefficients the normal first variation is exactly

    L [g_minus (a+b)/2 + (g_plus-g_minus) I_plus(a,b)],

where

    I_plus(a,b) = (a+b)/2                  if a,b >= 0,
                = 0                       if a,b <= 0,
                = a*a / [2(a-b)]          if a > 0 > b,
                = b*b / [2(b-a)]          if b > 0 > a.

These expressions integrate the positive part of q and include arbitrary coupled signs. They are not a quadrature approximation. The component diagnostic absorbs L into the slopes (equivalently L=1), and adds an independently specified smooth linear first variation. This is an algebraic component control, not a newly imposed physical constraint or a simulated observation.

## Sufficient bound

For a convex jump g_plus >= g_minus, choose any pointwise feasible slope lambda between the two. For every signed q,

    g_plus max(q,0) + g_minus min(q,0) - lambda q
      = (g_plus-lambda) max(q,0) + (lambda-g_minus) max(-q,0) >= 0.

Integration and addition of the unchanged smooth terms give F(d) >= G·d for every retained-node direction. Constant lambda on each segment or each fixed subsegment is a restricted but feasible choice. The bound does not require this choice to minimize any norm. A QP over such choices can tighten the bound but cannot determine its validity.

For arbitrary directions, F(d) >= -||G||₂ ||d||₂, or F(d) >= -||G||∞ ||d||₁. For the original domain tangent cone C and any n in its polar cone, n·d <= 0 for d in C, so

    F(d) >= (G+n)·d >= -||G+n||₂ ||d||₂,  d in C.

A zero feasible residual gives a sufficient exact first-order certificate in this retained parameterization. A nonzero residual gives only the corresponding bound; it does not prove nonstationarity. These statements make no first-arrival or inserted-knot claim. If integrated coefficients are known only within errors, those errors must be included in the bound. For example, ||G_exact-G_computed||₂ <= E gives the bound -(||G_computed+n||₂+E)||d||₂.

## Coordinate probes can miss coupled descent

Use F(a,b)=A integral|q(u)|du+c(a-b), A>0. For c=3A/8, all four individual signed-coordinate slopes are positive: their minimum is A/8. Nevertheless F(-1,1)=A/2-2c=-A/4. The functional is convex, but individual coordinate signs cannot certify joint normal stationarity.

## A restricted support can be inconclusive at a stationary point

In the same functional take c=A/5. A single constant supporting slope lambda gives

    G=(c+lambda/2, -c+lambda/2).

Its squared norm is 2c²+lambda²/2, so the exact global minimum over constant slopes is attained at lambda=0 and remains nonzero. The negative of that best restricted gradient is an ascent direction:

    F(-c,c)=Ac/2-2c²=A²/50 > 0.

Two fixed half-segment slopes lambda=-4c on [0,1/2] and +4c on [1/2,1] are feasible because 4c <= A. Their endpoint moments are (-c,c), which cancel the smooth term exactly. Thus their supporting gradient is zero and proves F(d)>=0 for every joint direction. This demonstrates why restricting the support family can lose tightness, and why -G requires a separate evaluation of the actual directional functional before it is used as a step.

## Reversed cusps remain ineligible

For a reversed cusp F(a,b)=-A integral|q|du, the one-sided slopes satisfy g_plus<g_minus. Averaging them to zero is a Clarke-gradient choice, but it is not a supporting lower bound: F(1,1)=-A. The diagnostic rejects this convex-support construction and preserves the failure. It neither smooths the cusp nor changes its physics.

## Native and derivative limitations

The retained native guide has an already established smooth/tangent descent component. Normal supporting coefficients cannot alter it. The component diagnostic reads the frozen direction and its dot product, preserves all native identifiers and the existing numerical descent evidence, and does not rerun the action or optimizer. Consequently it must not relabel that path stationary.

An internal-node support bound alone does not identify a consistent source or model derivative. That requires the joint first variation in external parameters and internal knots, along with an appropriate envelope argument and treatment of branch switches. Multiple feasible stationary supporting slopes can have different endpoint projections. A selected arbitrary projection is not automatically a unique derivative of the optimized travel time.

The root proposal's inequalities and polar-cone signs are correct under the stated convex-jump assumptions. The reviewed directional evaluator splits quadrature at the direction-dependent zero of q. A fixed-node auxiliary quadrature problem is therefore distinct from that evaluator and from the continuous integral. Constant-coefficient controls avoid this distinction exactly; general coefficients require a separate integration-error analysis.
