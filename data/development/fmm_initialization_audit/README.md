# First-arrival initialization experiment

This is an isolated, incomplete numerical correction. The production solver
and the original Hayward inversion runs have not been changed.

The following command records the historical baseline at commit `2d662da`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py
```

The current runner requires a new named variant to preserve this evidence:
`PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py --variant baseline_repeat --order 1`.
It saves separate outputs under `data/development/fmm_initialization_baseline_repeat/`
and archives its exact compilation sources. Optional `--order 2`, `--refine`,
and `--closed-seed-cells` isolate subsequent changes; they do not modify this
historical experiment. Use a fresh variant name for each new calculation.

The runner generates a temporary seeded entry point by copying the existing
ray optimizer body without alteration. It resamples an extracted path at the
requested path spacing, bends both that seed and the original direct seed,
and selects the smaller continuous action. The FMM field's finite-difference
time is recorded separately and is never substituted for that action.
The existing analytic time (`2.5e-5 s`), derivative (`3e-6 s/km`), and homogeneous
test tolerances are retained. This diagnostic command records failed gates
and exits unsuccessfully when any gate fails.

## First-order field

The independent implementation uses a positive-speed Godunov eikonal update
and a minimum heap. It samples slowness from the existing trilinear velocity
model. The exact receiver connects to the surrounding auxiliary cell vertices
through continuously integrated segment actions. Backtracing follows the
interpolated travel-time gradient, with a causal-neighbor descent fallback.
Only the receiver initializes the field; outer faces are not zero-time sources.
Primary written methods and numerical limits are in
[the implementation plan](../hayward_first_arrival_plan.md).

The auxiliary spacing and path spacing have separate roles. The former controls
the search for a first-arrival branch; the latter controls the continuous
polyline approximation and its derivatives. Bending does not guarantee recovery
from a seed in the wrong branch.

## Baseline result

The baseline contains 72 comparisons at auxiliary spacings 1, 0.5, and 0.25 km
and path spacings 0.5 and 0.25 km. All extracted paths succeed, retain exact
endpoints, and lie inside the declared model domain. Every selected ray meets
the existing local optimizer stopping rule. Of 61 accuracy/consistency checks,
51 pass and 10 fail.

The constant-top-layer test's direct/diving crossover is approximately
14.6604462162 km. All three auxiliary grids select a late direct ray at
14.68, 15, and 16 km, with respective time errors 0.000176503, 0.003189637,
and 0.014113381 s. Their source-gradient errors are about 0.0673, 0.0699,
and 0.0777 s/km. These six failed time/derivative checks establish unresolved
branch selection despite agreement among the three grids.

At 20 and 40 km the FMM seed recovers the diving branch. At path spacing
0.25 km the 20 km source-gradient error is `9.11e-6 s/km`, and the 40 km time
error is `2.82e-5 s`, exceeding the retained thresholds. The two remaining
failures are constant-gradient reference checks: a `4.48e-6 s/km` source-gradient
error at 10 km and a `2.84e-5 s` time error at 40 km. Finer path spacing is
needed to distinguish discretization from optimization error in those cases.
Homogeneous, reciprocity, and source finite-difference consistency checks pass.

Thus the current prototype supplies useful alternative paths but is not a
validated general first-arrival solver. No real observations enter this test,
and the effect on individual Hayward rays is still unmeasured. A sequence of
finite candidate paths supplies upper bounds on the continuum minimum, up to
quadrature error; it does not certify that the minimum was found.

`results.csv` records every comparison, `consistency.csv` records unchanged
thresholds and pass/fail values, and `paths.csv` preserves selected illustrative
paths. `summary.json` records failures and source/binary/output hashes. Runtime
columns are measured wall time and need not be byte-identical on rebuilding.
