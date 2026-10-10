# Hybrid control without active bounds

All 560 checks pass. Four smooth affine rays, forward/reverse at 0.5/0.25 km path spacing, return exactly the original path, time, endpoint derivative, update count and convergence flag when the hybrid optimizer is used. The other checks repeat the reduced principal-matrix fixture; the full cone quadratic has separate exhaustive and KKT tests in `../baseline/`.

The normalized archive includes the exact hybrid `control_optimizer.hpp`, both metric headers, the original core and the fixture source. Rebuild it in a fresh repository temporary directory:

```sh
mkdir -p tmp/cone_hybrid_fixture_source
 tar -xzf data/development/cone_ray_metric_checks/hybrid_no_bound/source_snapshot.tar.gz -C tmp/cone_hybrid_fixture_source
TMPDIR="$PWD/tmp" c++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -include tmp/cone_hybrid_fixture_source/diagnostics/cone_ray_metric.hpp -I tmp/cone_hybrid_fixture_source/diagnostics tmp/cone_hybrid_fixture_source/diagnostics/check_reduced_ray_metric.cpp -o tmp/cone_hybrid_fixture
./tmp/cone_hybrid_fixture
```

Exact executed commands and hashes are recorded in `summary.json`. These are invented fixtures, not observational results or a general first-arrival certificate.
