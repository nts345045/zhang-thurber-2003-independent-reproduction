# Explicit interface guide comparison for the 104 Loma diagnostic rays

The x-only sandwich admits a simple candidate: two Snell legs meet the x=0,
v=6 km/s interface and connect along it. This calculation evaluates that family
for every declared diagnostic ray. It does not enumerate all ray branches or
certify first arrivals. All 724 events, 52 receiver placements, 104 diagnostic
rays and their identifiers remain unchanged; no observation generation or
inversion is performed.

The candidate is applicable to 38 of the 104 rays. For 43 rays, the transverse
y-z separation is shorter than the two critical legs require. Another 23 have
an endpoint at x<0, where a finite critical leg cannot traverse the constant
6 km/s plateau. These labels describe this candidate family only. They do not
exclude a ray or change the live diagnostic.

## Captured comparison

This immutable comparison contains **65 of 104 completed diagnostic rows**,
numbered 0 through 64. The live convergence and identity streams flush
independently. Only their complete common prefix is joined; each original
captured prefix and its hash is saved. Later rows require a separate comparison.
Of these 65 rays, 23 have an applicable guide candidate. It is faster than 19
saved solutions at each spacing and slower than the other four.

Two production solutions satisfy their local stopping rule while exceeding the
explicit candidate by more than 20 milliseconds:

| Diagnostic row | Receiver | Production excess (ms) | Refined excess (ms) | Production local flag | Refined local flag |
| --- | --- | ---: | ---: | --- | --- |
| 49 | NC.HLT..EHZ | 25.693171 | 0.166394 | Converged | Not converged |
| 57 | NC.HQR..EHZ | 20.764619 | 0.186569 | Converged | Not converged |

Both use event `quakeml:NC.anss.org/Event/NC/20091683`, origin
`quakeml:NC.anss.org/Origin/NC/2660124`. The receiver epochs are
1989-05-19T21:20:00 through 1990-02-14T21:58:00 for HLT and
1989-07-11T19:55:00 through 1990-03-24T19:55:00 for HQR. Their FDSN identifiers
are `FDSN:NC_HLT__E_H_Z` and `FDSN:NC_HQR__E_H_Z`. Production selects the direct
seed for HLT and the FMM seed for HQR. Refinement selects FMM for both, but each
refined path exhausts its 1000-iteration budget. The comparisons demonstrate
that local convergence does not establish the first arrival. They do not
identify the complete set of missing branches or override the simulation gate.

The maximum positive excess over the candidate is 25.693171 ms at 0.5 km
field/path spacing and 0.186569 ms at 0.25 km. A negative excess means the saved
path is faster than this particular candidate. It is expected for an incomplete
candidate family and is retained without relabeling.

## Formula and checks

`diagnostics/first_arrival_1d_reference.py` supplies the independent exact
piecewise-linear Snell leg formulas. The full monotone-profile enumerator is
not called on the nonmonotone sandwich. With transverse slowness p=1/6 s/km,
let X_a and X_b be the two leg distances and R the y-z endpoint separation.
The guide length is L=R-X_a-X_b, and its travel time is
T=T_a+T_b+L/6. Each leg remains between its endpoint and x=0. Transverse
coordinates advance monotonically along the endpoint line. A nonnegative
L therefore keeps the entire candidate in the saved convex model box.

Applicability uses exact rational values derived from the binary64 inputs,
or outward interval bounds where radicals are irrational. A guide-length sign
that these bounds cannot resolve is retained as unresolved, rather than clipped
with a tolerance. The computed binary64 R is the distance input to this test.
Candidate times and derivatives use ordinary floating-point arithmetic; this
is not an interval certificate of time ordering.

Six invented controls cover a pure guide, coincident endpoints, a negative-x
endpoint, a short offset, a singular critical flat leg, and an unresolved sign.
All pass. Reciprocity is checked for applicable nondegenerate rays. The 114
source-derivative central differences at a 1e-5 km step have maximum absolute
error 2.55e-10 s/km. These derivatives belong to this candidate family. They do
not certify derivatives of the saved nonconverged paths or tied first arrivals.

## Provenance and rebuild

`identified_candidates.csv` retains all 104 sample records and their full
provider metadata, SEED/FDSN identities, native epochs and source hashes.
`identified_comparison.csv` appends the 65 saved numerical results and candidate
differences. `captured_convergence.csv` and `captured_identifiers.csv` preserve
the complete raw CSV prefixes read from the live run. `inputs/` preserves the
four frozen geometry tables; `source/` preserves the exact calculation and
independent leg implementation used for this capture. `summary.json` records
all hashes, captured byte counts, controls and counts. The derivative table's
matching `.identifiers.json` attaches each row to its event, origin, channel,
epoch and authoritative source hashes.

The underlying solver is frozen Loma run 001, commit
`bff2a451640a40bfdb73c92c536ef354c3c55c08`; its unchanged binary and source hashes
are recorded. No solver is rerun here. The maintained helper additionally writes
the derivative identities inline, verifies the frozen source files against the
run manifest, and gates derivative differences at 1e-8 s/km. The capture's
original source is retained, so these later checks are not attributed to it.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_loma_guides.py \
  --output data/development/loma_geometry_preflight/all_guides_NEW
```

Use a fresh output directory. This command captures whatever complete prefix
exists at invocation; it does not overwrite this 65-row evidence. The live
104-ray diagnostic continues independently, and simulation remains subject to
its unchanged convergence and initialization gates.
