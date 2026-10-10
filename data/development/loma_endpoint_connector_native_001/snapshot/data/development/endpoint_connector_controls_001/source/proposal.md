# Proposal: a constrained curved endpoint action

An exact local connector could remove the captured bottom-source polygon
partial error **if its action and all derivatives replace the same straight
element together**. Endpoint momentum alone is not a consistent replacement
for the derivative of the existing polygon action. This note derives a bounded
affine-layer hypothesis; it implements and validates no correction. The native
experiment remains held.

The motivating saved pair is 24104: event
`quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`, derived identifier
`FDSN:NC_HQR__E_H_Z`, epoch `1989-07-11T19:55:00` to
`1990-03-24T19:55:00`. The saved current and catalog coordinates remain distinct.
These identities describe authoritative simulation geometry, not simulated
pick identities. `provenance.json` pins the source record and numerical evidence.

## The two derivatives

Let depth z increase downward, slowness s=1/v, and
T[γ]=∫s(γ)|γ′|du. The endpoint momentum is p=s t, where t is the unit tangent
from source toward receiver. Integration by parts gives

    δT = p(b)·δb − p(a)·δa
         + ∫[|γ′|∇s − d(s t)/du]·δγ du.

On a regular stationary interior branch, the integral vanishes and the source
derivative is −p(a). This requires a well-defined branch derivative; at a tie,
the first-arrival directional derivative may select among different branch
momenta. A boundary source has only derivatives in admissible directions.
Normal reactions along a constrained guide cannot simply be omitted from the
variation of an arbitrarily prescribed path family.

For one straight edge of length L and tangent t, the exact fixed-other-endpoint
partial instead satisfies

    ∂a Sstraight = −s(a)t
                  + L∫₀¹(1−u)(I−t tᵀ)∇s(a+uLt)du.

Thus the discrepancy is the integrated transverse variational residual of the
chosen straight family. On the saved horizontal bottom edge it is L s′z/2,
the already verified −1.5850655663e−5 s/km. Its removal from the derivative
alone would leave a travel-time function whose finite differences disagree
with the supplied derivative. At a true positive bottom guide, contact can
rearrange over a shrinking interval under source motion; the optimized value
need not have the fixed-family partial. Fixed-polygon KKT stationarity does
not certify a differentiable minimized envelope.

## An exact action-level candidate in an affine layer

Assume isotropic positive speed v(z)=vB+g(z−B), g>0, within the relevant layer
and finite box z≤B. Use source a=(0,B−ε) and connector endpoint q=(ℓ,B), ℓ>0;
the horizontal axis follows their horizontal separation. Both endpoints and
the entire candidate must remain in that affine layer and box. Write
va=vB−gε and

    Xcrit(ε) = sqrt(vB²−va²)/g.

If ℓ≥Xcrit, the constrained minimum consists of a circular critical leg and
a horizontal guide of length ℓ−Xcrit. Its action is

    GB(a,q) = ℓ/vB + ∫[B−ε,B] sqrt(v(z)^−2−vB^−2) dz,
    ∂GB/∂az = −sqrt(va^−2−vB^−2),    ∂GB/∂ax = −1/vB.

This is more than a tangent guess: the one-form
dx/vB + sqrt(v(z)^−2−vB^−2) dz bounds travel time from below by
Cauchy–Schwarz. The critical leg and bottom guide attain that bound. The
nonnegative guide length is an admissibility condition, not a clipped value.
For fixed positive ℓ and ε→0,

    GB(B−ε,q)−GB(B,q)
      = (2/3)sqrt(2g/vB³) ε^(3/2) + O(ε^(5/2)).

The inward limiting normal derivative is zero; the derivative at positive ε
is generally nonzero. This value is C¹ in that normal limit, but its second
normal derivative is singular. An arbitrary constant gradient zeroing rule
does not follow.

If ℓ<Xcrit, the circular interior connector reaches q without crossing B. Its
action is

    Ginterior(a,q) = (2/g) asinh[g |q−a|/(2 sqrt(va vB))].

The contact transition must select the admissible branch, not extend a circle
below the box or retain a negative guide. At g=0 use the separate homogeneous
limit |q−a|/vB. An oblique homogeneous ray from (0,1) to (1,0), v=6, has
source-depth derivative +1/(6 sqrt(2)) s/km at the bottom. This is a direct
counterexample to setting every bottom normal derivative to zero.

The connector must also admit motion of q into the box. With both endpoint
depths below B, a positive guide has the condition ℓ≥Xa+Xq, with
Xi=sqrt(vB²−vi²)/g. Its action adds a second reduced integral from qz to B;
the q-depth derivative is −sqrt(vq^−2−vB^−2), and the horizontal q derivative
is +1/vB. Otherwise use the admissible interior circle with vB replaced by vq
in the interior formula. These endpoint variations belong to the same
connector action; q must not be artificially constrained to the bottom.

## What would change, and what would remain unresolved

The proposed discrete action would be

    Fnew(a,x₁,…)=GB(a,x₁)+Σremaining Sstraight(xᵢ,xᵢ₊₁).

Source and x₁ derivatives must both come from GB; other knots would optimize
this same action, and inversion trial values must use it. At a stationary
connector, each model derivative is the integral of the **actual grid basis**
along its curved and guided pieces: ∂G/∂m_j=−∫(∂v/∂m_j)/v² dl.
Differentiating only vB and g cannot supply the full Jacobian for arbitrary
nodal velocity perturbations. Nor can an affine formula be applied silently
to a general trilinear field. A later generalization would need a consistent
local connector action in the actual medium and matching model finite
differences. This note proposes no such implementation.

Even an exact first connector does not fix a wrong global branch, an
underoptimized remainder, or small source secants dominated by remaining
forward error. If the displaced critical contact lies beyond x₁, holding x₁
fixed imposes a different path family; free contact redistribution remains
necessary. Zero guide length, branch ties, sources at corners, other active
faces, velocity kinks crossed by the connector, and coincident endpoints
require explicit branch or directional treatment. A positive guide is assumed
only when its geometry is demonstrated. No native flag is promoted.

## Falsifiable invented control, without a global optimizer

Use the existing v(z)=5+z, B=1, source (0,1), receiver (2,1) geometry. Retain a
straight horizontal remainder from q to the receiver. Choose q at
ℓ∈{1/4,1/8,1/16} and inward ε∈{0,2^-22,2^-20,2^-18,2^-16}. For these
values the critical contact remains before q. Compare three explicitly
different calculations: the old straight-element action/partial, unchanged
action with momentum substituted only in the derivative, and the constrained
connector action with its own derivatives. No additional knots or iterative
global stopping criterion is needed for this test.

The connector-plus-remainder prediction is independent of ℓ and equals the
continuous finite-bottom value. Its increment scales as ε^(3/2), whereas the
old straight family has a leading gℓε/(2vB²) increment. The derivative-only
substitution must fail finite differences of its unchanged value. Check source
and q endpoint derivatives of each actual action, stable finite-step value
differences, and reciprocity. Preserve finite-difference step and arithmetic
error separately; require their error divided by the source increment to be
smaller than the unchanged source-accuracy allowance.

Retain the homogeneous oblique counterexample. Add q at ℓ=10^-3 with
ε∈{2^-26,2^-24,2^-22}: the transition is near
εcrit=gℓ²/[vB+sqrt(vB²−g²ℓ²)]≈8.33e−8 km. The first two cases admit a
positive guide and the third requires the interior connector. Record complete
curve containment and guide/contact status; no ε clipping or domain extension.
These cases distinguish consistent curved action from mesh insertion and from
normal-gradient clipping. Failure of any action/derivative or branch test
rejects this bounded hypothesis before a native experiment is considered.

## Mathematical source and scope

[Laurent Demanet, *Waves and Imaging*, §2.2, printed pp. 47–49](https://ocw.mit.edu/courses/18-325-topics-in-applied-mathematics-waves-and-imaging-fall-2015/c5db24b1a6d0d3301b1a3f21f6ceba3a_MIT18_325F15_CompleteLect.pdf)
provides primary lecture notes for the Fermat action, ray slowness vector and
branch distinction. The first-variation identity, constrained affine connector,
and proposed tests above are the present derivation, not a claim that those
notes analyze this repository's boundary discretization. No authors' simulation
code, output or figure data was used. No new numerical test, native trace,
inversion or observational request was performed.
