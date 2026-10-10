# Backtracking report checkpoint

This package records two ordinary `pdflatex` passes and saved-evidence validation
of the report's new backtracking, completion, launcher and invented ridge
paragraphs. No ray, reference, compiler for the numerical solver, or inversion
was run. The checkpoint reports no new field inversion; successful future
execution would still require final scientific assessment.

Commands executed from the integration repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/trial_backtracking_report_001/compile.py
PYTHONDONTWRITEBYTECODE=1 python3 data/development/trial_backtracking_report_001/validate.py
```

The compiler records all 16 TeX sources, both shared Markdown documents, both
pass logs, PDF text and `pdfinfo`. Both passes return zero. The first pass's
changed-label warning clears in the second; the pre-existing page14 PDF
page-group warning remains. Neither pass has an error, undefined reference or
overfull box. `validation_attempt_001` preserves the initial validator's
overly strict first-pass warning expectation and its explicit correction;
the TeX and compiled PDF were unchanged by that correction.

The final saved checks verify 107 local Markdown links, 118 literal TeX paths,
27 figure inclusions, and the hash-bound reviews behind the new quantitative
claims. The panel counts remain one independently reproduced and 61 partially
reproduced. The report has 117 pages. The new prose is on pages27 and39–40;
visual acceptance is a separate root review, not a claim of `validate.py`.

The evidence archive and restoration instructions are in
[`trial_backtracking_evidence_001`](../trial_backtracking_evidence_001/README.md).
Failed controls and unexecuted drafts remain preserved. The complete positive
final-table launcher fixture remains unavailable; the successful final ray
gate is bound to the exact audited binary and its return, with final scientific
diagnostics still required. No failed native flag or scientific limit changes.

The two scripts refuse to replace their existing completion receipts. Preserve
this package when preparing a later report checkpoint.
