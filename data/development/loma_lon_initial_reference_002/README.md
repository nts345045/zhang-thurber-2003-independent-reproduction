# Complete LON initial references with retained turning-speed precision

All **37,648** saved perturbed initial-source/receiver pairs have complete, valid references with unique defined source derivatives. The four-worker calculation took 422.1 s and retained **37,752** candidates. The largest candidate distance residual is **9.651941468291625e-10 km**, below the unchanged **1e-8 km** gate. Selected branches comprise 19,652 turning, 17,982 direct, 13 finite-bottom boundary and one flat direct case. Source time corrections remain native metadata and are excluded from propagation time; axes and source derivatives remain original x,y,z.

The separate module in source commit `1e69a8f` retains an exact rational enclosure midpoint of the turning speed reconstructed from the unchanged isolated root. It does not change root isolation, physical formulas, finite box, native support or acceptance limits. The original module (SHA `13020fef...`) and attempt `../loma_lon_initial_reference_001` remain unchanged.

`check.py` is byte-identical to the original generic saved-table review. It checks every native field, table/certificate value, original-XYZ derivative and boundary flag, all hashes and independent physical consistency bounds. `review.json` records a pass. `independent_review.json` records Earthscope's separate readback of all native rows, candidates, enclosures and 57 pinned files; it does not rerun reference arithmetic.

`attempt_comparison.csv.gz` joins every pair to complete native event/origin and receiver SEED/FDSN/epoch metadata. The saved-candidate comparison verifies every root interval, candidate signature, gate and isolation count; every nonturning candidate is exactly unchanged. All 19,705 turning candidate enclosures and rational depth/speed relationships pass exact Fraction checks.

Only pair **8156**, event **quakeml:NC.anss.org/Event/NC/255127**, receiver **NC.JSC..EHZ**, changes validity: invalid in preserved attempt001 and valid in new attempt002. No previously selected branch changes. There are 17,892 changed candidate times; the largest absolute change is **1.7013341846450203e-9 s** at pair8156. The largest source-gradient change in Euclidean norm is **1.3201001325412918e-13 s/km** at pair36287. Both extrema retain full native identity and candidate details in `attempt_comparison.json`. The original invalid candidate is compared as a candidate, not retrospectively labeled an accepted first arrival.

Reproduce in a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_initial_precise_turn_reference.py --data data/loma_lon_analytic_001 --plan data/development/loma_lon_initial_reference_plan_002/plan.json --output data/development/NEW_LON_REFERENCE --workers 4
```

The terminal saved-table review is `python3 data/development/loma_lon_initial_reference_002/check.py`. The candidate comparison was executed as `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/review_loma_initial_precise_turn_reference.py`; it requires fresh comparison filenames and preserves a source copy here. Its I/O path was also checked on four invented homogeneous pairs copied from the committed runner fixtures: native tables and candidate values remained unchanged. Root and Earthscope separately reviewed the comparison source. The numerical module and runner controls are retained in `../precise_turn_reference_checks` and `../loma_initial_precise_turn_runner_checks`.

The execution ledger, immutable summary and frozen input/source hashes distinguish computation completion from reference readiness. Time ranking remains ordinary floating-point evaluation, without interval-certified time ordering. Endpoint boundary derivatives remain branch derivatives. These references do not certify a numerical forward operator or accept any inversion.
