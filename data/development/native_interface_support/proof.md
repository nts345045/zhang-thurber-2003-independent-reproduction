# Exact segment primitives and interval support

## Retained geometry and first variation

Consider the saved finite polygon with fixed endpoints and nonzero segments in a positive continuous velocity model v(x). All movable knots are strictly inside the model box. Every cell has velocity independent of y and z and affine in x. Coordinates and model values below denote the exact rational values of the binary64 numbers parsed from the saved tables.

For a segment from a to b, let Delta=b-a, L=||Delta||₂, h=b_x-a_x, and s=1/v. If h is nonzero, introduce a primitive S with S'=s and define

    J = [S(b_x)-S(a_x)] / h,       T_segment = L J.

Continuous slowness makes S continuously differentiable even at a velocity-gradient jump. Therefore the segment action is differentiable when h is nonzero, including an endpoint on an internal face. Differentiation gives

    J_a = [J-s(a_x)] / h,
    J_b = [s(b_x)-J] / h,
    grad_a T = -Delta J/L + e_x L J_a,
    grad_b T =  Delta J/L + e_x L J_b.

Each primitive difference is split at every crossed x plane. For a cell interval [l,r] with slope m=(v(r)-v(l))/(r-l),

    integral_l^r dx/v(x) = log[v(r)/v(l)] / m,  m != 0,
                         = (r-l)/v(l),          m == 0.

These formulas apply to either sign of the segment's x displacement; the implementation reverses the primitive sign when necessary. No small-h approximation is used. Interval dependency can widen an enclosure but cannot invalidate it.

For h=0 away from a kink, J=s(a_x) and J_a=J_b=s'(a_x)/2. At an aligned kink, let g_minus and g_plus be the one-sided derivatives of slowness. For endpoint normal directions d_ax,d_bx, put q(u)=(1-u)d_ax+u d_bx. The normal first variation is

    L integral_0^1 [g_plus max(q,0)+g_minus min(q,0)] du.

If g_plus>=g_minus, the choice lambda=g_minus gives a lower support because

    g_plus max(q,0)+g_minus min(q,0)-g_minus q
      = (g_plus-g_minus) max(q,0) >= 0.

Thus J_a=J_b=g_minus/2 supplies valid supporting normal components. The usual length derivative retains the smooth tangential components. An aligned reversed jump is explicitly rejected; no average gradient is substituted for it.

At the actual x=0 face, v=6 on the left and v=6-2x on the right. Hence g_minus=0 and g_plus=1/18 s/km² throughout every aligned edge. The calculation uses this alpha=0 support only. Summing the segment endpoint contributions gives G with

    F(d) >= G·d

for every joint direction of the retained internal knots. The convex finite box permits sufficiently small displacements of all the strictly interior movable knots. The endpoints remain fixed.

## Rational enclosures

For each logarithm ratio r>0, set z=(r-1)/(r+1), so |z|<1. After retaining terms k=0,...,n of

    log(r) = 2 sum_{k>=0} z^(2k+1)/(2k+1),

the absolute remainder is at most

    2 |z|^(2n+3) / [(2n+3)(1-z²)].

Every term and this bound are exact Fractions. The implementation stops only when the remainder bound is at most 2^-160; budget exhaustion is an error. For the saved native path the maximum is 11 terms. Reciprocal arguments provide an exact interval sign-symmetry control.

The reviewed `candidate_sqrt_enclosure` encloses the square root of an exact nonnegative Fraction between dyadic rationals and verifies both squared inequalities exactly. Lengths, the vector norm and its error norm use 128 relative bits. Only the square-root routine is called from the separately frozen precise-turn helper; no ray enumeration or root isolation is used here.

All interval operations use exact rational endpoints. After completing each segment action or gradient component, the interval is rounded outward onto the absolute lattice 2^-128. The implementation verifies that the rounded interval contains the incoming interval. This limits denominator growth; subsequent sums and dot products remain exact. It introduces a bounded arithmetic error, not a change to the continuous action.

Let the accumulated internal-gradient intervals be [l_i,u_i], with midpoint m_i and radius r_i. For the exact feasible supporting vector, |G_i-m_i|<=r_i. Therefore

    ||G-m||₂ <= ||r||₂ <= E,
    ||G||₂ <= ||m||₂ + E <= B,
    F(d) >= -B ||d||₂.

The stored rational upper endpoints supply B and E. Binary64 decimal displays may round either way and are not the authoritative interval endpoints. These bounds concern arithmetic and integration of the saved polygon only.

## Independent tangent witness and derivative scope

The existing in-plane direction has zero x displacement at every knot incident on a kink edge and zero endpoint displacement. Its kink-normal first variation vanishes identically. Consequently F(d)=G·d for this direction, regardless of the feasible supporting slope selected on the aligned edges. The computed rational dot-product interval is strictly negative, establishing retained-node descent independently of how tight the support-norm bound is.

This does not make -G a certified descent direction; that direction would require its own complete directional evaluation. Nor does an internal support specify source or model derivatives. The calculation omits fixed endpoint components from the output table and makes no envelope, stationary-path, or first-arrival assertion.
