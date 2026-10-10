#!/usr/bin/env python3
"""Own and reap one bounded invented-control runner; preserve closed outer logs."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKAGE = ROOT / 'data/development/hayward_full_dd_geometry_export_controls_002'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
if sha(PACKAGE/'prepared.json') != '833201e5c9b6156d34940208972508a94c36b21c6b56b5a3d3f6d0febe4243bb':
    raise RuntimeError('Prepared controls changed')
if sha(PACKAGE/'prelaunch_review.json') != '2b127dcf79caf6aa39fb4e0af729bafcc2d5bd464e245b2a743c7c3853f17d57':
    raise RuntimeError('Prelaunch review changed')
prepared = json.loads((PACKAGE/'prepared.json').read_text())
child = None
interruptions = []
def forward(sig, frame):
    interruptions.append(sig)
    if child is not None and child.poll() is None:
        child.send_signal(sig)
signal.signal(signal.SIGINT, forward)
signal.signal(signal.SIGTERM, forward)
argv = [prepared['python'], str(PACKAGE/'run.py')]
receipt = {'status':'running', 'controller_pid':os.getpid(), 'command':argv,
           'started_utc':now(), 'controller_sha256':sha(__file__)}
with (HERE/'started.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
with (HERE/'stdout.log').open('x') as out, (HERE/'stderr.log').open('x') as err:
    child = subprocess.Popen(argv,cwd=str(ROOT),stdout=out,stderr=err,start_new_session=True,
                             env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    receipt['child_pid'] = child.pid
    try:
        code = child.wait()
    except BaseException:
        if child.poll() is None:child.send_signal(signal.SIGTERM)
        child.wait()
        raise
receipt.update(status='completed', finished_utc=now(), child_return_code=code,
               child_reaped=child.poll() is not None, received_signals=interruptions,
               stdout_sha256=sha(HERE/'stdout.log'),stderr_sha256=sha(HERE/'stderr.log'))
receipt['execution_sha256'] = sha(PACKAGE/'execution.json')
if (PACKAGE/'summary.json').exists():receipt['summary_sha256'] = sha(PACKAGE/'summary.json')
with (HERE/'completion.json').open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
dest = PACKAGE/'controller_provenance';dest.mkdir()
for name in ('controller.py','started.json','stdout.log','stderr.log','completion.json'):
    shutil.copyfile(str(HERE/name),str(dest/name))
print(json.dumps(receipt,sort_keys=True))
sys.exit(128+interruptions[0] if interruptions else code)
