# A stationary ray can arrive late

This independent limiting case uses an invented velocity field, not earthquake
observations. It diagnoses branch selection in the forward calculation before
changing the inversion. Reproduce it from the repository root with:

```sh
python3 diagnostics/run_first_arrival_audit.py
```

The medium is isotropic, with depth `z` positive downward, velocity `v0=4 km/s`
for `-1 <= z <= 0 km`, and `v=v0+a*z` below, where `a=0.2 s^-1`.
The source and receiver have depth `-h=-0.5 km` and horizontal separation `L`.
The rectangular model contains the paths considered below. The production
solver starts from a straight path and minimizes the continuous action
`T=integral ds/v`. Within the flat layer its initial path has zero gradient.

## Independent reference calculation

Let `q=cot(i)`, where `i` is the ray's inclination from vertical at the interface,
and let `B=v0/a`. Snell's law gives horizontal slowness
`p=1/[v0*sqrt(1+q^2)]`. Each flat-layer leg advances `h/q` horizontally.
In the gradient layer the ray is a circular arc with radius
`R=B*sqrt(1+q^2)`, horizontal half-span `B*q`, and turning depth `R-B`.
Thus a symmetric diving ray satisfies

```
L/2 = h/q + B*q,
q = [(L/2) +/- sqrt((L/2)^2 - 4*h*B)]/(2*B).
```

Both positive roots must be considered when they exist. Integrating slowness
along the flat segments and circular arc yields

```
T_diving = 2*[h*sqrt(1+q^2)/(v0*q) + asinh(q)/a].
T_direct = L/v0.
```

For the faster diving branch the source derivatives are
`dT/dx=-1/[v0*sqrt(1+q^2)]` and
`dT/dz=-q/[v0*sqrt(1+q^2)]` for a receiver to the right.
The first-arrival comparison uses the minimum of the direct and two turning
branches. A separately integrated polyline with 1,024 circular-arc segments
also supplies an explicit admissible faster path, without depending on the
global completeness of that comparison.

## Measured failure

| Separation (km) | Returned time (s) | Faster diving time (s) | Delay (s) |
|---|---:|---:|---:|
| 4 | 1 | No turning branch | 0 |
| 20 | 5 | 4.918988590 | 0.081011410 |
| 40 | 10 | 8.989374075 | 1.010625925 |

The direct path is declared converged with zero optimizer updates in all three
cases. Its projected gradient is below `3e-16 s/km`. Increasing the iteration
budget cannot move that exactly stationary initial path. Independent polyline
integration agrees with the diving time within `8.7e-7 s` in the tested cases.
At 40 km the returned source depth derivative is zero, whereas the faster
diving branch has `dT/dz=-0.174464590 s/km`.

Local stationarity and finite differences on the selected branch therefore
cannot establish a first arrival. Existing constant-gradient and sampled
field-ray checks did not expose this constant-layer example. The Hayward
starting model has a constant top extension, but the final DD model does not
have an exactly flat top layer. This example does not quantify the error of
an individual field ray or establish the cause of its source displacement.

`results.csv` contains the measured times and derivatives; `summary.json`
records the command and source/binary/result hashes. `nan` in the 4 km row
means that no diving solution exists, not a failed numerical evaluation.
Production code, active inversion inputs, and stopping thresholds were not
changed for this diagnostic.
