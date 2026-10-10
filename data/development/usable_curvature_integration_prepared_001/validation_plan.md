# Bounded validation plan after source review

The candidate changes only the outer action sum and curvature/direction arithmetic. A future validation snapshot must contain the full `after/src` roster, unchanged CMake file, the exact selected diagnostic sources and compiler/flags. Do not change the frozen long-running binaries or substitute this candidate into an existing run manifest.

## Existing evidence that can be reused

- `usable_ray_curvature_controls_001`: 183 checks in each build cover finite/representable admission, current-metric pivots, scaling and two-loop intermediates, fallback/reset and exceptions. Four actual finite trajectories are byte-identical to C. The component checks include D in both builds; they are not 366 distinct candidate behaviors.
- `loma_usable_curvature_native_001`: the full saved raw Candidate and its metadata were replayed with D, without a new FMM field. The complete source/model partials, path and history preserve all five C tables. The production candidate core/helper are byte-identical to that numerical implementation after normalizing only the include path and descriptive comment. No second single-ray audit is needed to establish that mapping.
- The existing cone-QP implementation, FMM field update/extraction and receiver cache are untouched. Their published component evidence remains relevant to those unchanged components.

## Minimal integration checks

1. Fresh CMake build and `dd validate FRESH_OUTPUT` exercise the actual production entry, analytic travel times/derivatives and existing matrix checks. Keep the existing thresholds and preserve any failure.
2. Compile and execute `diagnostics/check_inversion_ray_gate.cpp` against the full candidate source at the original O3/OpenMP flags. This invented component checks current/trial/final rejection and preserved accepted/candidate state, with no real inversion. Compile `diagnostics/check_external_inputs.cpp` against the same snapshot to retain native cross-epoch row and metadata coverage. The numerical row loader and guard are unchanged, so new broad data acquisition is unnecessary.
3. Run the existing small analytic first-arrival controls with production-entry comparisons:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py --variant usable_curvature_001 --refine --order 2 --closed-seed-cells --production-entry
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_rotated_affine.py --variant usable_curvature_001 --production-entry
```

These retain the 44-comparison/37-gate layered refinement and six oblique-affine comparisons/72 checks, including actual production source derivatives, local flags and seed-selection parity. No tolerance change or global certificate is implied. They are bounded invented fields, not another real full-cohort preflight.

The first-arrival runners currently list snapshot dependencies explicitly. Before those commands can execute against the candidate, add `src/usable_ray_curvature.hpp` to each frozen source/archive roster. This is a packaging dependency only; the source generator already copies the complete optimizer body. The older `run_forward_integration.py` also predates other current main.cpp headers, so a fresh use must freeze the complete `src` roster, not only add the new helper. No runner was edited here.

If thread/cache routing needs an additional integration check, use the existing invented forward/cache or refined-cache batching component at one/four threads, freezing the full candidate source. The old historical parity drivers that assert unchanged kernels against Hayward003/004 are not evidence for this numerical change and must not silently reuse their original equivalence claim.

## Native replay and remaining gates

The only exact cached-initialization native comparison established here is row3426, whose raw Candidate, post-resampling frame and metadata were saved and checked. A saved final polygon from another ray is not automatically the same raw initializer; treating it as a new seed would be a separately labeled experiment. No receiver fields, full native support or inversion should be rerun solely for another identical D/C single-ray table check.

Future numerical runs need a new manifest/binary and their prescribed full forward and final diagnostics. Existing full-cohort accuracy counts remain historical observations of the previous kernel. The candidate makes no general first-arrival, endpoint-discretization, exact-curvature-sign or nonsmooth-stationarity claim.
