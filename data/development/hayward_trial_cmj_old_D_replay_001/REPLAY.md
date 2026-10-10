# Replay from published inputs

Use the published `first-arrival-integration` commit containing this CMJ package. The guarded failure archive is already present at integration commit `447674de4c24a673b8e404c26525ac685b7b75b1`, but that older commit alone does not contain the CMJ diagnostic. The guide does not assume the original large working directory still exists.

From that checkout's root, prepare an exclusive minimal scratch root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_trial_cmj_old_D_replay_001/prepare_replay.py tmp/cmj_replay_fresh
```

This verifies the existing lossless guarded-failure archive and restores **only the 14 required original members** to their historical relative paths inside scratch. It copies the other five original dependencies (adopted D core/helper, adoption receipt, integration review and strict4000 lifecycle runner), the exact 53 prepared CMJ files, `prepared.json` and `prelaunch_review.json`. It then imports the copied, unchanged `run.py` and calls **only `verify()`**. All 19 original, nine compiler/runtime and 53 prepared pins must pass. No compilation, receiver field, ray or inversion occurs in this preparation.

The original 413 MiB failed-path table is one of the required historical pins, so it is restored in scratch. Its bytes remain delivered only through `hayward_guarded_failure_001/archive/failed_run.tar.gz`; this package does not publish another copy. The helper refuses an existing scratch destination, symlink ancestors and parent traversal. It creates no execution ledger, build, logs or results in the fresh replay folder.

On the matching recorded compiler/runtime environment, the optional numerical replay is then:

```sh
mkdir tmp/cmj_replay_fresh/tmp
PYTHONDONTWRITEBYTECODE=1 python3 tmp/cmj_replay_fresh/data/development/hayward_trial_cmj_old_D_replay_REPLAY/run.py
```

That is the deliberately separate expensive step: one receiver field, four configured evaluations and eight trace subcalls, with the old status/path parity gate before D, four OpenMP threads and a 16 GiB address-space cap. The runner owns and reaps compiler/native process groups and records actual command exits. Use a durable supervisor if detaching it; do not kill an interactive parent and leave its child unmanaged. A rerun requires another fresh scratch name. Other compiler/runtime environments require explicitly reviewed provenance rather than edited hashes.

`replay_input_closure.json` records the completed **input-only** check in `tmp/cmj_replay_input_closure_001`: 14 members restored, five repository dependencies copied, 55 fresh replay files, all 19/9/53 pins passed, zero compiler/field/ray/inverse calls. The numerical attempt, summary, false flags and original terminal review were not altered.
