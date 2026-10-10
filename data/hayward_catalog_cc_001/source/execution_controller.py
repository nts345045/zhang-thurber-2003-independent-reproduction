#!/usr/bin/env python3
"""Record the single authorized offline preparation; no solver invocation."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUTPUT = ROOT/'data/hayward_catalog_cc_001'
ADAPTER = ROOT/'prepare_hayward_cc.py'
EXPECTED = '01e0707098bf63456a911a91bc5cde31418fb491901c38b88b0445f9be9ba641'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')

command = [sys.executable, 'prepare_hayward_cc.py', '--catalog-dir', 'data/hayward',
           '--export-summary', 'data/development/native_dt_cc_001/summary.json',
           '--export-review', 'data/development/native_dt_cc_001/independent_export_review.json',
           '--output', 'data/hayward_catalog_cc_001']
assert not OUTPUT.exists(), 'Fresh isolated output required'
assert sha(ADAPTER) == EXPECTED, 'Reviewed adapter source changed'
pins = {name: sha(ROOT/name) for name in (
    'data/development/hayward_cc_input_checks/002/summary.json',
    'data/development/hayward_cc_input_checks/002/root_review.json')}
record = dict(status='running', started_utc=utc(), command=command,
              source_sha256=EXPECTED, controller_source_sha256=sha(Path(__file__)),
              reviewed_controls_sha256=pins, python_version=sys.version,
              network_requests=0, solver_invocations=0, run_configuration_created=False,
              return_code=None)
save(HERE/'execution.json', record)
try:
    with (HERE/'stdout.log').open('wb') as out, (HERE/'stderr.log').open('wb') as err:
        child = subprocess.Popen(command, cwd=str(ROOT), stdout=out, stderr=err)
        record['child_pid'] = child.pid
        save(HERE/'execution.json', record)
        record['return_code'] = child.wait()
    assert record['return_code'] == 0, 'Preparation process failed'
    assert sha(ADAPTER) == EXPECTED, 'Adapter source changed during execution'
    for name, digest in pins.items():
        assert sha(ROOT/name) == digest, 'Reviewed control changed'
    manifest = OUTPUT/'preparation_manifest.json'
    record['preparation_manifest_sha256'] = sha(manifest)
    record['status'] = 'completed'
except BaseException as exc:
    record['status'] = 'failed'
    record['exception'] = type(exc).__name__+': '+str(exc)
    raise
finally:
    record['finished_utc'] = utc()
    record['log_sha256'] = {'execution_logs/'+name: sha(HERE/name)
                           for name in ('stdout.log', 'stderr.log') if (HERE/name).exists()}
    if OUTPUT.exists():
        (OUTPUT/'execution_logs').mkdir(exist_ok=True)
        for name in ('stdout.log', 'stderr.log'):
            if (HERE/name).exists():
                shutil.copyfile(str(HERE/name), str(OUTPUT/'execution_logs'/name))
        shutil.copyfile(str(Path(__file__)), str(OUTPUT/'source/execution_controller.py'))
        for name in ('initial_launch_source.py', 'initial_launch_failure.json'):
            shutil.copyfile(str(HERE/name), str(OUTPUT/'execution_logs'/name))
        record['preserved_initial_launch_sha256'] = {
            'execution_logs/'+name: sha(HERE/name)
            for name in ('initial_launch_source.py', 'initial_launch_failure.json')}
        save(OUTPUT/'execution.json', record)
    save(HERE/'execution.json', record)
