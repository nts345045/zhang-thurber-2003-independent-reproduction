#!/usr/bin/env python3
"""Own, wait for, and reap the single reviewed fixed-polygon calculation."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def now():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def main():
    assert sha(HERE / 'prepared.json') == 'b76991263bddbaaaa75fd90b858f800fb4ec5339e40782b6aff8cf94f117ec08'
    assert sha(HERE / 'prelaunch_review.json') == '1ce2a61a1156b31f56405f929578bee783f89780c1d8adf75c753c6aa21804fb'
    assert not (HERE / 'execution.json').exists()
    plan = json.loads((HERE / 'prepared.json').read_text())
    python = plan['python']['executable']
    assert sha(python) == plan['python']['executable_sha256']
    command = [python, 'diagnostics/check_cmj_face_action.py', '--output', str(HERE.relative_to(ROOT))]
    receipt = dict(status='running', controller_pid=os.getpid(), controller_sha256=sha(Path(__file__)),
                   command=command, environment=plan['environment'], started_utc=now(),
                   prepared_sha256=sha(HERE / 'prepared.json'),
                   prelaunch_review_sha256=sha(HERE / 'prelaunch_review.json'),
                   python_sha256=plan['python']['executable_sha256'])
    child = None
    signals = []

    def forward(sig, frame):
        signals.append(sig)
        if child is not None and child.poll() is None:
            child.send_signal(sig)

    signal.signal(signal.SIGINT, forward)
    signal.signal(signal.SIGTERM, forward)
    with (HERE / 'execution.json').open('x') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write('\n')
    with (HERE / 'stdout.log').open('x') as out, (HERE / 'stderr.log').open('x') as err:
        child = subprocess.Popen(command, cwd=str(ROOT), stdout=out, stderr=err, start_new_session=True,
                                 env=dict(os.environ, **plan['environment']))
        receipt['child_pid'] = child.pid
        temporary = HERE / 'execution.json.new'
        temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        temporary.replace(HERE / 'execution.json')
        try:
            code = child.wait()
        except BaseException:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            child.wait()
            raise
    receipt.update(status='completed' if code == 0 else 'failed', child_reaped=child.poll() is not None,
                   return_code=code, received_signals=signals, finished_utc=now(),
                   output_sha256={p.name: sha(p) for p in [HERE / 'stdout.log', HERE / 'stderr.log', HERE / 'summary.json',
                                                         HERE / 'model_provenance.json'] + list(HERE.glob('event_*.json.gz'))
                                  if p.is_file()})
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    temporary.replace(HERE / 'execution.json')
    print(json.dumps(receipt, sort_keys=True))
    return 128 + signals[0] if signals else code


if __name__ == '__main__':
    sys.exit(main())
