# Invented reduced-metric component checks

These fixtures test algebra and smooth-ray behavior; they contain no provider observations. The root results preserve the first fallback-only control: 560 checks, zero failures. `pure_metric/` preserves 564 checks, zero failures, with the complete-direction variant. Each folder contains exact source snapshots, relative commands, hashes and a CSV of every check.

The algebra suite compares all 64 masks over two internal nodes and three axes with independent dense Gaussian elimination, repeated with four positive random weight sets (256 comparisons). It also compares the unchanged full inverse for 1–61 internal nodes, tests feasible directions/descent/free residuals for 96 boundary cases, and explicitly constructs a wrong-sign frozen-multiplier case. The latter passes only because the no-release limitation is detected while the direction remains descent; it is not an optimizer-success claim.

The fallback-only no-bound affine paths match the unmodified path, time, derivative, update count and flag exactly in both directions at 0.5/0.25 km spacing. The pure-metric variant instead compares against the exact positive affine-velocity time and endpoint derivative, since its search direction changes even without bounds. Maximum errors are 1.34141e-6 s and 3.09338e-7 s/km, below the existing 2.5e-5 s and 3e-6 s/km limits. Algebra tolerances in the CSV concern floating-point linear solves and do not alter ray stopping.

To rebuild a snapshot without a field run, extract it into a fresh repository temporary directory and compile the included source. For the pure-metric snapshot:

```sh
mkdir -p tmp/reduced_metric_fixture_source
 tar -xzf data/development/reduced_ray_metric_checks/pure_metric/source_snapshot.tar.gz -C tmp/reduced_metric_fixture_source
TMPDIR="$PWD/tmp" c++ -DAUDIT_REDUCED_ALL -O3 -std=c++17 -Wall -Wextra -Wpedantic -I tmp/reduced_metric_fixture_source/diagnostics tmp/reduced_metric_fixture_source/diagnostics/check_reduced_ray_metric.cpp -o tmp/reduced_metric_fixture
./tmp/reduced_metric_fixture
```

For the original snapshot, use its archive in a separate directory and omit `-DAUDIT_REDUCED_ALL`. The generated `control_optimizer.hpp` is included in each archive; no external solver run or authors' code is needed. Archive ownership and timestamps are normalized, and no absolute workspace paths are published.
