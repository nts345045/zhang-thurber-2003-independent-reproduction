# Frozen Loma initial-preflight launcher controls

These are invented two-event/two-receiver tests of
`run_loma_initial_preflight.py`. They make no actual Loma forward calculation
or inverse solve. Each completed fixture first runs a fresh frozen C++ analytic
simulation and its exhaustive independent output audit, then exercises a fresh
frozen preflight build using the exact audited input bytes.

The launcher copies the reviewed simulation into a disjoint directory. It
preserves the observation table, full native metadata and truth-defined sample
indices. The explicit assessment settings are path spacing 0.03125 km, FMM
spacing 0.125 km, 1,000 ray updates, four threads, a 128 GiB address-space limit,
and at most four refined receiver fields. It runs the `invert` entry point
only with `matrix_preflight_only 1` and `iterations 1`: iteration/stage zero
returns after the full initial-ray status export and matrix census, before
allocating or solving the full matrix. The history must be empty and no inverse
outputs may exist. It then runs `geometrycheck ... initial`, retaining every
truth-selected sample and feasible source central difference, with exactly half
the production path and FMM spacings.

The four invented full rays, four sample rays and twelve valid finite-difference
components pass their finite/initializer/local checks. The test also checks
native ID and coordinate joins, separate initial source origin corrections,
changed input/review rejection, fresh directory exclusivity, and omission only
of central differences that leave the saved box. False local stopping flags
remain explicit scientific failures; complete diagnostics are still retained.
Every such failure carries event/origin IDs and receiver NSLC/FDSN IDs and native
epochs, including valid empty values.

`001` preserves the first 38-control run, before extending the JSON failure
records and interruption controls. `002` preserves a failed stronger control:
the GNU-time supervisor was reaped before a compiler descendant finished writing
stderr, so the subsequent hash check rejected the premature frozen log hash.
The recorded and terminal hashes and executed sources remain in `002/failure.json`.
`003` tests the corrected whole-group cleanup with full failure identifiers, a
deliberately failing child process, partial artifact hashes, and a real driver
SIGTERM after a compiler (`cc1plus`) descendant starts. The launcher waits for
all non-zombie group members, uses bounded TERM/KILL escalation, and records
survivors instead of hashing potentially live outputs. Each suite retains its exact
executed launcher/helper source, commands, CMake-built solver snapshot, logs,
execution ledgers, and hashes. Sources and evidence of earlier runs are not
rewritten.

GNU `time` records each command's maximum RSS. Small-fixture memory does not
establish real Loma memory headroom. The initial preflight remains
`ready_for_accuracy_review` when these implementation and local-status checks
pass: the separate full continuous initial-z reference comparison and scientific
interpretation of sampled refinement/finite differences are still required.
No new sampled error threshold is introduced, no first-arrival certificate for
arbitrary three-dimensional updated models is claimed, and this helper cannot
launch an inverse solve.
