# Two-call strict-stop result

Both calls completed at the unchanged 1000-update cap, with returned convergence flags **false**. Removing the combined early stop improved the source-derivative accuracy of pair 8670 and worsened that of the passing control, pair 8674. Both final source errors meet the unchanged 3e-6 s/km Euclidean limit, but neither ray meets the retained strict 1e-7 projected-gradient condition. These are diagnostic results, not a passed forward-validation gate.

Both pairs use source 166, event `quakeml:NC.anss.org/Event/NC/10090456`, origin `quakeml:NC.anss.org/Origin/NC/2644764`. Pair 8670 uses `NC.JHL..EHZ` (`FDSN:NC_JHL__E_H_Z`, epoch 1989-10-19T20:40:00–1990-08-21T18:35:00); pair 8674 uses `NC.JRG..EHZ` (`FDSN:NC_JRG__E_H_Z`, epoch 1989-03-24T22:55:00–1990-08-07T20:50:00). [Full native context](inputs/native_context.json) preserves every source and receiver field, including blank location codes. Source time is excluded from propagation time.

| Pair | Source error, baseline D → strict (s/km) | Time error, baseline D → strict (microseconds) | Projected gradient, baseline D → strict (s/km) | Updates, baseline D → strict |
| --- | --- | --- | --- | --- |
| 8670 | 4.8070601218e-6 → 2.5116706023e-6 | 1.523071245 → 1.115055197 | 4.4893546263e-6 → 2.6038144123e-7 | 178 → 1000 |
| 8674 | 1.0599762986e-6 → 1.6103645968e-6 | 1.437047202 → 1.128581203 | 9.2239830653e-6 → 9.9613530280e-6 | 207 → 1000 |

Final action decreased by 0.408016048 and 0.308465999 microseconds, respectively. Both time errors remain below 25 microseconds. Both calls retain zero merged nodes and the original 516 and 552 path points; endpoints, grid, spacing 0.03125 km, null-seed straight initialization, metric, curvature handling, derivative formulas and Armijo budget are unchanged. Full final paths and all 288 model partials per ray are saved under [results/strict](results/strict/). Initializer metadata from the old FMM calculation is explicitly labeled as saved evidence; this experiment constructed no fields.

The two 1000-update counts establish exhaustion of the loop budget from the inspected control flow. The independently computed post-return strict flags are separately false. No iteration history was instrumented, so this package makes no claims about individual accepted steps, memory evolution or intermediate action monotonicity. The previous D flags remain true under their original combined stopping criterion; they have not been relabeled.

The single stopping change demonstrates sensitivity of pair 8670's accuracy to further optimization at the same representation dimension. The control's larger source error despite lower action prevents a general claim that further optimization improves source derivatives. Since neither call reaches strict stationarity, these results do not isolate the fully optimized polygon error, establish a global discrete or continuous first arrival, justify a production stopping change, or validate the full LON cohort. No further native calls were made.

[summary.json](summary.json) and [execution.json](execution.json) retain the exact saved outputs and terminal hashes. One inherited `scientific_scope` string in the frozen runner/summary says “four calls”; this is a copy error. The prepared plan, driver, execution inventory and independent [prelaunch review](prelaunch_review.json) establish **exactly two** native calls. This note corrects the wording without rewriting consumed source or results.

The tool-owned runner returned code 0; its compiler and two-call executable each returned code 0 and were reaped. [controller_completion.json](controller_completion.json) binds that observed return, saved outputs and final process-group check. `finish_receipt.py` records this lifecycle evidence only and performs no ray or action evaluation. The small compiled binary is an original summary-pinned artifact and is retained with its source and build command.
