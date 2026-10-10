# Independent B publication review

The review covers the frozen 147-member outer-accumulator delivery, its plot
arrays and native context, README/report claims, evidence links, and compiled
104-page PDF. It does not rerun a ray, numerical control, or plot generator.

Reproduce the saved-file checks from the integration repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_outer_accumulation_delivery_review_001/check.py
```

`checks.json` records the executed result. The figure PNG and independently
rendered PDF pages 31–32 were visually inspected. Those page images were made
with `pdftoppm -f 31 -l 32 -r 95 -png report/report.pdf` and are retained here.

The publication preserves the negative result: extended outer accumulation
does not produce a locally converged FMM ray. The two reference accuracy
checks, local flag, recorded action changes and curvature-pair counts remain
distinct. Neither this review nor the plot establishes a general correction,
global first-arrival completeness, or inversion readiness.

The two LaTeX passes succeeded. The first contains expected new-reference
warnings; the second is clean and the PDF resolves Figure 14. The first two
readback attempts are retained: one used the wrong field name for the previous
delivery's panel counts, and one incorrectly demanded a warning-free first
LaTeX pass. Correcting those review assumptions did not change any publication
file or numerical result.
