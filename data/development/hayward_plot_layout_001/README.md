# Hayward longitude-label layout revision

The original unguarded Hayward workflow finished with exit 0 after 33,712 s.
The longitude tick labels overlapped in the four common-event zoom figures.
This postprocessing revision adds `MaxNLocator(nbins=3)` to their longitude
axes. Limits, event membership, coordinates, styles, model values, and color
limits are unchanged.

`before/plot_hayward.py` preserves the executed plotting source, with SHA256
`f0b65aa8db41c77c02657409a6cdddd6af4976a906a17f72acb7a2c0c461a906`.
The historical solver `run_manifest.json` is untouched. `before.json` records
all 48 saved data-CSV hashes before the edit. After `python3 plot_hayward.py`,
every CSV, `figure_metrics.json`, and `numerical_review.json` remains
byte-identical. The geometry manifest changes only its plotting-source hash.
`summary.json` records those checks, commands, output hashes, and before/after
snapshots. This is a layout revision, not a new inversion or numerical result.

All field figures were visually inspected together. The revised Figure 6 and
report page 41 were inspected individually; longitude labels are readable.
The PDF remains 109 pages. Two LaTeX passes from `report/` completed; the final
log contains the pre-existing underfull-box notice, with no overfull or
undefined-reference warnings. An earlier compile command used the wrong
working directory and failed to find a relative figure; its logs are retained.
It produced no PDF. No inversion, ray trace, or resolution solve was rerun.
Plotting repeated deterministic coordinate and section calculations; their
saved numerical tables remained byte-identical.

The copies under `after/` preserve this completed layout checkpoint even when a
later report adds interpretation or new experiments. Process completion does
not establish local ray convergence, earliest arrivals, nonlinear convergence,
or recovery of the manuscript's model. The field figures describe the original
catalog-only subset and frozen original solver; the guarded first-arrival run
has its own source, inputs, manifest, and output directory.
