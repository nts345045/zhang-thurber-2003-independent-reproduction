#!/usr/bin/env python3
"""Own and reap one reviewed compile and the invented-only control command."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def now():return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def group_members(pgid):
    result=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==pgid and fields[0]!='Z':result.append(int(entry.name))
        except (FileNotFoundError,ProcessLookupError):continue
    return result


def stop_group(process):
    # Derived from the previously reviewed v3 process-group cleanup. Do not
    # freeze outputs while a compiler descendant remains a possible writer.
    signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
    for sig in (signal.SIGTERM,signal.SIGKILL):
        try:os.killpg(process.pid,sig)
        except ProcessLookupError:pass
        deadline=time.monotonic()+10
        while group_members(process.pid) and time.monotonic()<deadline:time.sleep(.1)
        if not group_members(process.pid):break
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:pass
    return dict(pgid=process.pid,live_members=group_members(process.pid),direct_child_reaped=process.poll() is not None)


def main():
    prepared=json.loads((HERE/'prepared.json').read_text())
    review=json.loads((HERE/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(HERE/'prepared.json'):
        raise ValueError('Require independent hash-bound preparation review')
    def verify():
        for root,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():
                if sha(root/name)!=digest:raise ValueError('Changed pinned source/input: '+name)
        for name,digest in prepared['runtime_sha256'].items():
            if sha(name)!=digest:raise ValueError('Changed runtime: '+name)
    verify()
    for name in ('execution.json','build','logs','cases','summary.json'):
        if (HERE/name).exists():raise ValueError('Preserve prior compile/control output: '+name)
    ledger=dict(status='running',controller_pid=os.getpid(),started_utc=now(),commands=[],
                prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
                input_sha256=prepared['input_sha256'],runtime_sha256=prepared['runtime_sha256'],
                environment=prepared['environment'],scope='Compile and invented controls only; zero native evaluations.')
    def write():
        temp=HERE/'execution.json.new'
        temp.write_text(json.dumps(ledger,indent=2,sort_keys=True,allow_nan=False)+'\n')
        temp.replace(HERE/'execution.json')
    write();(HERE/'build').mkdir();(HERE/'logs').mkdir()
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    unsettled=[];controls_started=False;code=1
    def command(stage,cmd):
        item=dict(stage=stage,command=cmd,started_utc=now());ledger['commands'].append(item);write()
        with (HERE/'logs'/ (stage+'.stdout.log')).open('x') as stdout,(HERE/'logs'/(stage+'.stderr.log')).open('x') as stderr:
            old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
            try:
                child=subprocess.Popen(cmd,cwd=str(ROOT),env=dict(os.environ,**prepared['environment']),
                                       stdout=stdout,stderr=stderr,start_new_session=True)
            except BaseException:
                signal.pthread_sigmask(signal.SIG_SETMASK,old_mask);raise
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
                item['pid']=child.pid;write();returned=child.wait()
                if returned!=0 or group_members(child.pid):raise RuntimeError(stage+' returned nonzero or left a live process group')
            except BaseException:
                state=stop_group(child);item['cleanup']=state
                if state['live_members'] or not state['direct_child_reaped']:unsettled.append(state)
                raise
            finally:
                item.update(return_code=child.returncode,child_reaped=child.poll() is not None,finished_utc=now());write()
    try:
        command('compile',prepared['compile_command'])
        binary=HERE/'build/metric_step';ledger['binary_sha256']=sha(binary);verify()
        controls_started=True
        command('controls',[ledger['binary_sha256'] if x=='COMPILED_BINARY_SHA256' else x for x in prepared['control_command']])
        summary=json.loads((HERE/'summary.json').read_text())
        if summary['status']!='passed' or not all(x.get('child_reaped') for x in summary['commands']):
            raise ValueError('Invented controls did not complete and reap every helper')
        verify();ledger['status']='completed';code=0
    except BaseException as exc:
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
    finally:
        # Inner C++ helpers use their own groups. A complete control summary is
        # required to attest their reaping after any interrupted controls stage.
        inner_reaped=not controls_started
        if controls_started:
            try:
                summary=json.loads((HERE/'summary.json').read_text())
                inner_reaped=all(x.get('child_reaped') for x in summary['commands'])
            except (OSError,ValueError,KeyError):inner_reaped=False
        stable=not unsettled and inner_reaped
        outputs={} if not stable else {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and (p.parts[len(HERE.parts)] in ('build','logs','cases') or p.name in ('summary.json','results.json','checks.json'))}
        ledger.update(return_code=code,finished_utc=now(),outputs_stable=stable,unsettled_groups=unsettled,
                      inner_helpers_reaped=inner_reaped,output_sha256=outputs)
        if (HERE/'summary.json').exists() and stable:ledger['summary_sha256']=sha(HERE/'summary.json')
        write()
    return code


if __name__=='__main__':sys.exit(main())
