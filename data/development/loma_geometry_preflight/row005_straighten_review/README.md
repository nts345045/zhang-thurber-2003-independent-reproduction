# Joint normal variation of the retained guide edge

This is an independent algebraic check of `row005_straighten001`, using its
frozen hashes and native identifier sidecar. It does not trace another ray.
The straightening proof and reduced L-BFGS signs/indexing were reviewed; no
material defect was found for the saved inputs. The crossing finder requires
strict sign-changing edges and does not discover an already exact x=0 vertex;
the saved original paths contain no such vertices.

For a guide edge of length L, let a and b be the joint normal endpoint motions,
and g_A and g_B the normal gradients from the regular incident legs. At x=0,
the one-sided slowness derivatives are 0 and 1/18 s/km². The first variation is

\[
D(a,b)=g_Aa+g_Bb+\frac{L}{18}\int_0^1\max((1-t)a+tb,0)\,dt.
\]

It is nonnegative for every pair (a,b) exactly when the required subgradient
moments A = -18 g_A/L and B = -18 g_B/L satisfy, with m = A+B,

\[
0\leq m\leq1,\qquad m^2/2\leq B\leq m-m^2/2.
\]

Indeed, the moments have the form A = integral (1-t) theta(t) dt and
B = integral t theta(t) dt for 0 <= theta <= 1. For fixed mass m, placing theta
at the left or right end gives the two bounds; convex mixtures fill the
interval. This checks coupled directions. At (A,B)=(0,1/2), every coordinate
direction passes, but the joint motion (a,b)=(-3,1) has variation -3L/144.
The component retains that failure as a control.

All four actual retained edges satisfy this algebraic normal certificate,
but their other restricted gradients remain above the existing 1e-7 s/km
criterion. No full stationarity flag is promoted. Restoring free guide knots
adds directions; this two-contact result does not certify those directions
or a continuous first arrival. The rational arithmetic certifies the algebra
of supplied binary64 partials, not interval bounds on the partials themselves.

Executed from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_geometry_preflight/row005_straighten_review/check.py
```

Use `--output tmp/row005_guide_certificate.json` for a fresh repeat. The
result records source and artifact hashes, action changes, remaining gradients,
moment margins, and four invented controls. No production source or threshold
was changed.
