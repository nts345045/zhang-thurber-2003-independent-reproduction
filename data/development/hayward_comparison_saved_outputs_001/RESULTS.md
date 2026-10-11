# Closed interruption readback

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

This execution exercises only the real zero-update interruption. The reader's
accepted-state joins, fixed-model velocity equality and two-panel plotting
are source-reviewed but remain unexecuted until a suitable actual attempt
closes. No successful inversion or manuscript-panel promotion follows from
this check. Standard attempt 002 and the fixed-model relocation are separate
ongoing attempts, with their status in the
[comparison checkpoint](../hayward_catalog_comparisons_001/ATTEMPTS.md).
