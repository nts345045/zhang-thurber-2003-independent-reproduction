# Invented scalar bottom-contact experiment

This is a restricted-family calculation, not a native ray correction. The
source, input coordinates, commands and all results are frozen beside this file.
The run completed with 87 recorded controls. Independent mathematical review is
requested separately; completion does not certify the perturbed minima.

The single cell has axes x = [-0.25, 0.5], y = [-0.5, 0.5], z = [-1, 0] km.
Its original eight nodal velocities give v = 6 + z km/s. The source is
(0, 0, -epsilon), the fixed receiver is (0.25, 0, 0), and the free contact is
(r, 0, 0), with 0 <= r <= 0.25 km. The family includes both endpoint contacts
and collapsed links. These coordinates are invented and have no provider IDs.

Every nodal perturbation uses the same eight-node trilinear velocity, reciprocal
velocity action and original nodal sensitivities along both straight segments.
There is no affine-model dispatch. The affine formulas are independent value
and derivative oracles for the unperturbed fixture only. The contact search
retains endpoints and roots bracketed by 16 uniform derivative intervals;
this is not a completeness proof for a perturbed model. A collapsed link has
zero action and nodal integral, but no assigned ordinary endpoint partial.

For epsilon > 0 the affine-family action is strictly convex. Its inward
value secant decreases from 0.00425385587 to 0.00000415291637 s/km over
epsilon = 2^-8 through 2^-28 km. At epsilon = 0 all contacts describe the same
horizontal curve; this nonunique representation does not define a unique
fixed-contact endpoint partial. The analytic family has the correct zero
inward value derivative limit, while its leading excess action is
3/(2 sqrt(2)) = 1.06066017 times the continuous curved-connector excess.
Thus the 6.066% coefficient error remains even though the boundary derivative
limit is correct. The old single-edge inward partial is 0.00347222222 s/km.

Each precision contains seven scalar cases, 224 original-node model-column
comparisons, and 448 perturbed models. The parameter is negative log velocity:
v_j is multiplied by exp(-h), so the column is -v_j dT/dv_j. The largest
fixed-curve and reoptimized-candidate central-difference discrepancies are
1.43723e-11 and 1.43870e-11 s, respectively, below the declared 1e-10 s budget.
All finite-h discrepancies are retained. The maximum action difference from
the affine oracle is 5.56099e-63 s; repeating at 80 and 120 Decimal digits
changes the saved model comparisons by at most 4.69632e-74 s.

These agreement checks are not outward quadrature or rounding bounds. All 224
numerical derivative error certificates remain unproved, and the 192
epsilon-positive perturbed-family envelope comparisons remain unresolved.
At epsilon = 0 every contact still partitions the same physical curve under
each nodal perturbation, which justifies that restricted-family value identity.
The geometry is confined to y = 0, so mirror-y nodal sensitivities coincide;
the calculation does not test unrestricted lateral paths. In particular, the
saved fixed-receiver normal partial still has a finite adjacent-edge contribution.
No claim is made that one contact corrects both endpoints, arbitrary trilinear
geodesics, the whole-ray envelope, or any production convergence flag.

Rebuild from the integration worktree root into a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_endpoint_scalar_contact.py --output data/development/loma_endpoint_scalar_contact_controls_NEW
```

The summary pins four input files and eleven output artifacts. This README is
an explanatory addition outside that frozen result inventory. No native ray,
additional mesh hierarchy, network request, inverse solve or production edit
was performed.
