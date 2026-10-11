# Initial-DD resolution report checkpoint

The updated [report](../../../report/report.pdf) compiled successfully in two
passes and contains 127 pages. Equations, units, the two native curved-ray
failures, and the new fourteen-panel resolution/noise figure were visually
checked on pages 26–27 and 63–64. Historical rebuild provenance and recovery
metrics were also checked on pages 15–16. The initial-model discussion and its figure
are adjacent. There are no undefined references, overfull boxes or compilation
errors; one underfull vertical box remains. [validation.json](validation.json)
binds the source, PDF and scientific packages without machine/process records.

The new initial-model DD calculation includes catalog differences, source
coupling and shared-pick covariance. Its packaged-input numerical replay and
separate figure replay reproduce the scientific outputs exactly. The report
also preserves both positive invented controls and failed native continuous
curve integrations. These outcomes do not establish final nonlinear recovery.
The manuscript audit remains **one reproduced panel and 61 partial panels**.

The [historical clean rebuild](../historical_clean_rebuild_001/README.md)
completed its eight inversions, 48 component checks and both TeX passes.
The report distinguishes that command completion from failed sampled ray checks
and worsening location RMS in the larger synthetic experiment. It also records
which figure files were regenerated and which were reused. The original
synthetic figures displayed here retain their baseline provenance.

Numerical replay is documented in the
[resolution package](../hayward_initial_full_dd_resolution_001/README.md), with
[separate plotting instructions](../hayward_initial_full_dd_resolution_001/PLOT.md).
The [invented controls](../layered_curved_components_001/README.md) and
[failed native attempts](../layered_reference_selected_curves_001/README.md)
retain their own scientific scope and commands. These component procedures
do not constitute the still-incomplete corrected inversion/recovery workflow.

To compile the report from the repository's saved figures, choose an absent
project-local output directory:

```sh
mkdir -p tmp
mkdir tmp/FRESH_initial_dd_report
mkdir -p tmp/FRESH_initial_dd_report/tmp
(
  cd report
  export TMPDIR="$PWD/../tmp/FRESH_initial_dd_report/tmp"
  export TEXMFVAR="$PWD/../tmp/FRESH_initial_dd_report/texmf-var"
  export TEXMFCONFIG="$PWD/../tmp/FRESH_initial_dd_report/texmf-config"
  export TEXMFCACHE="$PWD/../tmp/FRESH_initial_dd_report/texmf-cache"
  pdflatex -interaction=nonstopmode -halt-on-error \
    -output-directory=../tmp/FRESH_initial_dd_report report.tex
  pdflatex -interaction=nonstopmode -halt-on-error \
    -output-directory=../tmp/FRESH_initial_dd_report report.tex
)
```

Inspect the exit status and log of each pass. The new PDF is in the fresh
directory; this command preserves the published PDF and numerical outputs.
