# Corrected saved readback result

All **190 controls passed** in the root-owned execution. The three malformed completions wrongly accepted in controls001 now fail for their intended reasons: exceeding the configured iteration cap, continuing after a stage-2 no-update termination, and changing the known iteration-zero accepted numeric state. All 189 original recipes and expected outcomes are unchanged; the original failed results remain preserved.

The additional actual joint-DD fixture passed with two iterations, twenty rejected trials, seventy-three failed native-ray instances and 371 saved failed-path nodes. Its accepted fractions are `1/512` and `1/2048`. The independent saved readback reconstructed all twenty source/model trial states and both accepted updates, including all sixteen original increment columns; the final twelve-digit output matches. It also checked 7,200 native metadata cells, both epochs of the coincident receiver, and all eight original observations. These are tiny invented-control results, not a real-data inverse.

The independent checker at `../hayward_trial_completion_review_002/check.py` verified 6,945 consumed file hashes and independently compared the original recipe list, actual joint state transitions and source AST. It imports neither the reviewer nor any numerical forward code. `reviewed_inputs`, `configuration`, the old eligibility main pin and scientific limits are unchanged.

The seven launcher checks exercise the actual `check_inverse` child/source prefix and stop deliberately at the first table read. The source call to the full trial reviewer is verified, but **a complete positive `check_inverse` final-table execution is not covered here**: the invented outputs retain their original initializer-zero setting, while the inherited field launcher requires initialization. No successful final flags are fabricated. A separately reviewed launcher bridge and complete final diagnostics remain necessary before scientific acceptance.

Summary SHA256: `f199d8fe4f199852249474a30060b6c918b6577a632f0a6ad64c97f7bb9bf30f`.

Independent review SHA256: `e975435edc021696f0e8766e6e7bcb15a45c8bfa2d09e09388ad4e35e2e7374c`.
