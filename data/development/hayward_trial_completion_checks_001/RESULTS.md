# Preserved first readback result

The approved 189 saved-table controls completed with **186 passes and three failed expectations**. All five intact successful C++ fixtures passed, as did the explicitly invented positive schema controls. No compiler, ray, reference or inverse ran. `execution.json`, `summary.json`, logs and every mutated fixture are preserved.

The three malformed tables were wrongly accepted by candidate001:

- `history_past_configured_end` retains two actual completed iterations but declares a one-iteration cap.
- `stage2_must_not_continue` supplies a hypothetical extra iteration after a stage-2 no-update termination.
- `coordinated_initial_state_shift` changes all saved iteration-zero accepted/trial origin times and their delta/status joins by one second, while leaving the actual initial input times unchanged. Spatial coordinates and paths are untouched, so rejection cannot depend on an unrelated endpoint mismatch.

These are completion-evidence gaps, not numerical ray failures. Candidate002 adds only an explicit iteration bound, the existing stage-2 termination rule, and the known initial numeric state anchor for an iteration-zero solve snapshot. Candidate001 and these failed cases remain unchanged. The initial patch still cannot reconstruct intermediate states for iterations without solve snapshots, or independently read back the final successful full-ray flags.

Summary SHA256: `73d75f3ce9ab1e18e5f11e06212159069957c0b60e59e9399473cfd207c29c15`.
