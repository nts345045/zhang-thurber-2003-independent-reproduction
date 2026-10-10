#!/usr/bin/env python3
"""Independently read saved strict-call outputs; never retrace either ray."""
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def read(name):
    with (HERE / name).open() as stream:
        return list(csv.DictReader(stream))

def norm(values):
    return math.sqrt(sum(v*v for v in values))

def main():
    prepared = json.loads((HERE / 'prepared.json').read_text())
    summary = json.loads((HERE / 'summary.json').read_text())
    execution = json.loads((HERE / 'execution.json').read_text())
    prelaunch = json.loads((HERE / 'prelaunch_review.json').read_text())
    controller = json.loads((HERE / 'controller_completion.json').read_text())
    pins = {}
    assert controller['status'] == 'completed' and controller['driver_return_code'] == 0
    assert controller['native_calls'] == 2 and controller['field_constructions'] == 0
    assert controller['driver_pid'] is None
    assert controller['driver_combined_output'].strip() == sha(HERE / 'summary.json')
    for name, expected in controller['input_output_sha256'].items():
        assert sha(HERE / name) == expected, name
        pins[str(HERE / name)] = expected
    for key, root in [('original_sha256', ROOT), ('runtime_sha256', Path('/')), ('output_sha256', HERE), ('source_sha256', HERE)]:
        for name, expected in prepared[key].items():
            assert sha(root / name) == expected, (key, name)
            pins[str(root / name)] = expected
    for name, expected in summary['output_sha256'].items():
        assert sha(HERE / name) == expected, name
        pins[str(HERE / name)] = expected
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    assert execution['summary_sha256'] == sha(HERE / 'summary.json')
    assert summary['prepared_sha256'] == execution['prepared_sha256'] == prelaunch['prepared_sha256'] == sha(HERE / 'prepared.json')
    assert summary['prelaunch_review_sha256'] == execution['prelaunch_review_sha256'] == sha(HERE / 'prelaunch_review.json')
    assert summary['strict_1000_review_sha256'] == sha(HERE / 'inputs/strict_1000_review.json')
    assert json.loads((HERE / 'inputs/strict_1000_review.json').read_text())['status'] == 'passed'
    assert summary['maximum_updates'] == 4000 and prepared['settings']['maximum_updates'] == 4000
    assert prelaunch['status'] == 'passed' and execution['native_calls_completed'] == execution['native_calls_planned'] == 2
    assert [r['stage'] for r in execution['commands']] == ['compile_strict', 'trace_strict']
    for command in execution['commands']:
        assert command['return_code'] == 0
        assert not Path('/proc/{}/stat'.format(command['pid'])).exists()
        assert controller['recorded_child_return_codes'][command['stage']] == 0
        assert controller['terminal_non_zombie_process_group_members'][str(command['pid'])] == []
        for kind in ('stdout', 'stderr'):
            assert sha(HERE / 'logs' / (command['stage'] + '.' + kind + '.log')) == command[kind + '_sha256']
    assert summary['binary_sha256']['strict'] == sha(HERE / 'build/trace_strict')
    context = json.loads((HERE / 'inputs/native_context.json').read_text())
    grid = read('inputs/initial_grid.csv')
    bounds = {axis: (min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)) for axis in 'xyz'}
    depths = sorted(set(float(r['z']) for r in grid))[1:-1]
    scalars = read('results/strict/scalars_17.csv')
    narrow = read('results/strict/scalars_12.csv')
    baseline = read('inputs/baseline_D/scalars_17.csv')
    strict1000 = read('inputs/strict_1000/scalars_17.csv')
    reference = read('inputs/selected_reference.csv')
    paths = read('results/strict/paths.csv')
    kernels = read('results/strict/model_partials.csv')
    baseline_paths = read('inputs/baseline_D/paths.csv')
    assert len(scalars) == len(narrow) == len(baseline) == len(reference) == 2
    checked = 0
    comparisons = []
    for number, pair in enumerate((8670, 8674)):
        i, k = divmod(pair, 52)
        native, scalar, old, ref = context[number], scalars[number], baseline[number], reference[number]
        result = summary['variants']['strict'][number]
        assert result['pair_index'] == pair and result['native_context'] == native
        assert result['scalars_17'] == scalar and result['baseline_D_scalars_17'] == old
        selected_paths = [r for r in paths if int(r['pair_index']) == pair]
        selected_kernels = [r for r in kernels if int(r['pair_index']) == pair]
        for collection, index in [(selected_paths, 'node'), (selected_kernels, 'model_index')]:
            assert [int(r[index]) for r in collection] == list(range(len(collection)))
        assert len(selected_paths) == int(scalar['ray_path_points'])
        assert len(selected_kernels) == len(grid)
        for record in selected_paths + selected_kernels + [scalar, narrow[number], old, ref]:
            assert (int(record['event']), int(record['station'])) == (i, k)
            for prefix, fields in [('source_', native['source_native']), ('receiver_', native['receiver_native'])]:
                for key, value in fields.items():
                    if key not in ('id', 'x', 'y', 'z', 't'):
                        assert record[prefix + key] == value, (pair, prefix + key)
                        checked += 1
        xyz = [[float(r[a]) for a in 'xyz'] for r in selected_paths]
        assert xyz[0] == [float(native['source_native'][a]) for a in 'xyz']
        assert xyz[-1] == [float(native['receiver_native'][a]) for a in 'xyz']
        assert all(math.isfinite(v) and bounds[a][0] <= v <= bounds[a][1] for p in xyz for a, v in zip('xyz', p))
        assert all(a != b for a, b in zip(xyz[:-1], xyz[1:]))
        assert all(math.isfinite(float(r[c])) for r in selected_kernels for c in ('dT_dv', 'length'))
        assert all(scalar[c] == '1' for c in ('ray_finite', 'ray_path_in_domain', 'ray_exact_source_endpoint', 'ray_exact_receiver_endpoint'))
        assert all(scalar[c] == '0' for c in ('ray_initialization_attempted', 'ray_initialization_succeeded', 'ray_selected_fmm_seed'))
        source_error = [float(scalar['source_d'+a]) - float(ref['source_d'+a+'_s_per_km']) for a in 'xyz']
        old_error = [float(old['source_d'+a]) - float(ref['source_d'+a+'_s_per_km']) for a in 'xyz']
        time_error = float(scalar['ray_time']) - float(ref['time_s'])
        assert source_error == result['source_error_xyz_s_per_km']
        assert norm(source_error) == result['source_error_euclidean_norm_s_per_km']
        assert time_error == result['time_error_s']
        assert (norm(source_error) <= 3e-6) == result['source_limit_pass']
        assert (abs(time_error) <= 2.5e-5) == result['time_limit_pass']
        assert float(scalar['ray_time']) - float(old['ray_time']) == result['strict_minus_baseline_D_time_s']
        assert [float(scalar['source_d'+a])-float(old['source_d'+a]) for a in 'xyz'] == result['strict_minus_baseline_D_source_xyz_s_per_km']
        assert scalar['ray_iterations'] == '4000' and scalar['ray_converged'] == '0'
        assert float(scalar['ray_projected_gradient']) >= 1e-7
        assert result['derived_loop_termination'] == 'update_budget_exhausted' and not result['strict_gradient_test_pass']
        assert scalar['ray_merged_nodes'] == old['ray_merged_nodes'] == '0'
        assert scalar['ray_path_points'] == old['ray_path_points'] and result['representation_dimension_unchanged']
        earlier = strict1000[number]
        assert result['strict_1000_scalars_17'] == earlier
        assert float(scalar['ray_time']) - float(earlier['ray_time']) == result['strict_minus_strict_1000_time_s']
        assert [float(scalar['source_d'+a])-float(earlier['source_d'+a]) for a in 'xyz'] == result['strict_minus_strict_1000_source_xyz_s_per_km']
        assert scalar['ray_path_points'] == earlier['ray_path_points'] and earlier['ray_merged_nodes'] == '0'
        assert result['representation_dimension_unchanged_vs_strict_1000']
        nearest = min((abs(p[2]-z), n, p[2], z) for n, p in enumerate(xyz[1:-1], 1) for z in depths)
        old_path = [r for r in baseline_paths if int(r['pair_index']) == pair]
        max_shift = max(norm([float(a[c])-float(b[c]) for c in 'xyz']) for a,b in zip(selected_paths,old_path))
        comparisons.append({'pair_index': pair, 'native_context': native,
            'baseline_source_error_s_per_km': norm(old_error), 'strict_source_error_s_per_km': norm(source_error),
            'source_error_xyz_s_per_km': source_error, 'time_error_s': time_error,
            'strict_minus_baseline_time_s': result['strict_minus_baseline_D_time_s'],
            'strict_gradient_s_per_km': float(scalar['ray_projected_gradient']),
            'strict1000_source_error_s_per_km': norm([float(earlier['source_d'+a])-float(ref['source_d'+a+'_s_per_km']) for a in 'xyz']),
            'strict_minus_strict1000_time_s': result['strict_minus_strict_1000_time_s'],
            'updates': 4000, 'local_flag': False, 'merges': 0,
            'maximum_saved_node_displacement_km': max_shift,
            'nearest_internal_depth_plane': {'distance_km':nearest[0], 'node':nearest[1], 'node_z_km':nearest[2], 'plane_z_km':nearest[3]}})
    assert len(paths) == sum(int(r['ray_path_points']) for r in scalars) and len(kernels) == 2*len(grid)
    for name, expected in pins.items():
        assert sha(Path(name)) == expected, name
    review = {'status': 'passed', 'reviewer': 'scientific_audit',
        'reviewed_utc': datetime.datetime.utcnow().isoformat() + 'Z',
        'scope': 'Independent saved output/source/hash/native readback only; no compiler, ray, reference, action or network evaluation.',
        'summary_sha256': sha(HERE/'summary.json'), 'execution_sha256': sha(HERE/'execution.json'),
        'controller_completion_sha256': sha(HERE/'controller_completion.json'),
        'prelaunch_review_sha256': sha(HERE/'prelaunch_review.json'), 'checker_sha256': sha(Path(__file__)),
        'rechecked_unique_pin_count': len(pins), 'native_metadata_cells_checked': checked,
        'pairs': comparisons,
        'interpretation': ['Both strict calls exhausted the declared 4000-update cap and returned false local flags; neither is a stationary acceptance.',
            'The formerly failing pair crosses the unchanged source-error limit after more iterations, demonstrating stopping sensitivity for that case.',
            'The passing control has a larger source error despite lower travel time; derivative accuracy is not monotonic in action.',
            'The source-error limits now pass for both calls, but the failed strict flags remain failed.',
            'The two4000 calls reused savedD and strict1000 comparisons; no baseline or receiver-field rerun occurred.'],
        'next_discriminator_recommendation': 'No further native escalation is authorized. The mixed source trend and two failed strict flags leave the stationary fixed-representation error unresolved; preserve both and prioritize the saved guarded-Hayward failure census before any new experiment.',
        'limitations': ['Finite-case diagnostic only; no full-cohort or production-stop change.',
            'No accepted-step history is recorded; loop termination is inferred from unchanged control flow.',
            'These budget-exhausted calls do not isolate the stationary fixed-representation error; even a true local flag would not certify a global first arrival.']}
    with (HERE/'review.json').open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status':'passed', 'review_sha256':sha(HERE/'review.json'), 'pins':len(pins), 'native_cells':checked}))

if __name__ == '__main__':
    main()
