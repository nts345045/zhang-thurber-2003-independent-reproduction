# Bounded guide candidate for Loma sample 5

This calculation uses source event `NC20091683`, origin `NC2660124`, and
receiver `NC.BSL..EHZ` in its native 1989-08-25 to 1990-09-10 epoch. The complete
provider metadata remain in `identified_ray.csv`; `saved_ray_result.csv` retains
the selected preflight row. These are catalog-defined simulation coordinates,
not measured travel times or invented provider picks.

The saved velocity depends only on x. It is 6 km/s for x <= 0, decreases to
4 km/s over x = 0 to 1 km, then rises east of the slow region. The existing
monotone-profile first-arrival enumerator does **not** apply to this entire
sandwich after coordinate permutation. Its exact linear-layer leg integrals
can still evaluate a specifically declared candidate, with either sign of the
velocity slope. No branch enumeration is performed here.

The candidate consists of two Snell legs tangent to the 6 km/s plateau at x = 0,
and 58.5364526585 km of travel along that plane. Its action is
15.127837995735218 s. The saved 0.5 and 0.25 km paths have actions larger by
448.141 and 136.093 microseconds, respectively. This candidate stays within
x = 0 to 13.1587002510 km. Its y and z coordinates advance monotonically along
the line between the endpoints, so it stays in the original finite box.
No continuation beyond a model boundary is assumed.

Writing R for transverse distance and X_s, X_r for the two legs' transverse
distances, the action is T_s + T_r + (R - X_s - X_r)/6. The transverse slowness
is 1/6 s/km. The source derivative is
(0.186338998125, 0.163967957828, 0.029871166421) s/km. `result.json` includes
independent source-coordinate finite differences of this candidate formula,
the source eikonal residual, and all input, reference-module and frozen-core
hashes. It does not claim a unique derivative of the global minimum.

At x = 0 the one-sided normal slowness derivatives are 0 and 1/18 s/km².
A sustained interface path can therefore have a nonsmooth action even though
velocity is continuous. The separate invented `interface_stationarity` test
establishes this mechanism in the actual solver. Attribution to this real
geometry still requires the isolated optimizer path/history inspection.

Executed from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 data/development/loma_geometry_preflight/row005_guide_reference/check.py
```

To repeat without overwriting evidence, append
`--output tmp/row005_guide_reference_check`. The running preflight can append
rows to its convergence table; the saved single row and original-table hash
record the capture used here. This calculation invokes no production ray,
inversion, provider query or cohort change, and makes no global completeness
or first-arrival claim.
