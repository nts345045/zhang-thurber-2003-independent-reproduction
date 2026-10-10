# A Snell-law reference for the Hayward initial model

This derivation uses the continuous, horizontally uniform velocity actually saved in [initial_grid.csv](../hayward/initial_grid.csv), not the original layered table. Depth `z` is positive downward in km; velocity is in km/s and travel time in s. The file SHA-256 is `9e27c5356c1e04f2011fbc9d0fa70896f2bea31ead10379a03a119458bbb3810`.

| z (km) | v (km/s) | Gradient to next node (1/s) |
| ---: | ---: | ---: |
| -1 | 3.77 | 0 |
| 0 | 3.77 | 0.42666666666666664 |
| 4 | 5.476666666666667 | 0.09770833333333329 |
| 8 | 5.8675 | 0.05875000000000008 |
| 12 | 6.1025 | 0.13468749999999996 |
| 20 | 7.18 | domain ends |

Linear interpolation between these nodes is exactly the one-dimensional reduction of the solver's trilinear interpolation. The constant extension from -1 to 0 km is part of this computational model. No velocity below 20 km is specified.

## Fixed-depth leg integrals

Let `R` be horizontal source–receiver separation. A ray lies in their vertical plane because velocity depends only on depth. Horizontal slowness `p = sin(theta)/v` is conserved, where theta is measured from the vertical. Define

\[
 s(z,p)=\sqrt{1-p^2v(z)^2},\qquad
 q(z,p)=s(z,p)/v(z).
\]

Here `p` and `q` have units s/km. For a leg traversing depths `a < b`, its positive horizontal distance and time are

\[
 X(a,b;p)=\int_a^b \frac{p v(z)}{s(z,p)}\,dz,
 \qquad
 T(a,b;p)=\int_a^b \frac{1}{v(z)s(z,p)}\,dz.
\]

Split the interval at every model node. For a positive constant gradient `g`, with endpoint velocities `v_a <= v_b` and `s_a=s(a,p)`, `s_b=s(b,p)`, integration gives

\[
 X=\frac{s_a-s_b}{pg}
   =\frac{p(b-a)(v_a+v_b)}{s_a+s_b},
 \qquad
 T=\frac{1}{g}\log\!\left[
       \frac{v_b(1+s_a)}{v_a(1+s_b)}\right].
\]

The second expression for `X` avoids cancellation at small `p`. At `p=0`, use `X=0` and `T=log(v_b/v_a)/g` explicitly. At a turning endpoint `p*v_b=1`, set `s_b=0`: both integrals are finite despite the integrand singularity. Stable log differences or `log1p` should be used for short intervals.

For a flat interval of thickness `h` and velocity `v_f`,

\[
 X=\frac{h p v_f}{\sqrt{1-p^2v_f^2}},\qquad
 T=\frac{h}{v_f\sqrt{1-p^2v_f^2}}.
\]

A positive-thickness flat leg becomes infinitely long as `p*v_f` tends to one. A zero-thickness leg contributes zero and must not be evaluated as `0/0`.

For fixed endpoints, the distance derivative is

\[
 X_p=\int_a^b\frac{v(z)}{[1-p^2v(z)^2]^{3/2}}\,dz>0.
\]

Its gradient-layer expression is `(1/s_b - 1/s_a)/(g*p^2)`, with limit `(b-a)*(v_a+v_b)/2` at `p=0`; the flat-layer expression is `h*v_f/s_f^3`. These formulas provide direct branch monotonicity without a numerical derivative.

## Direct and turning branches

**Direct branch.** For distinct endpoint depths, sum fixed-depth legs between `min(z_s,z_r)` and `max(z_s,z_r)`. Solve `X_D(p)=R` over `0 <= p <= 1/v_deep`. Since `X_D` is strictly increasing, bisection or Brent's method has at most one root. Evaluate its endpoint limit: it is finite if the deepest part has positive gradient, and infinite if a positive-thickness maximum-velocity flat interval is traversed. A root exists exactly when the requested distance lies in that range. At the finite endpoint, the ray is tangent at the deeper endpoint and coincides with the limiting turning branch; count it once.

If both endpoints lie in the flat extension, also evaluate the straight ray directly:

\[
 L=\sqrt{R^2+(z_r-z_s)^2},\qquad T_D=L/v_0.
\]

This handles equal-depth endpoints, for which the vertical-leg distance equation is identically zero and cannot recover a horizontal ray. In particular, for equal depth and `R>0`, `p=1/v_0` and `T_D=R/v_0`. The straight path is an admissible candidate even at the `z=0` interface; a dipping ray can be faster. At equal depths inside a positive-gradient interval, a horizontal straight line is not a stationary ray, so it supplies no extra direct branch. Coincident endpoints have `T=0` and no unique travel-time gradient.

**Turning branches.** A downward-going ray turns at `z_t >= max(z_s,z_r)` where `p*v(z_t)=1`, then rises to the receiver. Its distance and time are

\[
 X_T(p)=X(z_s,z_t;p)+X(z_r,z_t;p),\qquad
 T_T(p)=T(z_s,z_t;p)+T(z_r,z_t;p).
\]

Enumerate every positive-gradient layer that can contain `z_t`, through the bottom at 20 km. No upward turning branch exists in this monotone profile. The ray can turn only once, but the endpoint distance equation can have multiple roots, including multiple roots within one turning layer.

Turning velocity `u=v(z_t)=1/p` is a useful root parameter. On one turning layer, every complete gradient interval contributes

\[
 X=\frac{\sqrt{u^2-v_a^2}-\sqrt{u^2-v_b^2}}{g},
\]

while the final partial interval, from velocity `v_a` to `u`, contributes

\[
 X=\frac{\sqrt{u^2-v_a^2}}{g_t},\qquad
 T=\frac{\operatorname{acosh}(u/v_a)}{g_t}.
\]

A flat leg contributes `h*v_0/sqrt(u^2-v_0^2)` to distance and `h*u/[v_0*sqrt(u^2-v_0^2)]` to time. Add contributions from both endpoint-to-turn legs. The admissible `u` interval is the velocity range of the turning layer, clipped below by the deeper endpoint's velocity. Split at every layer boundary; distance is continuous there, but its derivative can have different singular one-sided limits.

## Bracket every root

One sign-change bracket over an entire turning layer is insufficient. The following gives a completeness criterion without assuming one extremum:

1. On each open turning-layer interval, collect the distance expression as

   \[
   X_T(u)=\sum_m c_m\sqrt{u^2-a_m^2}
          +\frac{H v_0}{\sqrt{u^2-v_0^2}},
   \]

   where `a_m` are fixed endpoint/node velocities, `c_m` are signed reciprocal-gradient coefficients, and `H` is total flat-leg thickness. Terms absent from the path are omitted.

2. Isolate every stationary point from the explicit derivative

   \[
   \frac{X_T'(u)}{u}=
   \sum_m\frac{c_m}{\sqrt{u^2-a_m^2}}
       -\frac{H v_0}{(u^2-v_0^2)^{3/2}}.
   \]

   Interval bounds on each term can certify derivative sign on subintervals; uncertain intervals are subdivided. Interval Newton or derivative bounds can certify an isolated stationary point. The derivative of this last expression is

   \[
   -u\sum_m\frac{c_m}{(u^2-a_m^2)^{3/2}}
       +\frac{3H v_0u}{(u^2-v_0^2)^{5/2}}.
   \]

   Handle singular endpoints by their one-sided limits or an appropriate square-root variable. A fixed sampling grid alone does not certify that no narrow pair of roots was missed. If a critical interval cannot be resolved, report the reference as uncertified there rather than claim complete enumeration.

3. Partition at the certified stationary points and layer endpoints. On each remaining monotone interval, bracket `X_T(u)-R` and solve by bisection/Brent. Test critical points and layer endpoints separately: a tangent root need not change sign. Deduplicate shared endpoints, then evaluate the time of **every** surviving branch.

This is a scalar reference calculation; it needs no inversion machinery. The coefficient representation also permits independent checks of any proposed simpler bracketing rule for this particular profile.

### Explicit two-root example in the saved profile

Put both endpoints at `z=-h` in the flat layer and let the turn lie in the first gradient. Set `w=sqrt(u^2/v_0^2-1)`. Then

\[
 R=\frac{2h}{w}+\frac{2v_0}{g}w,\qquad
 T=\frac{2h\sqrt{1+w^2}}{v_0w}
       +\frac{2}{g}\operatorname{asinh}(w).
\]

The distance has a minimum `R_min=4*sqrt(h*v_0/g)` at `w=sqrt(h*g/v_0)`. Above that minimum there are two algebraic roots, provided both turning depths remain in the selected layer. For `h=0.5 km`, `R=12 km`, and the actual `v_0=3.77`, `g=0.42666666666666664`, both do:

| Candidate | Turning depth (km) | p (s/km) | T (s) |
| --- | ---: | ---: | ---: |
| Flat direct | none | 0.2652519894 | 3.1830238727 |
| Shallow turn | 0.0416981600 | 0.2640061036 | 3.1951775882 |
| Deeper turn | 1.3865490173 | 0.2292739634 | 3.1203137262 |

Here `R_min=8.4075858604 km`. The deeper turning ray beats the flat direct ray. Finding only the shallow turning root would give the wrong arrival even after comparison with the direct candidate. All other admissible turning layers must still be checked for a global first-arrival reference.

## Model bottom and global arrival

For a finite-domain FMM calculation, paths are restricted to `-1 <= z <= B=20 km`. Discard a formal turning point below `B`; do not extend the last gradient without an explicit model change. Finite-domain shortest paths can nevertheless reach the bottom tangentially, follow it, and leave tangentially. Define

\[
 p_B=1/v(B),\quad
 X_B=X(z_s,B;p_B)+X(z_r,B;p_B),\quad
 T_B=T(z_s,B;p_B)+T(z_r,B;p_B).
\]

When `R >= X_B`, include

\[
 T_{\mathrm{bottom}}=T_B+[R-X_B]/v(B).
\]

The horizontal boundary segment is nonnegative by construction. At equality it is the limiting bottom-turning ray. A non-tangent reflected path is not an additional first-arrival candidate: a bottom contact with nonzero vertical slowness can shorten its time by moving upward. This boundary segment is a consequence of the computational domain, not evidence for a physical reflecting interface or head wave.

For example, depths `z_s=8 km`, `z_r=-0.2 km` give `X_B=76.9951681437 km` and `T_B=13.4851741586 s`; at `R=90 km` this boundary candidate takes `15.2964320773 s`. Omitting it would leave the bounded-domain enumeration incomplete. Monotone speed offers no faster top-boundary excursion. Horizontal projections of the listed rays stay on the segment between the endpoints, so a rectangular horizontal domain introduces no additional constraint when both endpoints are inside it.

The first arrival is the minimum over the direct, all turning, and any bottom-boundary candidates. Retain branch labels and near ties when comparing against FMM. No root or candidate is discarded merely because its time exceeds another until enumeration has completed.

## Source derivatives and an FMM check

Let `e_h=(r_h-s_h)/R`. Let `sigma_s` be the sign of the initial vertical tangent: `sign(z_r-z_s)` for a nonhorizontal direct ray, and `+1` for a turning or bottom-boundary ray. Fermat's endpoint variation gives

\[
 \nabla_s T=
 \left(-p e_{h,x},\,-p e_{h,y},\,
       -\sigma_s\sqrt{v(z_s)^{-2}-p^2}\right).
\]

The flat straight-ray derivative is simply `(s-r)/(v_0*L)`. At `R=0` on a vertical direct ray, set the horizontal derivative to zero. The derivative with respect to source origin time is `+1`. No derivative of the optimizing `p` is added: stationarity removes that term. The spatial derivative satisfies `|grad_s T|=1/v(z_s)` on a unique smooth branch. At a tie between distinct first-arrival branches, the minimum can be nondifferentiable; report branch derivatives rather than a single purported exact gradient.

As a separate consistency check, the closed forms satisfy `dT/dp=p*dX/dp` (or `dT/du=p*dX/du` for a turning branch). Thus `dT/dR=p` along a regular branch. The stationary quantity with an imposed distance is `T(p)+p*[R-X(p)]`, not the unconstrained function `T(p)` alone.

This reference can independently validate `loc1d` FMM because its model is exactly one-dimensional. Compare times and source derivatives at identical physical coordinates while refining the FMM spacing, with identical domain bounds and off-grid source/receiver treatment. Include vertical/direct cases, equal-depth flat cases, the two-root example, turns across each gradient change, and bottom-boundary cases. Compare gradient errors away from branch ties and use one-sided domain derivatives at boundaries. Check reciprocity and eikonal residuals as additional diagnostics; neither alone proves global first-arrival correctness. This derivation does not validate FMM in a later three-dimensional inverse model.

Transient calculations checked the positive-gradient leg against independent numerical quadrature: for `a=4`, `b=8`, `p=0.12`, both gave `X=3.7198637276 km`, `T=0.9632419884 s`, and `X_p=57.9185785223 km^2/s`. Quadrature of both example turning times agreed within `3e-12 s`. Centered source-coordinate differences with a `1e-5 km` step on the deeper example branch gave horizontal and vertical derivatives `-0.22927396346` and `-0.13338690925 s/km`, within `3e-11 s/km` of the endpoint formula. These check formulas, not a completed global root enumerator or FMM implementation. No production code, data, or running job was changed.
