# Horizontal baseline identities

Treat every stored coordinate and velocity as its exact binary64 rational
value. Let the bottom be B and the last-layer velocity be
`v(z)=vB+g(z-B)`, with exact positive g and vB. For either retained horizontal
edge, let `delta=b-a`, `L=sqrt(delta·delta)>0`, and `t=delta/L`. Both endpoints
lie on z=B.

The straight-family action is `S=L/vB`. Differentiating this family with its
other endpoint fixed gives

```
partial_a S = (-t_x/vB, -t_y/vB, L*sprime/2)
partial_b S = ( t_x/vB,  t_y/vB, L*sprime/2)
sprime = -g/vB^2.
```

The normal length derivative vanishes at a horizontal edge. The depth
derivative of the integrand integrates the affine endpoint weight, whose
integral on [0,1] is 1/2. These are inward partials at the bottom.

The constrained connector equals the positive bottom guide at this baseline.
Its critical legs have zero length, so `G=L/vB=S` exactly. Under a small inward
endpoint displacement epsilon, the critical leg fits before the other endpoint
because its horizontal distance tends to zero while L is positive. Its reduced
action grows as epsilon^(3/2); therefore its inward limiting normal partial is
zero at each endpoint. Its tangential partials are respectively `-t/vB` and
`+t/vB`. This is the same action-level branch derived and tested in the frozen
affine connector controls, specialized to the exact horizontal baseline.

Only the first edge is replaced. Consequently the source vector becomes
`partial_a G`, while the complete first-interior-knot vector is

```
gradient_x1,new = partial_b G(a,x1) + partial_a S(x1,x2).
```

The second term is retained in every component. Its nonzero normal reaction is
not removed. The old vector is obtained by substituting `partial_b S` for
`partial_b G` in the same sum. No other vertex, path, action element, or saved
flag is modified by this static comparison.

The exact equality concerns the mathematical local elements only. Decimal
evaluation of square roots and comparison with saved binary64 outputs are
separately labeled numerical values. Neither this equality nor agreement of a
source component with a continuous reference establishes stationarity of the
remaining polygon, differentiability of a globally minimized envelope, or a
consistent Jacobian under arbitrary nodal velocity changes.
