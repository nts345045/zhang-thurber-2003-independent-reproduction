# Static endpoint connector on saved pair 24104

This calculation replaces only the mathematical first-edge action of the fixed
`fmm_0.031250_1000` polygon. It performs no perturbation, ray trace, optimization,
model-Jacobian evaluation, or flag change. The original local flag remains 1;
its separate full-ray source-accuracy failure is not relabeled.

The source is event `quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`. The receiver is `NC.HQR..EHZ`,
`FDSN:NC_HQR__E_H_Z`, epoch `1989-07-11T19:55:00` through
`1990-03-24T19:55:00`. All 199 original context fields, including the valid empty
location and distinct current/catalog coordinates, are preserved in
`native_context.csv` and attached identifier sidecars. These are authoritative
simulation-geometry identities, not invented simulated picks.

The source and first two interior vertices are exactly at the model bottom,
z=16 km. The last layer is positive, depth-only affine velocity; the exact slope
of its stored binary64 nodes is
`28472902268419/703687441776640` s^-1. Rounding this ratio to binary64 would change
it by `-1/720575940379279360` s^-1. The static formulas use the exact ratio. All
2528 saved vertices remain in the original box and all 2527 edges have positive
length. Convexity of the box keeps the horizontal connector inside it.

The first edge has length approximately 0.031257257325715641 km. Its straight
action and constrained bottom-guide action are mathematically the same `L/vB`,
approximately 0.004948665273216200 s. Their exact local difference is zero.
This identity is not inferred by subtracting rounded whole-ray totals. The
cached original total is preserved, and no new whole-ray time is evaluated.

Both endpoint derivatives of the first element change consistently with the
connector action. Its source-depth partial changes from approximately
−1.5850655663167804e−5 s/km to the inward limiting value zero. Its first-knot
normal contribution also becomes zero. The unchanged second edge still
contributes approximately −1.5850655661907541e−5 s/km at that knot. Therefore
the **complete** first-knot normal derivative changes from approximately
−3.1701311325075344e−5 to −1.5850655661907541e−5 s/km; it is not zeroed.
All tangential components and complete vectors are retained in
`derivatives.csv`.

The saved original source and first-knot vectors differ from the corresponding
closed-form straight-element vectors by norms 6.246e−18 and 7.182e−17 s/km.
The local connector source vector differs from the saved reviewed continuous
reference by 7.831e−17 s/km. These comparisons concern this isolated component;
they do not certify a new optimized forward result or remove errors elsewhere
on the polygon.

`exact_baseline_formulas.json` records exact rational geometry/model values and
symbolic equalities. Displayed radicals and vectors use Decimal80 and
Decimal100; their maximum observed spread is 6.755e−81 in the displayed scalar
units. This is a numerical consistency check, **not** an outward interval bound.
The normal derivatives at the bottom refer only to admissible inward motion.
No finite perturbations or global envelope derivative are assessed.

Reproduce into a fresh directory from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_loma_endpoint_connector.py \
  --output data/development/loma_endpoint_connector_native_FRESH
PYTHONDONTWRITEBYTECODE=1 python3 \
  data/development/loma_endpoint_connector_native_001/attach_formula_identifiers.py \
  --output data/development/loma_endpoint_connector_native_FRESH
```

The second command attaches the full native context directly to the formula
JSON, whose coordinates have no row-level pair column. It performs no numerical
calculation and refuses to overwrite an existing attachment. For this completed
package, `--verify-existing` verifies the separately added sidecar. The original
numerical helper and summary are unchanged. `identifier_packaging_correction.json`
records why the attachment was added after the static calculation; the prior
README is retained as `README_at_documentation_receipt.md` so its original
documentation-receipt hash remains checkable.

The helper verifies the reviewed observer and connector-control pins before
calculation, freezes small source/input/proof/review files, and rechecks all
original and copied hashes afterward. The full reference table remains in its
existing hash-pinned package; the complete selected reference row is copied.
`summary.json` pins 40 input/source files and 52 generated/snapshot files;
`execution.json` binds its terminal status. An initial invocation stopped before
any output or arithmetic because the newly written helper contained an obsolete
remembered review hash. The failure and original source are preserved separately
in `../loma_endpoint_connector_native_setup_001/`; the corrected pin matches the
unchanged committed observer review.

This affine component supplies no general trilinear connector or arbitrary
nodal sensitivity. A production method would need the same forward functional
through non-affine model perturbations and its matching source, knot, and model
derivatives. This result does not authorize such a change.
