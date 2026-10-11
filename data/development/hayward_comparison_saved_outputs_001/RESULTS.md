# Closed comparison readbacks

## Fixed-model relocation

One actual invocation of `plot_hayward_comparison.py --mode loc1d` read the
closed `data/hayward_loc1d_guarded_001/` attempt. The numerical command had
returned zero and reaped its children before readback. The renderer returned
zero with `saved_output_validation: passed`, verified 18 accepted snapshots,
and selected iteration 17. All accepted grid velocities equal their initial
values. Complete event/origin identities and receiver SEED/FDSN identities
remain attached to 1,092 events and 372 receiver epochs, including valid
empty location codes. The source archive retains full pick and association
identities, both endpoints of differential observations, and metadata epochs.

The [figure](loc1d_001/comparison_figure.pdf) shows zero velocity change at
8 km depth and horizontal source displacement at 1:1 coordinate scale.
Median and maximum three-dimensional displacement from the initial catalog
state are 2.849153 and 8.397198 km. The last recorded maximum source-coordinate
step is 0.441973 km; completion of 18 scheduled updates is not a convergence
test. The figure uses common limits enclosing the full grid and source positions.
History RMS and ray diagnostics remain pre-update quantities. No new final-model
accuracy, first-arrival, covariance or source-error calculation was performed.

The [one-page report](loc1d_001/report.pdf) compiled in two actual pdfLaTeX
passes, both returning zero. Text and visual inspection found no warnings,
clipping or overlap. The [package README](loc1d_001/README.md) documents the
exact rendered files, source archive, hash inventory and path mapping.
Its reduced archive is sufficient to inspect the figure and its scientific
tables; the original renderer also verifies additional solver outputs that
are not included. The manuscript audit remains one reproduced and 61 partial
panels. The separate standard replacement and DD runs remain ongoing.

## Interrupted standard attempt

One actual invocation of `plot_hayward_comparison.py --mode standard` read
`data/hayward_standard_guarded_001/` after its owning command had terminated
and reaped all children. The reader exited zero and reported
`saved_output_validation: passed`. This validates the saved-output disposition;
the inverse attempt remains interrupted with numerical return code `-15`.

The reader matched the frozen numerical source, catalog input and configuration
records and checked the complete native identity joins for 1,092 events and
372 receiver epochs. It found zero accepted updates, no selected iteration and
no recovery figure. The [summary](standard_001/render_summary.json) preserves
those results and its consumed table hashes. The original closed outcome and
all scientific inputs remained unchanged.

The generated [TeX status report](standard_001/report.tex) compiled in two
actual pdfLaTeX passes, both returning zero. The [one-page PDF](standard_001/report.pdf)
passed text and visual inspection without warnings, clipping or overlap.
No solver, ray calculation, covariance calculation or waveform processing ran.
The complete runtime records remain local; no live numerical files were read.

This earlier execution exercised only the real zero-update interruption.
The subsequent fixed-model readback above exercises accepted-state joins,
fixed-grid equality and two-panel plotting. No successful inversion or
manuscript-panel promotion follows from the interruption check. Standard
attempt 002 remains separate, with its status in the
[comparison checkpoint](../hayward_catalog_comparisons_001/ATTEMPTS.md).
