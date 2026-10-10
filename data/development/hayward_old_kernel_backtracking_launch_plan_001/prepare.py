"""Prepare a fresh old-kernel catalog-DD attempt only after bounded launcher review."""
import json
from pathlib import Path
import sys
import subprocess
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
import run_hayward_old_kernel_backtracking as m

def main():
    m.require(not (HERE/'plan.json').exists(),'Preserve previous launch plan')
    package=ROOT/'data/development/hayward_old_kernel_backtracking_launcher_001'
    checks=ROOT/'data/development/hayward_old_kernel_backtracking_launcher_checks_002'
    prepared=m.load(package/'prepared.json');source_review=m.load(package/'root_source_review.json')
    summary=m.load(checks/'summary.json');review=m.load(checks/'review.json')
    m.require(source_review['status']=='passed_source_review' and source_review['prepared_sha256']==m.sha(package/'prepared.json'),
              'Launcher source/preparation review is not current')
    m.require(summary['status']==review['status']=='passed' and review['summary_sha256']==m.sha(checks/'summary.json'),
              'Bounded launcher controls are not independently accepted')
    m.verify_hashes(package,prepared['output_sha256']);m.verify_hashes(ROOT,prepared['input_sha256'])
    m.require(all(m.sha(ROOT/n)==h for n,h in prepared['source_sha256'].items() if not n.startswith('src/') and n!='CMakeLists.txt'),
              'Current launcher/helper dependencies differ from preparation')
    prior=m.load(ROOT/'data/development/hayward_guarded_dd_launch_plan_001/plan.json')
    command=list(prior['command']);command[0]=str(Path(sys.executable).resolve())
    command[1]='run_hayward_old_kernel_backtracking.py'
    command[command.index('--output')+1]='data/hayward_old_kernel_backtracking_001'
    command[command.index('--build')+1]='tmp/hayward_old_kernel_backtracking_runs/001'
    get=lambda flag:ROOT/command[command.index(flag)+1]
    out,build=get('--output'),get('--build')
    m.require(not out.exists() and not out.is_symlink() and not build.exists() and not build.is_symlink(),
              'Require a fresh output/build pair')
    manifest,copied,evidence,parity,selected,adoption,expected=m.reviewed_inputs(
        get('--preflight'),get('--reference'),get('--accuracy-review'),get('--parity-review'))
    m.require(expected['observation_types']['2']==0,'This plan is catalog-only')
    for p in (package/'prepared.json',package/'root_source_review.json',checks/'summary.json',checks/'review.json',
              ROOT/'run_hayward_old_kernel_backtracking.py',ROOT/'diagnostics/review_old_kernel_trial_completion.py'):
        evidence[str(p.relative_to(ROOT))]=m.sha(p)
    plan=dict(status='prepared_not_launched',reviewed_base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),universal_newlines=True).strip(),
              commit_policy='Eligibility binds exact source/input/evidence/runtime bytes, not current HEAD. The actual run manifest records its own publication commit.',command=command,output=str(out.relative_to(ROOT)),build=str(build.relative_to(ROOT)),
              preflight=str(get('--preflight').relative_to(ROOT)),mode='dd',expected_counts=expected,
              source_adoption=adoption,source_sha256=prepared['source_sha256'],input_sha256=evidence,
              numerical_input_sha256=copied,numerical_settings=m.configuration(get('--preflight')/'run.cfg'),
              compiler=parity['compiler'],compiler_sha256=parity['compiler_sha256'],flags=parity['flags'],
              runtime_sha256=prepared['runtime_sha256'],python=str(Path(sys.executable).resolve()),
              python_sha256=m.sha(Path(sys.executable).resolve()),threads=m.THREADS,address_space_limit_GiB=m.LIMIT_GIB,
              binary_status='Not built; fresh build and binary/runtime/source hashes required in actual execution manifest.',
              inverse_launched=False,scientific_success=False,
              pending_gate='Root review and authorization of this exact concrete plan before durable controller launch.',
              final_requirements=['Completed child and full rejected-trial/native output readback.',
                                  'Independent final-model full guard/refinement/source diagnostics and scientific interpretation.',
                                  'No automatic other method, CC-data or Loma inversion cascade.'],
              limitations=adoption['limitations'])
    plan['preparation_source_sha256']=m.sha(Path(__file__))
    with (HERE/'plan.json').open('x') as f:json.dump(plan,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=plan['status'],sha256=m.sha(HERE/'plan.json'),command=command)))

if __name__=='__main__':main()
