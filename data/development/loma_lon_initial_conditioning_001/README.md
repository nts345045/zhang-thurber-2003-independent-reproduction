# Near-knot turning-parameter conditioning

This isolated diagnostic explains the distance-closure failure preserved in `../loma_lon_initial_reference_001/`. It does not replace that reference, change its validity flag, or calculate another branch or numerical ray.

The case is pair 8156, event 156 (`quakeml:NC.anss.org/Event/NC/255127`, origin `quakeml:NC.anss.org/Origin/NC/2644594`) and receiver 44 (`NC.JSC..EHZ`, `FDSN:NC_JSC__E_H_Z`, epoch `1989-05-10T21:40:00` to `1990-10-04T20:15:00`). **Every row of `nearby_parameters.csv` refers to this same case and joins to the complete verbatim `summary.json.native_row`**, including original source/receiver coordinates and all native metadata. Its propagation time excludes the saved source-time correction.

The unchanged monotone reference isolates the turning root in

\[
r=\sqrt{u^2-u_0^2},\qquad u=1/p,
\]

where \(u_0\) is the velocity at the 11 km layer top. It then evaluates `sqrt(float(u0*u0+r*r))` and stores the resulting binary64 \(u\) as a rational number. This loses part of the tiny squared-velocity excess before evaluating the legs. Replaying those exact steps reproduces the saved candidate time, turning depth, and failed closure exactly.

For an affine velocity leg, let \(q(v)=\sqrt{u^2-v^2}\), thickness \(h\), velocity endpoints \(v_a,v_b\), and gradient \(g\). The independent high-precision evaluator uses

\[
X=\frac{h(v_a+v_b)}{q(v_a)+q(v_b)},\qquad
T=\frac{\log[(v_b/v_a)(u+q(v_a))/(u+q(v_b))]}{g}.
\]

The constant-velocity limit is evaluated separately. Each partial leg from the layer top to its turn adds \(r/g\) in distance and \(\log[(u+r)/u_0]/g\) in time. Thus the two turning legs can be evaluated using \(u^2=u_0^2+r^2\) without reconstructing a rounded turning depth. This diagnosis uses Decimal arithmetic at 80 and 100 digits, separately from the frozen helper's interval/root-count implementation.

| Evaluation | Distance residual (km) |
|---|---:|
| Original saved candidate | +1.0783892889776325e-8 |
| Independent 100-digit legs at the same rounded \(u\) | +1.0783881504533754e-8 |
| Saved root-bracket midpoint, retaining \(u_0^2+r^2\) | -1.2148456344918210e-11 |
| Best of nine adjacent binary64 \(u\) values around the high-precision root | 5.3617330272111546e-9 in absolute value |
| Best of nine adjacent binary64 turning depths | 1.2239427908924954e-10 in absolute value |
| Best of nine adjacent binary64 \(r\) values | 1.9277709933045362e-20 in absolute value |

The difference between the first two distance evaluations is about 1.14e-14 km. The root bracket is already adequate for the unchanged 1e-8 km closure gate; its conversion to rounded \(u\) causes the dominant loss. Binary64 depth spacing and ordinary leg summation do not set the observed limit in this case. The nearby-parameter sweep diagnoses representation sensitivity; it is not a rule for selecting a convenient adjacent value.

The independent root has turning depth approximately 11.00000000088895849 km and branch action 9.13585257535141025 s. The original candidate action is about 1.6994e-9 s larger. That small action discrepancy does not override its failed closure check. The original selected time/derivatives remain blank. The high-precision target uses exactly the original binary64 transverse coordinate differences and `math.hypot` distance, not a higher-precision redefinition of the geometry.

An independently reviewed next arithmetic design could retain the squared-velocity excess through the turning-leg evaluation and preserve its parameter provenance. It must separately cover general turning layers, boundary roots, gradients and sampling; this one-case diagnosis does not validate such an implementation. No numerical helper or simulation/forward/inverse source is changed here.

`summary.json` preserves both precision evaluations, the exact original replay, full native metadata, and all input/source hashes. `review.json` records saved-table checks and the separate Earthscope agent's read-only arithmetic review. High-precision agreement is numerical evidence, not directed-rounding interval certification or a new completeness proof.

Reproduce using the matching maintained source and a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_loma_initial_turn_conditioning.py --output data/development/loma_lon_initial_conditioning_new
```
