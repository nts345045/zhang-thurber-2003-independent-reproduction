from pathlib import Path
import json,hashlib,shutil,difflib,datetime,ast
R=Path.cwd(); P=R/'data/development/hayward_old_kernel_trial_backtracking_integration_checks_001'
C=R/'data/development/hayward_old_kernel_trial_backtracking_candidate_001'
D=R/'data/development/hayward_trial_backtracking_integration_checks_001'
B=R/'data/development/hayward_cmj_saved_gradient_001/run.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(C/'prepared.json')=='5bb45c57b3f594485abbaf144da3b540f2c7f8d42dc783837976fbe33b5d96dd'
c=json.loads((C/'prepared.json').read_text())
for n,h in c['output_sha256'].items():assert sha(C/n)==h
P.mkdir();shutil.copytree(str(C/'after'),str(P/'source'))
(P/'source/diagnostics').mkdir();(P/'original_diagnostics').mkdir();(P/'inputs').mkdir()
for n in ('check_external_inputs.cpp','check_inversion_ray_gate.cpp'):
 shutil.copyfile(str(R/'diagnostics'/n),str(P/'original_diagnostics'/n))
 src=D/'source/diagnostics'/n if n=='check_inversion_ray_gate.cpp' else R/'diagnostics'/n
 shutil.copyfile(str(src),str(P/'source/diagnostics'/n))
a=(P/'original_diagnostics/check_inversion_ray_gate.cpp').read_text();b=(P/'source/diagnostics/check_inversion_ray_gate.cpp').read_text()
(P/'guard_fixture.patch').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='original/check_inversion_ray_gate.cpp',tofile='copied/check_inversion_ray_gate.cpp')))
shutil.copyfile(str(R/'data/development/hayward_trial_cmj_old_D_replay_001/inputs/build_provenance/CMakeFiles/dd.dir/flags.make'),str(P/'inputs/original_flags.make'))
old=B.read_text();prefix=old[:old.index('def fraction_record')]
prefix=prefix.replace('"""Four fixed saved-path gradient decompositions; no trace or field calls."""','"""Bounded invented core/external/guard checks of a frozen old-kernel candidate."""')
front='''def main():
    prepared=json.loads((HERE/'prepared.json').read_text())
    review=json.loads((HERE/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(HERE/'prepared.json'):
        raise RuntimeError('Missing passed hash-bound source/preparation review')
    verify(prepared)
    control=ROOT/prepared['controls_review']
    controls=json.loads(control.read_text())
    if controls.get('status')!='passed':raise RuntimeError('Upstream actual-loop controls review is not passed')
    ledger={'status':'running','started_utc':now(),'prepared_sha256':sha(HERE/'prepared.json'),
            'prelaunch_review_sha256':sha(HERE/'prelaunch_review.json'),'commands':[],
            'scope':'Invented core/external/guard fixtures only; no authoritative rays, cohort or inversion.'}
    ledger_path=HERE/'execution.json';dump(ledger_path,ledger)
    def update():
        temporary=HERE/'execution.json.new'
        with temporary.open('w') as f:json.dump(ledger,f,indent=2,allow_nan=False);f.write('\\n')
        os.replace(str(temporary),str(ledger_path))
'''
life=old[old.index('    unsettled_groups = []'):old.index('    try:\n        for name in',old.index('    unsettled_groups = []'))]
work='''    try:
        for name in ('build','logs','results'):(HERE/name).mkdir()
        build=HERE/'build/cmake';source=HERE/'source'
        command('cmake_configure',[prepared['cmake'],'-S',str(source),'-B',str(build),
                                  '-DCMAKE_CXX_COMPILER='+prepared['compiler']])
        command('cmake_build',[prepared['cmake'],'--build',str(build),'-j','2'])
        flags=(build/'CMakeFiles/dd.dir/flags.make').read_text().split('CXX_FLAGS = ',1)[1].splitlines()[0].split()
        if sorted(flags)!=sorted(prepared['flags']):raise RuntimeError('Original optimized assertion-enabled flags changed')
        compiler=next(line.split('=',1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                      if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
        if sha(compiler)!=prepared['runtime_sha256'][prepared['compiler']]:raise RuntimeError('CMake compiler changed')
        command('compiler_version',[compiler,'--version'])
        command('runtime_libraries',['ldd',str(build/'dd')])
        command('core_validate',[str(build/'dd'),'validate',str(HERE/'results/core')])
        core=read(HERE/'results/core/validation.csv')
        if len(core)!=48 or not all(r['passed']=='1' for r in core):raise RuntimeError('Core validation failed')
        results={}
        for label,name in [('external_input','check_external_inputs.cpp'),('inversion_gate','check_inversion_ray_gate.cpp')]:
            binary=HERE/'build'/label
            command('compile_'+label,[compiler]+flags+[str(source/'diagnostics'/name),'-lstdc++fs','-o',str(binary)])
            dest=HERE/'results'/label
            argv=[str(binary),str(dest)] if label=='inversion_gate' else [str(binary),str(HERE/'results/external_input.json'),str(dest)]
            command(label,argv)
            result=dest/'summary.json' if label=='inversion_gate' else HERE/'results/external_input.json'
            results[label]=json.loads(result.read_text())
            if results[label].get('status')!='passed':raise RuntimeError(label+' fixture failed')
        verify(prepared)
        summary={'status':'passed','prepared_sha256':sha(HERE/'prepared.json'),
                 'controls_review_sha256':sha(control),'core_checks':len(core),'components':results,
                 'flags':flags,'compiler':compiler,'compiler_sha256':sha(compiler),
                 'scope':'Invented core/external/guard fixtures only; no authoritative rays, cohort or inversion.',
                 'limitations':['The adapted trial fixture retains its original inputs/settings and records the actual permitted terminal outcome.',
                                'Only first pure-quality rejection and its subsequent actual ledger/state contracts are required; later current/final guard failure is distinct from no-evaluable-trial exhaustion.',
                                'No whole native trial or inversion acceptance is established.'],
                 'output_sha256':{str(p.relative_to(HERE)):sha(p) for sub in ('build','logs','results') for p in sorted((HERE/sub).rglob('*')) if p.is_file()}}
        dump(HERE/'summary.json',summary)
        ledger.update(status='completed',return_code=0,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'))
        update();print(ledger['summary_sha256'])
    except BaseException as error:
        ledger.update(status='failed_preserved',finished_utc=now(),error=str(error),outputs_stable=not unsettled_groups,unsettled_process_groups=unsettled_groups,
            output_sha256={} if unsettled_groups else {str(p.relative_to(HERE)):sha(p) for sub in ('build','logs','results') if (HERE/sub).exists() for p in sorted((HERE/sub).rglob('*')) if p.is_file()})
        update();raise

if __name__=='__main__':main()
'''
(P/'run.py').write_text(prefix+front+life+work)
compile((P/'run.py').read_text(),str(P/'run.py'),'exec')
# Preserve exact reviewed lifecycle ASTs; this does not execute the runner.
def funcs(text):return {x.name:ast.dump(x,include_attributes=False) for x in ast.walk(ast.parse(text)) if isinstance(x,ast.FunctionDef)}
f0,f1=funcs(old),funcs((P/'run.py').read_text())
for n in ('verify','group_members','signal_group','terminate_and_reap','interrupted','command'):assert f0[n]==f1[n]
(P/'README.md').write_text('''# Frozen old-kernel integration checks (prepared only)

This package uses the complete frozen old7111 kernel and CMake source from
`hayward_old_kernel_trial_backtracking_candidate_001/after`, whose sole
production-source change is the reviewed candidate003 main.cpp trial policy.
Maintained sources and the earlier D draft are unchanged.

The proposed commands compile at the original optimized, assertion-enabled
flags, run the existing 48 core checks and unchanged external-input fixture,
and run the copied guard fixture. Only its obsolete immediate-trial-abort
expectation is adapted. All original fixture geometry/settings and the
current/final, altered-ray, worker-exception, native-epoch, preflight and
17-digit round-trip assertions remain. The first pure local-stopping failure
must be retained before subsequent halved trials. Actual outcomes are recorded:
completion, no objective-evaluable trial, or a later current/final fatal guard.
The last case may follow a successful action-only trial; it is not exhaustion.
Unexpected or mixed trial exceptions are not accepted as pure-quality recovery.

No compilation or numerical run has occurred at preparation. Execution requires
an independent `prelaunch_review.json` bound to `prepared.json`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_old_kernel_trial_backtracking_integration_checks_001/run.py
```

All outputs remain in this fresh project subdirectory. Six lifecycle/check
functions are AST-identical to the reviewed CMJ saved-gradient runner, including
termination/reaping of child process groups and withholding output hashes if
live descendants remain. This bounded invented suite makes no native trial,
cohort, inversion acceptance, first-arrival or general convergence claim.
''')
shutil.copyfile(__file__,str(P/'prepare.py'))
original={str((C/'prepared.json').relative_to(R)):sha(C/'prepared.json'),str(B.relative_to(R)):sha(B)}
for n,h in c['output_sha256'].items():original[str((C/n).relative_to(R))]=h
for n in ('check_external_inputs.cpp','check_inversion_ray_gate.cpp'):original['diagnostics/'+n]=sha(R/'diagnostics'/n)
for p in (D/'source/diagnostics/check_inversion_ray_gate.cpp',D/'preserved_state.json',R/'data/development/hayward_trial_backtracking_controls_002/review.json',R/'data/development/hayward_trial_backtracking_controls_002/summary.json',R/'data/development/hayward_trial_backtracking_controls_002/execution.json',R/'data/development/hayward_trial_cmj_old_D_replay_001/inputs/build_provenance/CMakeFiles/dd.dir/flags.make'):original[str(p.relative_to(R))]=sha(p)
runtime=dict(c['runtime_sha256']);cmake=shutil.which('cmake');runtime[cmake]=sha(Path(cmake))
flags=(P/'inputs/original_flags.make').read_text().split('CXX_FLAGS = ',1)[1].splitlines()[0].split()
assert '-O3' in flags and '-fopenmp' in flags and not any('NDEBUG' in x for x in flags)
d={'status':'prepared_not_executed','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_prepared_sha256':sha(C/'prepared.json'),
 'candidate':str(C.relative_to(R)),'controls_review':'data/development/hayward_trial_backtracking_controls_002/review.json',
 'compiler':'/usr/bin/c++','cmake':cmake,'flags':flags,'original_sha256':original,'runtime_sha256':runtime,
 'source_sha256':{str(f.relative_to(P)):sha(f) for f in sorted((P/'source').rglob('*')) if f.is_file()},
 'output_sha256':{str(f.relative_to(P)):sha(f) for f in sorted(P.rglob('*')) if f.is_file()},
 'lifecycle_ast_parity':['verify','group_members','signal_group','terminate_and_reap','interrupted','command'],
 'planned_scope':['core validate (48 existing checks)','external-input fixture unchanged','adapted invented guard fixture'],
 'compile_calls':0,'numerical_calls':0}
for n,h in original.items():assert sha(R/n)==h
for n,h in runtime.items():assert sha(Path(n))==h
(P/'prepared.json').open('x').write(json.dumps(d,indent=2)+'\n')
print('prepared',sha(P/'prepared.json'),'runner',sha(P/'run.py'),'guard',sha(P/'source/diagnostics/check_inversion_ray_gate.cpp'))
print('pins',len(original),len(runtime),len(d['output_sha256']),len(d['source_sha256']))
