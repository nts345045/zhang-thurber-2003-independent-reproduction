# Identified external inputs and resolution algebra

These are component checks. No new real-data inversion or authoritative-geometry
reproduction has been run. All tiny solver fixtures use invented records labeled
as such, not purported provider observations.

From the repository root:

```sh
mkdir -p tmp/external_input_checks
TMPDIR="$PWD/tmp" g++ -std=c++17 -O2 -fopenmp diagnostics/check_external_inputs.cpp -lstdc++fs -o tmp/external_input_checks/check
OMP_NUM_THREADS=2 tmp/external_input_checks/check
OPENBLAS_NUM_THREADS=1 python3 -c 'import resolution_hayward; print(resolution_hayward.validate())'
```

The C++ fixture checks quoted CSV metadata, empty location/end-epoch fields,
missing/mismatched identities, index bounds, sparse ray support, catalog-only
weighting, diagnostic identity mappings, and an unweighted absolute-only
Jacobian against analytic homogeneous derivatives. Results are recorded in
`external_input_checks.json`.

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
