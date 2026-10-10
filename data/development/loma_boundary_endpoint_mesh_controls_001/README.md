# Explicit endpoint mesh: analytical controls, unresolved value derivatives

This is an isolated diagnostic, not a source-derivative correction. No native
ray, inverse calculation, network request or production file was changed.
The predeclared native plan is `../loma_boundary_endpoint_next_step/plan.json`;
its five mesh levels and four inward displacements have not been executed on
native pair 24104.

The driver freezes the captured solver and changes only initialization: it
retains the supplied knot mesh instead of redistributing its vertices in
arclength. `initialization.diff` shows the complete change. The optimizer and
derivative suffix is byte-identical, SHA-256
`393e741dff39ac594c9b160fc43c130c235db034ac2b2fd89c737a42eae888b1`.
All three ordinary-trace comparisons use identical initial meshes and preserve
path, action, derivatives, updates, merges, gradients and local flag exactly.
Zero-budget checks verify retention of each refined initial mesh.

The 836/836 passing checks are analytical action/partial, tied-chain-rule,
reference lower-bound, roster and parity checks across three invented cases.
Independent 80-digit reciprocal-affine formulas assess each saved polygon;
closed-form continuous values separately assess the optimizer output. A check
count is not a count of successful optimized rays. All 240 evaluations and
polygons remain in the case directories. There were no exceptions or merges.

| Invented case | Optimized records | False local flags | Source errors above 3e-6 s/km | Maximum time error |
| --- | ---: | ---: | ---: | ---: |
| Positive bottom guide | 25 | 2 | 24 | 1.561 microseconds |
| Homogeneous oblique source | 25 | 0 | 0 | 5.08e-15 seconds |
| Near-zero guide | 30 | 0 | 8 | 8.687 microseconds |

All optimized times satisfy the existing 25-microsecond limit. This does not
establish sufficiently accurate differences of nearby optimized values.
The source-error comparison includes all three components; fixed and tied
families are preserved separately from optimized records and carry no local
success flag.

## What the controls demonstrate

For the positive guide in v(z)=5+z, the baseline horizontal curve is an exact
minimum but its leading fixed-knot partial remains `-L/72` s/km. At the smallest
inward shift, epsilon=2^-22 km, every mesh level stops with zero updates because
its projected gradient is about 3.3e-9 s/km, below the unchanged 1e-7 gate. At
level 1 the reported value secant is -0.00347230 s/km; the exact continuous
secant is -0.0000313233 s/km. Even level 16 retains a 0.000172572 s/km source
error. The large-displacement level-1 and level-2 runs instead exhaust 1,000
updates and preserve false flags. Thus the controls expose both endpoint
resolution and incomplete contact-point relaxation; quadrature/sign errors do
not explain these discrepancies.

For the near-zero guide, the base polygons stop after two updates with
projected gradient about 6.98e-6 s/km and true flags under the existing combined
action-change/gradient rule. Their remaining continuous time error is 8.687
microseconds. At level 16, epsilon=2^-22 km, the continuous branch becomes
interior and its travel time increases by about 5.85e-12 seconds. The numerical
return instead decreases by 1.39637e-8 seconds after 21 updates. Its reported
secant is +0.058568 s/km versus the continuous -0.0000245440 s/km, although the
reported endpoint vector itself is within 1.189e-6 s/km of the continuous
vector. The change in forward error dominates this finite difference. This is
an observed failure of value-derivative consistency, not evidence for a
positive physical depth derivative.

The homogeneous oblique control preserves a nonzero bottom-source derivative,
confirming that setting every boundary normal component to zero is invalid.
The near-zero control also records the guide/interior transition explicitly.
Tangential knot nonuniqueness, local flags, node counts and both finite-step
reference values remain inspectable; no optimized-value envelope is certified.

## Next decision

Do not launch the native ladder solely on the basis of these arithmetic and
parity passes. These controls already show that endpoint insertion with the
unchanged stopping policy is insufficient to certify reoptimized-value
sensitivities. A native run could quantify the same behavior but would not by
itself establish an actionable correction beyond the existing fixed-polygon
subdivision evidence. Source/control review should decide its added value
first. No threshold, zero-gradient substitution, domain extension or flag
promotion is proposed by this package.

Rebuild controls only in fresh paths, using the project environment:

```bash
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python diagnostics/run_endpoint_mesh.py \
  --output data/development/loma_boundary_endpoint_mesh_controls_FRESH \
  --build tmp/loma_boundary_endpoint_mesh/FRESH
```

The completed summary is SHA-256
`534fa492a55bb167f6b751efdb46642c235369a806d8e308d490cca6afac622c`.
It pins every executed helper, captured header, generated optimizer, input,
output and command log. `plan.json` also pins the identified native geometry
and source snapshot without executing them. No independent review has been
implied by the summary's analytical-contract status.
