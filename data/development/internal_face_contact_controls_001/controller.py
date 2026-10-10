#!/usr/bin/env python3
"""Own one frozen compile and invented controls, including their helper group."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def now(): return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def group_members(pgid):
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            fields = (entry/'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z': result.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError): pass
    return result


def stop_group(process):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try: os.killpg(process.pid, sig)
        except ProcessLookupError: pass
        deadline = time.monotonic()+10
        while group_members(process.pid) and time.monotonic() < deadline: time.sleep(.1)
        if not group_members(process.pid): break
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired: pass
    return dict(pgid=process.pid, live_members=group_members(process.pid),
                direct_child_reaped=process.poll() is not None)


def main():
    prepared = json.loads((HERE/'prepared.json').read_text())
    review = json.loads((HERE/'prelaunch_review.json').read_text())
    if review.get('status') != 'passed' or review.get('prepared_sha256') != sha(HERE/'prepared.json'):
        raise ValueError('Require hash-bound root prelaunch review')
    def verify():
        for base, pins in ((ROOT, prepared['input_sha256']), (HERE, prepared['output_sha256'])):
            for name, digest in pins.items():
                if sha(base/name) != digest: raise ValueError('Changed source/input: '+name)
        for name, digest in prepared['runtime_sha256'].items():
            if sha(name) != digest: raise ValueError('Changed runtime: '+name)
        if sha(sys.executable) != prepared['python']['sha256']: raise ValueError('Changed Python')
    verify()
    for name in ('execution.json', 'build', 'logs', 'results'):
        if (HERE/name).exists(): raise ValueError('Preserve prior output: '+name)
    os.environ.update(prepared['environment'])
    ledger = dict(status='running', controller_pid=os.getpid(), started_utc=now(), commands=[],
                  prepared_sha256=sha(HERE/'prepared.json'), prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
                  environment=prepared['environment'], scope='Invented contacts only; no native, trace, field or inversion calls.')
    def write():
        temp = HERE/'execution.json.new'
        temp.write_text(json.dumps(ledger, indent=2, sort_keys=True, allow_nan=False)+'\n')
        temp.replace(HERE/'execution.json')
    def interrupted(sig, unused): raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    write(); (HERE/'build').mkdir(); (HERE/'logs').mkdir()
    unsettled = []; code = 1
    def command(stage, args):
        item = dict(stage=stage, command=args, started_utc=now()); ledger['commands'].append(item); write()
        with (HERE/'logs'/(stage+'.stdout.log')).open('x') as stdout, (HERE/'logs'/(stage+'.stderr.log')).open('x') as stderr:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
            try:
                # This controller is single-threaded. Restore the inherited
                # mask in the child while retaining parent PID-before-unmask.
                child = subprocess.Popen(args, cwd=str(ROOT), env=os.environ.copy(), stdout=stdout,
                                         stderr=stderr, start_new_session=True,
                                         preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, mask))
            except BaseException:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask); raise
            try:
                item['pid'] = child.pid; write()
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                returned = child.wait()
                if returned != 0 or group_members(child.pid):
                    raise RuntimeError(stage+' failed or left a live process-group member')
            except BaseException:
                state = stop_group(child); item['cleanup'] = state
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                if state['live_members'] or not state['direct_child_reaped']: unsettled.append(state)
                raise
            finally:
                item.update(return_code=child.returncode, child_reaped=child.poll() is not None, finished_utc=now())
                write()
    try:
        command('compile', prepared['compile_command'])
        ledger['binary_sha256'] = sha(HERE/'build/observe'); verify(); write()
        command('controls', [ledger['binary_sha256'] if x == 'COMPILED_BINARY_SHA256' else x
                             for x in prepared['control_command']])
        summary = json.loads((HERE/'results/summary.json').read_text())
        if summary['status'] != 'passed' or not all(c['child_reaped'] and c['return_code'] == 0 for c in summary['commands']):
            raise ValueError('Control summary or helper reaping failed')
        verify(); ledger['status'] = 'completed'; code = 0
    except BaseException as exc:
        if isinstance(exc, SystemExit) and isinstance(exc.code, int): code = exc.code
        ledger.update(status='failed_preserved', error=dict(type=type(exc).__name__, message=str(exc)))
    finally:
        stable = not unsettled and all(c.get('child_reaped') for c in ledger['commands'])
        outputs = {} if not stable else {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and (p.parts[len(HERE.parts)] in ('build', 'logs', 'results'))}
        ledger.update(return_code=code, finished_utc=now(), outputs_stable=stable,
                      unsettled_groups=unsettled, output_sha256=outputs)
        if stable and (HERE/'results/summary.json').exists(): ledger['summary_sha256'] = sha(HERE/'results/summary.json')
        write()
    return code


if __name__ == '__main__': sys.exit(main())
