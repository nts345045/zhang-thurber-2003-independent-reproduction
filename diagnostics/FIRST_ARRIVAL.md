# Shared first-arrival initializer

The canonical implementation is [src/first_arrival.hpp](../src/first_arrival.hpp).
It includes `core.hpp` and provides `first_arrival::Field` and its extracted
candidate paths. The diagnostic [first_arrival_fmm.hpp](first_arrival_fmm.hpp)
is a small include wrapper, so existing component and analytic fixtures compile
the same implementation used by the forward operator. The move changes the
include path and description only; the numerical implementation is unchanged.

FMM field times initialize paths. Reported physical travel times and derivatives
come from continuous action evaluation and bending. Finite auxiliary spacing and
successful component checks do not certify the globally earliest branch.

The maintained FMM runners record the canonical header as a dependency, together
with the wrapper and `core.hpp`. The initialization and rotated-affine runners
also copy both headers into their immutable source archives. The two Hayward
runners record `forward.hpp`, which is now included by their `main.cpp` dependency.
Historical result directories and their hashes retain the source state used to
produce them; they are not rewritten for this move.

For an invented field component check, choose a new output suffix:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/fmm_field_checks/run_checks.py --variant NEW_COMPONENT --order 2
```

The isolated header-promotion check is recorded separately in
[fmm_header_promotion](../data/development/fmm_header_promotion/). It compiles a
frozen copy of the wrapper, canonical header, core, and component fixture. Its
source snapshot, compiler/run output, result CSV, and hashes are preserved even
if compilation or a component assertion fails.

## Production entry checks

The layered and rotated-affine runners accept `--production-entry`. The default
still uses the generated prototype. With the option enabled, the prototype is
evaluated as a control, then the production optional-seed `trace` and
`trace_first_arrival` entries are evaluated. The analytic gates consume the
production rays. `entry_parity.csv` separately requires exact equality of time,
path nodes, source derivatives, nodal velocity derivatives, integrated nodal
lengths, and optimizer state. It also checks the initializer metadata. No parity
tolerance or weaker analytic gate is introduced.

The source snapshots include `src/forward.hpp` and the small shared
`production_entry_checks.hpp` helper. These commands create separate evidence:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_initialization_audit.py --variant NEW_PRODUCTION_LAYERED --refine --order 2 --closed-seed-cells --production-entry
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_rotated_affine.py --variant NEW_PRODUCTION_AFFINE --level baseline --production-entry
```

The layered refinement retains its 37 analytic gates; the rotated-affine suite
retains its 72 gates. Parity rows include additional source perturbation and
reciprocal calls used by those checks. These suites test the propagation entry
points; receiver-cache lifecycle, command-line behavior, and inversions require
their separate integration checks.

The saved integration variants pass all 37 layered gates with 58 exact parity
calls and all 72 rotated-affine gates with six exact parity calls. The
[aggregate validation record](../data/development/fmm_production_entry_validation.json)
verifies output and source-archive hashes. All non-timing layered result cells
match the historical refinement. In the rotated suite, selected and FMM-bent
results match the historical baseline; nine direct-seed time/gradient cells
differ at roundoff scale after the separate core endpoint change. The current
production and prototype entries agree exactly in both suites. Analytic gates
provide independent accuracy evidence; entry parity itself compares shared
current core/FMM implementations.

## Forward integration and saved diagnostics

Set `ray_initializer 1` and an explicit positive `fmm_spacing` in a run's
configuration to enable the second-order field with closed receiver-cell
seeds. `ray_spacing` controls the independent continuous path discretization.
An absent or zero `ray_initializer` retains straight initialization for the
preserved baseline. No full manuscript inversion has yet used the new entry.
The successful layered example required 0.0625 km auxiliary and path spacing;
coarser grids still miss some near-critical branches. A spacing validated on
one model is not a universal accuracy setting.

The inversion reuses receiver fields only when all model axes, nodal velocities,
and auxiliary spacing agree exactly. Moving sources can reuse the same fields;
velocity line-search trials invalidate them. Coincident native receiver records
share propagation fields while retaining separate numerical indices and metadata.
Fields are constructed serially and read concurrently during OpenMP ray bending.
The cache retains one field per distinct physical receiver for the current model.

Inversion, observation generation, and linearization stop on failed FMM extraction.
`raycheck` instead records extraction failures for inspection. A local optimizer's
nonconverged flag is retained and remains separate from extraction success. The
reported action is the smaller continuously integrated, bent action; the FMM
field value is diagnostic only. Histories report pre-update initializer counts.
Residual tables retain separate i/j initializer information and both native
identities; absolute observations have empty j-side diagnostic fields.

Configured ray checks halve both auxiliary and continuous path spacing, with
an iteration budget of at least 1000. Their CSVs record the two spacings, both
candidate actions, extraction status, selected seed, and local convergence.
Finite-difference rows also retain plus/minus convergence and initializer status.
Refinement agreement alone does not exclude a shared wrong branch.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_forward_integration.py --variant NEW_INTEGRATION
```

The saved [integration check](../data/development/forward_integration_baseline/summary.json)
passes 26 checks covering cache invalidation, distinct indices at coincident
receivers, continuous action selection, preserved failure flags, a manufactured
one-step inversion, and CSV widths. Its separate authoritative fixture preserves
an actual cross-epoch DD and its two absolute picks, all four identity associations,
and both linearized absolute rows. Original inputs are hashed and unchanged.
These two real rays are a metadata/dispatch check, not a representative scientific
accuracy sample. The original [48 component checks](../data/development/forward_core_validation/summary.json)
also pass. Source snapshots and numerical outputs are retained.
Inherited `source_file` values in the small authoritative fixture keep their
original interpretation relative to `data/hayward/`; provider IDs and source
hashes are copied verbatim rather than rewritten as new provider records.

The maintained 186-ray saved-model audit normally rejects solver sources that
differ from its historical comparison. To evaluate the integration sources,
explicitly use `--allow-solver-change`; every changed source hash is recorded.
All input-model, geometry and metadata hash checks still apply. This comparison
does not isolate the FMM stencil from the separate exact-endpoint correction.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_hayward_audit.py --variant NEW_INTEGRATED_FIELD --order 2 --closed-seed-cells --allow-solver-change --production-entry
```

The [saved production-entry comparison](../data/development/fmm_hayward_integrated_production_entry/summary.json)
passes all 186 exact comparisons of selected time, path, source and velocity
derivatives, integrated lengths, optimizer state, and initializer metadata.
Parity flags are saved in the same rows as the original resource IDs and native
channel epochs. All selected endpoints now match exactly. The original i775/k184
local convergence failure remains; the runner therefore correctly exits 1 and
records `failed_checks_recorded`. No extraction, domain, nonfinite, action-increase,
or entry-parity failure occurs. This still is not a first-arrival certificate or
a new inversion. The earlier shared-kernel run and its scope correction remain
saved in `fmm_hayward_integrated_order2_closed/`.
