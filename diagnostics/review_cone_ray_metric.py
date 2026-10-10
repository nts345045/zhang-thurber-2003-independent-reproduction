#!/usr/bin/env python3
"""Review saved full-cone ray diagnostics without tracing or changing a model."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
folder=ROOT/args.directory
baseline=ROOT/'data/development/ray_stopping_i775_budget_path'
reduced=ROOT/'data/development/ray_stopping_i775_reduced_all'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))
summary=json.loads((folder/'summary.json').read_text())
for collection in ['input_sha256','sha256']:
    for name,expected in summary[collection].items():
        if sha(ROOT/name)!=expected:raise ValueError('Changed recorded evidence/input: '+name)
if (folder/'identified_ray.csv').read_bytes()!=(baseline/'identified_ray.csv').read_bytes():raise ValueError('Native identity changed')
identity=rows(folder/'identified_ray.csv')[0]
results=rows(folder/'results.csv');history=collections.defaultdict(list);metrics=collections.defaultdict(list);paths=collections.defaultdict(list)
for row in rows(folder/'history.csv'):history[row['run_id']].append(row)
for row in rows(folder/'cone_metric.csv'):metrics[row['run_id']].append(row)
for row in rows(folder/'paths.csv'):paths[row['run_id']].append(row)
original={r['run_id']:r for r in rows(baseline/'results.csv')};limited={r['run_id']:r for r in rows(reduced/'results.csv')}
checks=[]
for result in results:
    name=result['run_id'];directions=metrics[name];accepted=[r for r in history[name] if r['phase']=='accepted']
    for row in history[name]+directions+paths[name]:
        if row['observation_index']!=identity['observation_index']:raise ValueError('Broken identity join')
    if any(not math.isfinite(float(result[k])) for k in ['time_s','projected_gradient','raw_gradient','source_dx','source_dy','source_dz']):raise ValueError('Nonfinite modeled result')
    endpoint_error=0
    for row,prefix in [(paths[name][0],'dd_source_'),(paths[name][-1],'receiver_')]:
        endpoint_error=max(endpoint_error,math.sqrt(sum((float(row[a])-float(identity[prefix+a+'_km']))**2 for a in ['x','y','z'])))
    comparisons=[]
    for label,reference in [('original',original[name.rsplit('_',1)[0]+'_4000']),('no_release',limited[name])]:
        comparisons.append({'reference':label,'reference_updates':int(reference['updates']),
                            'time_minus_reference_s':float(result['time_s'])-float(reference['time_s']),
                            'source_derivative_difference_s_per_km':math.sqrt(sum((float(result[k])-float(reference[k]))**2 for k in ['source_dx','source_dy','source_dz']))})
    checks.append({'run_id':name,'observation_index':identity['observation_index'],'result':result,
                   'strict_gradient_gate':float(result['projected_gradient'])<1e-7,
                   'combined_gate':result['converged']=='1' and float(result['projected_gradient'])>=1e-7,
                   'matches_unobserved_variant':result['logged_matches_unobserved_variant']=='1',
                   'metric_directions':len(directions),'metric_non_descent_directions':sum(float(r['slope'])>=0 for r in directions),
                   'maximum_active_set_solves':max(int(r['solves']) for r in directions),
                   'total_releases':sum(int(r['releases']) for r in directions),'total_blocks':sum(int(r['blocks']) for r in directions),
                   'quadratic_certificate_failures':sum(r['success']!='1' for r in directions),
                   'maximum_free_backward_error':max(float(r['free_equation_relative_backward_error']) for r in directions),
                   'maximum_free_equation_error':max(float(r['free_equation_max_error']) for r in directions),
                   'maximum_primal_violation':max(float(r['primal_violation']) for r in directions),
                   'maximum_dual_violation':max(float(r['dual_violation']) for r in directions),
                   'maximum_complementarity_error':max(float(r['complementarity_max_error']) for r in directions),
                   'accepted_non_descent_directions':sum(float(r['directional_slope'])>=0 for r in accepted),
                   'objective_increases':sum(float(r['action_change_s'])<0 for r in accepted),
                   'unchanged_objectives':sum(float(r['action_change_s'])==0 for r in accepted),
                   'maximum_line_search_evaluations':max(int(r['line_search_evaluations']) for r in accepted),
                   'line_search_failures':sum(r['phase']=='line_search_failed' for r in history[name]),
                   'maximum_endpoint_roundoff_km':endpoint_error,'comparisons':comparisons})
by_name={r['run_id']:r for r in results};seed_comparisons=[]
for spacing in ['0.500000','0.250000']:
    a=by_name['straight_'+spacing+'_1000'];b=by_name['fmm_'+spacing+'_1000']
    seed_comparisons.append({'path_spacing_km':float(spacing),'fmm_minus_straight_time_s':float(b['time_s'])-float(a['time_s']),
                            'source_derivative_difference_s_per_km':math.sqrt(sum((float(b[k])-float(a[k]))**2 for k in ['source_dx','source_dy','source_dz']))})
review={'status':'completed_with_preserved_failures' if any(r['converged']!='1' for r in results) else 'all_four_meet_existing_stopping',
        'command':'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_cone_ray_metric.py '+args.directory,
        'review_source_sha256':sha(Path(__file__)),'identity_mapping':'identified_ray.csv','identity_join_column':'observation_index',
        'native_identity':identity,'input_and_evidence_hashes_verified':True,'per_run':checks,'seed_comparisons':seed_comparisons,
        'limitations':['The quadratic KKT certificate is within a stated floating-point arithmetic tolerance, not an exact-real arithmetic proof.',
                       'Domain activity uses the unchanged 1e-10 km numerical boundary tolerance; no new physical path constraint is imposed.',
                       'One identified ray at two path spacings/two initializations does not validate all rays, global first-arrival selection, or production integration.',
                       'Ray action, domain, Armijo and stopping tolerances remain unchanged; coarse FMM can still stop under the existing combined criterion just above the strict 1e-7 gradient threshold.'],
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [folder/'summary.json',folder/'results.csv',folder/'history.csv',folder/'cone_metric.csv',folder/'identified_ray.csv',folder/'source_snapshot.tar.gz',baseline/'results.csv',reduced/'results.csv']}}
(folder/'review.json').write_text(json.dumps(review,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':review['status'],'seed_comparisons':seed_comparisons},indent=2))
