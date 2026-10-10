# Exact component controls for an interface stationarity bound

This is a separate diagnostic. It changes no production action, path, optimizer, derivative or stopping flag. `001` passes **447 checks**: 100 exact split-integral controls, 300 feasible-support bounds, nine domain-polar directions and the named coupled, stationary, nonconvex and saved-native controls.

The standalone component uses exact `Fraction` arithmetic for constant interface coefficients. Its closed positive-part integral is checked against an independently split polynomial antiderivative. It does not solve an auxiliary QP and does not use auxiliary optimizer convergence as a certificate. Every tested supporting coefficient is feasible; validity follows from the pointwise inequality proved below.

The saved native direction belongs to event **quakeml:NC.anss.org/Event/NC/20091683**, origin **quakeml:NC.anss.org/Origin/NC/2660124**, receiver **NC.BSL..EHZ** / **FDSN:NC_BSL__E_H_Z**, epoch **1989-08-25T19:45:00–1990-09-10T19:20:00**. `001/native_direction.csv` retains all 2,705 node records and their identifiers. Existing source hooks show that interface-normal components were zeroed before normalizing this negative-gradient direction. Its saved dot product and direction reconstruct a smooth/tangent gradient norm of approximately **6.82584e-6 s/km** and largest component **4.0134390673e-6 s/km**. These components cannot change when only the interface-normal supporting slopes change. The existing confirmed numerical action decrease and original false flag are retained; no action, gradient or ray is recomputed here.

Reproduce in a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_interface_stationarity_bound.py --output data/development/interface_stationarity_bound/NEW_VARIANT
```

`001/summary.json` contains every assertion, exact rational counterexample values, complete native context, existing high-precision action evidence, source/input hashes and output hashes. `001/source` freezes the executed diagnostic, reviewed directional evaluator and source hook, root's proposal, and existing numerical tables. The raw native evidence remains unchanged. The derivation below defines the scope and limitations; finite-direction controls illustrate its exact algebra and do not replace the proof.
