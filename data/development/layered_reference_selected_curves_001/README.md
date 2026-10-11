# Native reference-selected continuous curves

Both selected curves constructed successfully, but both integrations failed
with **Quadrature node rounded to a partition endpoint**. No native integral
or display output was produced. [RESULTS.md](RESULTS.md) describes these
completed attempts and their limits. The separately completed
[invented controls](../layered_curved_components_001/) remain unchanged.

This small package retains the exact compiled sources, both original numeric
inputs and complete native identifiers, the exact selected reference operands
and full reference records, constructed pieces/joins and failure results.
[manifest.json](manifest.json) binds every scientific file. Binaries, process
records, runtime receipts and session logs are omitted.

The roster is the original LOM24104 bottom-guide ray and LON8670 turning ray.
It is a test of reconstructing and integrating externally selected curves,
not an independent branch-enumeration test or a production solver replacement.
The original grid and fixed source/receiver coordinates are unchanged. The
stored old polygons supply endpoints only. Full event/origin, channel
SEED/FDSN/epoch and simulation metadata remain in the identity sidecars;
blank channel location codes remain valid.

Each curve sidecar contains its complete selected reference record, exact
rational phase speed, turn depth and guide operand, plus saved enclosures.
Reference path names in these records identify the original evidence; the
packaged observer consumes the self-contained supplied operands. LOM's guide
operand is the exact midpoint of its existing interval. LON's phase-speed
representative is retained directly, not recovered from rounded slowness.
The rational tokens are converted to working long double by two strtold
conversions and a division, without a correct-rounding claim.

[METHOD.md](METHOD.md) preserves the reviewed pre-execution design. Its
preparation/future wording is historical; the actual failed outcomes are in
the results. The archived [original preparer](provenance/prepare_original_inputs.py)
documents native/reference joins in the complete research workspace. It is
not needed to run the packaged observer and must not be treated as a
standalone input downloader or reference generator.

## Reproduce the two diagnostic attempts

Requirements are a POSIX environment and a C++17 compiler. The recorded run
used GCC 8.5 and extended-precision long double. Other arithmetic may expose a
different construction/partition outcome; successful execution alone would
not establish native derivative or first-arrival accuracy.

From the repository root, first create an absent project-local directory:

    mkdir -p tmp
    mkdir tmp/FRESH_selected_curve_attempts

Only after that succeeds, compile the unchanged packaged source:

    LC_ALL=C TMPDIR="$PWD/tmp/FRESH_selected_curve_attempts" \
      g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic \
      data/development/layered_reference_selected_curves_001/source/observe_reference_curve.cpp \
      -o tmp/FRESH_selected_curve_attempts/observe_reference_curve

Attach the complete output sidecars before invoking either observer:

    cp data/development/layered_reference_selected_curves_001/results/lom_24104.result.json.identifiers.json tmp/FRESH_selected_curve_attempts/
    cp data/development/layered_reference_selected_curves_001/results/lon_8670.result.json.identifiers.json tmp/FRESH_selected_curve_attempts/

Then run the two independent commands. In the recorded arithmetic each returned
1 after writing its explicit integration-failure result; this is not a passing
test or an instruction to repair and retry it.

    LC_ALL=C OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
      tmp/FRESH_selected_curve_attempts/observe_reference_curve \
      data/development/layered_reference_selected_curves_001/inputs/lom_24104.input \
      data/development/layered_reference_selected_curves_001/inputs/lom_24104.curve \
      tmp/FRESH_selected_curve_attempts/lom_24104.result.json

    LC_ALL=C OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
      tmp/FRESH_selected_curve_attempts/observe_reference_curve \
      data/development/layered_reference_selected_curves_001/inputs/lon_8670.input \
      data/development/layered_reference_selected_curves_001/inputs/lon_8670.curve \
      tmp/FRESH_selected_curve_attempts/lon_8670.result.json

Existing result paths, including dangling symlinks, are refused. Preserve
failures in their fresh destination. This packaging step copied the completed
attempts and did not repeat either integration.
