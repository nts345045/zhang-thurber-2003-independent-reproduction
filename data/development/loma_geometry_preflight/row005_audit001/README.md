# Identified Loma ray 5: optimizer and integration checks

The selected diagnostic is event index 473 and native receiver index 2:
`quakeml:NC.anss.org/Event/NC/20091683`, origin
`quakeml:NC.anss.org/Origin/NC/2660124`, and `NC.BSL..EHZ`
(`FDSN:NC_BSL__E_H_Z`). Its channel epoch is
1989-08-25T19:45:00 through 1990-09-10T19:20:00.
`identified_ray.csv` retains the complete native metadata, original coordinates,
source hashes and the numerical geometry. `diagnostic_row=5` links every path,
history and component check to that record; no observed pick identity is created.

This component copies the frozen solver from Loma run `001`, commit
`bff2a451640a40bfdb73c92c536ef354c3c55c08`. It adds the existing observation-only
history hooks and calls the unmodified trace as a control. All eight cases match
exactly in path, time, source/model derivatives, path-length weights and optimizer
status. Both selected 1000-iteration cases reproduce the live diagnostic's
printed results. The live run, cohort, ray selection and convergence rules were
not changed.

## Result

Split eight-point Gauss action agrees with an independent exact x-only integral
on every saved path: maximum absolute difference **1.21e-14 s**. For the tested
worst projected and worst x components, exact-action central differences at
1e-6 km agree with the analytic path gradient within **1.10e-10 s/km**.
Quadrature and exact-action central differences agree within **1.44e-9 s/km**.
Six invented constant, crossing, reverse and interface controls also pass; their
largest exact-integral error is 2.71e-20 s. These checks establish integration
consistency on these paths, not a global first-arrival certificate.

The FMM-started, lower-action candidate remains underoptimized:

| Field/path spacing (km) | Iteration limit | Time (s) | Projected gradient (s/km) | Converged |
| --- | ---: | ---: | ---: | --- |
| 0.5 / 0.5 | 1000 | 15.128286136801 | 2.4285e-3 | No |
| 0.5 / 0.5 | 4000 | 15.128074218924 | 8.9293e-5 | No |
| 0.25 / 0.25 | 1000 | 15.127974088614 | 2.7490e-3 | No |
| 0.25 / 0.25 | 4000 | 15.127923036731 | 5.2941e-5 | No |

All four cases exhaust their iteration budget. Action still decreases in their
last 100 updates, and no cone-direction reset occurs. The straight-started path
converges to approximately 16.21963 s, about 1.092 s later. Its local convergence
therefore does not identify the first arrival.

The independent [bounded x=0 guide candidate](../row005_guide_reference/README.md)
has time 15.127837995735 s. The two 4000-iteration FMM results exceed that feasible
candidate by 236.223 and 85.041 microseconds. Their source derivatives differ
from this candidate by 1.19e-5 and 1.02e-5 s/km in Euclidean norm. That guide is a
feasible analytic candidate, not a proof of complete branch enumeration. The
remaining time differences include polygonal approximation and unfinished
optimization; this experiment does not separate their contributions.

## Interface interpretation

The actual saved paths have six strict crossings of velocity-gradient kinks,
but **no exactly interface-aligned segment**, and none whose two ends are both
within 1e-8 km of the same kink. At 0.25 km spacing and 4000 iterations, 220 of
340 nodes lie within 0.001 km of x=0; the minimum x is −0.000892 km. The path
approaches a long guide but remains off the interface.

Its tested left and right exact-action derivatives approach the same analytic
derivative as the step shrinks. The separate invented
[interface stationarity counterexample](../../interface_stationarity/README.md)
shows that a genuinely aligned segment can have different one-sided derivatives.
That is a separate solver limitation, not the demonstrated cause of this ray's
slow convergence. No interface constraint or softened stopping test was imposed.

## Rebuild and files

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_loma_ray_diagnosis.py --variant NEW_NAME
```

The helper reads the preserved run `001`, refuses existing outputs, copies all
frozen source dependencies, retains the native identity, and rebuilds the
instrumented driver. `instrumentation.diff` records the history hooks;
`driver_adaptation.diff` records the diagnostic naming, explicit FMM spacing and
additional action checks. `summary.json` records commands and hashes;
`review.json` records the comparisons above. Both spacing directories contain
the direct/FMM results, every accepted update, final node coordinates/gradients,
cone records and left/right integration checks. The exact action splits at every
x plane and uses the logarithmic reciprocal-affine integral in long-double
arithmetic, independently of the Gauss implementation.

The earlier `../001/partial_findings.json` is explicitly incomplete (20 of 104
diagnostic rows) and has full native joins and prefix hashes. The complete
104-ray diagnostic continues separately. Synthetic observation generation remains
blocked by its local-convergence gate.
