"""Read saved eligibility and freeze the new launcher; no compiler or native command."""
import ast
import difflib
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
import run_hayward_old_kernel_backtracking as m

def main():
    m.require(not (HERE/'prepared.json').exists(),'Preserve existing preparation')
    plan=m.load(ROOT/'data/development/hayward_guarded_dd_launch_plan_001/plan.json')
    command=plan['command'];get=lambda flag:ROOT/command[command.index(flag)+1]
    manifest,copied,evidence,parity,selected,adoption,expected=m.reviewed_inputs(
        get('--preflight'),get('--reference'),get('--accuracy-review'),get('--parity-review'))
    scripts=['run_hayward_old_kernel_backtracking.py','diagnostics/review_old_kernel_trial_completion.py',
             'run_loma_initial_preflight.py','run_loma_analytic_simulation.py',
             'diagnostics/review_loma_analytic_simulation.py']
    sources=dict(selected);sources.update({name:ROOT/name for name in scripts})
    snapshot=HERE/'source_snapshot';snapshot.mkdir()
    for name,path in sources.items():
        dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(path),str(dest))
    original=ROOT/'run_hayward_guarded_inversion.py'
    completion=ROOT/'data/development/hayward_trial_completion_candidate_002/after/run_hayward_guarded_inversion.py'
    evidence[str(original.relative_to(ROOT))]=m.sha(original)
    evidence[str(completion.relative_to(ROOT))]=m.sha(completion)
    evidence[str((ROOT/'data/development/hayward_guarded_dd_launch_plan_001/plan.json').relative_to(ROOT))]=m.sha(ROOT/'data/development/hayward_guarded_dd_launch_plan_001/plan.json')
    # A leaf helper rename is the only completion-check implementation change.
    tree=ast.parse(m.__file__ and Path(m.__file__).read_text());old=ast.parse(completion.read_text())
    get_function=lambda t,n:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
    for name in ('configuration','check_inverse'):
        m.require(ast.dump(get_function(tree,name))==ast.dump(get_function(old,name)),name+' differs from reviewed completion candidate')
    receipt=dict(status='prepared_not_launched',scope=__doc__,expected_counts=expected,
                 source_adoption=adoption,input_sha256=evidence,
                 source_sha256={name:m.sha(path) for name,path in sources.items()},
                 source_mapping={name:str(path.relative_to(ROOT)) for name,path in sources.items()},
                 original004_required_sha256=manifest['sha256'],
                 runtime_sha256={parity['compiler']:parity['compiler_sha256'],**adoption['runtime_library_sha256']},
                 original_controller_sha256=m.sha(original),maintained_core_sha256=m.sha(ROOT/'src/core.hpp'),
                 completion_configuration_and_check_inverse_AST_unchanged=True,
                 numerical_calls=0,compiler_calls=0,inverse_launched=False,
                 limitations=adoption['limitations'])
    receipt['output_sha256']={str(p.relative_to(HERE)):m.sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    with (HERE/'prepared.json').open('x') as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=receipt['status'],prepared_sha256=m.sha(HERE/'prepared.json'),
                         evidence=len(evidence),sources=len(sources),outputs=len(receipt['output_sha256']))))

if __name__=='__main__':main()
