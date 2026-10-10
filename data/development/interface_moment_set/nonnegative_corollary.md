# A sufficient minimum-norm certificate for alpha=0

For the constant convex jumps in this diagnostic, each feasible pair of excess endpoint moments A_e,B_e is nonnegative. Relative to the alpha=0 supporting vector G_0, changing interface support adds only nonnegative x components at guide-incident knots. All other components remain fixed.

If every affected component of G_0 is nonnegative, then for every feasible change delta>=0,

    (G_0x+delta)²-G_0x² = 2 G_0x delta+delta² >= 0.

Summing over internal knots shows that alpha=0 globally minimizes the Euclidean norm over the full feasible continuous supporting set for this polygon. This conclusion needs no optimization of the moment variables. It is a sufficient sign criterion; a negative component makes this particular criterion inconclusive.

`001/sign_check.py` checks the saved rational component intervals and the actual zero/1/18 slopes. For the original polygon, 1873 affected components are exactly zero and two have strictly positive lower bounds. For the full-direction new polygon, 1871 are exactly zero and two have strictly positive lower bounds. Thus the sign criterion certifies minimum Euclidean support norm in these two cases. The tangent-step polygon instead has two strictly negative components; its sign certificate is explicitly inconclusive.

The lower projection bound in `001/summary.json` remains valid in all three cases. It limits any normal-support reduction for the tangent-step polygon to approximately 4.3523e-8 relative to its saved norm upper bound. The surviving smooth/tangent residual cannot be removed by a different normal supporting slope.

This is a certificate about a supporting-vector norm at fixed saved polygons. It does not label either polygon stationary, select source/model derivatives, establish a first arrival, characterize inserted-knot variations, or prove that mesh stiffness causes the optimizer's behavior. It also does not transfer automatically to a different metric norm with coordinate couplings.
