# Hayward preflight spacing declarations

The runner accepts independent preflight options `--path-spacing` and `--fmm-spacing` in km. Without overrides, the path spacing comes from the unchanged baseline configuration and FMM spacing remains 0.5 km, reproducing variant003 numerical settings. The generated configuration and run manifest record both values. Inversion uses that frozen configuration and rejects spacing overrides. Existing thread, exclusive-run, source/input hash, and terminal-state controls remain unchanged.

All 21 checks passed without launching a numerical job. Four configuration cases verify unchanged defaults and independent overrides; invalid values and inversion-phase overrides are rejected. The complete preflight validator text and five execution/interrupt guard functions are unchanged from frozen003. Exact source and before/after runner copies are retained in `source/`, with hashes in `results.json`. These checks do not establish that any new spacing is accurate or that a new preflight may pass.

No new full-cohort run was launched by this change. Accuracy comparisons and the failed003 evidence remain separate.
