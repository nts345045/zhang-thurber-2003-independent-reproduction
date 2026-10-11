# Closed fixed-model relocation: accepted state 18

This package preserves the actual `loc1d` comparison's closed saved-output
readback. The numerical attempt returned zero after 18 accepted updates, and the
renderer verified their history, trial and snapshot joins. The display uses
zero-based iteration 17, with 1,092 identified events, 372 receiver epochs and
462 unchanged velocity nodes. Its source displacement is relative to the initial
catalog position, not error against known truth. The catalog contains 14,262
absolute and 44,718 differential observations; no waveform rows were used.

[report.pdf](report.pdf) and [comparison_figure.png](comparison_figure.png) show
the saved result. The three renderer CSVs retain full event/origin and receiver
SEED/FDSN metadata, including valid blank location codes. The archived observation
table retains both event/pick/association endpoints and their distinct metadata
epochs. [scientific_outcome.json](scientific_outcome.json) records the numerical
source, configuration and closed outcome hashes without copying private runtime
records. [validation.json](validation.json) describes the bounded transport and
identity checks.

All renderer files, their five identity sidecars, `render_summary.json`, and the
separately compiled one-page report are byte-identical to the closed originals.
The report used two successful TeX passes. Packaging performed no inversion,
tracing, finite differences, new plotting or scientific recalculation.

## Restore the scientific tables

`source_tables.tar.gz` contains 61 regular files: the 59 tables referenced by
every figure/table sidecar, plus `run.cfg` and `authoritative_ids_required`.
They include the initial tables, all 18 accepted event/grid snapshots, all 18
trial ledgers and the history. [archive_index.json](archive_index.json) lists
every member's exact size and SHA-256. All members were read back and verified
against the closed originals. The archive is 5,591,201 bytes; its SHA-256 is
`7491bf2911d95d06e271125b7499792ffd755aaa591d6307d0433caa6bd04ad0`.

From the repository root, restore to a fresh directory:

```sh
set -eu
package=data/development/hayward_comparison_saved_outputs_001/loc1d_001
restore=tmp/FRESH_loc1d_001_tables
mkdir -p tmp
test ! -e "$restore"
test ! -L "$restore"
mkdir "$restore"
tar -xzf "$package/source_tables.tar.gz" -C "$restore"
```

The resulting tables are under
`$restore/data/hayward_loc1d_guarded_001/`.
[source_path_mapping.json](source_path_mapping.json) maps each unchanged sidecar
path to its archive member. Resolve a sidecar reference as
`$restore/<archive_member>`; it is not relative to this publication directory.
If literal historical paths are needed, place copies of the 13 renderer/report
files under `$restore/tmp/hayward_loc1d_saved_readback_001/`: their original
`../../data/hayward_loc1d_guarded_001/` references then resolve directly.

Table `source_file` strings also remain unchanged. Their original base and
repository-relative provider paths are explicit in the mapping. Provider XML
and historical metadata already in the repository are provenance dependencies,
not duplicate archive members. Restoring these tables does not reacquire or
reinterpret provider metadata.

## Precision and scope

Use `loc1d_accepted_it_17_events.csv` and its grid for the displayed state.
The raw run's `loc1d_last_accepted_*` files are earlier pre-trial checkpoints;
they are not included or treated as the final accepted state. The snapshot's
literal “run incomplete” coordinate label describes when it was written; the
separate closed outcome establishes that the attempt subsequently completed.
The ordinary final `loc1d_events.csv`/`loc1d_grid.csv` exports use 12 significant
digits and are not the plotted inputs. Their rounded strings must not be used
to infer a velocity update: every accepted model snapshot preserves the initial
binary64 velocities exactly.

History RMS and ray diagnostics describe pre-update states. Accepted objective
decreases use each iteration's fixed weights and do not establish a monotonic
post-update RMS, nonlinear convergence, source accuracy, updated-state ray
accuracy, first-arrival certification or covariance. The manuscript audit stays
at one reproduced panel and 61 partial panels.

This is a self-contained saved-geometry and identity package, not a complete
inversion restart or an execution receipt. The already published
`plot_hayward_comparison.py` successfully produced these outputs from the full
closed attempt. Its original command rehashes additional, omitted solve and
rejected-trial outputs; it cannot be replayed from this reduced archive alone.
The archive supports inspection of every figure source and acceptance join.
It does not replay the numerical attempt or replace the original renderer's
closure requirements. No standalone replot command is claimed here.
