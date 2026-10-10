# Completed-linearization readiness controls

Five invented two-ray checks pass for the explicit
`--completed-linearization-only` mode of
`diagnostics/compare_hayward_1d_support.py`. A matching successful command
may be read while the separate preflight ray check is still running. The
ledger is captured once, inputs are copied and verified, and no
`preflight.json` is created or overall preflight success inferred.

The controls reject a failed command, a mismatched command and an input
whose manifest hash changed. They also verify that later ledger changes
leave the snapshot unchanged and that the original completed-preflight
mode still works. The small homogeneous fixture is explicitly invented.

The command and source hashes are in `results.json`. Run `check.py` from
the repository root in a clean checkout without the existing
`tmp/hayward_1d_linearization_mode_checks` directory. Previous evidence is
preserved rather than overwritten.
