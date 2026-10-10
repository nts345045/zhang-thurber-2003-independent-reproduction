# Saved LON first-edge decomposition

This saved-component calculation does not resolve the source-derivative failure
of pair 8670. The analytic straight-edge derivative agrees with the saved
source partial to roundoff. An exact curved affine connector between the same
source and first saved knot slightly increases the discrepancy from the global
layered reference. The rest of the polygon is held fixed; no ray, receiver
field, optimizer, reference enumerator or inverse calculation was run.

## Inputs and identities

The input is the independently reviewed
[four-call old/D replay](../loma_lon_straight_curvature_replay_001/review.json).
Its old and D paths and source partials are identical for these two pairs.
Whole-ray times differ at roundoff, and no comparison of hidden optimizer
histories is implied. The current calculation pins and copies the consumed
tables, source, terminal ledger and reviews in
[calculation/snapshot](calculation/snapshot/). Every derived comparison retains
the full native event/origin/channel metadata and valid empty location codes.

Both pairs use event index 166,
`quakeml:NC.anss.org/Event/NC/10090456`, and origin
`quakeml:NC.anss.org/Origin/NC/2644764`. Pair 8670 uses receiver 38,
`NC.JHL..EHZ` / `FDSN:NC_JHL__E_H_Z`, with native epoch
`1989-10-19T20:40:00` to `1990-08-21T18:35:00`. Pair 8674 uses receiver 42,
`NC.JRG..EHZ` / `FDSN:NC_JRG__E_H_Z`, with epoch
`1989-03-24T22:55:00` to `1990-08-07T20:50:00`. These are the declared simulation
station placements; they are not event-time waveform measurements.

The actual saved 8 × 6 × 6 grid is depth-only. Its adjacent levels at 0 and
3 km have velocities 2.53 and 5.50640625 km/s as saved binary64 values. The
calculation uses their exact rational interpolant, not an external nominal
profile. Source depth is 2.92492374551 km; first-knot depths are
2.9293495581180906 and 2.9287919606384194 km. The first edges are respectively
0.02175534627 and 0.01787113896 km long.

## Action and derivative

Let the source be a, the first knot be b, d = b − a, L = |d|,
and v(z) = v0 + g z within the 0–3 km layer. Define va = v(a), vb = v(b),
Δ = vb − va, and I = log(vb/va)/Δ. Holding b fixed, the straight-edge action
and source derivative are

```
Ts = L I
∂a Ts = −I d/L + L g [log(vb/va) − Δ/va]/Δ² ez.
```

At Δ = 0, I = 1/va and the derivative of I with respect to va is
−1/(2 va²); a horizontal chord in a positive vertical gradient therefore has
a nonzero normal endpoint partial. For the unconstrained affine geodesic,

```
Tc = 2/|g| asinh(|g| L / (2 sqrt(va vb)))
∂a Tc = [−d/L − g L/(2 va) ez] / sqrt(va vb + (g L/2)²).
```

The homogeneous limit is L/va and −d/(L va). For g > 0 the connector is the
upper arc of a circle with depth center zc = −v0/g. With R² = dx² + dy² and
horizontal center a_xy + λc d_xy, the corrected center is

```
λc = [R² + (bz − zc)² − (az − zc)²] / (2 R²)
ρ² = λc² R² + (az − zc)²
   = (1 − λc)² R² + (bz − zc)².
```

The endpoint-radius equality is checked exactly, using rational R² without
rounding R. This sign was corrected in the planning discussion before the
first evaluation. On the upper arc, horizontal coordinates interpolate a
and b and depth is concave. For both native components λc > 1, so maximum
depth occurs at b. Exact rational checks place the complete curved connector
and straight edge within the same affine layer and finite grid box. The
analytic curved source formula also obeys the exact eikonal identity; its
numerical value agrees with the independently formed circular tangent.

## Results

All vector norms below have units s/km. The existing source limit remains
3 × 10⁻⁶ s/km. The component comparison does not update whole-ray acceptance.

| Pair | Saved − global reference | Saved − exact straight | Straight − curved | Curved − global reference |
| --- | ---: | ---: | ---: | ---: |
| 8670 | 4.807060122 × 10⁻⁶ | 9.2954 × 10⁻¹⁸ | 3.512571142 × 10⁻⁷ | 4.842636824 × 10⁻⁶ |
| 8674 | 1.059976299 × 10⁻⁶ | 1.6295 × 10⁻¹⁷ | 2.360149104 × 10⁻⁷ | 1.068446990 × 10⁻⁶ |

The local action reductions are 2.522812707 ns and 1.390680663 ns. These are
changes of the first action element, not newly optimized full-ray times.
The saved vectors satisfy the decomposition

```
saved − reference = (saved − straight) + (straight − curved)
                  + (curved − reference).
```

[components.json](calculation/components.json) retains both 80- and 120-digit
evaluations, exact geometric fractions, all vector differences, original
flags and full native context. [comparison.csv](calculation/comparison.csv)
provides the identified two-row comparison. The largest 80/120 change in a
reported source component is 4.255 × 10⁻⁷⁷ s/km. This is arithmetic sensitivity
evidence, not a certified transcendental roundoff bound.

Four formula controls pass: the homogeneous 3–4–5 chord, a vertical affine
logarithmic action, the horizontal affine chord's nonzero normal partial, and
the corrected circle-center radius identity. The calculation checks 82,698
native metadata cells across the saved paths, scalar records and reference
rows. No new numerical tolerance replaces the existing source criterion.

The straight-edge agreement rules out a material error in that saved
first-edge integration as the explanation of pair 8670's source discrepancy.
The isolated curved connector is insufficient. Its first knot is not
reoptimized, so the result does not establish the cause of the remaining
whole-path error or a stationary whole-ray correction. No original nodal
model sensitivities are replaced, and an affine-only production dispatch is
not proposed.

## Reproduce the saved calculation

From the integration checkout, choose a fresh output directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  data/development/loma_lon_first_edge_decomposition_001/check.py \
  --output tmp/loma_lon_first_edge_replay_001
```

The helper uses only the standard library, refuses an existing output
directory, snapshots the consumed files, and rehashes them after calculation.
It does not overwrite the reviewed replay or its failed source criterion.
Independent source/result review is recorded separately when available.
