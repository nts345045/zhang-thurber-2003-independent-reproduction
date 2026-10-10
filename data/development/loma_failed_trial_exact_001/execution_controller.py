from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/'data/development/loma_failed_trial_exact_001'
logs = ROOT/'tmp/loma_failed_trial_exact_001'
replay = ROOT/'data/development/loma_failed_search_3426_001'
summary = json.loads((replay/'summary.json').read_text())
assert summary['status'] == 'completed_with_original_flags_preserved'
assert summary['all_five_prior_numerical_tables_byte_identical']
assert summary['recorded_failed_trials'] == 24
assert not out.exists() and not logs.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native_review = replay/'review.json'
assert sha(native_review) == '2bc6060c7c4d19161b7ffedbae3fd3455ccebefcd2160f7874c56de1b9321f16'
assert json.loads(native_review.read_text())['summary_sha256'] == sha(replay/'summary.json')
command = ['python3','diagnostics/check_loma_failed_trials.py',
           '--replay',str(replay.relative_to(ROOT)),
           '--controls','data/development/loma_failed_trial_controls_002',
           '--review','data/development/loma_failed_trial_controls_002/review.json',
           '--output',str(out.relative_to(ROOT))]
logs.mkdir()
record = dict(status='running',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              command=command,controller_sha256=sha(Path(__file__)),
              input_sha256={str(p.relative_to(ROOT)):sha(p) for p in
                 (replay/'summary.json',native_review,ROOT/'diagnostics/check_loma_failed_trials.py',
                  ROOT/'data/development/loma_failed_trial_controls_002/summary.json',
                  ROOT/'data/development/loma_failed_trial_controls_002/review.json')})
shutil.copyfile(str(Path(__file__)),str(logs/'controller.py'))
(logs/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
with (logs/'stdout.log').open('wb') as stdout,(logs/'stderr.log').open('wb') as stderr:
    child = subprocess.Popen(command,cwd=str(ROOT),stdout=stdout,stderr=stderr,
                             env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),start_new_session=True)
    record['pid'] = child.pid
    (logs/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    code = child.wait()
record.update(status='completed' if code == 0 else 'failed',return_code=code,
              finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              stdout_sha256=sha(logs/'stdout.log'),stderr_sha256=sha(logs/'stderr.log'))
for p,s in record['input_sha256'].items():
    assert sha(ROOT/p) == s,p
if (out/'summary.json').exists():
    record['summary_sha256'] = sha(out/'summary.json')
(logs/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
if out.exists():
    shutil.copyfile(str(native_review),str(out/'input_replay_review.json'))
    for name in ('controller.py','stdout.log','stderr.log','execution.json'):
        shutil.copyfile(str(logs/name),str(out/('execution_'+name)))
print(json.dumps(record,indent=2),flush=True)
raise SystemExit(code)
