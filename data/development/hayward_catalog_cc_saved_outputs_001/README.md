# Closed catalog-plus-CC DD saved-output reader

`plot_hayward_catalog_cc.py` is a new, separate reader for the identified
`data/hayward_catalog_cc_backtracking_001` attempt. It has not been imported or
executed. This package contains source preparation, not an execution result.
All existing launchers, renderers, helpers and numerical inputs remain unchanged.
The reader requires the retained local attempt and its original controller,
plan and execution records. Those local control files are not supplied by a
clean published checkout; this source preparation does not claim standalone
replay from the public result packages.

After the attempt's sole owner has actually closed and reaped its controller,
the proposed command from the repository root is:

```sh
python3 -B plot_hayward_catalog_cc.py \
  --data data/hayward_catalog_cc_backtracking_001 \
  --controller-receipt tmp/hayward_catalog_cc_backtracking_controllers/001/execution.json \
  --output tmp/FRESH_catalog_cc_saved_outcome
```

Use an absent immediate child of repository `tmp/`. Matplotlib is needed only
when an accepted state can be plotted. The script writes `render_summary.json`
and `report.tex`; it does not invoke LaTeX. Verified accepted geometry also
produces `combined_figure.pdf`/`.png`, `event_points.csv`, `model_nodes.csv`,
`receiver_epochs.csv`, `cc_observations.csv`, and a full identity sidecar for
each of those six files. No accepted update means no recovery plot or derived
geometry tables. The original files are never overwritten or relabeled.

## Exact receipt adaptation

The unchanged DD renderer expects one `rebuild_outcome.json`. This attempt
instead has an outer controller receipt, `dd_inversion_execution.json`,
`dd_inversion_run_manifest.json`, and, on successful completion,
`dd_output_contract.json`. The adapter joins those existing records in memory;
it does not manufacture a rebuild outcome in the source run.

| Existing record | Readback use |
| --- | --- |
| Outer controller `execution.json` | Terminal status, actual launcher return/reaping, no unresolved live writers, exact plan/controller/command and inner-receipt hash joins |
| `dd_inversion_execution.json` | Original inner status and nullable error return; completed command returns and group settlement; success `output_sha256` or settled failure `partial_output_sha256` |
| `dd_inversion_run_manifest.json` | Actual source, all eleven copied input hashes, declared combined configuration and expected counts |
| `dd_output_contract.json` | Existing successful completion evidence and exact accepted-snapshot roster; no repeated rejected-path review |

The outer launcher return, inner error return and recorded `dd_invert` return
remain separate. The latter belongs to the existing GNU-time-supervised command;
the adapter does not invent a direct numerical-child wait. A null error code
remains unknown. `current_stage` is labeled the last recorded command stage:
a subsequent saved-output check can fail after that command has returned zero.
The inherited group fields exclude zombies and establish no live writers;
they do not claim literal process-table absence.

Missing settled generated-file inventory or a recorded run manifest prevents
geometry admission and permits a status-only report. Missing pinned control
sources, conflicting recorded hashes or unresolved writers refuse readback.
Successful exit from this reader means the disposition
was written; inspect `saved_output_validation` and `recovery_plot_created`.

## Scientific and identity reuse

The reader imports `plot_hayward_corrected.geometry()` and
`rebuild_hayward_corrected.accepted_states()` unchanged, with their exact source
hashes. It preserves complete history/terminal accepted-trial joins, objective
and step checks, snapshot metadata, finite source coordinates, physical-box
bounds, positive velocities, fixed node coordinates and both native receiver
epochs. Every consumed history, trial and accepted event/grid table is checked
against the joined closed inventory before these helpers are called.

The reviewed public source mapping `d462f00b…` supplies the exact numerical
source, configuration and scientific-input bindings. These are joined to the
exact reviewed combined plan and run manifest, including the specific launcher
`0b9d7c79…` and controller `595ce3b1…`. The eight original catalog-file hashes
are used with the explicit replacement hash for the combined observation table
and the declared combined `run.cfg`. No provider archive, source archive or
large rejected-ray/history archive is rescanned. The completed launcher's
`check_inverse()` and `review_trials()` are not invoked again.

The same 1,092 events, 372 receiver epochs and 462 model nodes accompany
14,262 absolute, 44,718 catalog-difference and 98 CC observations. The full CC
rows, not a reduced measurement summary, are written to `cc_observations.csv`.
They retain native measurement IDs, provider pick/association provenance,
SEED/FDSN channel codes, both endpoint epochs and valid blank location codes.
Every figure/table sidecar references all consumed accepted snapshots and
trial ledgers, the initial tables and the original full observation table.
CC timing uncertainty remains blank/unestimated. Literal CC squared is the
empirical row multiplier, so the conditional squared-objective factor is CC
to the fourth power; this is a declared data and weighting experiment.

The two panels show the last verified accepted state's velocity change at
the existing 8 km grid depth and source displacement from the initial catalog
state. Their common limits enclose the full saved grid and all initial and
accepted source positions, with a two-percent margin, equal coordinate scale
and 1:1 arrows. An unchanged velocity section is labeled zero without an
artificial color range. There is no extra CC plot panel.

History RMS and ray diagnostics remain pre-update quantities. Accepted-state
geometry, command completion and nonlinear convergence remain distinct.
Existing pending-final-diagnostic language is preserved as a limitation, not
a new requirement to run rays, refinements or covariance merely to report an
honest partial or failed attempt. No numerical calls, new scientific gates,
manuscript-panel promotion or production-source adoption are introduced.

`source_mapping.json` records the new source and documentation, exact imported
helper hashes and the static source contracts reviewed. The source check is
AST-only; no live numerical output or current runtime receipt was read while
preparing this package.
