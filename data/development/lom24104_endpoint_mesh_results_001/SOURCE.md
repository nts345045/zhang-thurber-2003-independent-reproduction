# Exact numerical source for the six-mesh replay

The `source/` mirror contains the exact 13 C++ and GMP source/header files used by the closed 16-pair observer. Every byte is checked against the executed preparation's source pins; `source_manifest.json` records each origin, size and SHA-256. Its `tmp/` names preserve historical relative include paths **inside this package**. They do not require the original workspace or its process/approval records. No frozen source was edited. Four original GMP license texts accompany the two GMP headers.

The translation unit is `source/tmp/integrated_face_memory16_source_001/observe_accelerated.cpp`. Six solver files there include the seven inherited files under `source/data/development/integrated_face_ray_candidate_001/`. Preserve this layout: two headers use `../../data/development/...` includes. Comments describing earlier source drafts are unchanged historical text.

## Build and arithmetic requirements

The executed build used GNU C++17 with `-O3 -Wall -Wextra -Wpedantic -fopenmp -ffp-contract=off`, linked to GMP 6.1.2 and the GCC 8 filesystem support library. From the repository root, the equivalent build command uses a fresh project-local output and temporary directory:

```sh
mkdir -p tmp
mkdir tmp/FRESH_endpoint_mesh_build && \
LC_ALL=C TMPDIR="$PWD/tmp/FRESH_endpoint_mesh_build" OMP_NUM_THREADS=1 \
c++ -std=gnu++17 -O3 -Wall -Wextra -Wpedantic -fopenmp -ffp-contract=off \
  data/development/lom24104_endpoint_mesh_results_001/source/tmp/integrated_face_memory16_source_001/observe_accelerated.cpp \
  -lgmp -lstdc++fs -o tmp/FRESH_endpoint_mesh_build/observe_solve
```

A compatible GMP 6.1.2 library must be available to the linker and loader; a different installed GMP version is not silently accepted. No binary or runtime library is distributed here. The copied GMP wrapper selects the included x86-64 header. Other architecture headers are deliberately absent.

`exact_cell_types.hpp::format()` retains these runtime guards:

- IEEE binary64 input: 8-byte `double`, radix 2 and 53 significand bits.
- Extended `long double`: radix 2, 64 significand bits, exponent limits -16381 and 16384, subnormals and round-to-nearest mode.
- GMP headers and runtime version 6.1.2, 64-bit limbs and no nail bits.

Use `LC_ALL=C`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` and `MKL_NUM_THREADS=1`, with temporary files in the fresh output tree. The original source and inputs are exact, but a different compatible compiler/math runtime is not asserted to reproduce every optimization history bit for bit. Incompatible arithmetic must fail the existing guards; it must not be repaired by changing those guards.

## Observer contract and scope

The unchanged command is:

```text
observe_solve INPUT OUTPUT_PREFIX CASE_ID 1000 24 10000
```

The last three arguments retain the 1,000-update limit, 24 halvings and 10,000 support sweeps. The compiled history limit is 16 pairs. Each of the six packaged `inputs/` files starts independently. Before invocation, all six output suffixes (`initial.csv`, `final.csv`, `attempts.jsonl`, `accepted_paths.csv`, `summary.json`, `acceleration.jsonl`) require their complete `.identifiers.json` companions. The portable wrapper owned by the results package handles these companions and fresh destinations; invoking the observer without them must fail.

This source transport does not compile or execute the solver, regenerate inputs, replay controls, or perform interval/reference calculations. Saved reference intervals remain explicit scientific inputs. The native optimization replay and any separate final interval reproduction must be described separately; scalar agreement is not an interval certificate or an optimized-source/first-arrival claim.
