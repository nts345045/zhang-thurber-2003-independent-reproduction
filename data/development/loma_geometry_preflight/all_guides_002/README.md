# Terminal explicit guide comparison

This is the complete 104-ray counterpart of the preserved
[65-ray comparison](../all_guides_001/README.md). It uses the same explicit
x=0, v=6 km/s guide and independent piecewise-linear Snell legs. The formulas,
finite-box argument, sign checks and scope are unchanged. No production rays
were rerun, no observational data were queried, and no simulation was launched.

The candidate is applicable to **38 of 104** diagnostic rays. The other 66 remain
in the table: 43 have insufficient transverse separation for these two critical
legs, and 23 have a negative-x endpoint in the constant-speed plateau. These
labels apply to this candidate family only, not to the validity of a ray or its
membership in the reproduction cohort.

For 23 applicable rays, the candidate is faster than the saved result at both
spacings. For the other 15 it is slower; the guide is not asserted to be the
first arrival. Three production paths report local convergence despite a
feasible earlier candidate:

| Row | Event suffix | Receiver | Production excess (ms) | Refined excess (ms) |
| --- | --- | --- | ---: | ---: |
| 49 | NC/20091683 | NC.HLT..EHZ | 25.693171 | 0.166394 |
| 57 | NC/20091683 | NC.HQR..EHZ | 20.764619 | 0.186569 |
| 88 | NC/256583 | NC.JSC..EHZ | 37.158685 | 0.132557 |

The maximum production excess is **37.158685 ms**; the maximum refined excess
is **0.186569 ms**. All three refined paths exhaust 1000 iterations without
local convergence. Their complete event/origin IDs, FDSN source identifiers,
epochs, source hashes, direct/FMM candidate times and selector flags are in
`identified_comparison.csv` and the linked
[terminal scientific review](../001/scientific_review.json).

All 104 native sample records remain byte-identical to the earlier candidate
calculation. Every original event, channel, epoch, source URL/hash and coordinate
is preserved inline in `identified_candidates.csv` and `identified_comparison.csv`.
The 114 source-derivative checks also carry the event/origin/channel/epoch IDs
inline; their maximum error is 2.55e-10 s/km at a 1e-5 km central-difference step,
well within the stated 1e-8 s/km diagnostic gate. Six invented controls and
reciprocity checks pass.

`summary.json` records the completed solver source/binary hashes, four exact
input tables, full captured convergence/identity tables, calculation source
snapshots, checks and result hashes. `inputs/` and `source/` preserve those
contents. The helper verifies the frozen solver source and all native metadata
before calculating. Time ordering uses ordinary floating-point arithmetic;
no interval certificate of the globally earliest time is claimed. Candidate
source derivatives belong to this family, not necessarily the first arrival.
The raw numerical solver times retain their original 12-significant-digit
precision.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_loma_guides.py \
  --output data/development/loma_geometry_preflight/all_guides_NEW
```

Choose a fresh output directory. This complete comparison does not overwrite the
earlier partial evidence or change any convergence/generation gate.
