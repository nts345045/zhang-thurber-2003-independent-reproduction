# Independent one-dimensional first-arrival reference

This diagnostic enumerates Snell-law candidates in a continuous, piecewise-linear,
nondecreasing velocity profile within a finite depth interval. Depth and horizontal
coordinates are in km; velocity is in km/s. The horizontal domain is unbounded, or
any convex rectangle containing both endpoints. Paths remain in the vertical plane
through the endpoints. No production solver, inversion, or provider request is run.
The formulas are derived in [the reference note](../first_arrival_1d_reference.md).

## Enumeration and its limits

The implementation is [first_arrival_1d_reference.py](../../../diagnostics/first_arrival_1d_reference.py).
It includes the monotone direct branch, constant-velocity straight paths, all
admissible downward turning layers, tangent paths along accessible plateau tops,
and constrained paths along the finite bottom boundary. It does not extend the
velocity profile below the model. Adjacent layers can label the same limiting ray;
these labels are retained. Reflections are not part of this transmission model.

In a turning layer, write `u = 1/p` and `r = sqrt(u*u - u0*u0)`, where `u0` is the
largest velocity at the layer entry or either endpoint. Closed-form leg integrals
give the distance equation as sums of `c*sqrt(r*r+d)` and `k/sqrt(r*r+d)`, plus
`c0*r` and possibly `k0/r`. Multiplication by `r` removes the latter endpoint
singularity. Coefficients are exact rational numbers for the supplied binary64
inputs, including the computed horizontal distance. Outward-rounded intervals
cover the complete admissible parameter interval. Function and derivative bounds
exclude empty intervals or establish a unique sign-changing root. Exact rational
tangencies are retained when the second derivative establishes uniqueness.
The flat-over-affine special case reduces to a quadratic with an exact
discriminant, so it retains both roots and the double root at the distance minimum.

`complete` means that no branch-isolation or boundary-sign uncertainty remains
under this model and arithmetic. `reference_valid` additionally requires finite
candidate times and distance closure within the declared tolerance, normally
`1e-8 km`. Travel times and their ordering are ordinary floating-point evaluations;
the code does not return interval bounds on the minimum-time gap. The `1e-9 s`
near-tie label is descriptive. Derivatives belong to an individual branch; a tie
between distinct branches need not have a unique first-arrival derivative.

General tangencies that cannot be isolated are reported in `unresolved`.
Exhausting the explicit subdivision budget also yields `complete=False` and
withholds `first_arrival`; `best_enumerated_candidate` is retained for inspection.
Nonmonotone profiles and endpoints outside the finite depth interval are explicitly
unsupported. The arithmetic assumes IEEE binary64 operations and correctly rounded
square roots. The checks exercise geophysical km and km/s scales; they do not
establish robustness for extreme magnitudes that overflow or underflow arithmetic.

`sample_path` returns analytic branch samples with exact endpoints, layer crossings,
and turning or guide depth. Gradient layers use circular arcs, flat layers use
straight segments, and guides use horizontal segments. These samples are a
diagnostic interface for later comparisons, not a change to production ray tracing.

## Rebuildable checks

Run from the repository root with Python, NumPy, and SciPy:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/first_arrival_1d_enumeration/check_reference.py
PYTHONDONTWRITEBYTECODE=1 python3 data/development/first_arrival_1d_enumeration/check_near_flat.py
PYTHONDONTWRITEBYTECODE=1 python3 data/development/first_arrival_1d_enumeration/compare_hayward_initial.py
```

[checks.json](checks.json) records 250 passing checks across 17 invented endpoint
cases, including constant and affine media, two turning roots, an exact double
root, offsets above and below that minimum, a root at a layer transition,
interior and terminal plateaus, the finite bottom, coincident endpoints, deliberate
budget exhaustion, and a rejected nonmonotone profile. Independent affine
hyperbolic-distance times agree within `1.9e-15 s`; source finite differences
agree within `9.2e-9 s/km`. Reciprocity is exact to the saved precision in these
examples. At a source exactly on a gradient knot, the check saves three centered
difference steps and cancels the leading step-size term by Richardson
extrapolation; it does not relax the derivative tolerance.

[invented_paths.csv](invented_paths.csv) contains only invented numerical geometry.
The checks verify endpoints, crossings, turning depths, domain containment, and
polygonal action convergence when sample spacing halves from 0.1 to 0.05 km.
The initial Hayward profile is read from the existing grid; its shallow flat
extension and grid-sampled velocity values are used unchanged. This profile is
the implemented continuous adaptation, not the original manuscript's layer table.
The JSON records source, script, and output SHA-256 hashes and library versions.

## Saved initial Hayward comparison

[hayward_initial_comparison.csv](hayward_initial_comparison.csv) preserves all
210 original identity associations for the 32 previously saved diagnostic rays.
The join checks the explicit diagnostic, event, and receiver indices against the
event and receiver metadata and verifies both native observation identities and
epochs. Every original identity column is retained unchanged, including provider
resource IDs, SEED/FDSN names, epochs, and source hashes. Original relative metadata
paths keep their `data/hayward` base, recorded explicitly in the derived CSV.
[hayward_initial_summary.json](hayward_initial_summary.json) contains all candidate
branches, closure results, comparison statistics, original derivative records,
and input hashes. The saved input hashes match the run manifest and earlier
diagnostic provenance; no initial file was changed.

All 32 cases have complete enumeration and valid closure. There is one candidate
per case: 20 direct and 12 turning rays, with no near ties. The maximum horizontal
closure error is `7.3e-12 km`.

| Saved result minus continuous 1D reference | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| Production time, microseconds | 3.82 | 38.87 | 143.95 |
| Refined time, microseconds | 1.32 | 11.79 | 37.48 |

None of these differences exceeds 1 ms. For the 24 saved source-derivative
components, the maximum absolute difference is `3.45e-5 s/km` for production and
`1.26e-5 s/km` for refined rays. These differences can include path discretization
and local optimization error; they do not identify the error mechanism by
themselves. This initial 1D sample does not show the large late-branch errors of
the invented counterexample. It does not validate every source/receiver pair or
any updated three-dimensional inversion model.

## Near-flat correction and retained failure evidence

Independent review found cancellation when a positive gradient approaches zero.
For a 1 km layer with endpoint speeds `5` and `nextafter(5,+infinity)` km/s, the
previous vertical time was 0.25 s instead of 0.20 s. With an additional 1 km
horizontal offset, the previous time was 0.50 s instead of 0.282842712474619 s,
and the sampled path length was 1.45075 km instead of approximately sqrt(2) km.

The fixed-depth time now evaluates `log1p(delta_v/va)` for the vertical term.
For an oblique leg it adds `log1p(delta_q/(u+qb))`, where
`delta_q=delta_v*(va+vb)/(qa+qb)` and `qa=sqrt(u*u-va*va)`.
These positive increments avoid rounding a ratio near one before taking its log.
Sampling uses `delta_theta=2*atan2(delta_v,qa+qb)` and local half-angle chord
increments, avoiding nearly equal angle and circle-coordinate subtraction.

The review also identified a turning root just beyond the finite bottom whose
midpoint rounded onto the boundary. Exact boundary membership now additionally
requires a zero distance-equation value. A bracket overlapping an unproven
boundary is reported unresolved; the true limiting root at exactly 40 km in the
regression remains admissible.

[near_flat_checks.json](near_flat_checks.json) records 106 passing regressions:
independent quadrature, a stable affine hyperbolic-distance formula, constant-limit
path geometry, and the finite-bottom cases. The unchanged module and previous
outputs are retained under [near_flat_failure](near_flat_failure/), including
39 failing regression checks. Reproduce that expected failure with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/first_arrival_1d_enumeration/check_near_flat.py --reference data/development/first_arrival_1d_enumeration/near_flat_failure/reference_before.py --output tmp/near_flat_failure_recheck.json
```

No existing tolerance was relaxed. All original 250 checks still pass.
[near_flat_correction.json](near_flat_correction.json) records the numerical
comparison and hashes. The maximum change in the 32 saved Hayward reference times
is `8.9e-15 s`; their branches, completeness, native identities, and reference
derivatives are unchanged. The 17 original invented first-arrival times change by
at most `3.6e-15 s`. The Hayward comparison CSV and summary were regenerated to
carry the corrected implementation hash and floating-point values.
