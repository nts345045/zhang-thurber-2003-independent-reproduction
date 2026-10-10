#!/usr/bin/env python3
"""Read completed reduced-direction diagnostics and preserve comparisons."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory')
args=parser.parse_args()
folder=ROOT/args.directory
baseline=ROOT/'data/development/ray_stopping_i775_budget_path'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))
summary=json.loads((folder/'summary.json').read_text())
for collection in ['input_sha256','sha256']:
    for path,expected in summary[collection].items():
        if sha(ROOT/path)!=expected:raise ValueError('Changed recorded input/evidence: '+path)
if (folder/'identified_ray.csv').read_bytes()!=(baseline/'identified_ray.csv').read_bytes():
    raise ValueError('Native identity differs from baseline')
identity=rows(folder/'identified_ray.csv')[0]
results=rows(folder/'results.csv')
history=collections.defaultdict(list);metric=collections.defaultdict(list)
for row in rows(folder/'history.csv'):history[row['run_id']].append(row)
for row in rows(folder/'reduced_metric.csv'):metric[row['run_id']].append(row)
reference={r['run_id']:r for r in rows(baseline/'results.csv')}
checks=[]
for result in results:
    name=result['run_id'];updates=[r for r in history[name] if r['phase']=='accepted'];directions=metric[name]
    if any(r['observation_index']!=identity['observation_index'] for r in history[name]+directions):
        raise ValueError('Broken native identity join')
    ref_name=name.rsplit('_',1)[0]+'_4000';ref=reference[ref_name]
    item={'run_id':name,'observation_index':identity['observation_index'],'result':result,
          'matches_unobserved_variant':result['logged_matches_unobserved_variant']=='1',
          'strict_gradient_gate':float(result['projected_gradient'])<1e-7,
          'combined_gate':result['converged']=='1' and float(result['projected_gradient'])>=1e-7,
          'accepted_updates':len(updates),'metric_directions':len(directions),
          'metric_non_descent_directions':sum(float(r['slope'])>=0 for r in directions),
          'metric_maximum_slope':max(float(r['slope']) for r in directions),
          'metric_maximum_free_equation_error':max(float(r['free_equation_max_error']) for r in directions),
          'metric_directions_with_wrong_sign_frozen_multipliers':sum(int(r['inward_multiplier_violations'])>0 for r in directions),
          'metric_wrong_sign_frozen_multipliers':sum(int(r['inward_multiplier_violations']) for r in directions),
          'metric_most_negative_signed_multiplier':min(float(r['most_negative_signed_multiplier']) for r in directions),
          'metric_added_fixed_coordinates':sum(int(r['added_fixed']) for r in directions),
          'objective_increases':sum(float(r['action_change_s'])<0 for r in updates),
          'unchanged_objectives':sum(float(r['action_change_s'])==0 for r in updates),
          'maximum_line_search_evaluations':max(int(r['line_search_evaluations']) for r in updates),
          'line_search_failures':[r for r in history[name] if r['phase']=='line_search_failed'],
          'reference_run':ref_name,'time_minus_reference_s':float(result['time_s'])-float(ref['time_s']),
          'source_derivative_difference_from_reference_s_per_km':math.sqrt(sum((float(result[k])-float(ref[k]))**2 for k in ['source_dx','source_dy','source_dz']))}
    # Undefined action_change on failed search is explicit not-applicable.
    for failure in item['line_search_failures']:
        failure['action_change_s']=None
    checks.append(item)
by_name={r['run_id']:r for r in results};comparisons=[]
for spacing in ['0.500000','0.250000']:
    a=by_name['straight_'+spacing+'_1000'];b=by_name['fmm_'+spacing+'_1000']
    comparisons.append({'path_spacing_km':float(spacing),'fmm_minus_straight_time_s':float(b['time_s'])-float(a['time_s']),
                        'source_derivative_difference_s_per_km':math.sqrt(sum((float(b[k])-float(a[k]))**2 for k in ['source_dx','source_dy','source_dz']))})
review={'status':'completed_with_preserved_failures' if any(r['converged']!='1' for r in results) else 'all_four_meet_existing_stopping',
        'command':'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_reduced_ray_metric.py '+args.directory,
        'review_source_sha256':sha(Path(__file__)),'identity_mapping':'identified_ray.csv','identity_join_column':'observation_index',
        'native_identity':identity,'input_and_evidence_hashes_verified':True,'per_run':checks,'seed_comparisons':comparisons,
        'limitations':['The no-release reduced metric is not the exact tangent-cone quadratic minimizer; wrong-sign frozen multipliers are retained in reduced_metric.csv.',
                       'The frozen set is recomputed each outer update, but no blocked coordinate is released within a direction solve.',
                       'Only one identified event/receiver ray is tested at two path spacings and two initializations; this does not establish a globally first arrival or production readiness.',
                       'Original objective, domain, Armijo and stopping thresholds are unchanged. The reduced-all variant changes the direction on every update; the fallback-only variant retains full-space L-BFGS attempts.'],
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [folder/'summary.json',folder/'results.csv',folder/'history.csv',folder/'reduced_metric.csv',folder/'identified_ray.csv',folder/'source_snapshot.tar.gz',baseline/'results.csv']}}
(folder/'review.json').write_text(json.dumps(review,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':review['status'],'seed_comparisons':comparisons},indent=2))
