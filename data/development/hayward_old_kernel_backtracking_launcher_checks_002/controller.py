"""Own the bounded launcher harness; keep open driver logs outside its artifact tree."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STATE=ROOT/'tmp/old_kernel_backtracking_launcher_checks_002_controller/execution.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(p):return json.loads(p.read_text())
def save(value):
 p=STATE.with_suffix('.json.new');p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');os.replace(str(p),str(STATE))
def main():
 if (HERE/'execution.json').exists():raise RuntimeError('Preserve existing execution')
 p=load(HERE/'prepared.json');r=load(HERE/'prelaunch_review.json')
 if r['status']!='passed' or r['prepared_sha256']!=sha(HERE/'prepared.json'):raise RuntimeError('Require current prelaunch review')
 harness=ROOT/'diagnostics/check_old_kernel_backtracking_launcher.py'
 if sha(harness)!=p['harness_sha256']:raise RuntimeError('Harness source changed')
 logs=ROOT/'tmp/old_kernel_backtracking_launcher_checks_002_controller';logs.mkdir()
 command=[sys.executable,str(harness),'--output',str(HERE.relative_to(ROOT))]
 ledger=dict(status='running',started_utc=now(),controller_pid=os.getpid(),command=command,
             prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
             controller_sha256=sha(Path(__file__)),harness_sha256=sha(harness),scientific_success=False)
 save(ledger)
 with (logs/'stdout.log').open('x') as a,(logs/'stderr.log').open('x') as b:
  process=subprocess.Popen(command,cwd=str(ROOT),stdout=a,stderr=b,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),start_new_session=True)
  ledger['child_pid']=process.pid;save(ledger);code=process.wait()
 for name in ('stdout','stderr'):shutil.copyfile(str(logs/(name+'.log')),str(HERE/('driver_'+name+'.log')))
 ledger.update(status='completed' if code==0 else 'failed_preserved',return_code=code,child_reaped=process.poll() is not None,
               finished_utc=now(),summary_sha256=sha(HERE/'summary.json') if (HERE/'summary.json').exists() else None,
               log_sha256={name:sha(HERE/name) for name in ('driver_stdout.log','driver_stderr.log')})
 save(ledger)
 shutil.copyfile(str(STATE),str(HERE/'execution.json'))
 print(json.dumps(dict(status=ledger['status'],return_code=code,summary_sha256=ledger['summary_sha256'])))
 raise SystemExit(code)
if __name__=='__main__':main()
