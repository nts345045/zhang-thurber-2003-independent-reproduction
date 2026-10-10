"""Record the independent full pin readback and verify the narrow final controller delta."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def main():
 p=load(HERE/'plan.json')
 assert sha(HERE/'plan.json')=='ad426b135b988ae044ebe70773e2316aea4fe6dd084ee27ea5f412ca1967e63c'
 assert sha(HERE/'controller.py')=='cebe0e1caba5935c89308e32d604605995912f3b7da28c40269720a0afdd5fea'
 assert sha(HERE/'controller_before_review.py')=='6c3d4bd4b40f7a3107fce5e7aea47f0e13fca3a8f56cbbf978efc5d865d6c2dd'
 counts=dict(plan_inputs=len(p['input_sha256']),mapped_sources=len(p['source_sha256']),
             runtimes=len(p['runtime_sha256']),python=1,numerical_inputs=len(p['numerical_input_sha256']))
 assert counts==dict(plan_inputs=8190,mapped_sources=15,runtimes=9,python=1,numerical_inputs=11)
 paths=[p['output'],p['build'],'tmp/hayward_old_kernel_backtracking_controllers/001']
 assert all(not (ROOT/n).exists() and not (ROOT/n).is_symlink() for n in paths)
 package=ROOT/'data/development/hayward_old_kernel_backtracking_launcher_001'
 saved=load(package/'prepared.json')
 assert sha(ROOT/'run_hayward_guarded_inversion.py')==saved['original_controller_sha256']
 assert sha(ROOT/'src/core.hpp')==saved['maintained_core_sha256']
 current={n:sha(ROOT/n) for n in ('run_hayward_old_kernel_backtracking.py','diagnostics/review_old_kernel_trial_completion.py')}
 assert all(current[n]==p['source_sha256'][n] for n in current)
 value=dict(status='passed',reviewer='scientific_audit',plan_sha256=sha(HERE/'plan.json'),
            controller_sha256=sha(HERE/'controller.py'),previous_reviewed_controller_sha256=sha(HERE/'controller_before_review.py'),
            controller_correction_sha256=sha(HERE/'controller_review_correction.patch'),
            current_source_sha256=current,checks_by_category=counts,independent_pin_checks=sum(counts.values()),
            independent_pin_auditor='earthscope_discovery',
            pin_audit_method='Independent inline read-only full pin check reported8226matches, followed by source review of the final narrow controller change. This receipt verifies exact old/new controller and plan identities without duplicating the full hash sweep.',
            final_controller_findings=['SIGINT/SIGTERM controller exits preserve130/143; negative child status maps to128+signal.',
              'Malformed or mismatched cleanup-ledger ownership records cleanup_errors/unresolvedgroup and withholds hashes; original exception remains.',
              'Source/input/runtime/configuration eligibility unchanged.'],
            fresh_paths=paths,original_controller_and_maintained_D_unchanged=True,
            inverse_launched=False,numerical_calls=0,review_source_sha256=sha(Path(__file__)),
            limitations=['Counts are8226checks across overlapping mappings, not8226unique files.',
              'Recorded process-group ownership cannot cover an abrupt death before the inner PID is recorded.',
              'Final review is conditional on publication, a fresh pin recheck and explicit root launch GO; no HEAD equality requirement.'])
 with (HERE/'pin_review.json').open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
 print(sha(HERE/'pin_review.json'))
if __name__=='__main__':main()
