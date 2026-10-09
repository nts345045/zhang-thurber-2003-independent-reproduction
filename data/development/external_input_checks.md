# Identified external inputs and resolution algebra

These records contain component checks and an initial-model numerical preflight.
They contain no inversion results. All tiny solver fixtures use invented records
labeled as such, not purported provider observations.

From the repository root:

```sh
mkdir -p tmp/external_input_checks
TMPDIR="$PWD/tmp" g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -fopenmp diagnostics/check_external_inputs.cpp -lstdc++fs -o tmp/external_input_checks/check_cross_epoch
TMPDIR="$PWD/tmp" g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -fopenmp src/main.cpp -lstdc++fs -o tmp/external_input_checks/dd_cross_epoch
OMP_NUM_THREADS=2 tmp/external_input_checks/check_cross_epoch tmp/external_input_checks/cross_epoch_checks.json
OMP_NUM_THREADS=2 tmp/external_input_checks/dd_cross_epoch validate tmp/external_input_checks/cross_epoch_validation
OPENBLAS_NUM_THREADS=1 python3 -c 'import resolution_hayward; print(resolution_hayward.validate())'
```

The C++ fixture checks quoted CSV metadata, empty location/end-epoch fields,
missing/mismatched identities, index bounds, sparse ray support, catalog-only
weighting, diagnostic identity mappings, and an unweighted absolute-only
Jacobian against analytic homogeneous derivatives. Results are recorded in
`external_input_checks.json`. The latest report also checks differential
observations whose two receiver records have the same channel and exact position
but different native epochs. The checks cover both receiver indices, analytic
prediction and source derivatives, a model derivative against finite-difference
action, diagnostic identity mappings, and rejection of inconsistent coordinates,
channels, epochs, and indices. Missing `station_j` retains legacy behavior;
explicit differential indices must be valid.

`cross_epoch_validation.csv` preserves all 48 passing numerical checks from the
same completed development run. `cross_epoch_validation_ray.csv` contains its
invented sandwich-medium ray. `external_input_checks_provenance.json` records
the commands, source and binary hashes, and original temporary result paths.
The three saved result files are exact copies; the earlier component report
without cross-epoch tests has been replaced. The commands above write new C++
results under `tmp/` without replacing this evidence.

`hayward_initial_ray_summary.json` summarizes the identified initial-model
diagnostics in `../hayward/` and records their hashes and input hashes. At
0.5 km production spacing and 0.25 km refined spacing, with 1000 maximum
updates, all 32 sampled rays converge at both spacings. The maximum travel-time
difference is 0.1065 ms (RMS 0.0370 ms). For eight sampled rays and three source
coordinates, centered finite differences with a 0.01 km half-step disagree with
the production derivatives by at most 8.155e-5 s/km. These flags satisfy the
existing combined time-change/gradient criterion; none of the saved gradient
norms is below the stricter 1e-7 s/km gradient-only threshold. The sample covers
32 of 14,262 used native event/receiver pairs. It supports beginning the
configured inversion, while updated models and unsampled rays still require
convergence assessment. All diagnostic identities remain attached through
`../hayward/initial_ray_identifiers.csv`.

The Python calculation compares source-block elimination with a direct full
joint-matrix inverse, including a source column with no data sensitivity. It
uses the same tiny-column scaling fallback as the C++ solver. Results are in
`resolution_algebra_checks.json`. This establishes the small-matrix algebra,
not ray accuracy, noise calibration, or field-model resolution.

`simulate_checks.json` records additional development checks of `dd simulate`:
analytical travel times, identified geometry, top-grid extension, and unchanged
baseline random generation with zero and nonzero noise. Those disposable
simulation fixtures are retained under `tmp/external_input_checks/` locally;
their complete rerun harness is not packaged here. The 48 existing numerical
checks also passed after the simulation command was added.
