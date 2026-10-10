"""Durable owner of one reviewed old-kernel attempt; no automatic next mode."""
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
sys.path.insert(0,str(ROOT))
from run_loma_analytic_simulation import atomic_json,sha,utc,verify_hashes
from run_loma_initial_preflight import live_group_members,require


def load(path):return json.loads(path.read_text())


def main():
    plan=load(HERE/'plan.json');review=load(HERE/'launch_review.json')
    require(review['status']=='passed' and review['plan_sha256']==sha(HERE/'plan.json') and
            review['controller_sha256']==sha(Path(__file__)), 'Require the exact final launch review')
    require(plan['status']=='prepared_not_launched' and not plan['inverse_launched'], 'Unexpected plan state')
    verify_hashes(ROOT,plan['input_sha256'])
    for name,digest in plan['source_sha256'].items():
        source=ROOT/plan['source_adoption']['source_mapping'].get(name,name)
        require(sha(source)==digest,'Changed exact launch source: '+name)
    for name,digest in plan['runtime_sha256'].items():require(sha(Path(name))==digest,'Changed launch runtime: '+name)
    require(sha(Path(plan['python']))==plan['python_sha256'],'Changed Python executable')
    out,build=ROOT/plan['output'],ROOT/plan['build']
    require(not out.exists() and not out.is_symlink() and not build.exists() and not build.is_symlink(),
            'Preserve existing output/build; no restart')
    logs=ROOT/'tmp/hayward_old_kernel_backtracking_controllers/001';logs.mkdir(parents=True)
    state=logs/'execution.json'
    ledger=dict(status='running',started_utc=utc(),controller_pid=os.getpid(),command=plan['command'],
                plan_sha256=sha(HERE/'plan.json'),launch_review_sha256=sha(HERE/'launch_review.json'),
                controller_sha256=sha(Path(__file__)),reviewed_base_commit=plan['reviewed_base_commit'],
                actual_launch_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),universal_newlines=True).strip(),
                scientific_success=False)
    atomic_json(state,ledger);process=None
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def recorded_inner_group():
        path=out/'dd_inversion_execution.json'
        if path.exists() and process is not None:
            inner=load(path)
            require(inner['driver_pid']==process.pid,'Inner ledger belongs to another launcher')
            return inner.get('current_child_pid')
        return None
    def cleanup_group():
        try:return recorded_inner_group()
        except Exception as error:
            # Keep the original failure; a malformed ledger cannot identify a
            # process group safely and must not permit partial-output hashing.
            ledger.setdefault('cleanup_errors',[]).append(type(error).__name__+': '+str(error))
            ledger['group_inventory_unresolved']=True
            return None
    def stop_group(group):
        if group is None:return
        for sig in (signal.SIGTERM,signal.SIGKILL):
            try:os.killpg(group,sig)
            except ProcessLookupError:pass
            deadline=time.monotonic()+10
            while live_group_members(group) and time.monotonic()<deadline:time.sleep(.05)
            if not live_group_members(group):return
    try:
        with (logs/'driver_stdout.log').open('x') as stdout,(logs/'driver_stderr.log').open('x') as stderr:
            process=subprocess.Popen(plan['command'],cwd=str(ROOT),stdout=stdout,stderr=stderr,
                                     env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),start_new_session=True)
            ledger['launcher_pid']=process.pid;atomic_json(state,ledger);code=process.wait()
        group=recorded_inner_group()
        # A killed launcher may leave its separately grouped numerical child.
        # Preserve the failure and settle that owned group before hashing logs.
        orphaned=group is not None and bool(live_group_members(group))
        if orphaned:
            ledger['orphaned_inner_group']=group;stop_group(group)
        remaining=live_group_members(group) if group is not None else []
        require(not remaining,'Owned numerical process-group writers remain')
        require(not orphaned,'Launcher exited with live numerical writers; owned group settled, failure preserved')
        ledger.update(status='launcher_reaped' if code==0 else 'failed_preserved',return_code=code,
                      launcher_reaped=process.poll() is not None,remaining_live_group_members=[])
        inner_path=out/'dd_inversion_execution.json'
        if code==0:require(inner_path.is_file(),'Missing successful launcher ledger')
        if inner_path.exists():
            inner=load(inner_path)
            ledger['inner_execution_sha256']=sha(inner_path);ledger['inner_status']=inner['status']
            if code==0:require(inner['status']=='completed_pending_final_diagnostics' and inner['return_code']==0,
                               'Zero launcher exit without terminal completed output contract')
    except BaseException as error:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:process.wait(timeout=35)  # Allow the tested launcher to settle its inner group first.
            except subprocess.TimeoutExpired:
                stop_group(cleanup_group());process.kill();process.wait()
        group=cleanup_group();stop_group(group)
        remaining=live_group_members(group) if group is not None else []
        ledger.update(status='interrupted' if isinstance(error,(SystemExit,KeyboardInterrupt)) else 'failed_preserved',
                      error=str(error),return_code=getattr(error,'code',1),
                      launcher_reaped=process is None or process.poll() is not None,
                      launcher_return_code=process.returncode if process is not None else None,
                      remaining_live_group_members=remaining)
    ledger['finished_utc']=utc()
    if ledger.get('remaining_live_group_members') or ledger.get('group_inventory_unresolved'):
        ledger['partial_hash_status']='withheld: live or unidentified owned process-group writers may remain'
    else:
        ledger['log_sha256']={name:sha(logs/name) for name in ('driver_stdout.log','driver_stderr.log') if (logs/name).exists()}
        inner_path=out/'dd_inversion_execution.json'
        if inner_path.exists():ledger['inner_execution_sha256']=sha(inner_path)
        ledger['partial_hash_status']='Only closed controller logs and the saved launcher ledger after recorded groups settle are pinned here; its original status is preserved and numerical outputs belong to that ledger.'
    atomic_json(state,ledger)
    exit_code=ledger.get('return_code',1)
    if ledger['status']=='launcher_reaped':exit_code=0
    elif not isinstance(exit_code,int) or exit_code==0:exit_code=1
    elif exit_code<0:exit_code=128-exit_code
    raise SystemExit(exit_code)


if __name__=='__main__':main()
