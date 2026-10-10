#!/usr/bin/env python3
"""Summarize saved observation-only ray-stopping evidence; no rays are computed."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', help='Repository-relative completed diagnostic directory')
args = parser.parse_args()
folder = ROOT / args.directory

def rows(name):
    with (folder / name).open() as stream:
        return list(csv.DictReader(stream))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

summary = json.loads((folder / 'summary.json').read_text())
for name, expected in summary['input_sha256'].items():
    if sha(ROOT / name) != expected:
        raise ValueError('Frozen input no longer matches: ' + name)
for name, expected in summary['sha256'].items():
    if sha(ROOT / name) != expected:
        raise ValueError('Recorded evidence no longer matches: ' + name)
results = rows('results.csv')
history = collections.defaultdict(list)
for row in rows('history.csv'):
    history[row['run_id']].append(row)
paths = collections.defaultdict(list)
for row in rows('paths.csv'):
    paths[row['run_id']].append(row)
fd = collections.defaultdict(list)
for row in rows('path_gradient_checks.csv'):
    fd[row['run_id']].append(row)
identified = rows('identified_ray.csv')
if len(identified) != 1:
    raise ValueError('Expected one complete native-identity mapping')
identity = identified[0]
for table in [results] + list(history.values()) + list(paths.values()) + list(fd.values()):
    if any(row['observation_index'] != identity['observation_index'] for row in table):
        raise ValueError('Broken observation identity join')

def stats(values):
    accepted = [r for r in values if r['phase'] == 'accepted']
    return {
        'accepted_updates': len(accepted),
        'non_descent_direction_fallbacks': sum(int(r['gradient_fallback']) for r in accepted),
        'boundary_limited_initial_steps': sum(float(r['feasible_initial_step']) < 1 for r in accepted),
        'minimum_accepted_step': min(float(r['accepted_step']) for r in accepted),
        'median_accepted_step': statistics.median(float(r['accepted_step']) for r in accepted),
        'maximum_line_search_evaluations': max(int(r['line_search_evaluations']) for r in accepted),
        'median_line_search_evaluations': statistics.median(int(r['line_search_evaluations']) for r in accepted),
        'curvature_pairs_accepted': sum(int(r['curvature_pair_accepted']) for r in accepted),
        'merged_nodes': sum(int(r['merged_nodes']) for r in accepted),
        'objective_increases': sum(float(r['action_change_s']) < 0 for r in accepted),
        'minimum_segment_km': min(float(r['min_segment_km']) for r in accepted),
        'last_action_change_s': float(accepted[-1]['action_change_s']),
        'last_maximum_node_step_km': float(accepted[-1]['max_node_step_km']),
        'last_memory_pairs': int(accepted[-1]['memory_pairs']),
    }

per_run = []
finite_errors = []
for result in results:
    name = result['run_id']
    rr = history[name]
    final = rr[-1]
    # Undefined step fields at initial/final rows and endpoint node gradients
    # are explicitly not applicable, not modeled NaN values.
    for row in rr:
        for key in ['time_s', 'projected_gradient', 'raw_gradient',
                    'min_segment_km', 'max_segment_km', 'tangential_gradient_norm',
                    'normal_gradient_norm']:
            if not math.isfinite(float(row[key])):
                finite_errors.append([name, row['phase'], row['updates'], key])
    for row in paths[name]:
        if any(not math.isfinite(float(row[k])) for k in ['x', 'y', 'z']):
            finite_errors.append([name, 'path', row['node']])
    accepted = [r for r in rr if r['phase'] == 'accepted']
    item = {
        'run_id': name, 'observation_index': identity['observation_index'],
        'result': result, 'all_updates': stats(rr), 'last_200_updates': stats(accepted[-200:]),
        'line_search_failure_records': sum(r['phase'] == 'line_search_failed' for r in rr),
        'final': {k: float(final[k]) for k in [
            'projected_gradient', 'raw_gradient', 'tangential_gradient_norm',
            'normal_gradient_norm', 'min_segment_km', 'max_segment_km',
            'min_internal_grid_plane_distance_km', 'x_min_active', 'x_max_active',
            'y_min_active', 'y_max_active', 'z_min_active', 'z_max_active']},
        'path_gradient_check_errors_s_per_km': {
            row['step_km']: float(row['error']) for row in fd[name]},
        'stop_classification': ('projected_gradient_below_1e-7' if float(result['projected_gradient']) < 1e-7
            else 'action_change_below_1e-11_and_projected_gradient_below_1e-5' if result['converged'] == '1'
            else 'not_converged'),
    }
    per_run.append(item)

by_name = {r['run_id']: r for r in results}
comparisons = []
def compare(label, first, second):
    a, b = by_name[first], by_name[second]
    comparisons.append({'comparison': label, 'first_run': first, 'second_run': second,
                        'second_minus_first_time_s': float(b['time_s']) - float(a['time_s']),
                        'source_derivative_difference_norm_s_per_km': math.sqrt(sum(
                            (float(b[k])-float(a[k]))**2 for k in ['source_dx', 'source_dy', 'source_dz']))})
for initialization in ['straight', 'fmm']:
    compare('increased_budget_same_spacing', initialization+'_0.500000_1000', initialization+'_0.500000_4000')
    compare('path_refinement_both_reach_unchanged_stopping', initialization+'_0.500000_4000', initialization+'_0.250000_4000')
for spacing in ['0.500000', '0.250000']:
    compare('initialization_difference_both_reach_unchanged_stopping', 'straight_'+spacing+'_4000', 'fmm_'+spacing+'_4000')
review = {
    'status': 'completed_component_review',
    'command': 'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_ray_stopping.py '+args.directory,
    'review_source_sha256': sha(Path(__file__)),
    'identity_mapping': 'identified_ray.csv', 'identity_join_column': 'observation_index',
    'native_identity': identity,
    'cases': len(results), 'instrumentation_matches_unmodified_all_cases': all(r['logged_matches_unmodified']=='1' for r in results),
    'modeled_nonfinite_records': finite_errors,
    'frozen_inputs_and_evidence_hashes_verified': True,
    'per_run': per_run, 'comparisons': comparisons,
    'interpretation': [
        'A non-descent projected L-BFGS direction invokes the existing unpreconditioned projected-gradient fallback and clears curvature memory. This occurs on every one of the final 200 accepted updates in all four longest-budget runs.',
        'Those final paths have active top-bound nodes. Their remaining raw gradient is predominantly normal to the path, while the infeasible part is removed by the projected-gradient test.',
        'The observed late progress is not accompanied by collapsed segments, repeated line-search failure, or disagreement in the tested feasible coordinate gradient. These observations isolate the active-bound direction projection as an immediate numerical bottleneck; they do not prove absence of every other effect.',
        'All four longest-budget runs stop by the existing combined action-change/projected-gradient rule, not by the separate 1e-7 projected-gradient threshold.',
        'Travel-time agreement is stronger than endpoint-derivative agreement. These local checks neither identify a globally first arrival nor establish derivative accuracy against an independent exact reference.',
    ],
    'next_component': 'Test the same weighted path-Laplacian metric in the feasible/free-coordinate subspace or a tangent-cone quadratic subproblem, retaining the original objective, domain, Armijo and ray-stopping rules. Do not infer that clipping a full-space SPD inverse direction preserves descent.',
    'sha256': {name: sha(folder/name) for name in ['summary.json', 'results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'identified_ray.csv', 'instrumentation.diff', 'source_snapshot.tar.gz']},
}
(folder/'review.json').write_text(json.dumps(review, indent=2, allow_nan=False)+'\n')
print(json.dumps({'cases': review['cases'], 'instrumentation_matches': review['instrumentation_matches_unmodified_all_cases'], 'nonfinite_errors': finite_errors, 'review': str(Path(args.directory)/'review.json')}, indent=2))
