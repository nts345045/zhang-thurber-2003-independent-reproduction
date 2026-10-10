#!/usr/bin/env python3
"""Read terminal D/C files; never trace rays or evaluate the action."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/development/loma_usable_curvature_native_001'
BASE = ROOT / 'data/development/loma_positive_curvature_native_001'
CONTROLS = ROOT / 'data/development/usable_ray_curvature_controls_001'
TABLES = ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path): return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def verify(base, mapping):
    for name, digest in mapping.items():
        need(sha(base / name) == digest, 'Changed pin: ' + str(base / name))


def num(value):
    result = float(value)
    need(math.isfinite(result), 'Nonfinite saved modeled value')
    return result


def norm(values):
    total = 0.
    for value in values:
        total += value * value
    return math.sqrt(total)


def check():
    need(sha(OUT / 'summary.json') == 'a37bc49a78d58fe29a5064dc7117f9eef5edfcf441487c6d3f3e34866f77d815', 'Unexpected terminal summary')
    s, e, p, controller, launch, source_review = [load(OUT / name) for name in
        ('summary.json', 'execution.json', 'prepared.json', 'controller_completion.json', 'prelaunch_review.json', 'source_review.json')]
    need(s['status'] == 'completed_usable_curvature_diagnostic' and e['status'] == 'completed' and
         e['return_code'] == 0 and e['summary_sha256'] == sha(OUT / 'summary.json'), 'Not completed')
    need(controller['status'] == 'completed' and controller['child_reaped'] and controller['driver_return_code'] == 0 and
         controller['driver_pid'] == e['pid'] == s['driver_pid'] and
         controller['summary_sha256'] == sha(OUT / 'summary.json') and
         controller['execution_sha256'] == sha(OUT / 'execution.json') and
         controller['launch_sha256'] == sha(OUT / 'launch.json') and
         controller['controller_sha256'] == sha(OUT / 'controller.py'), 'Controller binding differs')
    need(launch['status'] == source_review['status'] == 'passed' and
         launch['prepared_sha256'] == source_review['prepared_sha256'] == s['prepared_sha256'] == sha(OUT / 'prepared.json') and
         s['prelaunch_review_sha256'] == sha(OUT / 'prelaunch_review.json') and
         launch['launcher_sha256'] == source_review['launcher_sha256'] == p['launcher_sha256'] == sha(OUT / 'launcher.py') ==
         sha(ROOT / 'diagnostics/run_usable_curvature_native.py'), 'Source/launch binding differs')
    maps = [(ROOT, p['input_sha256']), (OUT, p['prepared_file_sha256']), (OUT / 'source', s['source_sha256']),
            (OUT, s['output_sha256']), (OUT, controller['log_sha256'])]
    for base, mapping in maps: verify(base, mapping)
    need(s['input_sha256'] == p['input_sha256'] and s['source_sha256'] == p['source_sha256'], 'Snapshot changed')
    need(sha(Path(s['compiler'])) == s['compiler_sha256'] and
         sha(ROOT / s['build'] / 'observe') == s['binary_sha256'], 'Compiler/binary changed')
    verify(Path('/'), s['runtime_library_sha256'])
    need([c['stage'] for c in s['commands']] == ['compile', 'runtime_libraries', 'observe'] and
         all(c['status'] == 'completed' and c['return_code'] == 0 for c in s['commands']), 'Incomplete execution stages')
    need((s['path_spacing_km'], s['field_spacing_km'], s['maximum_updates'], s['threads']) == (.03125, .125, 1000, 1), 'Settings changed')
    baseline, old_review, tests, tests_review = [load(path) for path in
        (BASE / 'summary.json', BASE / 'review.json', CONTROLS / 'summary.json', CONTROLS / 'review.json')]
    need(old_review['status'] == tests_review['status'] == 'passed' and
         old_review['summary_sha256'] == sha(BASE / 'summary.json') and
         tests_review['summary_sha256'] == sha(CONTROLS / 'summary.json'), 'Predecessor reviews stale')
    changed = []
    for name, digest in s['source_sha256'].items():
        need(sha(CONTROLS / 'source/D' / name) == digest, 'D differs from controlled source')
        if name in baseline['source_sha256']:
            need(sha(CONTROLS / 'source/C' / name) == sha(BASE / 'source' / name) == baseline['source_sha256'][name], 'C source changed')
            if digest != baseline['source_sha256'][name]: changed.append(name)
    need(set(changed) == {'src/core.hpp', 'diagnostics/observed_optimizer.hpp'} and
         set(s['source_sha256']) - set(baseline['source_sha256']) == {'diagnostics/usable_ray_curvature.hpp'}, 'Wrong change inventory')
    context = s['native_context']
    need(len(context) == 199 and context == p['native_context'] == baseline['native_context'] and
         rows(OUT / 'identified_ray.csv') == [context] and context['receiver_location_code'] == '', 'Native context changed')
    reference = load(OUT / 'inputs/reference_row.json')
    need(reference['reference_eligible'] == '1' and reference['reference_candidate_count'] == '1', 'Reference not unique/eligible')
    for name in ('curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        need(sha(OUT / 'inputs' / name) == sha(BASE / 'inputs' / name), 'Saved Candidate changed')
        side = load(OUT / 'inputs' / (name + '.identifiers.json'))
        need(side['file_sha256'] == sha(OUT / 'inputs' / name) and side['native_context'] == context, 'Seed identity changed')
    tables = {name: rows(OUT / name) for name in TABLES}
    need(tables['results.csv'] == s['results'] == baseline['results'] and len(s['results']) == 2, 'C/D result inventory differs')
    run_ids = {row['run_id'] for row in s['results']}
    for name, table in tables.items():
        need(sha(OUT / name) == sha(BASE / name) == p['expected_old_table_sha256'][name] ==
             old_review['diagnostic_C_table_sha256'][name], 'Not exact C table parity: ' + name)
        need(all(row['observation_index'] == '3426' and row['run_id'] in run_ids for row in table), 'Native row join changed')
        side = load(OUT / (name + '.identifiers.json'))
        need(side['file_sha256'] == sha(OUT / name) and side['native_context'] == context and
             side['context_sha256'] == sha(OUT / 'identified_ray.csv') and
             side['join_key'] == 'observation_index' and side['join_value'] == '3426', 'Output sidecar changed')
    need(s['native_C_neutrality_pass'] and all(s['baseline_table_equalities'].values()) and
         s['observed_paths_and_arrays_match_unobserved_variant'] and not s['production_adoption'] and
         not s['scientific_success'] and not s['exact_curvature_sign_claimed'], 'Scope/parity status differs')
    grid = rows(OUT / 'inputs/initial_grid.csv')
    bounds = {a: (min(num(r[a]) for r in grid), max(num(r[a]) for r in grid)) for a in 'xyz'}
    outcomes = []
    for result in s['results']:
        run = result['run_id']; path = [r for r in tables['paths.csv'] if r['run_id'] == run]
        need(result['logged_matches_unobserved_variant'] == '1' and len(path) == int(result['path_nodes']) and
             [int(r['node']) for r in path] == list(range(len(path))), 'Path/parity inventory differs')
        need(all(bounds[a][0] <= num(row[a]) <= bounds[a][1] for row in path for a in 'xyz'), 'Path outside model')
        for row, prefix in ((path[0], 'source'), (path[-1], 'receiver')):
            need(all(num(row[a]) == num(reference['reference_' + prefix + '_' + a]) ==
                     num(context[prefix + '_' + a + '_km']) for a in 'xyz'), 'Endpoint differs')
        grad, projected = [], []
        for row in path[1:-1]:
            for a in 'xyz':
                value = num(row['gradient_' + a]); grad.append(value); d = -value
                if ((num(row[a]) <= bounds[a][0] + 1e-10 and d < 0) or
                        (num(row[a]) >= bounds[a][1] - 1e-10 and d > 0)): d = 0.
                projected.append(d)
        need(norm(grad) == num(result['raw_gradient']) and norm(projected) == num(result['projected_gradient']), 'Saved gradient norms differ')
        need(all(norm(num(b[a]) - num(first[a]) for a in 'xyz') > 0 for first, b in zip(path, path[1:])), 'Zero final edge')
        history = [r for r in tables['history.csv'] if r['run_id'] == run]
        accepted = [r for r in history if r['phase'] == 'accepted']
        need(history[0]['phase'] == 'initial' and history[-1]['phase'] == 'final' and
             len(history) == len(accepted) + 2 and len(accepted) == int(result['updates']), 'History inventory differs')
        previous = num(history[0]['time_s']); memory = []; retained = []; combined = []; counts = dict(decreases=0, equals=0, increases=0)
        for i, row in enumerate(accepted):
            need(int(row['iteration']) == i and int(row['updates']) == i + 1, 'Update ordering differs')
            current, step, slope = [num(row[k]) for k in ('time_s', 'accepted_step', 'directional_slope')]
            searches = int(row['line_search_evaluations'])
            need(step > 0 and slope < 0 and 1 <= searches <= 24 and
                 step == num(row['feasible_initial_step']) * 2. ** (1-searches), 'Saved line search differs')
            need(current <= previous + 1e-4 * step * slope and num(row['action_change_s']) == previous-current, 'Recorded approximate Armijo/change differs')
            counts['decreases' if current < previous else 'increases' if current > previous else 'equals'] += 1
            previous = current
            if int(row['gradient_fallback']) or int(row['merged_nodes']): memory = []
            if row['curvature_pair_accepted'] == '1': memory = (memory + [i])[-8:]; retained.append(i)
            need(int(row['memory_pairs']) == len(memory), 'Memory evolution differs')
            if num(row['action_change_s']) < 1e-11 and num(row['projected_gradient']) < 1e-5: combined.append(i)
            if i + 1 < len(accepted): need(num(row['projected_gradient']) >= 1e-7, 'Ignored strict convergence')
        final = history[-1]
        need(combined == [len(accepted)-1] and int(final['iteration']) == len(accepted)-1 and
             result['converged'] == '1' and num(final['projected_gradient']) >= 1e-7, 'Combined/strict stopping interpretation differs')
        for key in ('time_s', 'projected_gradient', 'raw_gradient', 'path_nodes', 'updates'):
            need(num(final[key]) == num(result[key]), 'Final history/result mismatch')
        dt = num(result['time_s']) - num(reference['reference_time_s'])
        components = [num(result['source_d'+a])-num(reference['reference_source_d'+a+'_s_per_km']) for a in 'xyz']
        error = norm(components)
        comparison = [r for r in s['continuous_reference_comparison'] if r['run_id'] == run]
        need(len(comparison) == 1 and comparison[0]['time_error_s'] == dt and
             comparison[0]['source_error_euclidean_norm_s_per_km'] == error and
             comparison[0]['accepted_curvature_pairs'] == len(retained) and comparison[0]['native_context'] == context and
             comparison[0]['time_limit_pass'] == (abs(dt) <= 2.5e-5) and
             comparison[0]['source_limit_pass'] == (error <= 3e-6), 'Reference arithmetic differs')
        outcomes.append(dict(result=result, termination='combined_action_change_and_projected_gradient',
            strict_1e_minus7_satisfied=False, accepted_updates=len(accepted), retained_pairs=len(retained),
            final_memory_creation_iterations=memory, last_action_change_s=num(accepted[-1]['action_change_s']),
            recorded_approximate_action_counts=counts, gradient_fallbacks=sum(int(r['gradient_fallback']) for r in history),
            time_error_s=dt, source_error_xyz_s_per_km=components, source_error_euclidean_norm_s_per_km=error,
            time_limit_pass=abs(dt)<=2.5e-5, source_limit_pass=error<=3e-6))
    for base, mapping in maps: verify(base, mapping)
    return dict(status='passed', reviewer='ray_math_review', material_issue_found=False,
        scope='Independent saved-output/hash/native/source and stopping readback; no native tracing or action evaluation.',
        summary_sha256=sha(OUT/'summary.json'), execution_sha256=sha(OUT/'execution.json'),
        controller_completion_sha256=sha(OUT/'controller_completion.json'), prepared_sha256=sha(OUT/'prepared.json'),
        prelaunch_review_sha256=sha(OUT/'prelaunch_review.json'), source_review_sha256=sha(OUT/'source_review.json'),
        launcher_sha256=sha(OUT/'launcher.py'), checker_sha256=sha(Path(__file__)),
        verified_input_pins=len(p['input_sha256']), verified_prepared_pins=len(p['prepared_file_sha256']),
        verified_source_pins=len(s['source_sha256']), verified_output_pins=len(s['output_sha256']),
        controller_child_reaped=True, controller_return_code=0, changed_existing_source_files=changed,
        added_source_file='diagnostics/usable_ray_curvature.hpp', full_native_context=context,
        all_five_C_tables_byte_identical=True, exact_table_sha256={name:sha(OUT/name) for name in TABLES},
        output_row_counts={name:len(table) for name,table in tables.items()},
        same_variant_observer_numeric_parity_recorded=True, results=outcomes,
        time_limit_s=2.5e-5, source_vector_limit_s_per_km=3e-6,
        limitations=['All five saved tables have byte parity; separately exported model arrays are unavailable, so same-variant array neutrality relies on the recorded exact-numeric C++ comparison.',
                     'Both flags use the unchanged combined stopping rule, not the strict projected-gradient rule.',
                     'No new sy/component history was captured; exact signs or informative curvature are not inferred.',
                     'Recorded Armijo/action comparisons concern approximate totals, not certified Fermat action differences.',
                     'This one-ray parity result establishes no general convergence, global first-arrival, production-adoption, or inversion-readiness claim.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    args = parser.parse_args()
    result = check()
    if args.write_review:
        with (OUT / 'review.json').open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(result, indent=2, allow_nan=False))
