"""Independent saved launcher/control accounting; no harness, compiler or numerical rerun."""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from run_loma_initial_preflight import live_group_members

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(p.read_text())
verified={}
def pins(base,mapping):
 for n,h in mapping.items():
  p=base/n
  if sha(p)!=h:raise AssertionError('Changed pin: '+str(p))
  verified[str(p)]=h

def main():
 summary=load(HERE/'summary.json');execution=load(HERE/'execution.json');prepared=load(HERE/'prepared.json')
 assert summary['status']=='passed' and summary['controls_total']==summary['controls_passed']==62
 assert len(summary['checks'])==len({r['name'] for r in summary['checks']})==62 and all(r['passed'] for r in summary['checks'])
 assert summary['numerical_calls']==summary['compiler_calls']==summary['inverse_calls']==0
 assert execution['status']=='completed' and execution['return_code']==0 and execution['child_reaped']
 assert execution['summary_sha256']==sha(HERE/'summary.json') and execution['prepared_sha256']==sha(HERE/'prepared.json')
 assert execution['prelaunch_review_sha256']==sha(HERE/'prelaunch_review.json')
 assert execution['controller_sha256']==sha(HERE/'controller.py')
 assert execution['harness_sha256']==prepared['harness_sha256']==sha(ROOT/'diagnostics/check_old_kernel_backtracking_launcher.py')
 pins(HERE,prepared['output_sha256']);pins(HERE,summary['artifact_sha256']);pins(ROOT,summary['source_sha256'])
 pins(HERE,execution['log_sha256'])
 assert not {'execution.json','driver_stdout.log','driver_stderr.log'} & set(summary['artifact_sha256'])
 package=ROOT/'data/development/hayward_old_kernel_backtracking_launcher_001'
 p=load(package/'prepared.json');review=load(package/'root_source_review.json')
 assert summary['prepared_sha256']==sha(package/'prepared.json')==review['prepared_sha256'] and review['status']=='passed_source_review'
 pins(ROOT,p['input_sha256']);pins(package,p['output_sha256']);pins(package/'source_snapshot',p['source_sha256'])
 pins(ROOT,p['original004_required_sha256']);pins(Path('/'),p['runtime_sha256'])
 assert sha(ROOT/'run_hayward_guarded_inversion.py')==p['original_controller_sha256']
 assert sha(ROOT/'src/core.hpp')==p['maintained_core_sha256']
 assert sha(ROOT/'diagnostics/review_old_kernel_trial_completion.py')==p['source_adoption']['completion_helper_sha256']
 records={r['case']:r for r in summary['commands']};assert set(records)=={'zero','nonzero','early_zero','early_nonzero','sigterm'}
 lifecycle={}
 for name,r in records.items():
  directory=HERE/('lifecycle_'+name);ledger=load(directory/'dd_inversion_execution.json')
  expected='fixture_completed' if name=='zero' else ('interrupted' if name=='sigterm' else 'failed')
  assert ledger['status']==expected and not live_group_members(r['child_group'])
  assert r['return_code']==(0 if name=='zero' else (143 if name=='sigterm' else 1))
  mapping=ledger.get('output_sha256',ledger.get('partial_output_sha256'));assert mapping
  pins(directory,mapping)
  if name=='nonzero':assert ledger['return_code']==7
  if name=='sigterm':assert ledger['return_code']==143 and ledger['exception_child']['remaining_live_group_members']==[]
  if name.startswith('early_'):
   assert ledger['completed_commands'][0]['remaining_live_group_members']
   assert ledger['exception_child']['remaining_live_group_members']==[]
   assert ledger['completed_commands'][0]['return_code']==(0 if name=='early_zero' else 7)
  lifecycle[name]={'driver_return_code':r['return_code'],'status':ledger['status'],
                   'supervisor_return_code':ledger.get('completed_commands',[{}])[-1].get('return_code') if ledger.get('completed_commands') else None,
                   'live_group_members_now':[],'stable_hashed_outputs':len(mapping)}
 result=dict(status='passed',reviewer='scientific_audit',summary_sha256=sha(HERE/'summary.json'),
             execution_sha256=sha(HERE/'execution.json'),prepared_sha256=sha(HERE/'prepared.json'),
             launcher_prepared_sha256=sha(package/'prepared.json'),root_source_review_sha256=sha(package/'root_source_review.json'),
             review_source_sha256=sha(Path(__file__)),verified_unique_files=len(verified),executed_artifact_pins=len(summary['artifact_sha256']),
             saved_checks=62,lifecycle=lifecycle,original_source_and_evidence_unchanged=True,
             scope='Saved results/source/hash readback only. Actual full real eligibility readback and copied-prefix sentinel are distinct; no scientific eligibility claim for invented inputs.',
             limitations=summary['limitations'])
 with (HERE/'review.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps(dict(status=result['status'],review_sha256=sha(HERE/'review.json'),verified_unique_files=len(verified))))
if __name__=='__main__':main()
