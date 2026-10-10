# Frozen replay of LOM initial ray 3426

This records the failed search without changing its forward model, initialization, optimizer, stopping conditions or update budget. The original frozen observer, core and compiler are reused at 0.03125 km path spacing, 0.125 km FMM spacing, 1,000 maximum updates and one thread. The controller finished with code 0 at 2026-10-10 06:01:31 UTC.

All five prior numerical CSVs are byte-identical, and both in-process observed/unobserved comparisons pass for the straight and FMM starts. The selected FMM path retains its original false convergence flag after 53 accepted updates. This successful recording operation does not turn the failed numerical criterion into a pass.

The new tables contain the 1,134-node failed base path and direction, all 24 evaluated trial paths (27,216 vertices), and the exact recorded binary64 decision scalars. Each trial has unchanged topology, exact fixed endpoints and zero merged nodes. All coordinates, directions and scalars use 17 significant digits. The evaluated steps run from 1 to 2^-23; the separately recorded post-loop value is 2^-24.

The cached and reevaluated base actions are identical at 6.5184200416993878 s. All 24 Armijo right-hand sides round to that value. The recorded trial actions exceed it by 1–23 binary64 ULPs (8.881784197001252e-16 to 2.042810365310288e-14 s). Every trial differs from the base; the last still changes 120 coordinates. These are recorded arithmetic facts. They do not establish the exact action changes or the cause of rejection; the separate exact-action readback is required for that conclusion.

`identified_ray.csv` and every numerical CSV sidecar retain event NC10090782, origin NC2642854, channel NC.JSJ..EHZ / FDSN:NC_JSJ__E_H_Z, and the 1989-05-02T15:00:00–1990-09-14T21:50:00 epoch. Current initial coordinates remain distinct from catalog geometry provenance. The simulated origin-time correction is separate from propagation time; no provider pick identity is invented.

`prepared.json` pins the original observation, independently reviewed 22 capture controls, frozen source and inputs. `root_prelaunch_review.json` reviews the exact insertion diffs before launch. The detached controller record, compile/replay logs and terminal `execution.json` preserve execution evidence. `review.json` independently checks 66 input, 30 prepared, 16 source and 54 output pins, 87 native fields, all eight sidecars, all trial coordinates, gradient–direction multiplication and binary64 Armijo calculations. Its checker is preserved at `../loma_failed_search_review_001/review_saved_result.py`. Neither the capture controls nor this readback reruns or certifies exact physical actions.

Repeat only into fresh directories, after recreating and reviewing the control snapshot:

```sh
python3 diagnostics/observe_loma_failed_search.py --phase prepare \
  --observer data/development/loma_initial_failure_3426_001 \
  --controls data/development/failed_search_capture_controls_001 \
  --controls-review data/development/failed_search_capture_controls_001/review.json \
  --output data/development/loma_failed_search_3426_REPEAT \
  --build tmp/loma_failed_search_3426/REPEAT
python3 diagnostics/observe_loma_failed_search.py --phase run \
  --output data/development/loma_failed_search_3426_REPEAT
```

The actual run used a detached controller and an exclusive execution marker. Its immutable native records and original failure are retained. No inversion or production source change is included.
