# Exact endpoint moments of a constant convex interface jump

For a nonzero segment of length L, let its one-sided normal slowness derivatives be constant g_minus<=g_plus. Write c=L(g_plus-g_minus)>=0 and q(u)=(1-u)a+ub for the linearly interpolated endpoint normal direction. The normal first variation is

    L g_minus(a+b)/2 + c integral_0^1 max(q(u),0) du.

The first term is fixed and linear. Only the second term requires a supporting choice. Let lambda(u) be any measurable function with 0<=lambda<=c and define its endpoint moments

    A = integral_0^1 (1-u) lambda(u) du,
    B = integral_0^1 u lambda(u) du,
    m = A+B = integral_0^1 lambda(u) du.

Then aA+bB is a feasible lower support for the positive-part integral. The claim here is a description of every such moment pair for constant c, independent of any optimizer.

## Necessary bounds

For c>0, 0<=m<=c. Among all densities with mass m and upper bound c, filling [0,m/c] minimizes the first moment B. Filling [1-m/c,1] maximizes it. To verify the lower bound directly, set t=m/c. The mass difference between lambda and c*1_[0,t] is zero, and

    integral_0^1 (u-t) [lambda(u)-c*1_[0,t](u)] du >= 0.

Both products are nonnegative: on the left both factors are nonpositive, and on the right both are nonnegative. The vanishing mass difference removes the term proportional to t. The upper bound follows by reflection u->1-u. Therefore

    m²/(2c) <= B <= m-m²/(2c),       0<=m<=c.

Equivalently the moment set is

    (A+B)² <= 2cA,       (A+B)² <= 2cB.

These two inequalities imply A,B>=0 and, after addition, m<=c. This is a closed convex set. For c=0 the only feasible pair is A=B=0; division formulas are not used. A negative c is a reversed cusp and is outside this convex-support construction.

## Constructive sufficiency

For 0<m<c, set t=m/c, B_min=m²/(2c), B_max=m-B_min, and

    theta=(B-B_min)/(B_max-B_min).

Every pair satisfying the bounds has 0<=theta<=1 and is realized by

    lambda(u)=c [(1-theta)1_[0,t](u)+theta 1_[1-t,1](u)].

Its mass is m, and its first moment is (1-theta)B_min+theta B_max=B. Its other endpoint moment is A=m-B. Even when the intervals overlap, their weights sum to c, so the pointwise bound remains valid. At m=0 use lambda=0. At m=c use lambda=c, which forces A=B=c/2. Thus the inequalities describe the complete moment set, rather than a restricted constant or piecewise-constant approximation.

## Support equivalence

For every feasible density,

    aA+bB = integral_0^1 q(u) lambda(u) du
          <= c integral_0^1 max(q(u),0) du.

Equality is attained by lambda=c on the subset where q>0 and zero elsewhere. Since q is affine, this subset is empty, full, or a single endpoint interval. Its moments are elementary rational integrals when a,b,c are rational. Consequently the support function of this two-dimensional moment set is exactly c*I_plus(a,b). No fixed quadrature nodes or approximate support family are required for this constant-coefficient result.

The argument characterizes feasible supporting moments and their support function. It does not solve a norm-minimization problem or determine a source/model derivative. For variable face coefficients, this constant-c moment set is not the corresponding full support set.

## Native residual and curvature interpretation

On the saved x=0 guide, changing feasible normal support affects only x components at guide-incident internal knots. Let P retain every y/z component and every x component at a knot not incident on an aligned kink. Then P*G is independent of every feasible interface support choice. Thus

    inf_feasible_G ||G||₂ >= ||P*G||₂.

The accompanying diagnostic encloses this fixed norm from the already saved rational gradient intervals. It compares the lower bound with the norm upper bound of the saved alpha=0 support. A close pair of bounds limits how much changing normal support alone can improve this residual. It does not identify the spectrum of the path Hessian or establish a causal explanation for slow optimization.

For additional scale information, the saved tangent trials define the second-order secant coefficient

    K(h) = [T(P+h*d)-T(P)-h*F(d)]/h².

The diagnostic bounds K from the recorded action and first-variation intervals without reevaluating either. Positive K quantifies curvature along this one saved direction. It is not a full Hessian bound or an isolated test of mesh stiffness. The polygons, native identities and convergence flags remain unchanged.
