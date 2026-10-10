# Inert archive of completed execution sentinels

The usable-curvature diagnostic D pins four ancestor `execution.lock` files
as inputs and its own file as an output. Earlier publications omitted those
five files. The transitive failed-search sentinel is already tracked; it is
included here for a complete six-record chain. Each is a seven-byte record:
six historical PID digits and a newline. `archive.json` retains those exact
42 bytes as JSON strings, their hashes, 29 actual prepared/summary/publication
lookups, 32 terminal/native/packaging file pins, and each ray's existing
event/origin/channel/epoch identities.

These files were one-use launch sentinels, created with `O_EXCL` and left after
completion. Their existence is not evidence of a live process. The archive is
ordinary inert JSON; it does not publish additional active lock files. No
process is queried, signalled or resumed. Original locks, ledgers and frozen
summaries are unchanged.

Each decoded record matches the completed execution ledger's PID and the
summary's output hash. The ledger binds the summary, which binds its prepared
inputs. Controller receipts and native identity files are also checked. The
outer-accumulation receipt explicitly says its original launcher did **not**
reap the detached driver and records a null detached return code; this archive
preserves that caveat. It does not upgrade that receipt to a reaped result.
The curvature-capture packaging receipts cover raw component data and gzip
provenance, not the omitted sentinel bytes; their existing hashes are retained.

## Restore only into a fresh scratch checkout

Use the published **`first-arrival-integration` branch, or its matching
published commit**, for these diagnostics. `main` deliberately retains the
legacy baseline source and is not the source snapshot for this preparation.
Run the following from a checkout containing this published archive and its
terminal evidence, after that integration revision has been published:

```sh
mkdir -p tmp
PYTHONDONTWRITEBYTECODE=1 python3 data/development/terminal_lock_archive_001/restore.py --scratch tmp/terminal_evidence_checkout_001
git archive first-arrival-integration | tar --extract --file=- --skip-old-files --directory=tmp/terminal_evidence_checkout_001
PYTHONDONTWRITEBYTECODE=1 python3 data/development/terminal_lock_archive_001/restore.py --verify tmp/terminal_evidence_checkout_001
```

Replace the branch name with the matching immutable published integration
commit for a pinned reproduction. The restoration happens **before** the
checkout overlay. The destination must not exist, even as an empty directory;
symlinked destinations or ancestors are rejected. The helper creates only six
historical files with exclusive creation and read-only permissions, plus a
receipt. `--skip-old-files` preserves the restored, byte-identical failed-search
sentinel already present in Git. The final command checks all 32 terminal pins
and all 29 historical lookups against the populated scratch snapshot. A wrong
or incomplete revision fails that check. It performs no numerical calculation.

Never copy the overlay into a live worktree or remove an existing lock to use
this helper. Existing runtime state is outside its write scope. Restored files
remain historical evidence and intentionally prevent relaunch into the old
output directories; any new experiment needs its own fresh output directory.

This closes only the six sentinel dependencies. Other data archives, source
snapshots, compilers and libraries retain their existing reproduction rules.

## Captured checks

`capture.py` creates the inert archive without modifying its inputs.
`check.py` exercises a fresh metadata-only checkout under
`tmp/terminal_lock_archive_checks_001/`, an equivalent minimal fixture for the
same overlay and lookup operations. All 15 checks passed: six exact restored
records, 29 real dependency lookups, 32 terminal/native pins, public read-only
verification, read-only restored files, rejection of existing/empty/symlinked
destinations, unsafe/duplicate/corrupted records, stale hashes and a
hash-consistent but nonterminal ledger. All 38 original terminal/sentinel files
remained byte-identical. `check_results.json` retains the commands and hashes.
No solver, native replay, network retrieval or Git mutation was used.
