# Proposal: a local value problem with the original trilinear action

**Planning only. No implementation, native calculation, or production change.**
The smallest useful next experiment should reuse the existing segment action
and test a better resolved *local value problem*, before introducing a curved
element or a new whole-ray optimizer. The reviewed 24104 component demonstrates
the mechanism on an affine baseline; it does not supply a nodal-grid Jacobian.

## One action for every model

For positive nodal velocities, retain the actual continuous trilinear field
`v(x;m)=sum_j N_j(x) v_j` on the original finite box D. Define

    A(P;m) = sum_edges integral_0^1 |b-a| / v(a+t(b-a);m) dt,
    G_N(a,b;m) = min A((a,p1,...,p[N-1],b);m),  pi in D,
    G(a,b;m) = inf_N G_N(a,b;m).

Repeated vertices contribute zero action and must remain allowable as limits;
there is no positive minimum link length or merge rule in this definition.
The nested polygon classes can represent a disappearing endpoint layer.
Positive continuous velocity on the compact box makes the action continuous
in each finite polygon, including a collapsed edge. Piecewise-linear curves
approximate rectifiable curves, so this is a convergent action discretization.
That statement does **not** imply convergence of its endpoint derivatives.

Use the same definitions under every nodal perturbation, including changes
that destroy depth-only or affine structure. A future first-element action
would be `G(a,x1;m)` plus the unchanged remaining segment actions. An affine
closed form can be an oracle or an evaluation shortcut for the same G; it
cannot select a different production functional.

No arbitrary small search box is needed. If v_max is the actual grid maximum
and S(a,b) is the straight competitor, any improving curve has length at most
`v_max*S(a,b)`. Its points therefore lie in the intersection of D with
`|x-a|+|x-b| <= v_max*S(a,b)`. This is a physical comparison bound for a
numerical search, not an extra path constraint or model assumption.

## Falsifiable first control: a free contact is insufficient by itself

Take invented `v(z)=V+g(z-B)`, V=6 km/s, g=1 s^-1, B=0, a=(0,0,-epsilon),
b=(1/4,0,0), in a finite positive-velocity cell. In the feasible two-link
bottom-contact family c=(r,0,0), let

    alpha = log(V/(V-g*epsilon))/(g*epsilon),
    beta = V*alpha,
    r_star = epsilon/sqrt(beta^2-1).

When `0<r_star<1/4`, its exact minimized excess over horizontal bottom travel
is `epsilon*sqrt(beta^2-1)/V`. Its leading coefficient is
`sqrt(g/V^3)*epsilon^(3/2)`. The continuous curved connector instead has
coefficient `(2/3)*sqrt(2g/V^3)`. The ratio is `3/(2sqrt(2))`, about 1.06066.
Thus a freely placed contact can recover the correct zero inward limiting
derivative while retaining a 6.066% leading-coefficient error at finite
epsilon. It can be a consistent variational approximation without being an
exact connector. This is an explicit
bottom-contact-family result, not a proof of the unrestricted G_2 minimizer.
At finite epsilon the contact may move or the guide may disappear.

The first proposed calculation is only this bracketed scalar minimization
with stable logarithm/square-root formulas, checked against the exact affine
connector and the maintained fixed-straight-element partial. Predeclare
epsilon = 2^-k km for k=8,12,16,20,24,28, plus the boundary limit. It should
recover the two-link coefficient above, not falsely agree with the curved
coefficient. Record the fixed-contact partial separately from the reoptimized
value secant. Allow both r=0 and r=1/4, including collapsed-contact states;
do not choose a fixed-knot partial from the nonunique boundary minimizers.
This tests a concrete mechanism before any general local solver.

The only accompanying first-stage model test is the same one-free-contact
family evaluated with the actual eight-node trilinear basis, independently
perturbing every node as specified below. Keep that identical restricted
value definition for every model; there is no affine-formula dispatch.
Compare its original-basis kernels first on fixed curves and then against
the reoptimized scalar-family values. This tests internal model-derivative
consistency of a declared approximation, not a general three-dimensional
geodesic or native correction. Any unproved scalar minimum stays unresolved.
The broader roster below is a conditional later plan, not part of this first
bounded calculation.

## Bounded continuation if that control is correct

Use one invented trilinear cell and nested local polygons with N=2,4,8,16
links. Retain the actual knot positions; do not redistribute them uniformly,
impose a contact, or clip endpoint derivatives. The proposed inner calculation
must distinguish a numerical candidate from a justified minimum. A local
stationarity flag alone is insufficient, as the prior endpoint-mesh controls
already demonstrate. Use 80/120-digit arithmetic for this diagnostic and
report quadrature and minimization error separately. Precision agreement is
not itself an interval certificate.

The control roster is limited to:

1. The positive affine guide and disappearing-layer ladder above; require
   the refined action coefficient to approach the continuous oracle.
2. The previously reviewed exact below/at/above critical-distance cases;
   preserve guide-free competitors and a vanishing guide without clipping.
3. A homogeneous oblique bottom source and a negative vertical gradient;
   neither has a blanket zero normal derivative. Include g=2^-20 and 2^-40
   as limiting controls, with source and first-vertex inward directions kept
   distinct from inadmissible outward derivatives.
4. Perturb each of the eight actual cell velocities independently in both
   directions, then one mixed perturbation that varies both tangential axes.
   Use identical action/integration code for affine and non-affine values.
   Compare every original nodal kernel and all admissible source/first-vertex
   derivatives with reoptimized values, not with fixed-path differences.
5. A two-cell version whose connector crosses a grid face, retaining the
   original shape functions on both sides. An aligned gradient kink or a
   branch tie is reported as directional/unresolved unless separately handled.

The eight-node perturbations use the solver parameter convention
`v_j(h)=v_j*exp(-h)`, with h=2^-12,2^-16,2^-20,2^-24. First check the kernel
on a frozen admissible curve to isolate interpolation/integration signs;
then repeat against the same reoptimized connector action. The frozen-curve
check alone is not an envelope/Jacobian validation.

## Matching derivatives and the stopping impediment

For a regular stationary branch, the physical nodal derivative is

    dG/dv_j = -integral_curve N_j(x)/v(x)^2 ds.

The current solver's negative-log-velocity column is `-v_j*dG/dv_j`.
All original trilinear basis functions must be retained; differentiating
only V and g is insufficient. Source and first-vertex derivatives must come
from this same value problem, and both must enter the assembled path action.
Path-motion terms can be omitted only under the applicable variational
stationarity/envelope conditions. Multiple minimizing paths can instead give
different directional model derivatives.

At a collapsing link, the ordinary fixed-polygon endpoint partial is not an
envelope certificate. Initially evaluate admissible endpoint secants of the
reoptimized value and keep them separate from fixed-knot partials. For a
displacement h, a value error bounded by eta at each end contributes at most
`2*eta/|h|` to a first secant. Require that contribution below one quarter of
a declared 1e-8 s/km local derivative budget, plus a separately controlled
truncation/discretization error. For model h above, use a 1e-10 s local column
budget with the corresponding eta/h bound. These are proposed component
checks, not replacements for existing scientific or production gates.

If only candidate upper values or ordinary KKT flags are available, label the
endpoint-value comparison unresolved. More links, higher precision, or stable
time totals alone do not establish its derivative. In particular, a fixed
link budget may spend all its freedom bending along a laterally varying
bottom; the affine contact limit need not transfer to that discrete family.

This is the main impediment, and the reason to start with the scalar control.
A curved local element remains an alternative if the polygon hierarchy is
too costly, but it must minimize the same trilinear action, allow contact and
guide-free alternatives, and supply the same original-node sensitivities.
No native experiment should follow until these invented value/derivative
tests and their failure classifications receive independent review.

## Native context and provenance

The motivating saved component is pair 24104, event
`quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`,
`FDSN:NC_HQR__E_H_Z`, epoch 1989-07-11T19:55:00 to 1990-03-24T19:55:00.
`provenance.json` preserves its complete native context and hashes the
reviewed baseline, controls, and maintained geometry/forward code.
All proposed experiment geometries are invented and have no provider IDs.
