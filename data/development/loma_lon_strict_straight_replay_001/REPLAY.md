# Reproduce the two strict-stopping diagnostics

Use an exact published `first-arrival-integration` commit containing both
`loma_lon_strict_straight_replay_001` (1,000-update cap) and
`loma_lon_strict_straight_4000_replay_001` (4,000-update cap). The committed
packages are immutable evidence. Their runners refuse an existing execution
ledger; retain those ledgers and run fresh sibling copies instead.

From the project checkout, replace `DELIVERY_COMMIT` with that commit:

```sh
lon_strict_checkout="$PWD/tmp/lon_strict_replay_checkout_NEW"
test ! -e "$lon_strict_checkout"
git worktree add --detach "$lon_strict_checkout" DELIVERY_COMMIT
cd "$lon_strict_checkout"
```

The following copies only each package's prepared-file inventory and its
preparation/review records. It verifies the original-input and compiler/runtime
hashes using the existing runner without invoking its execution entry point.
All writes are exclusive and confined to the fresh scratch checkout.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
root = Path.cwd().resolve()
if root.parent.name != 'tmp' or root.name != 'lon_strict_replay_checkout_NEW':
    raise RuntimeError('Run inside the new project-local scratch checkout')

for name in ('loma_lon_strict_straight_replay_001',
             'loma_lon_strict_straight_4000_replay_001'):
    source = root / 'data/development' / name
    prepared_bytes = (source / 'prepared.json').read_bytes()
    prepared = json.loads(prepared_bytes.decode())
    review = json.loads((source / 'prelaunch_review.json').read_text())
    if (review.get('status') != 'passed' or
        review.get('prepared_sha256') != hashlib.sha256(prepared_bytes).hexdigest()):
        raise RuntimeError('Preparation review does not bind this package: ' + name)
    dest = source.with_name(name + '_REPLAY')
    dest.mkdir()
    names = set(prepared['output_sha256']) | {'prepared.json', 'prelaunch_review.json'}
    for relative in sorted(names):
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise RuntimeError('Unsafe prepared member: ' + relative)
        payload = (source / path).read_bytes()
        expected = prepared['output_sha256'].get(relative)
        if expected and hashlib.sha256(payload).hexdigest() != expected:
            raise RuntimeError('Prepared member hash mismatch: ' + relative)
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(payload)
    spec = importlib.util.spec_from_file_location('strict_replay_runner', str(dest / 'run.py'))
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.verify(prepared)
    if any((dest / p).exists() for p in ('execution.json', 'build', 'results', 'logs', 'summary.json')):
        raise RuntimeError('A prepared replay unexpectedly contains runtime outputs')
    print('Verified fresh prepared replay:', dest.relative_to(root))
PY
```

All original-input pins refer to preserved files in the committed checkout.
The 4,000-update package consumes the saved 1,000-update evidence at its original
path; it does not substitute the results of the new 1,000-update replay. Do not
regenerate either `prepared.json`, edit pinned sources, or replace compiler or
system-library files to make a hash check pass. A missing or changed dependency
is an explicit reproduction failure.

Run each existing runner from its fresh sibling directory:

```sh
(
  cd data/development/loma_lon_strict_straight_replay_001_REPLAY
  PYTHONDONTWRITEBYTECODE=1 python3 run.py
)
(
  cd data/development/loma_lon_strict_straight_4000_replay_001_REPLAY
  PYTHONDONTWRITEBYTECODE=1 python3 run.py
)
```

Each runner compiles its frozen source and makes exactly two straight-initialized
trace calls, for identified pairs 8670 and 8674. It writes a new execution
ledger, binary hashes, logs and full identified output tables. It does not
construct an FMM field or perform an inverse solve. Strict flags, time/source
accuracy and termination at the update cap remain separate outcomes. The saved
prelaunch reviews bind identical prepared sources and inputs; they do not
prejudge the results of the new executions.
