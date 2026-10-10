#!/usr/bin/env python3
"""Saved-record audit only: no ray trace or action evaluation."""
import csv
import difflib
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/development/loma_failed_search_3426_001'
RUN = 'fmm_0.031250_1000'
OLD = ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')
NEW = ('failed_search_directions.csv', 'failed_search_trials.csv', 'failed_search_decisions.csv')


def need(ok, message):
    if not ok:
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


def same(a, b):
    return struct.pack('>d', float(a)) == struct.pack('>d', float(b))


def finite(value):
    return math.isfinite(float(value))


def main():
    summary = load(OUT / 'summary.json')
    execution = load(OUT / 'execution.json')
    prepared = load(OUT / 'prepared.json')
    root_review = load(OUT / 'root_prelaunch_review.json')
    launch = load(OUT / 'launch.json')
    need(summary['status'] == 'completed_with_original_flags_preserved' and
         execution['status'] == 'completed' and execution['return_code'] == 0,
         'Replay is not successfully terminal')
    need(execution['summary_sha256'] == sha(OUT / 'summary.json'), 'Detached terminal ledger')
    prepared_hash = sha(OUT / 'prepared.json')
    need(summary['prepared_sha256'] == execution['prepared_sha256'] ==
         launch['prepared_sha256'] == root_review['prepared_sha256'] == prepared_hash,
         'Preparation/review/launch linkage differs')
    need(root_review['status'] == 'passed' and
         launch['root_review_sha256'] == sha(OUT / 'root_prelaunch_review.json'), 'Root review differs')
    need(len(summary['commands']) == 2 and all(r['status'] == 'completed' and r['return_code'] == 0
         for r in summary['commands']), 'Incomplete compile/replay commands')
    need(summary['threads'] == launch['threads'] == 1, 'Unexpected thread count')
    checks = [(ROOT, prepared['input_sha256']), (OUT, prepared['prepared_file_sha256']),
              (OUT / 'source', prepared['source_sha256']), (OUT, summary['output_sha256']),
              (ROOT, root_review['source_sha256'])]
    anchors = {name: sha(OUT / name) for name in
               ('summary.json', 'execution.json', 'prepared.json', 'root_prelaunch_review.json', 'launch.json')}

    def verify_hashes():
        for base, mapping in checks:
            for name, digest in mapping.items():
                need(sha(base / name) == digest, 'Pinned file differs: ' + name)
        for name, digest in anchors.items():
            need(sha(OUT / name) == digest, 'Anchor changed during readback: ' + name)

    verify_hashes()
    need(summary['source_sha256'] == prepared['source_sha256'] and
         summary['input_sha256'] == prepared['input_sha256'], 'Prepared source/input pins changed')
    need(sha(Path(summary['compiler'])) == summary['compiler_sha256'], 'Compiler changed')
    need(sha(ROOT / summary['commands'][1]['command'][0]) == summary['binary_sha256'], 'Replay binary changed')
    manifest = load(OUT / 'inputs/preflight_run_manifest.json')
    need(sha(ROOT / manifest['binary']) == manifest['binary_sha256'] == summary['frozen_binary_sha256'],
         'Original preflight binary changed')
    original = ROOT / prepared['original_observer']
    prior = load(original / 'summary.json')
    need(load(OUT / 'inputs/original_observer_summary.json') == prior, 'Original summary copy changed')
    need(sha(original / 'identified_ray.csv') == sha(OUT / 'identified_ray.csv'), 'Identified context changed')
    for name in OLD:
        need(sha(OUT / name) == sha(original / name) == prepared['expected_old_table_sha256'][name] ==
             prior['output_sha256'][name], 'Original numerical CSV changed: ' + name)
    context_rows = rows(OUT / 'identified_ray.csv')
    need(len(context_rows) == 1 and context_rows[0] == summary['native_context'] == prior['native_context'],
         'Full native context differs')
    context = context_rows[0]
    events, stations = rows(OUT / 'inputs/initial_events.csv'), rows(OUT / 'inputs/stations.csv')
    i, k = divmod(3426, len(stations))
    need((context['event'], context['station'], context['observation_index']) == (str(i), str(k), '3426'),
         'Pair index differs')
    native_fields = 0
    for prefix, item in (('source_', events[i]), ('receiver_', stations[k])):
        for name, value in item.items():
            need(context['native_' + prefix + name] == value, 'Native metadata field differs: ' + prefix + name)
            native_fields += 1
        for axis in 'xyz':
            need(same(context[prefix + axis + '_km'], item[axis]), 'Current endpoint geometry differs')
    need(context['source_event_resource_id'] == context['native_source_event_resource_id'] and
         context['source_origin_resource_id'] == context['native_source_origin_resource_id'] and
         all(context['receiver_' + name] == context['native_receiver_' + name] for name in
             ('network_code', 'station_code', 'location_code', 'channel_code', 'channel_seed_id',
              'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end')),
         'Provider identity or native epoch differs')
    need(context['receiver_location_code'] == '' and same(context['source_t'], events[i]['t']),
         'Empty location or separate origin correction changed')
    tables = {name: rows(OUT / name) for name in OLD + NEW}
    for name, records in tables.items():
        sidecar = load(OUT / (name + '.identifiers.json'))
        need(sidecar['file'] == name and sidecar['file_sha256'] == sha(OUT / name) and
             sidecar['context_sha256'] == sha(OUT / 'identified_ray.csv') and
             sidecar['native_context'] == context and sidecar['join_key'] == 'observation_index' and
             sidecar['join_value'] == '3426' and sidecar['context_csv'] == 'identified_ray.csv',
             'Detached native sidecar: ' + name)
        need(all(row['observation_index'] == '3426' for row in records), 'Wrong table pair index')
    results = tables['results.csv']
    need(results == summary['results'] and len(results) == 2 and
         all(r['logged_matches_unobserved_variant'] == '1' for r in results), 'Observer/control parity failed')
    selected = [r for r in results if r['run_id'] == RUN]
    need(len(selected) == 1 and selected[0]['converged'] == context['ray_converged'] == '0',
         'Original local failure flag changed')
    for key, native_key in [('time_s', 'ray_time'), ('projected_gradient', 'ray_projected_gradient'),
                            ('raw_gradient', 'ray_raw_gradient'), ('source_dx', 'source_dx'),
                            ('source_dy', 'source_dy'), ('source_dz', 'source_dz')]:
        need(float(format(float(selected[0][key]), '.12g')) == float(context[native_key]), 'Saved 12-digit parity')
    base = tables[NEW[0]]
    trials = tables[NEW[1]]
    decisions = tables[NEW[2]]
    need(len(base) == 1134 and len(decisions) == 24 and len(trials) == 1134 * 24, 'Incomplete capture inventory')
    need(all(r['run_id'] == RUN and r['iteration'] == '53' for name in NEW for r in tables[name]),
         'Wrong captured run or iteration')
    path = [r for r in tables['paths.csv'] if r['run_id'] == RUN]
    history = [r for r in tables['history.csv'] if r['run_id'] == RUN and r['phase'] == 'line_search_failed']
    need(len(history) == 1 and history[0]['iteration'] == '53' and history[0]['line_search_evaluations'] == '24',
         'Original failed-history row differs')
    need(len(path) == len(base), 'Base/final path counts differ')
    grid = rows(OUT / 'inputs/initial_grid.csv')
    bounds = {axis: (min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)) for axis in 'xyz'}
    slope = 0.0
    for n, (row, saved) in enumerate(zip(base, path)):
        endpoint = n in (0, len(base)-1)
        need(int(row['node']) == int(saved['node']) == n and row['is_endpoint'] == str(int(endpoint)), 'Base node order')
        for axis in 'xyz':
            need(same(row[axis], saved[axis]) and finite(row[axis]) and finite(row['q' + axis]), 'Base/direction frame differs')
            if endpoint:
                need(float(row['q' + axis]) == 0 and row['gradient_' + axis] == '', 'Fixed endpoint convention')
                prefix = 'source_' if n == 0 else 'receiver_'
                need(same(row[axis], context[prefix + axis + '_km']), 'Exact endpoint differs')
            else:
                need(finite(row['gradient_' + axis]) and same(row['gradient_' + axis], saved['gradient_' + axis]),
                     'Captured gradient differs from saved final path')
                slope += float(row['gradient_' + axis]) * float(row['q' + axis])
    need(same(slope, history[0]['directional_slope']) and slope < 0, 'Saved full-direction dot product differs')
    identical_paths = 0
    rhs_equal_cached = 0
    trial_changes = []
    for index, record in enumerate(decisions):
        step = 2. ** -index
        need(int(record['trial_index']) == index and same(record['step'], step) and
             same(record['post_loop_halved_step'], 2. ** -24), 'Attempted/post-loop step differs')
        need(record['valid'] == '1' and record['merged_nodes'] == '0' and record['path_nodes'] == '1134' and
             record['binary64_accepted'] == '0', 'Original decision/topology differs')
        cached = float(record['cached_base_action_s'])
        reeval = float(record['reevaluated_base_action_s'])
        action = float(record['trial_action_s'])
        rhs = float(record['armijo_rhs_s'])
        need(all(math.isfinite(v) for v in (cached, reeval, action, rhs)) and
             same(cached, history[0]['time_s']) and same(cached, selected[0]['time_s']) and
             same(reeval, decisions[0]['reevaluated_base_action_s']) and
             same(record['directional_slope'], slope), 'Saved decision scalars differ')
        need(same(rhs, cached + (1e-4 * step) * slope) and action > rhs,
             'Binary64 Armijo expression/recorded rejection differs')
        need(same(record['post_loop_halved_step'], history[0]['accepted_step']) and
             same(decisions[0]['step'], history[0]['feasible_initial_step']), 'Original history step linkage differs')
        block = trials[index * len(base):(index + 1) * len(base)]
        unchanged = True
        changed_coordinates = 0
        for n, (trial, row) in enumerate(zip(block, base)):
            need(int(trial['trial_index']) == index and int(trial['node']) == n and same(trial['step'], step),
                 'Trial ordering or step differs')
            for axis in 'xyz':
                coordinate = float(row[axis])
                value = float(trial[axis])
                expected = coordinate if n in (0, len(base)-1) else coordinate + step * float(row['q' + axis])
                need(finite(value) and same(value, expected), 'Actual rounded trial is not base + step * direction')
                need(bounds[axis][0] <= value <= bounds[axis][1], 'Recorded valid trial is outside domain')
                unchanged = unchanged and value == coordinate
                changed_coordinates += int(value != coordinate)
        need(record['path_identical_to_base'] == str(int(unchanged)), 'Identical-path label differs')
        identical_paths += int(unchanged)
        rhs_equal_cached += int(same(rhs, cached))
        trial_changes.append(dict(index=index, step=step, changed_coordinates=changed_coordinates,
                                  saved_trial_minus_cached_action_s=action-cached,
                                  saved_armijo_rhs_minus_cached_action_s=rhs-cached))
    for file, artifact in [('observed_optimizer.hpp', 'capture_insertion.diff'), ('check_ray_stopping.cpp', 'capture_driver.diff')]:
        before = (original / 'source/diagnostics' / file).read_text()
        after = (OUT / 'source/diagnostics' / file).read_text()
        expected = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                              fromfile='original_observation', tofile='capture_observation'))
        need(expected == (OUT / artifact).read_text(), 'Saved capture insertion diff differs')
    verify_hashes()
    review = dict(status='passed_saved_evidence_review', material_issue_found=False,
        scope='Independent saved-table, binary64 construction and source/hash readback; no ray rerun or action certification.',
        summary_sha256=anchors['summary.json'], execution_sha256=anchors['execution.json'],
        prepared_sha256=prepared_hash, root_prelaunch_review_sha256=anchors['root_prelaunch_review.json'],
        launch_sha256=anchors['launch.json'], checker_path=str(Path(__file__).resolve().relative_to(ROOT)),
        checker_sha256=sha(Path(__file__)), input_hashes_verified=len(prepared['input_sha256']),
        prepared_hashes_verified=len(prepared['prepared_file_sha256']),
        frozen_source_hashes_verified=len(prepared['source_sha256']), output_hashes_verified=len(summary['output_sha256']),
        native_identifiers={key: context[key] for key in ('event', 'station', 'source_event_resource_id',
            'source_origin_resource_id', 'receiver_channel_seed_id', 'receiver_channel_fdsn_source_id',
            'receiver_metadata_epoch_start', 'receiver_metadata_epoch_end')},
        native_fields_matched=native_fields, native_metadata_and_empty_location_preserved=True,
        source_t_separate_from_pure_ray_time=True, old_five_numerical_CSVs_byte_identical=True,
        observed_unobserved_array_parity_records=2, captured_nodes=len(base), captured_trials=len(decisions),
        captured_trial_vertices=len(trials), all_binary64_trial_coordinates_reconstructed=True,
        all_binary64_Armijo_rhs_reconstructed=True, all_recorded_rejections_consistent=True,
        gradient_direction_dot_product_reconstructed=True, original_local_converged=False,
        cached_action_s=float(decisions[0]['cached_base_action_s']),
        recorded_reevaluated_action_s=float(decisions[0]['reevaluated_base_action_s']),
        recorded_reevaluated_minus_cached_s=float(decisions[0]['reevaluated_base_action_s'])-float(decisions[0]['cached_base_action_s']),
        saved_directional_slope=slope, identical_trial_paths=identical_paths,
        Armijo_rhs_equal_cached_action_count=rhs_equal_cached, saved_trial_arithmetic=trial_changes,
        limitations=['Recorded base reevaluation is checked for linkage and consistency, not independently recomputed.',
            'Trial action scalars are recorded binary64 evaluations; this review certifies no exact action or failure cause.',
            'Control arrays are not separately saved: their equality is established by reviewed in-process code and its two true records.',
            'Native catalog identities describe simulation geometry provenance; no synthetic provider pick is invented.',
            'Original local-convergence flags and independent continuous-reference accuracy are unchanged.'])
    with (OUT / 'review.json').open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(status=review['status'], review_sha256=sha(OUT / 'review.json'),
                          captured_trials=len(decisions), captured_trial_vertices=len(trials)), indent=2))


if __name__ == '__main__':
    main()
