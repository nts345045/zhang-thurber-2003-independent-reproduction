#!/usr/bin/env python3
"""Own and reap the reviewed runner; keep live controller logs separate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
LIVE = ROOT / 'tmp/hayward_trial_cmj_controller_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


os.chdir(str(ROOT))
if (OUT / 'execution.json').exists() or (OUT / 'launch.json').exists():
    raise RuntimeError('This exclusive replay has already been launched')
review = json.loads((OUT / 'prelaunch_review.json').read_text())
if review.get('status') != 'passed' or review['prepared_sha256'] != sha(OUT / 'prepared.json'):
    raise RuntimeError('Missing passed preparation review')
LIVE.mkdir()
child = None
pending_signals = []


def forward(signum, frame):
    pending_signals.append(signum)
    if child is not None:
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass


for signum in (signal.SIGTERM, signal.SIGINT):
    signal.signal(signum, forward)
command = [sys.executable, str(OUT / 'run.py')]
started = utc()
with (LIVE / 'stdout.log').open('x') as stdout, (LIVE / 'stderr.log').open('x') as stderr:
    if pending_signals:
        raise RuntimeError('Controller interrupted before runner launch')
    child = subprocess.Popen(command, cwd=str(ROOT), stdout=stdout, stderr=stderr, start_new_session=True,
                             env=dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                                      LC_ALL='C', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')))
    try:
        # Also deliver a signal received in the small Popen/assignment interval.
        for signum in pending_signals:
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass
        save(OUT / 'launch.json', dict(controller_pid=os.getpid(), driver_pid=child.pid,
             started_utc=started, command=command, controller_sha256=sha(Path(__file__)),
             runner_sha256=sha(OUT / 'run.py'), prepared_sha256=sha(OUT / 'prepared.json'),
             prelaunch_review_sha256=sha(OUT / 'prelaunch_review.json'),
             live_logs=str(LIVE.relative_to(ROOT)), controller_owns_driver_wait=True))
        code = child.wait()
    except BaseException:
        forward(signal.SIGTERM, None)
        # The reviewed runner terminates/reaps its own compiler/native groups.
        child.wait()
        raise
(OUT / 'controller_logs').mkdir()
for name in ('stdout.log', 'stderr.log'):
    shutil.copyfile(str(LIVE / name), str(OUT / 'controller_logs' / name))
receipt = dict(status='completed' if code == 0 else 'failed_preserved', controller_pid=os.getpid(),
               driver_pid=child.pid, driver_return_code=code, child_reaped=True,
               started_utc=started, finished_utc=utc(), forwarded_signals=pending_signals,
               launch_sha256=sha(OUT / 'launch.json'), controller_sha256=sha(Path(__file__)),
               log_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted((OUT / 'controller_logs').iterdir())})
for name in ('summary.json', 'execution.json', 'old_parity.json'):
    if (OUT / name).exists():
        receipt[name.replace('.json', '') + '_sha256'] = sha(OUT / name)
save(OUT / 'controller_completion.json', receipt)
sys.exit(code)
