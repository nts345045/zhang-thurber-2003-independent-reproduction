#!/usr/bin/env python3
"""Read saved outer-accumulator results; never compile, trace or evaluate action."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/development/loma_outer_accumulation_native_001'
OLD = ROOT / 'data/development/loma_initial_failure_3426_001'
TABLES = ('results.csv', 'history.csv', 'paths.csv',
          'path_gradient_checks.csv', 'cone_metric.csv')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def check_hashes(mapping, base):
    for name, expected in mapping.items():
        need(sha(base / name) == expected, 'Changed pinned file: ' + name)
    return len(mapping)


def ordered_norm(values):
    total = 0.0
    for value in values:
        total += value * value
    return math.sqrt(total)


def history_action_counts(history):
    previous = float(history[0]['time_s'])
    counts = dict(decreases=0, equals=0, increases=0)
    for row in history:
        if row['phase'] == 'accepted':
            current = float(row['time_s'])
            key = 'decreases' if current < previous else 'increases' if current > previous else 'equals'
            counts[key] += 1
            previous = current
    return counts


def first_scalar_difference(old, new, ignored):
    for index, (a, b) in enumerate(zip(old, new)):
        need(a.keys() == b.keys(), 'A/B history schema differs')
        differences = {key: dict(A=a[key], B=b[key]) for key in a
                       if key not in ignored and a[key] != b[key]}
        if differences:
            return dict(history_row=index, A_phase=a['phase'], B_phase=b['phase'],
                        A_iteration=a['iteration'], B_iteration=b['iteration'],
                        A_updates=a['updates'], B_updates=b['updates'], differences=differences)
    return None


def review():
    prepared, summary, execution = [load(OUT / name) for name in
                                    ('prepared.json', 'summary.json', 'execution.json')]
    prelaunch = load(OUT / 'prelaunch_review.json')
    need(summary['status'] == 'completed_single_change_diagnostic' and
         execution['status'] == 'completed' and execution['return_code'] == 0,
         'Native diagnostic has not completed successfully')
    need(execution['summary_sha256'] == sha(OUT / 'summary.json'), 'Terminal ledger mismatch')
    controller = load(OUT / 'controller_completion.json')
    need(controller['status'] == 'completed' and
         controller['native_summary_sha256'] == sha(OUT / 'summary.json') and
         controller['native_execution_sha256'] == sha(OUT / 'execution.json') and
         controller['launch_sha256'] == sha(OUT / 'launch.json') and
         controller['driver_pid'] == summary['driver_pid'] == execution['pid'],
         'Controller completion linkage mismatch')
    need(controller['detached_driver_return_code'] is None and
         'did not reap detached driver' in controller['driver_terminal_evidence'],
         'Unknown detached-driver return code was changed')
    need(controller['recorded_stage_return_codes'] ==
         {c['stage']: c['return_code'] for c in summary['commands']}, 'Controller stage codes differ')
    need(summary['prepared_sha256'] == prelaunch['prepared_sha256'] == sha(OUT / 'prepared.json'),
         'Prepared snapshot mismatch')
    need(prelaunch['status'] == 'passed' and
         summary['prelaunch_review_sha256'] == sha(OUT / 'prelaunch_review.json'),
         'Prelaunch review mismatch')
    counts = {
        'original_inputs': check_hashes(prepared['input_sha256'], ROOT),
        'prepared_files': check_hashes(prepared['prepared_file_sha256'], OUT),
        'candidate_sources': check_hashes(prepared['source_sha256'], OUT / 'source'),
        'terminal_outputs': check_hashes(summary['output_sha256'], OUT),
        'controller_logs': check_hashes(controller['output_sha256'], OUT)}
    need(sha(Path(prepared['compiler'])) == prepared['compiler_sha256'], 'Compiler changed')
    need(sha(ROOT / prepared['build'] / 'observe') == summary['binary_sha256'], 'Binary changed')
    for path, digest in summary['runtime_library_sha256'].items():
        need(sha(Path(path)) == digest, 'Runtime library changed')
    need([c['stage'] for c in summary['commands']] == ['compile', 'runtime_libraries', 'observe'] and
         all(c['status'] == 'completed' and c['return_code'] == 0 for c in summary['commands']),
         'Incomplete/failed commands')
    original = load(OLD / 'summary.json')
    original_history = rows(OLD / 'history.csv')
    need(prepared['original_results'] == summary['original_results'] == original['results'],
         'Before-change A results changed')
    controls = load(OUT / 'inputs/controls_summary.json')
    need(prepared['source_sha256'] == controls['variants']['outer_extended']['source_sha256'],
         'Candidate differs from reviewed controls')
    old_core = (OLD / 'source/src/core.hpp').read_text()
    change = '  double T = 0;\n  for (size_t i = 1; i < p.size(); i++) {'
    need(old_core.count(change) == 1 and (OUT / 'source/src/core.hpp').read_text() ==
         old_core.replace(change, change.replace('double T', 'long double T')),
         'Change is not exactly the one accumulator declaration')
    context = prepared['native_context']
    need(rows(OUT / 'identified_ray.csv') == [context], 'Native context copy differs')
    for prefix, name, index in [('native_source_', 'initial_events.csv', int(context['event'])),
                                ('native_receiver_', 'stations.csv', int(context['station']))]:
        native = rows(OLD / 'inputs' / name)[index]
        need(all(context[prefix + k] == v for k, v in native.items()), 'Native metadata mismatch')
    need(context['event'] == '65' and context['station'] == '46' and
         context['receiver_location_code'] == '', 'Wrong pair or empty location lost')
    reference = load(OUT / 'inputs/reference_row.json')
    need(reference['reference_eligible'] == '1' and reference['reference_candidate_count'] == '1',
         'Reference is not unique/eligible')
    assessment = load(OUT / 'inputs/reference_summary.json')
    grid_pin = 'data/development/loma_initial_reference_001/inputs/initial_grid.csv'
    need(assessment['input_source_sha256'][grid_pin] == sha(OUT / 'inputs/initial_grid.csv'),
         'Reference and candidate model differ')
    tables = {name: rows(OUT / name) for name in TABLES}
    values = tables['results.csv']
    need(values == summary['results'] and len(values) == 2 and
         {r['initialization'] for r in values} == {'straight', 'fmm'}, 'Wrong result inventory')
    run_ids = {r['run_id'] for r in values}
    for name, table in tables.items():
        sidecar = load(OUT / (name + '.identifiers.json'))
        need(sidecar['file'] == name and sidecar['file_sha256'] == sha(OUT / name) and
             sidecar['native_context'] == context and sidecar['join_key'] == 'observation_index' and
             sidecar['join_value'] == '3426' and sidecar['context_sha256'] == sha(OUT / 'identified_ray.csv'),
             'Native sidecar mismatch: ' + name)
        need(all(r['observation_index'] == '3426' and r['run_id'] in run_ids for r in table),
             'Unidentified/unknown table row: ' + name)
    grid = rows(OUT / 'inputs/initial_grid.csv')
    bounds = {a: (min(float(r[a]) for r in grid), max(float(r[a]) for r in grid)) for a in 'xyz'}
    outcomes = []
    for result in values:
        run = result['run_id']
        need(result['logged_matches_unobserved_variant'] == '1', 'Observer mismatch')
        need(result['max_updates'] == '1000' and float(result['path_spacing_km']) == .03125,
             'Settings changed')
        need(all(math.isfinite(float(result[k])) for k in
                 ('time_s', 'projected_gradient', 'raw_gradient', 'source_dx', 'source_dy', 'source_dz')),
             'Nonfinite modeled result')
        path = [r for r in tables['paths.csv'] if r['run_id'] == run]
        need(len(path) == int(result['path_nodes']) and
             [int(r['node']) for r in path] == list(range(len(path))), 'Path inventory changed')
        need(all(bounds[a][0] <= float(r[a]) <= bounds[a][1] for r in path for a in 'xyz'),
             'Nonfinite/outside path')
        for row, prefix in [(path[0], 'source'), (path[-1], 'receiver')]:
            need(all(float(row[a]) == float(reference['reference_' + prefix + '_' + a]) for a in 'xyz'),
                 'Endpoint changed')
            need(all(math.isnan(float(row['gradient_' + a])) for a in 'xyz'),
                 'Endpoint path-gradient placeholder changed')
        gradient, projected = [], []
        for row in path[1:-1]:
            for a in 'xyz':
                value = float(row['gradient_' + a]); need(math.isfinite(value), 'Nonfinite path gradient')
                gradient.append(value)
                direction = -value
                if ((float(row[a]) <= bounds[a][0] + 1e-10 and direction < 0) or
                        (float(row[a]) >= bounds[a][1] - 1e-10 and direction > 0)):
                    direction = 0.0
                projected.append(direction)
        need(ordered_norm(gradient) == float(result['raw_gradient']) and
             ordered_norm(projected) == float(result['projected_gradient']), 'Saved gradient norms differ')
        history = [r for r in tables['history.csv'] if r['run_id'] == run]
        need(history[0]['phase'] == 'initial' and history[-1]['phase'] == 'final', 'History incomplete')
        accepted = [r for r in history if r['phase'] == 'accepted']
        failed = [r for r in history if r['phase'] == 'line_search_failed']
        need(all(r['phase'] in ('initial', 'accepted', 'line_search_failed', 'final') for r in history),
             'Unknown history phase')
        need(len(accepted) == int(result['updates']) and len(failed) <= 1 and
             [int(r['updates']) for r in accepted] == list(range(1, len(accepted) + 1)),
             'Accepted update count differs')
        previous = float(history[0]['time_s'])
        equal_actions = 0
        for row in accepted:
            current = float(row['time_s']); step = float(row['accepted_step']); slope = float(row['directional_slope'])
            need(step > 0 and math.isfinite(slope) and slope < 0 and
                 1 <= int(row['line_search_evaluations']) <= 24, 'Invalid accepted search record')
            need(current <= previous + 1e-4 * step * slope and
                 float(row['action_change_s']) == previous - current,
                 'Recorded binary64 Armijo/action-change mismatch')
            equal_actions += current == previous
            previous = current
        final = history[-1]
        for key in ('time_s', 'projected_gradient', 'raw_gradient', 'path_nodes', 'updates'):
            need(float(final[key]) == float(result[key]), 'Final result/history mismatch: ' + key)
        if failed:
            need(history[-2] == failed[0] and int(failed[0]['line_search_evaluations']) == 24 and
                 result['converged'] == '0', 'Incorrect failed-search termination')
            termination = 'line_search_failed_after_24_trials'
        elif accepted and int(final['iteration']) == int(accepted[-1]['iteration']):
            need(float(accepted[-1]['action_change_s']) < 1e-11 and
                 float(final['projected_gradient']) < 1e-5 and result['converged'] == '1',
                 'Combined stopping condition does not hold')
            termination = 'combined_action_change_and_projected_gradient'
        elif int(final['iteration']) == 1000:
            termination = 'update_budget_exhausted'
        else:
            need(float(final['projected_gradient']) < 1e-7 and result['converged'] == '1',
                 'Strict stopping condition does not hold')
            termination = 'strict_projected_gradient'
        fd = [r for r in tables['path_gradient_checks.csv'] if r['run_id'] == run]
        need([float(r['step_km']) for r in fd] == [1e-4, 1e-5, 1e-6], 'FD inventory differs')
        for row in fd:
            node, axis = int(row['node']), 'xyz'[int(row['axis'])]
            need(float(row['analytic_gradient']) == float(path[node]['gradient_' + axis]) and
                 float(row['error']) == float(row['numerical_gradient']) - float(row['analytic_gradient']),
                 'Saved FD frame/arithmetic differs')
        time_error = float(result['time_s']) - float(reference['reference_time_s'])
        source_error = math.sqrt(sum((float(result['source_d' + a]) -
                                     float(reference['reference_source_d' + a + '_s_per_km'])) ** 2 for a in 'xyz'))
        comparison = [r for r in summary['continuous_reference_comparison'] if r['run_id'] == run]
        need(len(comparison) == 1, 'Comparison join ambiguous')
        comparison = comparison[0]
        need(comparison['time_error_s'] == time_error and
             comparison['source_error_euclidean_norm_s_per_km'] == source_error and
             comparison['time_limit_pass'] == (abs(time_error) <= 2.5e-5) and
             comparison['source_limit_pass'] == (source_error <= 3e-6) and
             comparison['original_local_convergence_flag'] == result['converged'] and
             comparison['native_context'] == context and comparison['final_history'] == final,
             'Reference arithmetic/flag/native mismatch')
        curvature_pairs = sum(int(r['curvature_pair_accepted']) for r in accepted)
        need(curvature_pairs == comparison['accepted_curvature_pairs'], 'Curvature-pair count differs')
        curvature_updates = [int(r['updates']) for r in accepted if r['curvature_pair_accepted'] == '1']
        old = [r for r in original['results'] if r['initialization'] == result['initialization']][0]
        old_history = [r for r in original_history if r['run_id'] == run]
        old_curvature = [r for r in old_history if r['phase'] == 'accepted' and
                         r['curvature_pair_accepted'] == '1']
        history_comparison = dict(
            compared_fields='All saved scalar columns as serialized; non-action comparison excludes only time_s and action_change_s.',
            A_rows=len(old_history), B_rows=len(history),
            first_any_scalar_difference=first_scalar_difference(old_history, history, ()),
            first_non_action_scalar_difference=first_scalar_difference(old_history, history,
                                                                         ('time_s', 'action_change_s')),
            A_action_counts=history_action_counts(old_history), B_action_counts=history_action_counts(history),
            A_accepted_curvature_pairs=len(old_curvature),
            A_last_curvature_iteration=int(old_curvature[-1]['iteration']) if old_curvature else None,
            A_last_curvature_update=int(old_curvature[-1]['updates']) if old_curvature else None,
            B_last_curvature_iteration=int([r for r in accepted if r['curvature_pair_accepted'] == '1'][-1]['iteration'])
            if curvature_updates else None,
            limitation='Matching saved scalar prefixes do not establish equality of unsaved intermediate paths, directions or arrays.')
        outcomes.append(dict(initialization=result['initialization'], candidate_result=result,
                             original_A_result=old, termination=termination, accepted_updates=len(accepted),
                             A_B_history_comparison=history_comparison,
                             accepted_curvature_pairs=curvature_pairs,
                             curvature_pair_accepted_updates=curvature_updates,
                             last_curvature_pair_update=curvature_updates[-1] if curvature_updates else None,
                             maximum_memory_pairs=max(int(r['memory_pairs']) for r in history),
                             gradient_fallback_records=sum(int(r['gradient_fallback']) for r in history),
                             accepted_equal_binary64_actions=equal_actions, final_history=final,
                             last_accepted_history=accepted[-1] if accepted else None,
                             time_error_s=time_error, source_error_euclidean_norm_s_per_km=source_error,
                             time_limit_pass=abs(time_error) <= 2.5e-5, source_limit_pass=source_error <= 3e-6,
                             minimum_accepted_step=min(float(r['accepted_step']) for r in accepted) if accepted else None,
                             maximum_search_evaluations=max(int(r['line_search_evaluations']) for r in history)))
    need(summary['selected_run_id'] == min(values, key=lambda r: float(r['time_s']))['run_id'],
         'Selected candidate differs from minimum saved action')
    for mapping, base in [(prepared['input_sha256'], ROOT),
                          (prepared['prepared_file_sha256'], OUT), (summary['output_sha256'], OUT),
                          (controller['output_sha256'], OUT)]:
        check_hashes(mapping, base)
    return dict(status='passed', reviewer='scientific_audit/ray_math_review',
                scope='Independent saved-table/source/native/hash readback; no solver or action evaluation.',
                summary_sha256=sha(OUT / 'summary.json'), execution_sha256=sha(OUT / 'execution.json'),
                controller_completion_sha256=sha(OUT / 'controller_completion.json'),
                controller_terminal_evidence=controller['driver_terminal_evidence'],
                detached_driver_return_code=controller['detached_driver_return_code'],
                prepared_sha256=sha(OUT / 'prepared.json'), prelaunch_review_sha256=sha(OUT / 'prelaunch_review.json'),
                review_helper_sha256=sha(Path(__file__)), verified_hashes=counts,
                original_A_retained=True, candidate_B_observed_unobserved_exact_numeric_parity_records=True,
                native_context=context, results=outcomes, selected_run_id=summary['selected_run_id'],
                material_issue_found=False, ray_runs_by_reviewer=0,
                limitations=[
                    'Observer neutrality is the recorded C++ exact numeric comparison of both B runs, not a separate Python ray recomputation. Signed zero representations are not distinguished.',
                    'The C++ equality includes dv/length/source/path arrays; model arrays are not separately exported for this review.',
                    'Candidate B is compared with the saved continuous reference and original A is retained separately; equality of B to A is neither required nor expected.',
                    'The field original_local_convergence_flag denotes B\'s unmodified flag, not the original A flag.',
                    'Reconstructed Armijo decisions use recorded binary64 values, not certified continuous action changes.',
                    'A single ray and unchanged local flags do not establish a general cure, branch completeness or inversion readiness.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true', help='Write new immutable native review.json')
    arguments = parser.parse_args()
    result = review()
    if arguments.write_review:
        with (OUT / 'review.json').open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps(result, indent=2, allow_nan=False))
