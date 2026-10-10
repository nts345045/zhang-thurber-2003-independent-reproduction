# Guarded direct-offset reference, 104 native samples

This repeats the declared 104-sample reference comparison using the direct-root delta = u - vmax correction, exact rational-u metadata, and explicit unresolved arithmetic/iteration failures. The old monotone reference, production solver, inputs, sampled rays and convergence flags are unchanged.

All 104 references are valid and complete, without near ties; selected branches remain 73 direct, 23 critical guide, six turning and two flat direct. The saved production/refined convergence counts remain 73 each. `prior_comparison.json` verifies all native metadata and branch kinds against `../layered_reference_001/` and records the small numerical changes. The material production accuracy findings, including locally converged wrong branches, are unchanged.

All source/input hashes and full branch certificates are preserved. The matching source passes the original 355 layered checks and 65 targeted direct-root integration/failure checks. The earlier `layered_reference_delta_002/` comparison used the same arithmetic before adding the iteration-exhaustion catch; it is retained separately.

This remains a diagnostic reference comparison, without simulation, observation generation, inversion, or production substitution. The exact rational parameter is retained for future sampling; the older monotone path sampler was not modified and can lose near-critical information if it reconstructs u from rounded p.
