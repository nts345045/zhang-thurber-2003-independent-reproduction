# Completed matched CMJ replay

The authorized replay completed on 2026-10-10 at 09:54:52 UTC with code 0. One original receiver field accepted all 45,603,129 nodes. Four configured evaluations comprised exactly eight trace subcalls. The controller reaped the runner; the runner reaped each compiler and executable process group before freezing outputs. Both compilations and both numerical commands returned 0 with empty stderr.

Before D ran, the original results reproduced every recorded 17-digit status field and every selected-path/native field exactly. Both complete original Candidates round-tripped binary64 coordinates and field times exactly; D loaded and resaved identical Candidate files. See [old_parity.json](old_parity.json), [summary.json](summary.json), [execution.json](execution.json), and [controller_completion.json](controller_completion.json).

Both rays use receiver 160, `NC.CMJ..EHZ`, `FDSN:NC_CMJ__E_H_Z`, blank location, epoch 1996-11-12T23:45:00–1998-06-09T19:30:00. Event 981 is `quakeml:NC.anss.org/Event/NC/518943`, origin `quakeml:NC.anss.org/Origin/NC/4251144`; event 987 is `quakeml:NC.anss.org/Event/NC/519264`, origin `quakeml:NC.anss.org/Origin/NC/4252064`. All original fields and trial coordinates remain in [inputs/native_context.json](inputs/native_context.json) and the numerical tables.

| Event | Version | Start | Updates | Local flag | Projected gradient (s/km) | Reported action (s) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 981 | Original | Straight | 907 | 0 | 0.00047621894853158383 | 5.8263118784510874 |
| 981 | Original | FMM, selected | 1000 | 0 | 0.00049649035047086309 | 5.8263118708703301 |
| 981 | D | Straight | 1000 | 0 | 0.00051509670045919384 | 5.8263118784317820 |
| 981 | D | FMM, selected | 1000 | 0 | 0.00049658579025209989 | 5.8263118709255952 |
| 987 | Original | Straight | 865 | 0 | 0.00049975078169704724 | 5.8369124533465948 |
| 987 | Original | FMM, selected | 836 | 0 | 0.00049378622676222908 | 5.8369124438144935 |
| 987 | D | Straight | 1000 | 0 | 0.00053277853351176463 | 5.8369124528566401 |
| 987 | D | FMM, selected | 1000 | 0 | 0.00055435395870530009 | 5.8369124435953772 |

All eight starts retained false local flags and zero merges. The selected paths retained 1029 and 1031 points. Original early false returns correspond to exhausted line searches under the unchanged control flow; all four D calls exhausted the 1000-update budget. These labels are derived from returned status and control flow, without iteration instrumentation. Neither selected D ray meets the existing strict gradient test or the combined stopping test. D minus original selected reported actions are +5.526512580900089e-11 and -2.1911628067528e-10 s. These compare outputs of different outer accumulation arithmetic, and do not certify a physical action ordering.

The adopted package changes outer action accumulation and usable-curvature handling together. It did not resolve either local failure in this three-dimensional trial. This result does not isolate either change, diagnose the other 179 failed rays, or establish a failure mechanism. Derivatives were disabled as in the original action-only trial, so no endpoint/model partial or continuous first-arrival accuracy claim follows. The original inverse trial remains rejected; no inverse, restart, full-trial evaluation, extra field, or additional ray was run.

The independent saved-output [review](review.json) passed: SHA-256 `9f8f69021ef47ed775026ffd7f3b9fb3da3cd5cc73750dae4e0f4b9e75fbc2c5`. It verified 103 pins and 293,088 native cells, including original status/path equality and complete Candidate equality, without another field or trace evaluation.
