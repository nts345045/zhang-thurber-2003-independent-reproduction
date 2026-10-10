# Saved-direction curvature

## One-sided extension `002`

After independent review of `one_sided_extension.md`, variant `002` completed 56 checks and computed all 2,704 edge contributions for the unchanged saved tangent direction. At a transverse segment endpoint on a velocity-gradient break, the second-order coefficient uses the slowness slope on the side approached as h tends to zero from above. This makes the eight edges excluded by the conservative `001` calculation eligible. The 1,874 aligned guide edges still have exactly zero normal motion; moved aligned cusp edges remain outside this calculation's scope.

The full scalar second variation is approximately 4.588213117378969 s/km². Its geometric, cross and medium contributions are 4.577181786960545, 0.016295647788475975 and −0.005264317370051715 s/km², respectively. The exact rational interval width for the total is below 7.932e−36 s/km². These are outward bounds for the declared continuous piecewise-affine model and exact saved coordinates/direction; the displayed decimal values are rounded.

Along that same direction, the production metric's continuous midpoint formula has energy 15.301312457406674 s/km², while replacing midpoint slowness by exact segment-mean slowness gives 15.301380574407984 s/km². Their relative difference is about 4.45e−6. The exact-mean isotropic metric decomposes into geometric curvature plus longitudinal energy 10.72419878744744 s/km². Thus changing only midpoint to mean slowness has little effect in this particular comparison, while the isotropic metric assigns substantial energy to longitudinal motion. The aligned guide contributes approximately 6.55e−14 s/km² of geometric curvature but 1.155682212678674 s/km² of isotropic metric energy. These scalar measurements do not determine a Hessian spectrum, prove a production convergence mechanism, or validate a replacement metric. They are not a bitwise replay of C++ binary64 metric sampling.

The saved action secants approach half of the one-sided second variation: at h=2^-17, 2^-18 and 2^-19 km, the interval for twice the secant minus the curvature is centered near −1.91412e−5, −9.58557e−6 and −4.79652e−6 s/km². This is finite-step consistency evidence, not a proof of a convergence rate. The first endpoint-piece or nonzero-x-difference event is at h≈0.0709848 km; the first finite-domain face event is at h≈39.1479 km. Every saved secant retains explicit event-range labels. No new trial or step was taken.

Recorded command:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
python3 diagnostics/check_native_interface_curvature.py \
  --directional-kink-endpoints \
  --output data/development/native_interface_conditioning/002
```

`002/source` freezes the arithmetic, model, native path, saved direction and reviewed derivation. `execution_receipt.json` records the terminal command, log and summary hashes. The original false local flag and source/model derivative choices remain unchanged. This result is a second derivative from h>0 along one fixed direction, not a two-sided Hessian, all-direction stationarity certificate, new stopping rule or source derivative.

## Preserved partial calculation `001`

Variant `001` completed 34 invented checks, then preserved eight ineligible native edges. Its full-curvature field is false. Four knots in the already saved direction move normally at non-guide velocity-gradient breaks: two knots at x=1 km, one at x=5 km and one at x=6 km. Their eight incident edges violate the proposal's conservative zero-normal-movement condition for kink endpoints. The 1,874 x=0 guide edges retain zero normal movement.

The table contains all 2,704 native edges. Excluded edges retain their exact coordinates, signed x differences, direction components, native identifiers and reasons. The contribution sums and metric energies in `001/summary.json` cover eligible edges only, as `contributions_complete=false` states. They are not the full path curvature or full path metric energy. No comparison of the complete second variation with the saved secants is claimed.

The identified path belongs to event `quakeml:NC.anss.org/Event/NC/20091683`, origin `quakeml:NC.anss.org/Origin/NC/2660124`, and receiver `NC.BSL..EHZ` (`FDSN:NC_BSL__E_H_Z`), epoch `1989-08-25T19:45:00` to `1990-09-10T19:20:00`. Full native context, the original false flag, exact frozen path and exact rational saved tangent direction remain attached. No new direction, solve, step, optimizer, stopping criterion or production source was used.

The controls cover homogeneous transverse curvature, the fixed-endpoint longitudinal parameterization freedom, reciprocal-affine oblique and equal-x edges, an extremely small but nonzero x difference, reversal, and a transverse crossing split at a fixed fraction with both endpoint normal coordinates fixed. The moved-kink endpoint control explicitly rejects an ineligible case. Independent 170-digit Decimal second differences are consistency checks; interval validity follows from the exact rational formulas, logarithm remainder and square-root enclosures. The tiny-x-difference control preserves a broad interval, approximately [0.0108563,0.0217127] s/km², rather than replacing it by the equal-x formula.

Two initial test-assertion failures are retained separately. `control_roundoff_001` preserves the 1e-110 Decimal subtraction remainder for an exactly linear action. `control_roundoff_002` preserves the mistaken demand that independently outward-rounded opposite slope intervals sum to exactly [0,0]. Corrected checks use exact rational action identities and interval containment. No numerical formula or tolerance was relaxed. These failed controls ran before the native calculation.

Recorded command, from the integration repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
python3 diagnostics/check_native_interface_curvature.py \
  --output data/development/native_interface_conditioning/001
```

For reproduction use a fresh output directory. `001/source` freezes the helper and all reviewed arithmetic/model/path/direction inputs; `execution_receipt.json` pins the terminal summary and log. The native calculation took approximately 17.2 seconds. `proposal.md` and `one_sided_extension.md` preserve the plans as written before their calculations. The failed eligibility result in `001` remains unchanged; its frozen source retains the conservative endpoint rule.
