# Terminal Loma geometry diagnostic 001

All 104 declared nearest/farthest diagnostic rays completed, with 24 endpoint
finite-difference components. Every native event/origin/channel/epoch join and
frozen input hash passed. Initializers succeeded for all 104 rays at both
settings and all 48 perturbed rays; no numerical output is nonfinite.
The complete authoritative geometry remains 724 events and 52 receiver
placements. This diagnostic does not evaluate all 37,648 pairs.

The settings fail the scientific acceptance gate. Each spacing has **31 local
convergence failures**. At 0.5 km, these comprise 30 farthest and one nearest
source; at 0.25 km, 29 farthest and two nearest sources. Their union contains
34 distinct identified rays. `scientific_review.json` preserves all of them,
including resource IDs, SEED/FDSN codes, epochs, source hashes and numerical
flags. No failure is dropped and no stopping rule is softened.

The largest time change under refinement is **0.0370261284 s**, diagnostic row
88: event `quakeml:NC.anss.org/Event/NC/256583`, origin
`quakeml:NC.anss.org/Origin/NC/2645094`, channel `NC.JSC..EHZ`
(`FDSN:NC_JSC__E_H_Z`), epoch 1989-05-10T21:40:00 through
1990-10-04T20:15:00. The production path reports convergence without an update,
but the refined path finds a faster branch and exhausts 1000 iterations.

The independent [explicit guide comparison](../all_guides_002/README.md)
constructs a feasible earlier path for 23 rays at each spacing. Three production
paths report local convergence while exceeding that candidate by 20.765 to
37.159 milliseconds. The guide is a feasible comparison, not a proof of complete
branch enumeration. Its applicability labels do not change the diagnostic
sample or reproduction cohort.

The largest endpoint finite-difference discrepancies are 1.2592e-3 s/km at
production spacing and 1.2564e-3 s/km after refinement. Both arise from row 5,
where the unperturbed and perturbed paths are unconverged. Only 12 of the 24
components have all four local flags true (production, refined, plus, minus).
Even among those, discrepancies reach 1.5426e-4 and 1.5297e-4 s/km. The step is
0.01 km. These differences include path/branch error and finite-difference
truncation; they are not a certificate of endpoint sensitivity accuracy.

No synthetic observations, full arrival table, matrix preflight or inversion
was launched. The current ray settings must be resolved before generation.
The earlier [20-row snapshot](partial_findings.json),
[65-row guide capture](../all_guides_001/README.md), and
[identified row-5 integration/optimizer check](../row005_audit001/README.md)
remain unchanged. The row-5 check verifies integration accuracy on its retained
paths and shows continued optimization progress; it does not diagnose every
failure in this terminal sample.

## Frozen execution and artifacts

The run used commit `bff2a451640a40bfdb73c92c536ef354c3c55c08`, frozen source under
`source/`, and unchanged inputs under `data/loma_lom_001/` from the repository
root. Field/path spacings were 0.5/0.5 km and 0.25/0.25 km, each with 1000
iterations, closed second-order FMM initialization, four configured threads,
and a 128 GiB address-space limit. The geometry loop executes serially. Runtime
was 2509.03 s (41.82 minutes), and peak RSS was 5,421,056 KiB (5.17 GiB).

`summary.json` records build/run commands, source/input/output/binary hashes,
compiler/libraries and exact identity checks. `run_loma_geometry_preflight.py`
is the runner used for this launch. `launch_review.json` records the actual
runtime checks and the later maintained-runner improvements. The maintained
runner refuses optimized Python, checks sample index bounds and records a child
command before launch; those later changes are not attributed to this snapshot.
`compile_*` and `geometrycheck_*` logs and `resource_usage.txt` are retained.
The executable is rebuilt from the preserved source rather than versioned.

The run directory contains the nine unchanged prepared inputs and three raw
numerical diagnostic CSVs. Both numerical tables join to
`geometry_truth_ray_identifiers.csv` using `(diagnostic_row,event,station)`;
that identity table contains every provider ID, native epoch and coordinate.
The terminal guide directory also preserves an inline identified 104-row
comparison. Scientific acceptance is recorded separately in
`scientific_review.json`; process exit zero means the diagnostic completed.
