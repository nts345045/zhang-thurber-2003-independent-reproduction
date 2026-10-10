# Authoritative geometry and CC-support report checkpoint

This package records two ordinary TeX passes for the report incorporating the
closed authoritative Loma Figure 2 and identified CC spatial-support map. It
performs no solver, reference calculation, waveform measurement or inversion.
The manuscript audit remains one reproduced panel and 61 partial panels.

`compile.py` is byte-identical to the preceding accepted-update report compiler.
From the repository root, use project-local `TMPDIR`, `TEXMFVAR` and
`TEXMFCONFIG`, then run the pinned Python with `-B`. Existing receipts must be
preserved; a repeated build belongs in a fresh receipt directory.

`preservation.json` records the published figure bytes and all 13 main-branch
baseline pins before compilation. `validate.py` checks compilation, paths,
closed new-figure bindings, caption counts, generated panel records and those
preserved bytes. `render_receipt.json` and `visual_review.json` bind the inspected
PDF pages. These input-support figures do not establish inversion accuracy or
promote manuscript reproduction status. The historical Figure 3 recovery still
uses the earlier random geometry.

This validator is a checkpoint checker for the recorded integration worktree:
`ROOT.parents[1]` locates the separate protected main baseline, and runtime
hashes bind the installed tools used here. It is not a fresh-checkout build
test. The two figure packages document portable replay from saved inputs with
their declared plotting dependencies; a clean end-to-end project rebuild
remains pending.
