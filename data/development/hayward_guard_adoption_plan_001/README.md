# Reusing Hayward004 evidence with a separately frozen inverse guard

This is an adoption plan, not an inverse launch. Hayward004 still has a live
sampled-ray stage. Its old `--phase invert` route points to the original004
binary, which lacks the new per-evaluation guard and must not be used for the
next inversion.

`comparison.json` verifies all 13 immutable objects in the004 run manifest.
Seven numerical/CSV headers and `CMakeLists.txt` are byte-identical between the
frozen004 source and the reviewed guarded source. The complete definitions of
`configured_trace`, `prepare_receiver_fields`, `rays`, `read_events`,
`read_grid`, `observations`, `validate_identities`, `linearize`, and `smooth`
are also byte-identical. This comparison includes the actual field preparation,
native support/epoch routing, ray selection and inverse row conventions.
The guarded `src/main.cpp` hash is
`8a6f1ea8ea8c37ec71fe01a8971cd63227895192411c91ccc3b82f20727be4ae`.

The main-file differences have three separate roles. Analytic-truth simulation
support is not invoked by a Hayward inversion. Optional matrix-preflight
exports and receiver batching affect diagnostic bookkeeping; batch zero is
the original all-at-once path and remains the004 default. The inversion guard
wraps the unchanged ray calls, validates their existing finite/domain/exact
endpoint/initializer/local flags, and stops before using an invalid Jacobian
or objective. It preserves failed candidate and last-accepted states
separately. On a valid evaluation it does not alter a ray, weight, source,
model, row, objective, step or tolerance. Final output is delayed until the
final forward evaluation passes.

These source comparisons support reuse of the mathematical evidence for the
**same initial model, geometry and ray support**. They do not make the new
executable the old one, establish bitwise compiler equivalence, or certify
later 3D models. The guard fixtures004 preserve actual failure and successful
output checks, but they use `-O2`. Hayward004 used CMake with
`-std=gnu++17 -O3 -Wall -Wextra -Wpedantic -fopenmp`; those build settings
must be retained and checked in the new frozen build.

A minimal safe launcher should perform the following sequence:

1. Require the terminal004 execution ledger, every recorded preflight hash,
   unchanged native input/config hashes, the full14262-ray continuous-reference
   review, and the independent completed sample/refinement review. The string
   `ready_for_accuracy_review` alone is not acceptance. No new accuracy limit
   should be invented or weakened to launch an inversion.
2. Copy the exact004 inputs and configuration into a fresh inverse directory,
   for example `data/hayward_first_arrival_guarded_001`. Preserve observations,
   both DD native epochs, source/pick/arrival IDs, all selection manifests and
   inverse settings. Use4threads. The old004 directory, binary, source archive
   and final preflight evidence remain immutable.
3. Build a separate guarded binary from a complete source snapshot. Pin the
   compiler executable/version, CMake, generated compile/link commands,
   dependent runtime library hashes, binary hash, environment and source
   whitelist. Record the earlier004 binary and source hashes as inherited
   evidence, not as the new executable's identity. The004 manifest did not
   pin a historical compiler executable hash; recording it now must not be
   described as a historical measurement.
4. Before adoption, run bounded production-entry controls with the exact004
   and guarded sources built through the same CMake/O3 toolchain. Existing
   invented success/failure fixtures can test successful output parity, failed
   current/trial/final evaluations, unchanged diagnostic mode, native cross-
   epoch IDs, and no final output on failure. Include1/4thread behavior. A
   fresh rebuild of004 may also be compared with its archived binary, but a
   binary mismatch is a finding to explain, not a reason to overwrite it.
   These small controls avoid retracing the entire real cohort solely to
   retest an unchanged numerical operator.
5. Launch the actual inverse command only after the reviews pass, using a new
   exclusive execution ledger and detached process group. Use the tested
   Loma launcher lifecycle: bounded TERM/KILL cleanup, descendant completion
   before final hashes, recorded child exit status and maximum RSS. Do not
   reuse the older driver whose interrupt handling could leave a child live.
6. The first actual inverse evaluation naturally computes the full support
   again to assemble its Jacobian. The new guard checks that evaluation and
   every candidate/final evaluation before use. There is no cached-ray
   substitution. Any failed evaluation terminates that mode with its native
   failure records and candidate/accepted snapshots; it is not success and
   no failed ray or event is silently removed.
7. Preserve method-specific final ray/refinement and source-partial checks,
   native output audits, accepted-step/LSQR histories and scientific review.
   The initial 1D continuous reference does not apply to an updated3D model.
   Local stopping flags still do not establish globally earliest arrival.

The wrapper should permit explicit modes in separate ledgers. Starting with
DD gives one concrete guarded inverse result or failure before committing
resources to other modes. Failure of one mode must not produce an all-methods
completion marker. This choice does not change the intended standard/DD/fixed
1D comparison or authorize omission of a method from the final report.

No source, configuration, binary, input or live process was modified for this
plan. Header and function hashes in `comparison.json` describe the source at
plan creation; any later source difference requires a renewed scope check.
