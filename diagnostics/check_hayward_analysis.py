#!/usr/bin/env python3
"""Check report parsing with invented fixtures only; run from the repository root.

No provider observations or inversion outputs are loaded. AST extraction loads
function definitions from analyze.py without executing its baseline or field
analysis. Every generated CSV, JSON, and LaTeX report remains under
 tmp/hayward_analysis_checks/ and is a disposable formatting/validation fixture,
not an authoritative Hayward result. Python 3.6 and NumPy are required.
"""
import ast, csv, hashlib, json, shutil
from pathlib import Path
import numpy as np

source = Path('analyze.py')
syntax = ast.parse(source.read_text())
namespace = {'__file__':str(source.resolve())}
# Execute definitions only, never the legacy analysis or real Hayward branch.
module = ast.Module([n for n in syntax.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))])
exec(compile(module, str(source), 'exec'), namespace)
review = namespace['analyze_hayward']
base = Path('tmp/hayward_analysis_checks/fixture')
base.mkdir(parents=True, exist_ok=True)
report = base/'report'

def write(name, rows, fields=None):
    with (base/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)
def save(name, value):
    (base/name).write_text(json.dumps(value, indent=2)+'\n')
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def refresh():
    save('figure_metrics.json', {'input_sha256':{p.name:digest(p) for p in base.glob('*.csv')}})
    manifest['input_sha256'] = {str(base/p):digest(base/p) for p in ['dd_events.csv','dd_grid.csv','dd_linearization_rows.csv']}
    save('absolute_resolution_manifest.json', manifest)
def expect_failure(label, substring):
    try:
        review(base, report, required=True)
    except (RuntimeError, ValueError) as e:
        assert substring in str(e), (label, str(e))
        checks.append(label)
    else:
        raise AssertionError(label+' unexpectedly succeeded')

events=[dict(id=i,x=i+1,y=i+2,z=i+3,t=0,event_resource_id='invented:event,"{}"'.format(i),origin_resource_id='invented:origin:'+str(i)) for i in range(2)]
write('initial_events.csv',events)
grid=[dict(x=0,y=0,z=0,v=6),dict(x=10,y=10,z=10,v=6)]
write('initial_grid.csv',grid)
write('stations.csv',[dict(id=0,x=0,y=0,z=0,t=0,channel_seed_id='XX.FIX..HHZ',location_code='')])
obs=[dict(i=0,j=-1,station=0,type=0,value=1,station_j=-1,event_i_resource_id=events[0]['event_resource_id'],pick_i_resource_id='invented:pick:0'),
     dict(i=1,j=-1,station=0,type=0,value=2,station_j=-1,event_i_resource_id=events[1]['event_resource_id'],pick_i_resource_id='invented:pick:1'),
     dict(i=1,j=0,station=0,type=1,value=1,station_j=0,event_i_resource_id=events[1]['event_resource_id'],pick_i_resource_id='invented:pick:1')]
write('observations.csv',obs)
selection={'fixture_kind':'invented analysis fixture; no provider observations','uncertainty_interpretation':'independent 1-sigma assumed','uncertainty_weight':'0.05/sigma','timing_calibration_caveat':'no timing stability implied'}
save('selection_manifest.json',selection)
for mode in ['standard','dd','loc1d']:
    write(mode+'_events.csv',events)
    write(mode+'_grid.csv',grid)
    residual=[]
    for i,r in enumerate(obs):
        rr={k:v for k,v in r.items() if k!='value'}
        rr['residual']=[.1,-.2,.3][i]
        residual.append(rr)
    write(mode+'_residuals.csv',residual)
    history=[dict(iteration=i,stage=0,absolute_rms=.4,catalog_rms=.5,precise_rms='nan',velocity_step=.1,location_step=.2,step_fraction=1-i,objective_before=10-i,objective_after=9,lsqr_iterations=20,lsqr_relative_normal_residual=1e-9 if i==0 else 1e-7,lsqr_converged=1-i,ray_count=2,ray_converged_count=2-i,ray_projected_gradient_max=2e-6 if i==0 else .01,ray_raw_gradient_max=.01) for i in range(2)]
    write(mode+'_history.csv',history)
    rays=[dict(event=i,station=0,production_time=1+i,refined_time=.9999+i,difference=.0001,production_gradient=1e-6,refined_gradient=1e-6,production_raw_gradient=1e-6,refined_raw_gradient=1e-6,production_iterations=4,refined_iterations=5,production_converged=1,refined_converged=1,production_merged=0,refined_merged=0,diagnostic_row=i) for i in range(2)]
    write(mode+'_ray_convergence.csv',rays)
    derivatives=[dict(event=i,station=0,axis=a,production_derivative=.1,refined_derivative=.1,finite_difference=.104,production_error=-.004,refined_error=-.004,diagnostic_row=i) for i in range(2) for a in range(3)]
    write(mode+'_ray_derivatives.csv',derivatives)
    write(mode+'_ray_identifiers.csv',[dict(diagnostic_row=i,event=i,station=0,source_event_resource_id=e['event_resource_id']) for i,e in enumerate(events)])
write('absolute_resolution.csv',[dict(node=i,x=g['x'],y=g['y'],z=g['z'],v=6,resolution_diagonal=.5,independent_pick_sigma_velocity_km_s=.1) for i,g in enumerate(grid)])
write('dd_linearization_rows.csv',[dict(i=i,station=0,observed=1+i,predicted=1+i,residual=0,ray_converged=1,ray_projected_gradient=1e-6,ray_raw_gradient=1e-6,ray_time=1+i,ray_iterations=4) for i in range(2)])
manifest={'fixture_kind':'invented analysis fixture','conditioning':dict(model_schur_condition_number=10,inverse_relative_residual=1e-16,minimum_source_normal_eigenvalue=.1),'resolution_diagonal_min_max':[.5,.5],'velocity_sigma_min_max_km_s':[.1,.1]}
refresh()
checks=[]
r=review(base,report,required=True)
m=r['modes']['dd']
assert m['final_residual_rms_seconds']['2'] is None
assert abs(m['final_residual_rms_seconds']['0']-np.sqrt(.025))<1e-15
assert m['accepted_updates']==1 and m['lsqr']['unconverged']==1
assert m['all_ray_history']['minimum_converged_percent']==50
assert m['boundary_sources']==0 and m['catalog_displacement_3d_km']['rms']==0
assert m['final_sampled_rays']['production']['source_derivative_components_over_existing_tolerance']==6
assert '\\begin{tabular}' in (report/'hayward_results.tex').read_text()
assert '10^{-6}' in (report/'hayward_results.tex').read_text()
checks.append('complete quoted-identity fixture; empty type-2 category; final RMS; history flags; boundary counts; LaTeX rendering')
p=base/'standard_history.csv'
original=p.read_text()
p.write_text(original.replace(',nan,',',inf,',1))
refresh()
expect_failure('infinity is rejected even in absent precise-data category','nonfinite modeled')
p.write_text(original.replace(',0.4,',',nan,',1))
refresh()
expect_failure('nonfinite modeled absolute residual is rejected','nonfinite modeled')
p.write_text(original)
refresh()
p=base/'standard_grid.csv'
original_grid=p.read_text()
p.write_text(original_grid+'\n')
expect_failure('stale figure input hash is rejected','Stale Hayward figure input')
p.write_text(original_grid)
refresh()
fig=json.loads((base/'figure_metrics.json').read_text())
del fig['input_sha256']['standard_grid.csv']
save('figure_metrics.json',fig)
expect_failure('missing figure input hash is rejected','Missing Hayward figure input hashes')
refresh()
p=base/'standard_events.csv'
original_events=p.read_text()
p.write_text(original_events.replace('invented:origin:0','invented:origin:WRONG'))
refresh()
expect_failure('changed provider-origin identity is rejected','event identities do not match')
p.write_text(original_events)
refresh()
p=base/'standard_history.csv'
p.write_text(original.replace(',10,9,',',10,11,',1))
refresh()
r=review(base,report,required=True)
assert r['modes']['standard']['accepted_objective_increases_above_audit_tolerance']==1
checks.append('accepted objective increase remains an explicit numerical flag')
p.write_text(original)
refresh()
p=base/'standard_ray_derivatives.csv'
original_derivative=p.read_text()
p.write_text(original_derivative.splitlines()[0]+'\n')
refresh()
r=review(base,report,required=True)
assert r['modes']['standard']['final_sampled_rays']['derivative_components']==0
checks.append('empty boundary-skipped derivative table remains reportable')
p.write_text(original_derivative)
refresh()
r=review(base,report,required=True)
checks.append('fixture restored and final JSON serializes without NaN')
Path('tmp/hayward_analysis_checks/results.json').write_text(json.dumps({'status':'passed','fixture_kind':'invented analysis fixture; no provider observations','checks':checks,'real_analysis_run':False,'inversions_run':False},indent=2)+'\n')
print(json.dumps({'status':'passed','checks':len(checks),'paths':'tmp/hayward_analysis_checks/'},indent=2))
