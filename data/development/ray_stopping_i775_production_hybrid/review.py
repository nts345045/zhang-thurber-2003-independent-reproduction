#!/usr/bin/env python3
"""Compare the promoted trace observations with frozen finite-guard evidence."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE = ROOT / 'data/development/ray_stopping_i775_cone_hybrid_finite_guard'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))
summary = json.loads((HERE / 'summary.json').read_text())
reference_summary = json.loads((REFERENCE / 'summary.json').read_text())
# Source hashes refer to the exact compiled archive, so later source changes do
# not invalidate this comparison of frozen evidence.
with tarfile.open(str(HERE / 'source_snapshot.tar.gz'), 'r:gz') as archive:
    for name, expected in summary['source_sha256'].items():
        data = archive.extractfile(name).read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Changed source snapshot: ' + name)
        member = archive.getmember(name)
        if member.uid or member.gid or member.mtime or member.uname or member.gname:
            raise ValueError('Unnormalized archive metadata: ' + name)
files = ['results.csv', 'paths.csv', 'history.csv', 'cone_metric.csv',
         'path_gradient_checks.csv', 'identified_ray.csv']
for folder, manifest in [(HERE, summary), (REFERENCE, reference_summary)]:
    for name in files + ['source_snapshot.tar.gz', 'instrumentation.diff']:
        path = folder / name
        if sha(path) != manifest['sha256'][str(path.relative_to(ROOT))]:
            raise ValueError('Changed frozen evidence: ' + str(path.relative_to(ROOT)))
for name, expected in summary['input_sha256'].items():
    if not name.startswith('src/') and sha(ROOT / name) != expected:
        raise ValueError('Changed observational input: ' + name)
identity = rows(HERE / 'identified_ray.csv')
if len(identity) != 1 or identity != rows(REFERENCE / 'identified_ray.csv'):
    raise ValueError('Native identity mapping changed')
identity = identity[0]
current = rows(HERE / 'results.csv')
reference = {r['run_id']: r for r in rows(REFERENCE / 'results.csv')}
expected_runs = set(reference)
if set(r['run_id'] for r in current) != expected_runs or len(current) != 4:
    raise ValueError('Expected the same four seed/spacing controls')
history = collections.defaultdict(list)
metrics = collections.defaultdict(list)
paths = collections.defaultdict(list)
for name, target in [('history.csv', history), ('cone_metric.csv', metrics), ('paths.csv', paths)]:
    for row in rows(HERE / name):
        if row['observation_index'] != identity['observation_index']:
            raise ValueError('Broken identifier join in ' + name)
        target[row['run_id']].append(row)
per_run = []
for row in current:
    name = row['run_id']
    accepted = [r for r in history[name] if r['phase'] == 'accepted']
    numeric_columns = ['time_s', 'projected_gradient', 'raw_gradient',
                       'source_dx', 'source_dy', 'source_dz']
    if not all(math.isfinite(float(row[k])) for k in numeric_columns):
        raise ValueError('Nonfinite modeled result')
    for point in paths[name]:
        if not all(math.isfinite(float(point[k])) for k in ['x', 'y', 'z']):
            raise ValueError('Nonfinite path position')
    endpoints_exact = all(float(point[axis]) == float(identity[prefix + axis + '_km'])
                          for point, prefix in [(paths[name][0], 'dd_source_'),
                                                (paths[name][-1], 'receiver_')]
                          for axis in ['x', 'y', 'z'])
    per_run.append({'run_id': name, 'observation_index': identity['observation_index'],
                    'updates': int(row['updates']), 'converged': row['converged'] == '1',
                    'projected_gradient': float(row['projected_gradient']),
                    'strict_gradient_gate': float(row['projected_gradient']) < 1e-7,
                    'combined_gate': row['converged'] == '1' and float(row['projected_gradient']) >= 1e-7,
                    'all_result_columns_equal_reference': row == reference[name],
                    'numeric_result_minus_reference': {k: float(row[k]) - float(reference[name][k]) for k in numeric_columns},
                    'matches_actual_trace_including_dv_length': row['logged_matches_unobserved_variant'] == '1',
                    'exact_endpoints': endpoints_exact,
                    'accepted_steps': len(accepted), 'cone_replacements': len(metrics[name]),
                    'retained_lbfgs_directions': len(accepted) - len(metrics[name]),
                    'finite_strict_descent_and_action_decrease': all(
                        math.isfinite(float(r['directional_slope'])) and float(r['directional_slope']) < 0 and
                        math.isfinite(float(r['action_change_s'])) and float(r['action_change_s']) > 0 for r in accepted),
                    'line_search_failures': sum(r['phase'] == 'line_search_failed' for r in history[name]),
                    'maximum_line_search_evaluations': max(int(r['line_search_evaluations']) for r in accepted),
                    'quadratic_certificate_failures': sum(r['success'] != '1' for r in metrics[name]),
                    'maximum_free_backward_error': max(float(r['free_equation_relative_backward_error']) for r in metrics[name]),
                    'maximum_primal_violation': max(float(r['primal_violation']) for r in metrics[name]),
                    'maximum_dual_violation': max(float(r['dual_violation']) for r in metrics[name]),
                    'maximum_complementarity_error': max(float(r['complementarity_max_error']) for r in metrics[name])})
rejection_command = ['python3', 'diagnostics/run_ray_stopping.py', '--variant',
                     'historical_mode_rejection', '--budgets', '1000', '--cone-hybrid']
rejection = subprocess.run(rejection_command, cwd=str(ROOT), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
rejection_ok = rejection.returncode == 2 and 'Historical optimizer modes require the pre-promotion trace' in rejection.stderr
rejection_ok = rejection_ok and not (ROOT / 'tmp/ray_stopping/historical_mode_rejection').exists()
rejection_ok = rejection_ok and not (ROOT / 'data/development/ray_stopping_historical_mode_rejection').exists()
comparison = {name: (HERE / name).read_bytes() == (REFERENCE / name).read_bytes() for name in files}
review = {'status': 'verified' if all(comparison.values()) and rejection_ok and
          all(r['matches_actual_trace_including_dv_length'] and r['exact_endpoints'] and
              r['finite_strict_descent_and_action_decrease'] and not r['quadratic_certificate_failures'] for r in per_run)
          else 'differences_or_failures_preserved',
          'command': 'PYTHONDONTWRITEBYTECODE=1 python3 ' + str(Path(__file__).resolve().relative_to(ROOT)),
          'source_sha256': sha(Path(__file__)), 'reference': str(REFERENCE.relative_to(ROOT)),
          'identity_mapping': 'identified_ray.csv', 'identity_join_column': 'observation_index',
          'native_identity': identity, 'archive_and_evidence_hashes_verified': True,
          'all_six_result_files_byte_equal_reference': all(comparison.values()),
          'byte_equal_reference': comparison, 'per_run': per_run,
          'historical_mode_rejection': {'command': rejection_command, 'return_code': rejection.returncode,
                                        'stderr': rejection.stderr, 'rejected_before_creating_output': rejection_ok},
          'sha256': {str(path.relative_to(ROOT)): sha(path) for folder in [HERE, REFERENCE]
                     for path in [folder / 'summary.json'] + [folder / name for name in files]},
          'limitations': ['Four controls of one identified ray establish promotion and observation parity, not general first-arrival or inversion convergence.',
                         'The retained combined stopping criterion allows the coarse FMM path to stop above the strict 1e-7 projected-gradient gate.',
                         'The frozen historical diagnostic includes a generated optimizer variant; the new control calls the actual promoted trace.',
                         'The KKT certificate uses bounded floating-point tolerances, not exact arithmetic.',
                         'Endpoint path-gradient and initial/final step fields use nan only for not-applicable quantities.']}
(HERE / 'review.json').write_text(json.dumps(review, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': review['status'], 'byte_equal_reference': comparison,
                  'historical_mode_rejected': rejection_ok}, indent=2))
