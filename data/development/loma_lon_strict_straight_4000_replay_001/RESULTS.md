# Fixed-cap result

Both calls exhausted the unchanged diagnostic cap of **4000 updates** and returned **false strict-convergence flags**. Pair 8670's source-derivative error improved further; the passing control's error increased further. Both final errors satisfy the unchanged continuous-reference accuracy limits, but neither meets the retained 1e-7 projected-gradient stopping criterion. No further cap escalation or native calls follow this experiment.

Both pairs use source 166, event `quakeml:NC.anss.org/Event/NC/10090456`, origin `quakeml:NC.anss.org/Origin/NC/2644764`. Pair 8670 uses `NC.JHL..EHZ` (`FDSN:NC_JHL__E_H_Z`, epoch 1989-10-19T20:40:00–1990-08-21T18:35:00); pair 8674 uses `NC.JRG..EHZ` (`FDSN:NC_JRG__E_H_Z`, epoch 1989-03-24T22:55:00–1990-08-07T20:50:00). [Full native context](inputs/native_context.json) preserves all fields and blank locations. Source time is excluded from propagation time.

| Pair | Saved run | Updates | Returned flag | Projected gradient (s/km) | Time error (microseconds) | Source error, Euclidean norm (s/km) |
| --- | --- | --- | --- | --- | --- | --- |
| 8670 | D, original combined stop | 178 | 1 | 4.4893546263e-6 | 1.523071245 | 4.8070601218e-6 |
| 8670 | Strict, cap 1000 | 1000 | 0 | 2.6038144123e-7 | 1.115055197 | 2.5116706023e-6 |
| 8670 | Strict, cap 4000 | 4000 | 0 | 1.8280566202e-7 | 1.030139916 | 1.7805069594e-6 |
| 8674 | D, original combined stop | 207 | 1 | 9.2239830653e-6 | 1.437047202 | 1.0599762986e-6 |
| 8674 | Strict, cap 1000 | 1000 | 0 | 9.9613530280e-6 | 1.128581203 | 1.6103645968e-6 |
| 8674 | Strict, cap 4000 | 4000 | 0 | 3.4647916629e-6 | 1.032573171 | 1.8823643876e-6 |

The 4000-call actions are lower than the saved 1000-call actions by 0.084915281 and 0.096008033 microseconds, respectively; reductions from the original D outputs are 0.492931329 and 0.404474031 microseconds. Both final time errors remain below 25 microseconds and both source norms remain below 3e-6 s/km. All runs retain zero merges and 516 or 552 points. The grid, exact endpoints, spacing 0.03125 km, null-seed straight initialization, strict source bytes, metric, derivative formulas, helper and Armijo budget remain unchanged. [Full final paths and model partials](results/strict/) include native identifiers on every row.

Only the maximum update count differs from the strict-1000 experiment. Both prior result sets were copied and compared without repeating their traces. `run.cfg.diff` and `driver.cpp.diff` show the cap setting and its matching validation guard; every numerical source file is byte-identical. The runner classifies the loop exit against 4000 and retains the post-return convergence flag separately. The recorded count proves budget exhaustion from the inspected loop; no history instrumentation was added, so individual steps, curvature-memory evolution and intermediate monotonicity are not assessed.

This comparison confirms further optimization sensitivity at the same representation dimension. It does not establish strict stationarity, the fully optimized polygon's derivative error, a global first arrival, full-cohort accuracy or a production stopping policy. In particular, decreasing action accompanied opposite source-error trends for the two rays. The old D flags and both strict failure flags remain unchanged, and numerical completion is distinct from a passed forward-validation gate.

[summary.json](summary.json) and [execution.json](execution.json) preserve the exact two-call inventory, comparisons with both prior runs and output hashes. The tool-owned runner, compiler and two-call executable all returned code 0; children were reaped and their process groups were empty. [controller_completion.json](controller_completion.json) binds that observed lifecycle and this result note. Its reproducible `finish_receipt.py` checks saved hashes and process state only, with no ray or action evaluation. The summary-pinned binary is retained with its complete source and build command.
