# Invented trilinear endpoint shooting controls

This is a completed numerical candidate experiment, not a native correction.
All coordinates and velocities are invented. No station/event identities,
production files, native ray calculation, inverse solve or Git operation enter
this package. The [predeclared proposal](../loma_endpoint_connector_next_step_001/shooting_control.md)
and exact executed source are copied under `source/`.

The same original eight-node trilinear velocity, Hamiltonian ODE, action and
nodal kernels are used for every model. There is no affine dispatch. Direct
and one-bottom-guide stationary candidates include explicit zero-first-cap,
zero-last-cap and both-zero-cap systems. The selected value is the least action
among the successfully matched admissible roots, not a certified global value.
Exact affine connectors are independent comparison oracles only.

## Recorded results

The execution completed in 551 seconds. Both declared ODE settings completed
20 baseline cases and 80 perturbation comparisons each. All 40 baseline time
and full endpoint-vector comparisons pass the existing 25 microsecond and
3e-6 s/km limits. The largest time, source-vector and receiver-vector errors
are respectively 1.96534e-11 s, 1.02297e-13 s/km and 1.02296e-13 s/km.
These include positive guides, both endpoint orientations, a vanishing guide,
both-bottom endpoints, homogeneous oblique rays and weak/negative gradients.

For source displacements 2^-8, 2^-12 and 2^-16 km, numerical excess action
divided by the independent affine excess is 1 to within 4.4e-9. These controls
distinguish the curved candidate from the scalar polygon family's 6.066%
leading excess discrepancy. Ratios based on subtraction of total actions at
still smaller displacements are not used as coefficient-accuracy evidence.

All 160 perturbation comparisons have a selected candidate. The 80 original
nodal-column comparisons use q_j = -log(v_j), so their kernels are
-v_j dT/dv_j. Maximum central-difference discrepancy is 1.60383e-12 s at
h = 2^-16 and 6.57995e-10 s at h = 2^-20. Shrinking the perturbation worsens
the discrepancy; this is evidence of a numerical floor, not a convergence
certificate. Tightening the ODE settings changes these differences by at most
2.18279e-11 s. The 56 central endpoint comparisons have maximum discrepancy
6.13131e-8 s/km, below 3e-6 s/km.

**All 24 raw inward bottom-normal secants exceed 3e-6 s/km.** They are preserved
as finite-step failures against that limit. For example, the affine receiver
secants have magnitudes 6.26465e-5, 1.56612e-5 and 3.90038e-6 s/km as h falls
from 2^-20 through 2^-24 to 2^-28 km, while the limiting branch momentum is zero.
Across all eight ladders, reducing h by 16 reduces the discrepancy by factors
3.9623 to 4.0154. This supports the predicted square-root truncation trend;
it does not turn the raw discrepancies into passes. The smallest mixed-model
secants reach 3.96185e-6 s/km. The largest change between ODE settings is
1.86265e-9 s/km. No finite-difference extrapolation or forced normal zero is used.

## Evidence and limits

`invented_inputs.json` declares the cell, cases and settings. `execution.json`
records the command, UTC times and Python/NumPy/SciPy versions.
`baseline_results.json` retains both candidate attempts and sampled paths;
`perturbations.json` retains every perturbed candidate, failure and selection.
`comparisons.json` contains independent affine oracle values.
`summary.json` pins three inputs and eight original output/source files.
`read_saved.py` and `saved_readback.json` subsequently verify those pins and
reconstruct the 160 stored comparisons without ODE/root evaluation.

The mixed unperturbed branches' full trajectories/actions were not saved.
Their baseline kernel/momentum components and secants are retained in each
comparison, but the saved-only readback cannot independently reintegrate those
base branches or reconstruct their one-sided secants from a separately saved
base action. This limitation is explicit in the readback.

The solver attempts one root per topology. Other contacts, faces, corners and
unfound roots remain outside this roster. Box, invariant and reaction tests
sample the numerical trajectories; they are not rigorous enclosures. Duration
bounds use the cell diagonal divided by the minimum positive nodal velocity.
Local contact estimates are guesses. Polynomial evaluation outside the cell
is permitted only for rejected root trials, not for physical candidate paths.
The guide precheck rejects a strictly negative normal derivative everywhere
on the bottom face; mixed-sign faces instead face the actual-arc reaction test.

These results support further review of this action-consistent local candidate.
They do not establish completeness, a differentiable global envelope, native
accuracy, or a production correction. No native execution is authorized here.

## Rebuild

From the integration worktree, choose a fresh output path:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=tmp/matplotlib tmp/waveform_env/bin/python -u diagnostics/check_endpoint_shooting.py --output data/development/loma_endpoint_shooting_controls_NEW
```

The saved-only checker also requires a fresh output copy without an existing
`saved_readback.json`; it accepts that directory and the repository root as its
two arguments. Preserve this package unchanged when rebuilding.
