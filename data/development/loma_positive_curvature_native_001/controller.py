#!/usr/bin/env python3
"""Detached controller; keep live logs outside the frozen native inventory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BUILD = ROOT / json.loads((OUT / 'prepared.json').read_text())['build']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


os.chdir(str(ROOT))
command = [sys.executable, 'diagnostics/run_positive_curvature.py', '--phase', 'run', '--output', str(OUT.relative_to(ROOT))]
started = utc()
with (BUILD / 'controller_stdout.log').open('w') as stdout, (BUILD / 'controller_stderr.log').open('w') as stderr:
    child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                             env=dict(os.environ, OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT/'tmp')))

    def forward(signum, frame):
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, forward)
    save(OUT / 'launch.json', dict(controller_pid=os.getpid(), driver_pid=child.pid, started_utc=started,
         command=command, controller_sha256=sha(Path(__file__)), launcher_sha256=sha(ROOT/command[1]),
         prepared_sha256=sha(OUT/'prepared.json'), prelaunch_review_sha256=sha(OUT/'prelaunch_review.json'),
         logs_outside_native_inventory=True, threads=1))
    code = child.wait()
(OUT / 'controller_logs').mkdir()
for name in ('controller_stdout.log', 'controller_stderr.log'):
    shutil.copyfile(str(BUILD/name), str(OUT/'controller_logs'/name))
receipt = dict(status='completed' if code == 0 else 'failed', controller_pid=os.getpid(), driver_pid=child.pid,
               driver_return_code=code, started_utc=started, finished_utc=utc(), launch_sha256=sha(OUT/'launch.json'),
               controller_sha256=sha(Path(__file__)), child_reaped=True,
               log_sha256={str(p.relative_to(OUT)):sha(p) for p in (OUT/'controller_logs').iterdir()})
for name in ('summary.json','execution.json'):
    if (OUT/name).exists():
        receipt[name.replace('.json','')+'_sha256'] = sha(OUT/name)
save(OUT/'controller_completion.json', receipt)
sys.exit(code)
