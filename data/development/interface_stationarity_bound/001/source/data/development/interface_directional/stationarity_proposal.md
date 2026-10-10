# A sufficient first-order bound at convex slowness interfaces

This is a proposed diagnostic, not an implemented stopping rule. The saved
failed paths and their flags remain unchanged. Its purpose is to test all
infinitesimal path directions, including combinations of normal motions that
individual coordinate probes can miss.

## Assumptions and directional action

Keep the endpoints fixed and exclude zero-length segments from this derivation.
Velocity is positive, continuous and piecewise differentiable on the existing
grid. For an unperturbed segment lying in an internal face, let `u` run from
zero to one, let `L` be its length, and let the normal displacement be
`q(u) = (1-u) d_a + u d_b`. Denote the two face-normal slowness derivatives by
`g_minus(u)` and `g_plus(u)`. The normal contribution to the first variation is

$$
\int_0^1 L\{g_+(u)\max[q(u),0]+g_-(u)\min[q(u),0]\}\,du.
$$

The normal contribution to the segment-length derivative is zero on this
aligned segment. Tangential terms and derivatives of nonaligned segments
remain linear functions of the node directions. At intersecting grid faces,
the first-order normal terms must be checked separately for each axis.

If `g_plus(u) >= g_minus(u)` everywhere on each aligned segment, the complete
directional functional `F(d)` is convex and positively homogeneous. A local
slowness minimum is a special case. A reversed, nonconvex cusp does not satisfy
this assumption; it cannot be assigned a passing status by the construction
below. Uncertain sign or integration bounds also remain unresolved.

## Construct a supporting gradient

Choose a constant `alpha` in `[0,1]` separately on each aligned face segment,
and set

$$
\lambda(u)=(1-\alpha)g_-(u)+\alpha g_+(u).
$$

Pointwise, the directional slowness term is at least `lambda(u) q(u)` for
every signed `q`. Integrating its two endpoint weights and adding the smooth
terms therefore produces a vector `G(alpha)` satisfying

$$
F(d)\geq G(\alpha)^T d
$$

for every node direction. The vector depends affinely on the segment
coefficients. Minimizing its Euclidean norm over the coefficient box is a
convex quadratic problem. Constant coefficients give only a restricted family
of supporting gradients, so this minimization may remain inconclusive even
at a stationary path. It must not be described as an exact solution over all
pointwise supporting slopes.

For unconstrained interior nodes, any feasible coefficient vector gives the
sufficient bound `F(d) >= -norm(G) norm(d)`. For the original rectangular
domain, let `C` be the cone of allowable directions at the current nodes and
`C_polar` its polar cone. For any `n` in `C_polar`,

$$
F(d)\geq [G(\alpha)+n]^T d
      \geq-\|G(\alpha)+n\|\,\|d\|,\qquad d\in C.
$$

The smallest norm over `n` is the norm of the projection of `-G` onto `C`.
Fixed endpoint components are omitted. These constraints describe the
existing domain and endpoint conditions; they introduce no interface barrier
or restriction of normal directions.

## Required checks before using the bound

Small residual norm would bound the most negative first variation, subject
to integration error. It would establish approximate local stationarity only;
it would not identify the global first-arrival branch or validate source
derivatives. Conversely, the negative of a supporting gradient from this
restricted family is not necessarily a descent direction. Evaluate the full
directional functional and the actual action before accepting any move.

Start with exact constant-coefficient ridge and plateau examples, a reversed
cusp, and combined normal directions. Then examine the retained native guide
path, including its already established tangential descent. Keep continuous
and quadrature-defined bounds distinct: a fixed positive quadrature yields a
finite convex problem, but a continuous bound additionally needs control of
its integration error. Refinement agreement alone is not an interval proof.
The direction-dependent cuts in `interface_directional.hpp` must not silently
be replaced with fixed nodes and then called the same functional.
