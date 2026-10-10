#!/usr/bin/env python3
import os,sys,json,hashlib,subprocess,signal,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'data/development/loma_lon_initial_accuracy_001'
COMMAND=[sys.executable,'diagnostics/compare_loma_initial_rays.py','--data','data/loma_lon_initial_preflight_001','--reference','data/development/loma_lon_initial_reference_002','--output','data/development/loma_lon_initial_accuracy_001']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(j):
 p=HERE/'controller_execution.json';q=p.with_suffix('.tmp');q.write_text(json.dumps(j,indent=2)+'\n');os.replace(str(q),str(p))
def utc():return datetime.datetime.utcnow().isoformat()+'Z'
assert not OUT.exists()
assert sha(ROOT/COMMAND[1])=='1712d8ab9f55739aea26c58fd3fb5efb561078b1e184943979331d0e03fb8faf'
record={'status':'starting','controller_pid':os.getpid(),'started_utc':utc(),'command':COMMAND,'source_sha256':sha(ROOT/COMMAND[1]),'controller_sha256':sha(Path(__file__)),'environment':{'PYTHONDONTWRITEBYTECODE':'1'},'scope':'Saved-table comparison only; no ray solve or inversion'}
save(record)
child=None
try:
 def interrupted(number,frame):
  if child is not None and child.poll() is None:
   try:os.killpg(child.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  raise KeyboardInterrupt('controller signal '+str(number))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 with (HERE/'stdout.log').open('wb') as stdout,(HERE/'stderr.log').open('wb') as stderr:
  child=subprocess.Popen(COMMAND,cwd=str(ROOT),env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr,start_new_session=True)
  record.update(status='running',child_pid=child.pid);save(record)
  code=child.wait()
 record.update(status='completed' if code==0 else 'failed',child_return_code=code,child_reaped=True,finished_utc=utc())
 if (OUT/'summary.json').exists():record['summary_sha256']=sha(OUT/'summary.json')
 if (OUT/'execution.json').exists():record['execution_sha256']=sha(OUT/'execution.json')
 record['log_sha256']={n:sha(HERE/n) for n in ['stdout.log','stderr.log']};save(record)
except BaseException as error:
 if child is not None and child.poll() is None:
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   child.wait()
 record.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=repr(error),finished_utc=utc(),child_return_code=child.returncode if child else None,child_reaped=child is not None)
 save(record);raise
