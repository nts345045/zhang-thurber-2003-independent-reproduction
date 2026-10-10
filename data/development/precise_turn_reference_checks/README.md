# Rational turning-speed diagnostic variant

`diagnostics/first_arrival_1d_precise_turn_reference.py` is a separate diagnostic copy of the validated monotone reference. The old helper remains unchanged at SHA-256 `13020fef85113c302b27d846e1b4286c13576348a10710ba8a4c6fbd999e1c98`. No production solver or saved reference table is changed.

The change replaces the binary64 square root used to reconstruct a turning candidate after root isolation. For exact rational squared velocity \(w\), an integer square root gives dyadic bounds \(l,h\). Before returning their rational midpoint, the helper verifies exactly

\[
l^2\leq w\leq h^2,\qquad (h-l)^2\leq w\,2^{-254}.
\]

The dyadic quantum scales with the numerator/denominator bit lengths, so the width bound is relative rather than tied to an absolute velocity range. Existing exact layer-boundary candidates retain their exact velocities. The physical leg formulas, interval root isolation, root-count decisions, candidate gates and tolerances are unchanged. Candidate metadata retains rational squared velocity, the enclosure, its midpoint, and turning depth.

The variant sampler uses those rational parameters before evaluating the small velocity differences near a turn. When they are absent, it preserves the original conversions and sampled path exactly, including Fraction endpoint callers. Final sampled coordinates remain binary64 and do not constitute an exact representation of a continuous curve.

Variant `003/` passes **135 component checks**, the **250 unchanged monotone checks**, and the **106 unchanged near-flat/boundary checks**. The component count includes the two aggregate legacy-suite assertions. The original suite assertions and thresholds are unmodified; only their reference API and output directory are rebound to the frozen variant. The overall source manifest pins the actual variant; inherited internal suite hash records also retain the original baseline helper.

Checks include relative scaling of exact enclosures over exponents from -1000 to +1000, tiny squared-velocity excesses, invalid arguments, byte equality of all root-isolation/leg functions, exact and adjacent finite-bottom cases from the prior suite, legacy sampler parity, rational sampler use, and the identified near-11 km case from the separate conditioning diagnosis.

For original LON pair 8156, event `quakeml:NC.anss.org/Event/NC/255127`, origin `quakeml:NC.anss.org/Origin/NC/2644594`, receiver `NC.JSC..EHZ` / `FDSN:NC_JSC__E_H_Z`, epoch `1989-05-10T21:40:00`–`1990-10-04T20:15:00`, the diagnostic candidate retains the original root interval and branch count. Its distance residual is **-1.2143175354140112e-11 km**, within the unchanged **1e-8 km** gate. Its time differs from the independent 100-digit branch root by 1.91491267287347e-12 s and its source-derivative vector norm by 3.496446946337351e-18 s/km. Full native metadata and both original/diagnostic references are in `003/native_case.json`. The original full LON001 reference remains invalid and blank at this pair.

Negative development evidence remains preserved:

- `001/` stopped before numerical checks because the Python3.6 inspection harness had not registered importlib modules in `sys.modules`; the startup record identifies this harness problem.
- `002/` passes all old numerical suites but retains two failed added Decimal cross-checks for exact dyadic roots. A finite-precision Decimal conversion need not fall within a collapsed zero-width rational interval. `003/` uses the stronger exact squared identity for collapsed intervals and retains the 120-digit check for noncollapsed intervals. The numerical module and scientific gates did not change between `002/` and `003/`.

This evidence validates candidate arithmetic and the stated regression scope. It is not a full LON replacement run, a new completeness proof, interval-certified minimum-time ranking, or a validation of the numerical forward/inverse solver. A fresh full batch requires independent review and separate provenance. No full batch has been run by this checker.

Reproduce with a fresh variant name:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_precise_turn_reference.py --variant new_control
```
