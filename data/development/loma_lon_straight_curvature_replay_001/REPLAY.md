# Fresh-checkout reproduction

The completed package is immutable. `run_v3.py` refuses an existing execution ledger, so do not delete that ledger or replay into this directory. The original task is limited to four trace calls; this guide describes a separate reproduction and was not executed during that task.

Use a newly created checkout of the exact delivery commit that contains this package and the adopted D source. Create it under the project `tmp/` directory, rather than outside the project. For example, from the integration repository, replace `DELIVERY_COMMIT` with that published commit:

```sh
lon_replay_checkout="$PWD/tmp/lon_straight_replay_checkout_NEW"
test ! -e "$lon_replay_checkout"
git worktree add --detach "$lon_replay_checkout" DELIVERY_COMMIT
cd "$lon_replay_checkout"
```

Every historical original-input pin is tracked in that commit except one inert CMake flags text file. Its exact copy is already frozen as `inputs/old_flags.make`. The following preparation restores that file only to an absent path in the new checkout, and copies only prepared files into a fresh replay package. It does not modify the original live checkout, compiler, libraries, completed outputs or existing files:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib
import json
from pathlib import Path
import shutil

root = Path.cwd().resolve()
if root.parent.name != 'tmp' or root.name != 'lon_straight_replay_checkout_NEW':
    raise RuntimeError('Run only inside the newly created project-local scratch checkout')
source = root / 'data/development/loma_lon_straight_curvature_replay_001'
prepared = json.loads((source / 'prepared_v3.json').read_text())
relative = 'tmp/loma_initial_preflight_runs/lon_001/compiled/CMakeFiles/dd.dir/flags.make'
data = (source / 'inputs/old_flags.make').read_bytes()
if hashlib.sha256(data).hexdigest() != prepared['original_sha256'][relative]:
    raise RuntimeError('Frozen flags file does not match its historical pin')
target = root / relative
target.parent.mkdir(parents=True, exist_ok=True)
with target.open('xb') as handle:
    handle.write(data)
dest = root / 'data/development/loma_lon_straight_curvature_replay_REPLAY'
dest.mkdir()
names = set(prepared['output_sha256']) | {'prepared_v3.json', 'prelaunch_review.json'}
for name in sorted(names):
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as handle:
        handle.write((source / name).read_bytes())
print(dest)
PY
```

The original compiler and runtime hash requirements remain active. This is an exact historical source/runtime reproduction, not permission to substitute different compiler libraries or a newer production core. If any pin fails, preserve the failure rather than overwriting a live compiler directory or changing the manifest. Once reproduction is separately authorized, run `python3 run_v3.py` from the fresh `..._REPLAY` directory. It again executes two old calls, checks all original 12-significant-digit physical/status/native fields, and only then executes the two D calls.

The fresh destination receives no old execution ledger, binary, result table or terminal summary. The historical prelaunch review is retained as the review of the identical source, inputs and four-call contract; a new execution gets its own ledger, compiler commands, binary hashes and output hashes. No history instrumentation or FMM field construction is added by this guide.
