# Completed invented controls

Both independent control programs completed successfully using the exact four
packaged C++ sources. Their scientific outputs are copied without re-encoding.

| Control | Scope | Result |
| --- | --- | --- |
| [Affine arrivals](results/affine.json) | Nine homogeneous/affine geometries plus coincident-endpoint and invalid-profile checks | 58 checks passed |
| [Full nodal integrals](results/curved_integrals_summary.json) | Six groups, with complete supplied grids, curves, nodal vectors and comparisons in [44 JSONL records](results/curved_integrals.jsonl) | 24 assertions passed |

The affine controls compare the integrated action with separately implemented
closed-form travel time, endpoint closure and analytic source momentum. The
largest observed action discrepancy was 5.42e-19 s, endpoint closure discrepancy
1.27e-18 km, and source-momentum central-difference discrepancy 2.63e-13 s/km.
Cases include a turn, finite-bottom guides, bottom endpoints, reversal and a
velocity change of 2^-30 km/s over 10 km. No clamp or endpoint repair was used.

The full-nodal controls compare every node against independent cubic-polynomial
or elementary trigonometric antiderivatives. The homogeneous fixture's maximum
velocity-kernel discrepancy was 3.795e-19 s/(km/s), and its maximum nodal length
discrepancy was 1.518e-18 km. The arc/guide fixture's corresponding discrepancies
were 2.711e-20 s/(km/s) and 1.084e-19 km. The saved results also cover reversal,
exact independence from display spacing, explicit rejection after a one-ULP
lateral model perturbation, and preservation of supplied nonunique-branch
metadata. Layer-coherent model differences alone are not used as evidence for
independent nodal columns.

The nodal run made seven integration attempts: six completed, and the ineligible
model was rejected before samples. It recorded 27 subpieces, 648 quadrature
samples and two display calls. No branch enumerator, optimizer or real-data
evaluation was called by that program. The separate affine controls exercised
only their explicitly limited affine branch constructor.

All error scales above are observations in working arithmetic. The 16-point
rule supplies the returned integrals; the 8-point rule supplies discrepancies
on the same partition. Neither these discrepancies nor the finite regression
tolerances certify an outward error bound or universal accuracy. This package
does not establish piecewise-profile branch completeness, unique model
derivatives at ties, or a validated production forward/inverse calculation.

The documented portable replay was also executed once from the repository
root in a fresh project-local directory. Both compilations and both controls
exited successfully. The 58 and 24 checks passed, and the three scientific
result files matched the original bundled bytes. This verifies the stated
component replay on the recorded runtime; it is not the full tomography
rebuild.
