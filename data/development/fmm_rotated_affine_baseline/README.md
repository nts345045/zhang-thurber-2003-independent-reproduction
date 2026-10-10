# Rotated affine-velocity validation

This isolated test uses invented geometry and a smooth positive velocity field,
`v(x)=v0+g·x`. It tests the optional second-order FMM initializer with closed-cell
source seeding, followed by the unchanged continuous bending optimizer. It does
not change production code or test a competing direct/diving branch.

## Independent reference derivation

Let `G=|g|`, `e=g/G`, `va=v(a)`, `vb=v(b)`, and `R=|b-a|`. Rotate coordinates so
that `e` is vertical, and translate the vertical origin to the plane `v=0`.
The resulting height is `h=v/G`, so Fermat's action is

`T=(1/G) integral sqrt(dx_horizontal^2+dh^2)/h`.

The stationary path lies in the plane containing `e` and `b-a`. The conserved
horizontal slowness gives a circular arc centered on `h=0`. Define
`D=|(b-a)-e[e·(b-a)]|`, `ha=va/G`, and `hb=vb/G`. For nonzero `D`, its center is

`c=(D^2+hb^2-ha^2)/(2D)`, with radius `r=sqrt(c^2+ha^2)`.

Writing the arc as `x=c+r*cos(theta)`, `h=r*sin(theta)` gives the independent
integral `T=|log[tan(theta_a/2)/tan(theta_b/2)]|/G`. Substituting the endpoint
coordinates yields

`cosh(G*T)=1+G^2*R^2/(2*va*vb)`, and hence

`T=2/G*asinh(G*R/(2*sqrt(va*vb)))`.

This is the positive-half-space geodesic. The implementation tests every
coordinate extremum of its circular arc, including stationary angles, against
the finite model box. Since the entire arc lies inside the box, the unconstrained
minimum is also feasible in this model. An independent published derivation for
an arbitrary linear velocity gradient is given in Appendix B of
[Fomel, Luo, and Zhao (2009)](https://www.math.uci.edu/~zhao/homepage/research_files/FS_factored.pdf).
No author software was used.

With `u=G*R/(2*sqrt(va*vb))`, differentiating the closed form gives

`grad_a T = R/[sqrt(va*vb)*sqrt(1+u^2)] * [(a-b)/R^2 - g/(2*va)]`.

The reverse ray tests the derivative at `b`. The exact formula's central finite
difference provides an additional derivative consistency check. The circular
integral and a densely sampled circular arc evaluated by the existing continuous
segment action provide separate time checks.

## Geometry and result

The box is `[-15,15]^3` km, `v0=6` km/s, and
`g=0.12*(1,2,3)/sqrt(14)` s^-1. The endpoints are
`a=(-10.13,-5.24,7.35)` km and `b=(11.27,7.19,-7.41)` km. Two further cases reflect
all vectors in the x coordinate or cyclically permute coordinates. Both endpoint
directions are tested. Endpoints are off the auxiliary grid. Velocity remains
positive throughout the box: 3.11358–8.88642 km/s. The analytic arcs have at least
3.73 km clearance from every box face.

All 72 checks pass at auxiliary spacing 0.5 km and path spacing 0.25 km. The
largest FMM-bent time error is 4.3076e-6 s, endpoint-derivative error 4.5738e-7
s/km, and reciprocity discrepancy 5.10e-9 s. Every FMM-bent and selected ray
satisfies the unchanged local convergence criterion. Both candidates are tested
separately, so a successful straight-seed result cannot conceal an inaccurate
FMM-bent candidate.

The original tolerances remain 2.5e-5 s for time, 3e-6 s/km for endpoint
derivatives, and 2e-5 s for reciprocity. Since these gates pass, no auxiliary or
path refinement was run for this fixture. Distinct `field_refine` and
`path_refine` runner levels are available if later failures require them. The
circular-polyline action differs from the closed form by at most 3.57e-9 s; the
exact formula's derivative finite difference differs by at most 5.24e-12 s/km.

## Reproduction and limits

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_rotated_affine.py --variant NEW_NAME
```

The runner rejects existing variant directories. It sets `TMPDIR` to repository
`tmp`, compiles the snapshot under that directory, and saves source/result/binary
hashes. Commands and archive member paths are relative to the repository;
archive owner identifiers and timestamps are zeroed. Python 3.6 is supported.
The exact compilation inputs, including the generated unchanged bending body,
are preserved in `source_snapshot.tar.gz`. `references.csv` contains the model,
geometry, analytic bounds, and exact derivatives; `results.csv` contains both
computed candidates, `checks.csv` retains every gate, and `paths.csv` preserves
the analytic, initial, and bent paths.

This validates rotation/reflection behavior and smooth-field action/derivatives
for the stated cases. It does not resolve the recorded near-critical branch
selection errors in layered models, certify arbitrary heterogeneous first
arrivals, or authorize production integration.
