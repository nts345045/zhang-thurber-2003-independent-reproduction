# Identified initial ray 9291: continuous 1D comparison

This calculation compares the eight completed isolated controls in
`initial_ray_first_arrival_003_9291_audit001` with the existing exact-leg,
certified branch-enumeration reference. It does not rerun the ray optimizer
or assume that the whole Hayward003 preflight passed. Source event NC390228,
origin NC3655699, receiver NC.CCY..EHZ and its native 1992–1994 epoch are
preserved in `inputs/identified_ray.csv`; every comparison row carries the
event, origin, pick, arrival, channel and epoch identifiers and points to that
complete metadata mapping.

The reference first arrival turns at depth 4.000928869091735 km and takes
3.6454799943574034 s. Its distance closure is 3.08e-12 km. The saved 0.5 km
FMM candidate is later by 194.506 microseconds and has a false local stopping
flag. The saved 0.25 km FMM candidate is later by 54.0410 microseconds and has
a true local stopping flag; its source-derivative error norm is
1.509995e-5 s/km (largest component 1.50505e-5). Raising the saved iteration budget from 1000 to 4000 does
not change either FMM result. The true local flag therefore does not certify
the existing analytic-control tolerances (2.5e-5 s and source vector norm
3e-6 s/km). No new
field acceptance rule is introduced here.

`midpoint_review.json` independently checks the source and all hashes of
the separate `initial_ray_first_arrival_003_9291_midpoint001` calculation.
An arithmetic midpoint preserves the curve and action; its positive-depth
tent supplies an additional descent direction without snapping a knot to
the interface. For a horizontal edge of length L in a smooth depth profile,
this first variation is L times the slowness depth derivative divided by
two. The actual control uses the saved slightly nonhorizontal coordinates
and the exact piecewise-affine integral. This is evidence about additional
polyline freedom, not a complete continuous-path stationarity certificate.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 data/development/initial_ray_first_arrival_003_9291_reference001/check.py
```

The helper uses copied inputs and a frozen reference source. Their original
paths and hashes are in `provenance.json`. Time ranking uses ordinary floating
point; the reference's completeness and distance certificates are retained
in `result.json`. This reference applies to the saved monotone 1D initial
model and does not establish results for later three-dimensional models.

The later `fine_path_review.json` compares four saved controls with the same
reference and native identities. The FMM field stays at 0.5 km while path
spacing changes to 0.125 and 0.0625 km. Selected FMM time errors are 13.0745
and 3.26671 microseconds, with source-vector error norms 2.66245e-6 and
7.87554e-7 s/km; both satisfy the existing analytic controls. Component
maxima 2.10691e-6 and 5.93061e-7 are also retained descriptively. The 0.125 km
straight start has source-error norm 3.81288e-6 s/km and does not satisfy that
control, despite its true local flag. All four unchanged optimizer-parity
checks pass. Reproduce these comparisons with `check_fine_paths.py`; no
ray optimization occurs.
