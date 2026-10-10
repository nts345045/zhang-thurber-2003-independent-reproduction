from pathlib import Path
import json,hashlib,shutil,ast,datetime
R=Path.cwd();P=R/'data/development/internal_ridge_stationarity_controls_001';B=R/'data/development/hayward_cmj_saved_gradient_001/run.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(P/'source/src').mkdir(parents=True);(P/'inputs').mkdir()
original={str(B.relative_to(R)):sha(B)}
for name,expected in [('core.hpp','c9500361c5ca3ff55b2fbcec0aedfb3639d3f3b68a53431267e6849c3a933044'),('usable_ray_curvature.hpp','5236f9df135dc2449662db70bb68aded36cae3f5ce23e7471caa02d45ce5daac'),('ray_metric.hpp','a282299431787361ff343dd71fc984fad0abcb675f7bf23b42189d1c61ba8732')]:
 p=R/'src'/name;assert sha(p)==expected;original[str(p.relative_to(R))]=expected;shutil.copyfile(str(p),str(P/'source/src'/name))
for name,source in [('moment_set_proof.md','data/development/interface_moment_set/proof.md'),('moment_set_summary.json','data/development/interface_moment_set/001/summary.json'),('moment_set_review.json','data/development/interface_moment_set/001/root_review.json'),('adoption.json','data/development/usable_curvature_adoption_001/adoption.json')]:
 p=R/source;original[source]=sha(p);shutil.copyfile(str(p),str(P/'inputs'/name))
old=B.read_text();prefix=old[:old.index('def fraction_record')].replace('"""Four fixed saved-path gradient decompositions; no trace or field calls."""','"""Invented fixed-path ridge observations and exact directional controls."""')
front='''def main():
    prepared=json.loads((HERE/'prepared.json').read_text())
    review=json.loads((HERE/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(HERE/'prepared.json'):
        raise RuntimeError('Missing passed hash-bound source/preparation review')
    verify(prepared)
    ledger={'status':'running','started_utc':now(),'prepared_sha256':sha(HERE/'prepared.json'),
            'prelaunch_review_sha256':sha(HERE/'prelaunch_review.json'),'commands':[],
            'scope':'Invented fixed paths and exact analytic directional components; no trace or optimization.'}
    ledger_path=HERE/'execution.json';dump(ledger_path,ledger)
    def update():
        temporary=HERE/'execution.json.new'
        with temporary.open('w') as f:json.dump(ledger,f,indent=2,allow_nan=False);f.write('\\n')
        os.replace(str(temporary),str(ledger_path))
'''
life=old[old.index('    unsettled_groups = []'):old.index('    try:\n        for name in',old.index('    unsettled_groups = []'))]
work='''    try:
        for name in ('build','logs','results'):(HERE/name).mkdir()
        command('compiler_version',[prepared['compiler'],'--version'])
        binary=HERE/'build/observe'
        command('compile',[prepared['compiler']]+prepared['flags']+[str(HERE/'observe.cpp'),'-I'+str(HERE/'source'),'-o',str(binary)])
        command('runtime_libraries',['ldd',str(binary)])
        command('observe',[str(binary),str(HERE/'results')])
        expected='path_evaluations=14 direct_segment_evaluations=2 trace_calls=0 optimizer_calls=0'
        if (HERE/'logs/observe.stdout.log').read_text().strip()!=expected:raise RuntimeError('Unexpected observation inventory')
        command('exact_and_saved_checks',[sys.executable,str(HERE/'check.py'),str(HERE/'results')])
        result=json.loads((HERE/'results/checks.json').read_text())
        if result['status']!='passed':raise RuntimeError('Invented checks failed')
        verify(prepared)
        summary={'status':'passed','prepared_sha256':sha(HERE/'prepared.json'),
                 'exact_rational_checks':result['exact_rational_checks'],'numerical_consistency_checks':result['numerical_consistency_checks'],
                 'path_evaluations':14,'direct_segment_evaluations':2,'trace_calls':0,'optimizer_calls':0,
                 'scope':ledger['scope'],'continuous_claim_basis':result['continuous_claim_basis'],
                 'limitations':result['limitations'],
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
for name in ('run.py','check.py'):compile((P/name).read_text(),str(P/name),'exec')
def funcs(text):return {x.name:ast.dump(x,include_attributes=False) for x in ast.walk(ast.parse(text)) if isinstance(x,ast.FunctionDef)}
f0,f1=funcs(old),funcs((P/'run.py').read_text())
for n in ('verify','group_members','signal_group','terminate_and_reap','interrupted','command'):assert f0[n]==f1[n]
shutil.copyfile(__file__,str(P/'prepare.py'))
prior=R/'data/development/hayward_trial_cmj_old_D_replay_001/prepared.json';original[str(prior.relative_to(R))]=sha(prior);d0=json.loads(prior.read_text())
runtime=dict(d0['runtime_sha256']);runtime[sys.executable] if False else None
# Python executable identity is a runner dependency in addition to the original C++ runtime pins.
import sys
runtime[sys.executable]=sha(Path(sys.executable))
d={'status':'prepared_not_executed','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'compiler':d0['compiler'],'flags':d0['flags'],'original_sha256':original,'runtime_sha256':runtime,
   'output_sha256':{str(p.relative_to(P)):sha(p) for p in sorted(P.rglob('*')) if p.is_file()},
   'planned_evaluations':{'fixed_paths':14,'direct_segments':2,'traces':0,'optimizers':0},
   'scope':'Exact rational/analytic invented controls; separate binary64 quadrature observation only.',
   'lifecycle_ast_parity':['verify','group_members','signal_group','terminate_and_reap','interrupted','command']}
for n,h in original.items():assert sha(R/n)==h
for n,h in runtime.items():assert sha(Path(n))==h
(P/'prepared.json').open('x').write(json.dumps(d,indent=2)+'\n')
print('prepared',sha(P/'prepared.json'),'observe',sha(P/'observe.cpp'),'check',sha(P/'check.py'),'run',sha(P/'run.py'))
print('pins',len(original),len(runtime),len(d['output_sha256']))
