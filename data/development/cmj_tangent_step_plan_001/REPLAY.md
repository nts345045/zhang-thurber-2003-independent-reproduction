# Inspect or replay the saved tangent-step experiment

Use the exact published `first-arrival-integration` commit in a **fresh
disposable checkout below the project's `tmp/` directory**. Keep the original
checkout and completed packages unchanged. The five packages are published
directly, including both executed `build/metric_step` files and closed logs;
no archive restoration or system-binary replacement is needed.

The failed `cmj_tangent_step_source_001` preserves its signed-zero serialization
failure. The corrected `cmj_tangent_step_source_002` preserves 50 passed
invented checks. Read its `RESULTS.md` and the native package's `RESULTS.md`
alongside the immutable preparation-time README files.

## Restore the authored input-map dependency

The native preparation pins `tmp/cmj_tangent_native_input_map_001.md`.
[native_input_map.md](native_input_map.md) is its byte-exact published copy
(8,117 bytes, SHA-256
`2122e564e394e79917ecaf65c3d41974e4b50b89f8532b314c2fd3a65a1ff151`).
From the fresh checkout root, restore only that authored document:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
src = Path('data/development/cmj_tangent_step_plan_001/native_input_map.md')
dst = Path('tmp/cmj_tangent_native_input_map_001.md')
data = src.read_bytes()
assert hashlib.sha256(data).hexdigest() == '2122e564e394e79917ecaf65c3d41974e4b50b89f8532b314c2fd3a65a1ff151'
assert not dst.parent.is_symlink() and not dst.is_symlink()
dst.parent.mkdir(exist_ok=True)
if dst.exists():
    assert dst.is_file() and dst.read_bytes() == data
else:
    with dst.open('xb') as stream:
        stream.write(data)
PY
```

This restores a document, not process state. No frozen preparation or native
identifier is rewritten. The existing CMJ starting paths, action/component
records, authoritative observations and prior reviews remain at their pinned
published paths. System compiler, Python and library hashes are prerequisites
recorded in each preparation; a mismatch must remain a mismatch.

## Prepare one numerical replay in that disposable checkout

Use a separate fresh checkout for each choice below. These controllers refuse
completed output directories. The following block retains the completed
package as `_SAVED` and creates only its original preparation inventory at the
original package path. Set `TANGENT_PACKAGE` to exactly one of:

- `cmj_tangent_step_source_001` — reproduce the preserved invented failure;
- `cmj_tangent_step_source_002` — repeat the corrected invented controls;
- `hayward_cmj_tangent_step_001` — repeat the bounded two-polygon diagnostic.

```sh
export TANGENT_PACKAGE=hayward_cmj_tangent_step_001
python3 - <<'PY'
from pathlib import Path
import hashlib, json, os, shutil
name = os.environ['TANGENT_PACKAGE']
assert name in ('cmj_tangent_step_source_001', 'cmj_tangent_step_source_002',
                'hayward_cmj_tangent_step_001')
base = Path('data/development') / name
saved = base.with_name(name + '_SAVED')
assert base.is_dir() and not base.is_symlink()
assert not saved.exists() and not saved.is_symlink()
prepared = json.loads((base / 'prepared.json').read_text())
review = json.loads((base / 'prelaunch_review.json').read_text())
assert review['status'] == 'passed'
assert review['prepared_sha256'] == hashlib.sha256((base / 'prepared.json').read_bytes()).hexdigest()
for rel, digest in prepared['output_sha256'].items():
    assert hashlib.sha256((base / rel).read_bytes()).hexdigest() == digest
base.rename(saved)
base.mkdir()
for rel in list(prepared['output_sha256']) + ['prepared.json', 'prelaunch_review.json']:
    target = base / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists() and not target.is_symlink()
    shutil.copy2(str(saved / rel), str(target))
if name == 'cmj_tangent_step_source_001':
    # Historical original-source pins differ from the published 002 helpers.
    # Restore them only in this disposable checkout; both versions stay saved.
    for rel in ('diagnostics/tangent_metric_step.cpp',
                'diagnostics/check_tangent_metric_step.py'):
        target = Path(rel)
        assert target.is_file() and not target.is_symlink()
        data = (saved / 'source' / rel).read_bytes()
        assert hashlib.sha256(data).hexdigest() == prepared['input_sha256'][rel]
        target.write_bytes(data)
print(base / ('run.py' if name.startswith('hayward_') else 'controller.py'))
PY
```

Run the printed script in the foreground with the recorded interpreter,
`PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 SCRIPT`. The invented
controllers compile their own small fixture with the recorded flags; the
native wrapper reuses the unchanged published 002 binary (SHA-256
`bb637be19c82175afac2bc1d99036f1f11efb4f629834d2d57d24a5bbc2dbb9f`,
mode `0755`) and performs no compilation. The recorded `TMPDIR` is
machine-specific and must already exist inside the project. Compilers may use
that directory outside the disposable checkout but within the same project.
This receipt-level replay requires the recorded environment. A portable rerun
needs a separately documented new preparation, never edits to historical pins.

Keep each new execution's outputs and failures. Historical terminal reviews
describe the saved executions and must not be relabeled as reviews of a new
run. The native scope remains two metric solves, at most two rounded trials
and 2,058 new edge actions; it does not trace, invert, certify a first arrival
or change the original failed convergence flags. No maintained solver source
or main-branch baseline needs to change.
