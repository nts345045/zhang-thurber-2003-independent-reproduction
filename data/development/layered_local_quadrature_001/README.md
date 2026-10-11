# Local quadrature on selected continuous rays

The isolated local-coordinate kernel passed **58 affine, 24 full-nodal and
4 tiny-partition checks**, then completed both previously failing selected-ray
integrals. This package preserves those closed outcomes and the earlier
exception-only localization. It does not replace a production ray solver.

See [RESULTS.md](RESULTS.md) for measured discrepancies and limits,
[scientific_validation.json](scientific_validation.json) for exact saved
arithmetic, and [manifest.json](manifest.json) for scientific file/input hashes.
[HISTORICAL_DESIGN.md](HISTORICAL_DESIGN.md) is the byte-preserved proposal as
written **before** execution; its unexecuted wording records that historical
stage. The results here record the subsequent completed runs.

Each unchanged stored partition `[a,b]` uses local `q` in `(0,1)` and measure
`L(b-a)dq`. Near the piece end, a backward increment avoids adding a microscopic
Gauss displacement to a global parameter near one. Circular endpoints are
recomputed from the original defining parameters. This changes rounded
arithmetic; it is not bitwise equivalence of forward and backward curves.
Original face roots, point-based cells, physical-box/basis guards and all
trilinear nodal kernels remain. No interval is dropped, snapped or clamped.

`source/` contains the tested kernel, observer, unchanged construction/control
dependencies and new independent tiny-mass fixture. `diagnostic_source/` holds
the preceding exception-only kernel. The three [diffs](diffs/) expose these
changes against the already published sources. Duplicated small headers and
controls ensure quoted C++ includes select the intended kernel during replay.

The original numeric inputs/specifications are reused from
[`../layered_reference_selected_curves_001/inputs/`](../layered_reference_selected_curves_001/inputs/).
The two [identifier companions](identifiers/) are byte-identical to that
published package. They bind every result to full event/origin resources,
receiver SEED/FDSN identifiers, metadata epochs, model/coordinate context and
existing selected-reference records. Valid blank location codes and empty
catalog-use inventories are preserved: these are reference-selected curves on
authoritative geometry, not newly measured arrival observations. Each companion
applies to the same case under both `diagnosis/` and `native/`.

## Replay from the repository root

Requirements are a C++17 compiler and the existing committed input package.
The observed platform used binary long double with 64 significand bits. The
floating regression checks are not portable error certificates. Choose a fresh
output directory; these commands create all generated files there.

```sh
set -eu
PKG=data/development/layered_local_quadrature_001
ORIGINAL=data/development/layered_reference_selected_curves_001
OUT=tmp/FRESH_layered_local_quadrature
test ! -e "$OUT"
mkdir -p "$OUT/build" "$OUT/results" "$OUT/tmp"
export TMPDIR="$PWD/$OUT/tmp"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 LC_ALL=C
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic "$PKG/source/check_affine_arrival.cpp" -o "$OUT/build/affine"
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic "$PKG/source/check_curved_integrals.cpp" -o "$OUT/build/full_nodal"
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic "$PKG/source/check_tiny_partition.cpp" -o "$OUT/build/tiny_partition"
"$OUT/build/affine" > "$OUT/results/affine.json"
"$OUT/build/full_nodal" "$PWD/$OUT/results/full_nodal_summary.json" > "$OUT/results/full_nodal.jsonl"
"$OUT/build/tiny_partition" > "$OUT/results/tiny_partition.json"
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic "$PKG/source/observe_reference_curve.cpp" -o "$OUT/build/observer"
for CASE in lom_24104 lon_8670; do
  cp "$PKG/identifiers/$CASE.json" "$OUT/results/$CASE.result.json.identifiers.json"
  "$OUT/build/observer" "$ORIGINAL/inputs/$CASE.input" "$ORIGINAL/inputs/$CASE.curve" "$OUT/results/$CASE.result.json"
done
```

For the historical failure variant, copy the original package's constructor
and observer into a separate fresh source directory, with
`diagnostic_source/layered_curved_ray.hpp` named `layered_curved_ray.hpp` there.
Compile that observer with the same flags. Supply the same original inputs
and complete output companions. Both saved outcomes here returned **exit 1**
and `integration_failed`; a failed integral must not be relabelled as success.
This optional diagnostic replay is separate from the completed local-q runs.

Neither replay calculates a new reference, optimizes a ray, validates all
native nodal entries against an independent oracle, or certifies first arrival
or optimized-source derivatives. Runtime logs, executables and machine/process
records remain outside this scientific delivery.
