# All 104 identified Loma geometry rays: layered reference

All 104 declared diagnostic pairs have complete, valid candidate-family
references in the original finite box. The minima comprise 73 direct paths,
23 critical guides, six turning paths and two flat direct paths. There are
no near ties under the reference's existing 1e-9 s reporting scale. This
comparison generates no observations, changes no simulation gate and does
not replace the production tracer.

The profile is exactly x-only. The reference uses `(y,z,x)` as its coordinates
and maps its source derivatives back to the original axes. Every original
diagnostic row, native event/origin/channel ID, SEED/FDSN code and metadata
epoch is preserved in `comparison.csv` and the frozen inputs. Full candidate
families, root certificates and native metadata are retained in
`references.jsonl`. All 24 available source-derivative components appear in
`derivative_comparison.csv`; derivatives for other rays are not invented.

Both saved spacings retain 73 true and 31 false local stopping flags. At
production spacing, the maximum time error is 37.158685 ms and lies among
the locally flagged-converged rays. Their RMS error is 5.81934 ms. The false
flags have maximum time error 455.699 microseconds. At refined spacing,
the corresponding maxima are 41.0553 and 186.569 microseconds. Small negative
differences, no larger than 4.12e-12 s, inherit the saved 12-significant-digit
time rounding. These are descriptive differences, not a new field threshold.

`review.json` groups errors by the unchanged flags and retains complete
metadata for the five largest errors at each spacing. It also reports
Euclidean source-error norms for the eight rays with complete saved derivative
vectors. Reproduce that summary with `review.py`.

The reference module passed 355 isolated invented checks and an independent
source review before this comparison. A further independent read-only review
verified every numerical and native row, all derivative permutations and the
19 recorded output hashes. `independent_review.json` records that scope.
Candidate completeness concerns families sufficient for the minimum; equal
maxima can support continuously many geometrical paths. Time ranking remains
ordinary floating point, not an interval-certified minimum-time comparison.

The exact command, source snapshots and input/output hashes are in
`summary.json`. Reproduce in a fresh directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_loma_layered_reference.py --output data/development/loma_geometry_preflight/layered_reference_repeat
```
