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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/development/usable_curvature_integration_checks_001'
BUILD = ROOT / 'tmp/usable_curvature_integration_checks_controller_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


os.chdir(str(ROOT))
command = [sys.executable, 'diagnostics/run_usable_curvature_integration_checks.py', '--output', str(OUT.relative_to(ROOT)), '--build', 'tmp/usable_curvature_integration_checks_001']
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
    save(BUILD / 'launch.json', dict(controller_pid=os.getpid(), driver_pid=child.pid, started_utc=started,
         command=command, controller_sha256=sha(Path(__file__)), launcher_sha256=sha(ROOT/command[1]),
         candidate_prepared_sha256=sha(ROOT/'data/development/usable_curvature_integration_prepared_001/prepared.json'),
         logs_outside_native_inventory=True, threads=1))
    code = child.wait()
(OUT / 'controller_logs').mkdir()
shutil.copyfile(str(Path(__file__)),str(OUT/'controller.py'))
shutil.copyfile(str(BUILD/'launch.json'),str(OUT/'launch.json'))
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
