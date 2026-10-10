#!/usr/bin/env python3
"""Record the authorized sequential availability inventory; never request samples."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = HERE / 'inventory_execution.json'
    ledger = dict(status='running', started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        scope='Complete original 14,262-window availability inventory; empty supported results retained; no waveform samples',
        controller_sha256=sha(Path(__file__)), acquisition_source_sha256=sha(HERE / 'acquire.py'), stages=[])
    with path.open('x') as f:
        json.dump(ledger, f, indent=2); f.write('\n')
    try:
        for stage, count in [('routable_availability', 142), ('cmw1_availability', 2)]:
            command = ['python3', str((HERE / 'acquire.py').relative_to(ROOT)), stage, '--fetch',
                '--batches', str(count), '--inventory-no-spans', '--summary', stage + '_all_001.json']
            record = dict(stage=stage, status='running', command=command)
            ledger['stages'].append(record)
            path.write_text(json.dumps(ledger, indent=2) + '\n')
            started = time.monotonic()
            with (HERE / (stage + '_stdout.log')).open('xb') as out, (HERE / (stage + '_stderr.log')).open('xb') as err:
                child = subprocess.Popen(['/usr/bin/time', '-v', '-o', str(HERE / (stage + '_resources.txt'))] + command,
                    cwd=str(ROOT), stdout=out, stderr=err, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
                record['supervised_pid'] = child.pid
                path.write_text(json.dumps(ledger, indent=2) + '\n')
                code = child.wait()
            record.update(status='completed' if code == 0 else 'failed', returncode=code,
                seconds=time.monotonic() - started,
                output_sha256={stage + suffix:sha(HERE / (stage + suffix)) for suffix in
                    ('_stdout.log', '_stderr.log', '_resources.txt', '_all_001.json')})
            if sha(HERE / 'acquire.py') != ledger['acquisition_source_sha256']:
                raise ValueError('Acquisition source changed during the inventory')
            path.write_text(json.dumps(ledger, indent=2) + '\n')
            if code:
                raise RuntimeError('Inventory stopped at an access or identity failure')
        ledger['status'] = 'completed'
    except BaseException as error:
        ledger.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        ledger['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        path.write_text(json.dumps(ledger, indent=2) + '\n')


if __name__ == '__main__':
    main()
