#!/usr/bin/env python3
"""Read the completed positive-retention experiment; never trace/evaluate action."""
import argparse
import csv
import difflib
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/development/loma_positive_curvature_native_001'
BASE = ROOT / 'data/development/loma_seed_loaded_b_native_001'
CAPTURE = ROOT / 'data/development/loma_curvature_capture_native_001'
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
        need(sha(base / name) == digest, 'Hash mismatch: ' + str(base / name))


def num(value):
    value = float(value)
    need(math.isfinite(value), 'Nonfinite modeled value')
    return value


def norm(values):
    total = 0.0
    for value in values:
        total += value * value
    return math.sqrt(total)


def first_difference(before, after, ignored=()):
    for i, (b, c) in enumerate(zip(before, after)):
        need(b.keys() == c.keys(), 'B/C scalar schema differs')
        difference = {k: {'B': b[k], 'C': c[k]} for k in b if k not in ignored and b[k] != c[k]}
        if difference:
            return dict(history_row=i, B_iteration=b['iteration'], C_iteration=c['iteration'],
                        B_phase=b['phase'], C_phase=c['phase'], differences=difference)
    return None


def action_counts(history):
    previous = num(history[0]['time_s'])
    counts = dict(decreases=0, equals=0, increases=0)
    for row in history:
        if row['phase'] == 'accepted':
            current = num(row['time_s'])
            counts['decreases' if current < previous else 'increases' if current > previous else 'equals'] += 1
            previous = current
    return counts


def check():
    expected = {'summary.json': 'b3b62eb763f3fe6a6d7dffbdd6592fcbd0130c2a49a4df227381e818adb6e87c',
                'execution.json': '1ae4af743d7899566442935d79a002458443075396526e7059712387c161193a',
                'prepared.json': '79562a3f2485633c84342571a77fd94f39d32e4a6d7e64247808a82ef628e60f',
                'prelaunch_review.json': 'f31cfb8cb330e42cb31e9206307bda7ef3730da62d9bf976ed983d08e8fe95d7'}
    verify(OUT, expected)
    summary, execution, prepared, prelaunch, controller = [load(OUT / n) for n in
        ('summary.json', 'execution.json', 'prepared.json', 'prelaunch_review.json', 'controller_completion.json')]
    need(summary['status'] == 'completed_positive_curvature_diagnostic' and execution['status'] == 'completed' and
         execution['return_code'] == 0 and execution['summary_sha256'] == sha(OUT / 'summary.json'), 'Not terminal')
    need(controller['status'] == 'completed' and controller['child_reaped'] is True and
         controller['driver_return_code'] == 0 and controller['driver_pid'] == execution['pid'] == summary['driver_pid'] and
         controller['summary_sha256'] == sha(OUT / 'summary.json') and
         controller['execution_sha256'] == sha(OUT / 'execution.json') and
         controller['launch_sha256'] == sha(OUT / 'launch.json') and
         controller['controller_sha256'] == sha(OUT / 'controller.py'), 'Controller links/lifecycle differ')
    need(summary['prepared_sha256'] == prelaunch['prepared_sha256'] == sha(OUT / 'prepared.json') and
         prelaunch['status'] == 'passed' and summary['prelaunch_review_sha256'] == sha(OUT / 'prelaunch_review.json') and
         prelaunch['launcher_sha256'] == prepared['launcher_sha256'] == sha(OUT / 'launcher.py') ==
         sha(ROOT / 'diagnostics/run_positive_curvature.py'), 'Prelaunch/source link mismatch')
    maps = [(ROOT, prepared['input_sha256']), (OUT, prepared['prepared_file_sha256']),
            (OUT / 'source', summary['source_sha256']), (OUT, summary['output_sha256']),
            (OUT, controller['log_sha256'])]
    for base, mapping in maps:
        verify(base, mapping)
    need(summary['source_sha256'] == prepared['source_sha256'] and
         summary['input_sha256'] == prepared['input_sha256'], 'Snapshot inventory mismatch')
    need(sha(Path(summary['compiler'])) == summary['compiler_sha256'] and
         sha(ROOT / summary['build'] / 'observe') == summary['binary_sha256'], 'Compiler/binary changed')
    verify(Path('/'), summary['runtime_library_sha256'])
    need([c['stage'] for c in summary['commands']] == ['compile', 'runtime_libraries', 'observe'] and
         all(c['status'] == 'completed' and c['return_code'] == 0 for c in summary['commands']), 'Failed/incomplete stages')
    need((summary['path_spacing_km'], summary['field_spacing_km'], summary['maximum_updates'], summary['threads']) ==
         (.03125, .125, 1000, 1), 'Diagnostic settings changed')
    need(summary['baseline_retention_predicate'] == 'sy > 1e-14' and summary['diagnostic_retention_predicate'] == 'sy > 0' and
         not summary['safe_general_retention_rule_claimed'] and not summary['production_adoption'] and
         not summary['scientific_success'], 'Scope or predicate changed')
    source_changes = []
    for name in summary['source_sha256']:
        before, after = [(p / 'source' / name).read_text() for p in (BASE, OUT)]
        if before != after:
            source_changes.append(name)
            if name in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp'):
                marker = '      if (sy > 1e-14) {'
                need(before.count(marker) == 1 and after == before.replace(marker, '      if (sy > 0) {', 1),
                     'Unexpected numerical source difference: ' + name)
                diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                    fromfile='seed_loaded_B/' + name, tofile='positive_curvature/' + name))
                need(diff == (OUT / (Path(name).name + '.retention.diff')).read_text(), 'Saved retention diff changed')
            else:
                need(name == 'diagnostics/extracted_retention.hpp' and after == before.replace('sy > 1e-14', 'sy > 0'),
                     'Unexpected extra source difference: ' + name)
    need(set(source_changes) == {'src/core.hpp', 'diagnostics/observed_optimizer.hpp', 'diagnostics/extracted_retention.hpp'},
         'Wrong changed-source inventory')
    driver = (OUT / 'source/diagnostics/check_ray_stopping.cpp').read_text()
    need('extracted_retention.hpp' not in driver and 'first_arrival::Field field' not in driver and
         'read_saved_candidate(g,a,b,saved_run,audit_observation,argv[7],argv[8])' in driver,
         'Native driver changed its seed source or imports the fixture predicate')
    controls, control_review = [load(OUT / 'inputs' / n) for n in ('controls_summary.json', 'controls_review.json')]
    need(controls['status'] == control_review['status'] == 'passed' and
         control_review['summary_sha256'] == sha(OUT / 'inputs/controls_summary.json') and
         control_review['execution_sha256'] == sha(OUT / 'inputs/controls_execution.json') and
         all(controls['variants'][v]['checks_passed'] == 100 for v in ('seed_loaded_B', 'positive_curvature')),
         'Reviewed control links changed')
    baseline = load(BASE / 'summary.json')
    need(summary['baseline_results'] == baseline['results'] == rows(BASE / 'results.csv') and
         summary['seed_loaded_B_review_sha256'] == sha(BASE / 'review.json') and
         load(BASE / 'review.json')['status'] == 'passed', 'Baseline was not preserved')
    context = summary['native_context']
    need(len(context) == 199 and context == prepared['native_context'] == baseline['native_context'] ==
         load(CAPTURE / 'summary.json')['native_context'] and rows(OUT / 'identified_ray.csv') == [context],
         'Full native context differs')
    need(context['observation_index'] == '3426' and context['event'] == '65' and context['station'] == '46' and
         context['receiver_location_code'] == '', 'Pair/empty location changed')
    original = ROOT / 'data/development/loma_initial_failure_3426_001/inputs'
    for prefix, filename, index in [('native_source_', 'initial_events.csv', 65), ('native_receiver_', 'stations.csv', 46)]:
        native = rows(original / filename)[index]
        need(all(context[prefix + k] == v for k, v in native.items()), 'Original native table join differs')
    reference = load(OUT / 'inputs/reference_row.json')
    need(reference['reference_eligible'] == '1' and reference['reference_candidate_count'] == '1', 'Reference is not unique/eligible')
    ref_summary = load(OUT / 'inputs/reference_summary.json')
    need(ref_summary['input_source_sha256']['data/development/loma_initial_reference_001/inputs/initial_grid.csv'] ==
         sha(OUT / 'inputs/initial_grid.csv'), 'Pure reference uses another model')
    for name in ('curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        need((OUT / 'inputs' / name).read_bytes() == (CAPTURE / name).read_bytes(), 'Captured Candidate changed')
        side = load(OUT / 'inputs' / (name + '.identifiers.json'))
        need(side['file_sha256'] == sha(OUT / 'inputs' / name) and side['native_context'] == context and
             side['join_key'] == 'observation_index' and side['join_value'] == '3426', 'Seed sidecar changed')
    tables = {name: rows(OUT / name) for name in TABLES}
    results = tables['results.csv']
    need(results == summary['results'] and len(results) == 2 and
         {r['initialization'] for r in results} == {'straight', 'fmm'}, 'Result inventory differs')
    run_ids = {r['run_id'] for r in results}
    equality = {}
    for name, table in tables.items():
        need(all(r['observation_index'] == '3426' and r['run_id'] in run_ids for r in table), 'Unidentified table row')
        side = load(OUT / (name + '.identifiers.json'))
        need(side['file_sha256'] == sha(OUT / name) and side['native_context'] == context and
             side['join_key'] == 'observation_index' and side['join_value'] == '3426' and
             side['context_sha256'] == sha(OUT / 'identified_ray.csv'), 'Output sidecar mismatch')
        need(sha(BASE / name) == prepared['expected_old_table_sha256'][name], 'Saved B table changed')
        equality[name] = sha(OUT / name) == sha(BASE / name)
    need(equality == summary['baseline_table_equalities'], 'B/C table comparison differs')
    grid = rows(OUT / 'inputs/initial_grid.csv')
    bounds = {a: (min(num(r[a]) for r in grid), max(num(r[a]) for r in grid)) for a in 'xyz'}
    outcomes = []
    for result in results:
        run = result['run_id']
        need(result['logged_matches_unobserved_variant'] == '1' and result['max_updates'] == '1000' and
             num(result['path_spacing_km']) == .03125, 'Same-variant parity/settings differ')
        for key in ('time_s', 'projected_gradient', 'raw_gradient', 'source_dx', 'source_dy', 'source_dz'):
            num(result[key])
        path = [r for r in tables['paths.csv'] if r['run_id'] == run]
        need(len(path) == int(result['path_nodes']) and [int(r['node']) for r in path] == list(range(len(path))),
             'Path order/count differs')
        need(all(bounds[a][0] <= num(r[a]) <= bounds[a][1] for r in path for a in 'xyz'), 'Path outside box')
        for endpoint, prefix in [(path[0], 'source'), (path[-1], 'receiver')]:
            need(all(num(endpoint[a]) == num(reference['reference_' + prefix + '_' + a]) ==
                     num(context[prefix + '_' + a + '_km']) for a in 'xyz'), 'Exact endpoint differs')
            need(all(math.isnan(float(endpoint['gradient_' + a])) for a in 'xyz'), 'Endpoint NaN placeholders changed')
        gradient, projected = [], []
        for row in path[1:-1]:
            for a in 'xyz':
                value = num(row['gradient_' + a]); gradient.append(value); direction = -value
                if ((num(row[a]) <= bounds[a][0] + 1e-10 and direction < 0) or
                        (num(row[a]) >= bounds[a][1] - 1e-10 and direction > 0)):
                    direction = 0.0
                projected.append(direction)
        need(norm(gradient) == num(result['raw_gradient']) and norm(projected) == num(result['projected_gradient']),
             'Final saved gradient norms differ')
        lengths = [norm(num(b[a]) - num(a0[a]) for a in 'xyz') for a0, b in zip(path, path[1:])]
        need(min(lengths) > 0, 'Zero-length final edge')
        history = [r for r in tables['history.csv'] if r['run_id'] == run]
        accepted = [r for r in history if r['phase'] == 'accepted']
        need(history[0]['phase'] == 'initial' and history[-1]['phase'] == 'final' and
             len(history) == len(accepted) + 2 and len(accepted) == int(result['updates']) and
             [int(r['iteration']) for r in accepted] == list(range(len(accepted))) and
             [int(r['updates']) for r in accepted] == list(range(1, len(accepted) + 1)), 'History sequence differs')
        previous = num(history[0]['time_s']); memory = []; retained = []; early_stop = []
        for i, row in enumerate(accepted):
            current, step, slope = [num(row[k]) for k in ('time_s', 'accepted_step', 'directional_slope')]
            searches = int(row['line_search_evaluations'])
            need(step > 0 and slope < 0 and 1 <= searches <= 24 and
                 step == num(row['feasible_initial_step']) * 2.0 ** (1 - searches), 'Invalid search record')
            need(current <= previous + 1e-4 * step * slope and num(row['action_change_s']) == previous - current,
                 'Recorded binary64 Armijo/change differs')
            previous = current
            if int(row['gradient_fallback']) or int(row['merged_nodes']): memory = []
            if row['curvature_pair_accepted'] == '1':
                memory.append(i); memory = memory[-8:]; retained.append(i)
            need(int(row['memory_pairs']) == len(memory), 'Memory evolution differs')
            for k, value in row.items():
                if k not in ('run_id', 'observation_index', 'phase'): num(value)
            if num(row['action_change_s']) < 1e-11 and num(row['projected_gradient']) < 1e-5:
                early_stop.append(i)
            if i + 1 < len(accepted):
                need(num(row['projected_gradient']) >= 1e-7, 'Strict criterion passed before continued update')
        final = history[-1]
        for key in ('time_s', 'projected_gradient', 'raw_gradient', 'path_nodes', 'updates'):
            need(num(final[key]) == num(result[key]), 'Result/final history differs: ' + key)
        need(early_stop == [len(accepted) - 1] and int(final['iteration']) == len(accepted) - 1 and
             result['converged'] == '1' and num(final['projected_gradient']) >= 1e-7,
             'Actual combined/strict stopping interpretation differs')
        need(num(final['min_segment_km']) == min(lengths) and num(final['max_segment_km']) == max(lengths),
             'Final edge-length inventory differs')
        fd = [r for r in tables['path_gradient_checks.csv'] if r['run_id'] == run]
        need([num(r['step_km']) for r in fd] == [1e-4, 1e-5, 1e-6], 'Saved finite-difference inventory differs')
        for row in fd:
            node, axis = int(row['node']), 'xyz'[int(row['axis'])]
            need(num(row['analytic_gradient']) == num(path[node]['gradient_' + axis]) and
                 num(row['error']) == num(row['numerical_gradient']) - num(row['analytic_gradient']),
                 'Saved FD frame/arithmetic differs')
        time_error = num(result['time_s']) - num(reference['reference_time_s'])
        components = [num(result['source_d' + a]) - num(reference['reference_source_d' + a + '_s_per_km']) for a in 'xyz']
        source_error = norm(components)
        comparison = [r for r in summary['continuous_reference_comparison'] if r['run_id'] == run]
        need(len(comparison) == 1, 'Reference join ambiguous'); comparison = comparison[0]
        need(comparison['time_error_s'] == time_error and comparison['source_error_euclidean_norm_s_per_km'] == source_error and
             comparison['time_limit_pass'] == (abs(time_error) <= 2.5e-5) and
             comparison['source_limit_pass'] == (source_error <= 3e-6) and comparison['native_context'] == context and
             comparison['diagnostic_local_convergence_flag'] == result['converged'] and comparison['final_history'] == final and
             comparison['accepted_curvature_pairs'] == len(retained), 'Reference/flag/history summary differs')
        old = [r for r in rows(BASE / 'history.csv') if r['run_id'] == run]
        old_result = [r for r in baseline['results'] if r['run_id'] == run][0]
        old_retained = [int(r['iteration']) for r in old if r['phase'] == 'accepted' and r['curvature_pair_accepted'] == '1']
        outcomes.append(dict(run_id=run, diagnostic_result=result, baseline_B_result=old_result,
            termination='combined_action_change_and_projected_gradient', strict_1e_minus7_satisfied=False,
            last_accepted_history=accepted[-1], final_history=final, accepted_updates=len(accepted),
            accepted_curvature_pairs=len(retained), retained_pair_iterations=retained,
            final_memory_creation_iterations=memory, final_memory_ages_at_last_iteration=[len(accepted)-1-k for k in memory],
            no_saved_computed_sy_or_s_y_arrays=True, gradient_fallbacks=sum(int(r['gradient_fallback']) for r in history),
            merged_nodes=sum(int(r['merged_nodes']) for r in accepted), action_counts=action_counts(history),
            B_action_counts=action_counts(old), baseline_retained_pairs=len(old_retained),
            baseline_last_retained_iteration=old_retained[-1], minimum_step=min(num(r['accepted_step']) for r in accepted),
            maximum_line_search_evaluations=max(int(r['line_search_evaluations']) for r in accepted),
            scalar_histories_identical=(history == old), first_any_scalar_difference=first_difference(old, history),
            first_non_action_scalar_difference=first_difference(old, history, ('time_s', 'action_change_s')),
            first_non_action_nonretention_scalar_difference=first_difference(old, history,
                ('time_s', 'action_change_s', 'curvature_pair_accepted', 'memory_pairs')),
            time_error_s=time_error, source_error_xyz_s_per_km=components,
            source_error_euclidean_norm_s_per_km=source_error, time_limit_pass=abs(time_error) <= 2.5e-5,
            source_limit_pass=source_error <= 3e-6, final_path_nodes=len(path), all_final_edges_positive=True,
            final_path_and_gradient_serialized_fields_equal_B=path == [r for r in rows(BASE/'paths.csv') if r['run_id'] == run]))
    need(summary['selected_run_id'] == min(results, key=lambda r: num(r['time_s']))['run_id'] and
         summary['observed_paths_and_arrays_match_unobserved_variant'], 'Selection/parity summary differs')
    for base, mapping in maps: verify(base, mapping)
    return dict(status='passed', material_issue_found=False, reviewer='scientific_audit/ray_math_review',
        scope='Independent saved-source/table/native/hash and recorded stopping/retention review; no ray or action evaluation.',
        summary_sha256=sha(OUT/'summary.json'), execution_sha256=sha(OUT/'execution.json'),
        controller_completion_sha256=sha(OUT/'controller_completion.json'), prepared_sha256=sha(OUT/'prepared.json'),
        prelaunch_review_sha256=sha(OUT/'prelaunch_review.json'), launcher_sha256=sha(OUT/'launcher.py'),
        checker_sha256=sha(Path(__file__)), verified_input_pins=len(prepared['input_sha256']),
        verified_prepared_pins=len(prepared['prepared_file_sha256']), verified_source_pins=len(summary['source_sha256']),
        verified_output_pins=len(summary['output_sha256']), controller_child_reaped=True, controller_driver_return_code=0,
        source_changes=source_changes, exact_two_numerical_retention_literal_changes=True,
        baseline_B_retained=True, baseline_B_table_sha256={n:sha(BASE/n) for n in TABLES},
        diagnostic_C_table_sha256={n:sha(OUT/n) for n in TABLES}, baseline_table_equalities=equality,
        output_row_counts={n:len(v) for n,v in tables.items()}, full_native_context=context,
        pure_travel_time_excludes_source_t_s=num(context['native_source_t']),
        same_variant_observer_numeric_parity_recorded=True, results=outcomes,
        selected_run_id=summary['selected_run_id'], time_limit_s=2.5e-5, source_vector_limit_s_per_km=3e-6,
        limitations=[
            'C changes only the two retention literals; this review does not require C to reproduce B.',
            'Observed/unobserved path, source, dv and length equality is the recorded exact numeric C++ check; signed-zero bit patterns are not distinguished and model arrays are not separately exported.',
            'Retained-pair flags and memory are reconstructed; computed sy and full s/y arrays were not captured for C.',
            'Saved scalar prefixes cannot establish equality of unsaved intermediate paths or directions.',
            'Armijo/action changes use saved approximate binary64 totals, not certified exact Fermat action differences.',
            'Both runs stop under the unchanged combined criterion, not the strict projected-gradient criterion.',
            'Positive-only retention remains unsafe generally: reviewed invented cases preserve subnormal reciprocal overflow and positive-infinity admission.',
            'One successful local flag is not a global first-arrival certificate, a general convergence remedy, or production/inversion approval.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    args = parser.parse_args()
    result = check()
    if args.write_review:
        with (OUT/'review.json').open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(result, indent=2, allow_nan=False))
