# Scientific spending assessment, 13 October 2026

Read the [four-page assessment and appendix](../../progress_assessment.pdf)
or its [LaTeX source](../../progress_assessment.tex). It recommends stopping
open-ended model development. A human-led review of existing failures is
proposed only, with a 10,000-token ceiling and no new simulations.

The assessment concerns Zhang and Thurber (2003). The user explicitly
authorized replacing the unrelated Zhu et al. references in their prompt.
Earlier deliverables, numerical code, configurations and observations were
preserved. No additional agent, inversion, ray evaluation, parameter search
or project regeneration was launched.

## Supporting records

- `evidence.json`: arithmetic checks on saved synthetic and field tables,
  checked package hashes, identifier-field counts, closed-run summaries,
  original source hashes and checks not performed.
- `panel_inventory.csv`: all 62 individual audit entries, with generation
  and publication agreement recorded separately, quantitative comparisons,
  limitations, data paths and plot paths.
- `panel_inventory.tex`: compact appendix; its 32 rows enumerate every
  entry, grouping only the seven identically supported sections for each
  Figure 10 or 11 letter.
- `inventory_check.json`: panel counts and reference-existence check.
- Four `*_history.csv` files: byte-identical copies of closed-run histories.
- Four `*_terminal_trials.csv` files: final rejected-trial tables. The
  `failure_prefix` column is reduced to basenames and line endings are LF;
  all numerical cells and statuses are preserved. These are aggregate
  trial diagnostics, not newly exported event or station data.
- `report_validation.json`: final report hashes, page/word limits, figure
  provenance, compilation outcome, visual review and limitations.
- [Report identity sidecar](../../progress_assessment.pdf.identifiers.json):
  links the reused field figure to complete existing native-identity tables.

The four previously running inversions are now failed attempts, with native
exit code 1 after ray rejection prevented objective evaluation. Their
histories contain 7–9 accepted-update records, checked against trial tables;
their later geometries were not newly validated. No final scientific
success or panel promotion is implied. Private execution records remain
local; the evidence file preserves their hashes and sanitized dispositions.
References beginning with `tmp/first_arrival_integration` in its hash list
identify retained local originals and are not public-checkout dependencies.
The public CSV copies support inspection of the reported histories and
failure pattern. The original DD bootstrap's external terminal state
remains unknown; the nested controller/launcher closure is documented.

## Compile this assessment only

From the repository root, using the existing TeX installation:

```sh
mkdir -p tmp/progress_assessment_build
TEXMFVAR="$PWD/tmp/progress_assessment_build/texmf-var" TEXMFCONFIG="$PWD/tmp/progress_assessment_build/texmf-config" /usr/bin/pdflatex -interaction=nonstopmode -halt-on-error -output-directory=tmp/progress_assessment_build progress_assessment.tex
TEXMFVAR="$PWD/tmp/progress_assessment_build/texmf-var" TEXMFCONFIG="$PWD/tmp/progress_assessment_build/texmf-config" /usr/bin/pdflatex -interaction=nonstopmode -halt-on-error -output-directory=tmp/progress_assessment_build progress_assessment.tex
```

This uses two existing generated figures and compiles only the assessment.
It does not run scientific calculations. The delivered PDF was actually
compiled twice and visually inspected; the validation record names its
exact sources. The initial draft requested an unavailable `xurl` package;
the final source uses the installed `url` package and adds no dependencies.

All 46 distinct panel data/plot references were present and tracked.
The inventory retains the existing convention of one entry per Figure 3
letter; exact matching of every inner published subplot remains unverified.
No supplementary panel was identified in the publisher's original listing.
That is not proof that no ancillary material exists elsewhere.

The local aggregate goal counter (59,062,766 tokens) is not a reconciled
billing record. No dollar expenditure or per-experiment agent cost was
inferred from it. Proposed future allowances are spending ceilings, not
promises of successful model repair.
