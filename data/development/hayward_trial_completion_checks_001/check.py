#!/usr/bin/env python3
"""Prepare or run saved-table completion controls; never compile, trace or invert."""
import argparse
import ast
import csv
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = ROOT / 'data/development/hayward_trial_completion_candidate_001'
CONTROLS = ROOT / 'data/development/hayward_trial_backtracking_controls_002'
FIXTURES = ('valid_dd', 'valid_loc1d', 'half', 'quarter', 'worse', 'all', 'state', 'mixed_invalid')
MODE = {name: ('dd' if name in ('valid_dd', 'state', 'mixed_invalid') else 'loc1d') for name in FIXTURES}
R = 'loc1d_rejected_trial_it_0_ls_0_'
S = 'loc1d_iteration_0_solve_'
L = 'loc1d_iteration_0_trials.csv'
H = 'loc1d_history.csv'
MAIN = 'a10dcdc300d9a4e43f6ae0cba2e354d7cec549438319cf411b577790b2373058'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def table(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames)
        records = list(reader)
    assert fields and len(fields) == len(set(fields))
    assert all(None not in r and None not in r.values() for r in records)
    return fields, records


def write_table(path, fields, records):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)


def cells(path, changes):
    fields, records = table(path)
    for index, key, value in changes:
        assert key in fields
        records[index][key] = value
    write_table(path, fields, records)


def cell(name, row, key, value):
    return dict(op='cell', file=name, row=row, key=key, value=value)


def roster():
    tests = []

    def add(name, base='half', accept=False, steps=(), config=None, message=None, kind='trial'):
        tests.append(dict(name=name, base=base, expected_accept=accept, steps=list(steps),
                          config=config or {}, required_error_fragment=message, kind=kind))

    for base in ('valid_dd', 'valid_loc1d', 'half', 'quarter', 'worse'):
        add('intact_' + base, base, True)
    for base in ('all', 'state', 'mixed_invalid'):
        add('terminal_failure_' + base, base, message='Missing history/matrix iterations')
    add('schema_joint_clamp_exp', 'state', True, [dict(op='joint_schema')])
    add('schema_stage_skip_and_stage2_break', 'valid_dd', True,
        [dict(op='stages', iterations=[0, 2, 4])], dict(iterations=9, stage_length=2))
    add('schema_stage_skip_reaches_cap', 'valid_dd', True,
        [dict(op='stages', iterations=[0, 2])], dict(iterations=4, stage_length=2))
    add('schema_invalid_models_without_quality', 'valid_dd', True,
        [dict(op='stages', iterations=[0], status='invalid_trial_model')], dict(iterations=1, stage_length=1))
    add('nonincrease_equality_is_allowed', steps=[cell(L, 1, 'objective_after', '0.025446381722154902'),
        cell(H, 0, 'objective_after', '0.0254463817222')], accept=True)
    add('legacy_absent_station_j', accept=True, steps=[dict(op='absent_station_j')])
    add('initializer_attempted_and_succeeded', accept=True,
        steps=[dict(op='initializer_success')], config=dict(ray_initializer=1))

    names = [R+x+'.csv' for x in ('ray_status','ray_failures','ray_paths','events','grid','context','accepted_events','accepted_grid')]
    names += [S+x+'.csv' for x in ('accepted_events','accepted_grid','delta','weights','context')]
    names += [L, 'loc1d_last_accepted_events.csv', 'loc1d_last_accepted_grid.csv']
    for name in names:
        add('missing_' + name[:-4], steps=[dict(op='remove', file=name)])
    for name in ('loc1d_iteration_99_trials.csv', 'loc1d_iteration_99_solve_delta.csv',
                 'loc1d_rejected_trial_it_0_ls_7_context.csv', 'loc1d_last_accepted_extra.csv'):
        add('orphan_' + name[:-4], steps=[dict(op='orphan', file=name)])
    add('fatal_prefix', steps=[dict(op='orphan', file='loc1d_failed_forward_context.csv')])
    for name in (R+'ray_status.csv', R+'ray_paths.csv', S+'delta.csv', L, 'initial_events.csv'):
        add('symlink_' + name[:-4], steps=[dict(op='symlink', file=name)])
    add('dangling_symlink', steps=[dict(op='symlink', file=R+'grid.csv', dangling=True)])
    for name in (R+'ray_status.csv', S+'weights.csv', H, 'observations.csv'):
        add('duplicate_header_' + name[:-4], steps=[dict(op='duplicate_header', file=name)])
    add('extra_csv_cell', steps=[dict(op='extra_cell', file=R+'ray_status.csv')])

    mutations = [
        ('delta_duplicate_index', S+'delta.csv', 1, 'parameter_index', '0'),
        ('delta_increment', S+'delta.csv', 3, 'increment', '.125'),
        ('delta_reference', S+'delta.csv', 0, 'reference_x', '.25'),
        ('delta_component', S+'delta.csv', 0, 'component', 't'),
        ('delta_event', S+'delta.csv', 0, 'event', '1'),
        ('delta_origin', S+'delta.csv', 0, 'source_origin_resource_id', 'wrong'),
        ('delta_nonfinite', S+'delta.csv', 0, 'increment', 'nan'),
        ('trial_source', R+'events.csv', 0, 't', '.3'),
        ('accepted_source', R+'accepted_events.csv', 0, 'x', '.25'),
        ('accepted_model', R+'accepted_grid.csv', 0, 'v', '5.01'),
        ('trial_grid_axis', R+'grid.csv', 0, 'x', '-1.99'),
        ('trial_grid_value', R+'grid.csv', 0, 'v', '5.01'),
        ('trial_event_id', R+'events.csv', 0, 'id', '1'),
        ('trial_event_native', R+'events.csv', 0, 'event_resource_id', 'wrong'),
        ('trial_coordinate_basis', R+'events.csv', 0, 'coordinate_basis', 'final'),
        ('source_outside', R+'events.csv', 0, 'x', '9'),
        ('context_phase', R+'context.csv', 0, 'phase', 'final'),
        ('context_precision', R+'context.csv', 0, 'significant_digits', '12'),
        ('context_derivatives', R+'context.csv', 0, 'derivatives_requested', '1'),
        ('context_trial', R+'context.csv', 0, 'line_search_trial', '1'),
        ('context_mode', R+'context.csv', 0, 'mode', 'dd'),
        ('context_initializer', R+'context.csv', 0, 'initialization_required', '1'),
        ('solve_columns', S+'context.csv', 0, 'columns', '9'),
        ('solve_source_columns', S+'context.csv', 0, 'source_columns', '4'),
        ('solve_model_columns', S+'context.csv', 0, 'model_columns', '1'),
        ('solve_iteration', S+'context.csv', 0, 'iteration', '1'),
        ('solve_stage', S+'context.csv', 0, 'stage', '1'),
        ('solve_before', S+'context.csv', 0, 'objective_before', '.1'),
        ('solve_lsqr_iterations', S+'context.csv', 0, 'lsqr_iterations', '21'),
        ('solve_lsqr_flag', S+'context.csv', 0, 'lsqr_converged', '0'),
        ('solve_lsqr_residual', S+'context.csv', 0, 'lsqr_relative_normal_residual', '.1'),
        ('solve_smoothing', S+'context.csv', 0, 'smoothing_weight', '2'),
        ('solve_damping', S+'context.csv', 0, 'damping_parameter', '.2'),
        ('solve_weight_basis', S+'context.csv', 0, 'weight_basis', 'recomputed at trial'),
        ('solve_objective_basis', S+'context.csv', 0, 'objective_basis', 'includes damping'),
        ('weight_index', S+'weights.csv', 1, 'observation_index', '0'),
        ('weight_second_epoch', S+'weights.csv', 2, 'station_j', '0'),
        ('weight_original_second_epoch', S+'weights.csv', 2, 'original_station_j', '0'),
        ('weight_original_pick', S+'weights.csv', 0, 'original_pick_i_resource_id', 'wrong'),
        ('weight_original_note', S+'weights.csv', 0, 'original_note', 'unquoted replacement'),
        ('weight_original_collision', S+'weights.csv', 0, 'original_current_residual', '0'),
        ('weight_value', S+'weights.csv', 0, 'value', '0'),
        ('weight_negative', S+'weights.csv', 0, 'fixed_row_multiplier', '-1'),
        ('weight_nan', S+'weights.csv', 0, 'current_residual', 'nan'),
        ('status_second_epoch', R+'ray_status.csv', 2, 'receiver_metadata_epoch_start', '1980-01-01T00:00:00Z'),
        ('status_blank_location', R+'ray_status.csv', 2, 'receiver_location_code', '--'),
        ('status_seed', R+'ray_status.csv', 2, 'receiver_channel_seed_id', 'XX.MOCK.01.HHZ'),
        ('status_origin', R+'ray_status.csv', 2, 'source_origin_resource_id', 'wrong'),
        ('status_position', R+'ray_status.csv', 2, 'source_x', '0'),
        ('status_origin_time', R+'ray_status.csv', 2, 'source_t', '0'),
        ('status_receiver_position', R+'ray_status.csv', 2, 'receiver_z', '1'),
        ('status_index', R+'ray_status.csv', 2, 'station', '0'),
        ('status_flag_format', R+'ray_status.csv', 2, 'ray_converged', 'false'),
        ('status_hides_failure', R+'ray_status.csv', 2, 'ray_converged', '1'),
        ('status_invents_failure', R+'ray_status.csv', 0, 'ray_converged', '0'),
        ('status_negative_gradient', R+'ray_status.csv', 0, 'ray_projected_gradient', '-1'),
        ('status_nonfinite_gradient', R+'ray_status.csv', 0, 'ray_raw_gradient', 'inf'),
        ('status_nonfinite_time', R+'ray_status.csv', 0, 'ray_time', 'nan'),
        ('status_negative_iterations', R+'ray_status.csv', 0, 'ray_iterations', '-1'),
        ('status_initializer_failure', R+'ray_status.csv', 0, 'ray_initialization_attempted', '1'),
        ('status_derivative_flag', R+'ray_status.csv', 0, 'ray_derivatives_evaluated', '1'),
        ('status_derivative_value', R+'ray_status.csv', 0, 'source_dx', '0'),
        ('status_no_points', R+'ray_status.csv', 2, 'ray_path_points', '0'),
        ('roster_mixed_reason', R+'ray_failures.csv', 0, 'reasons', 'local_stopping_failed;nonfinite_ray'),
        ('roster_wrong_pair', R+'ray_failures.csv', 0, 'event', '0'),
        ('roster_expected_nodes', R+'ray_failures.csv', 0, 'expected_velocity_nodes', '7'),
        ('roster_requested_derivatives', R+'ray_failures.csv', 0, 'derivatives_requested', '1'),
        ('path_epoch', R+'ray_paths.csv', 1, 'receiver_metadata_epoch_end', '1990-01-01T00:00:00Z'),
        ('path_node_index', R+'ray_paths.csv', 1, 'node', '0'),
        ('path_source_endpoint', R+'ray_paths.csv', 0, 'z', '2.9'),
        ('path_receiver_endpoint', R+'ray_paths.csv', -1, 'z', '.1'),
        ('path_outside', R+'ray_paths.csv', 1, 'z', '6'),
        ('path_nan', R+'ray_paths.csv', 1, 'x', 'nan'),
        ('ledger_objective_on_rejection', L, 0, 'objective_after', '0'),
        ('ledger_rejection_evaluated', L, 0, 'objective_evaluated', '1'),
        ('ledger_unknown_status', L, 0, 'status', 'retry'),
        ('ledger_fraction', L, 1, 'step_fraction', '.25'),
        ('ledger_unequal_before', L, 1, 'objective_before', '.1'),
        ('ledger_wrong_trial', L, 1, 'trial', '0'),
        ('ledger_accepted_increase', L, 1, 'objective_after', '1'),
        ('ledger_accepted_not_evaluated', L, 1, 'objective_evaluated', '0'),
        ('ledger_other_prefix', L, 0, 'failure_prefix', 'loc1d_rejected_trial_it_0_ls_1'),
        ('ledger_traversal', L, 0, 'failure_prefix', '../loc1d_rejected_trial_it_0_ls_0'),
        ('ledger_nonrejected_prefix', L, 1, 'failure_prefix', 'loc1d_rejected_trial_it_0_ls_0'),
        ('history_fraction', H, 0, 'step_fraction', '.25'),
        ('history_after', H, 0, 'objective_after', '.1'),
        ('history_before', H, 0, 'objective_before', '.1'),
        ('history_stage', H, 0, 'stage', '1'),
        ('initial_event_id', 'initial_events.csv', 0, 'id', '2'),
        ('initial_station_id', 'stations.csv', 1, 'id', '0'),
        ('observation_bad_i', 'observations.csv', 0, 'i', '2'),
        ('observation_bad_station', 'observations.csv', 0, 'station', '2'),
        ('observation_blank_second_epoch', 'observations.csv', 2, 'station_j', ''),
        ('observation_negative_second_epoch', 'observations.csv', 2, 'station_j', '-1'),
        ('observation_other_second_epoch', 'observations.csv', 2, 'station_j', '2'),
        ('stale_conventional_events', 'loc1d_last_accepted_events.csv', 0, 't', '.1'),
        ('stale_conventional_grid', 'loc1d_last_accepted_grid.csv', 0, 'v', '5.1'),
    ]
    for name, file, row, key, value in mutations:
        add(name, steps=[cell(file, row, key, value)])
    for flag in ('ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint'):
        add('nonlocal_' + flag, steps=[cell(R+'ray_status.csv', 2, flag, '0')])
    for name in (S+'delta.csv', S+'weights.csv', R+'ray_status.csv', R+'ray_paths.csv', R+'ray_failures.csv'):
        for op in ('drop_last', 'duplicate_last', 'reverse'):
            # A single-row roster is unchanged by reversal; avoid a vacuous test.
            if name == R+'ray_failures.csv' and op == 'reverse':
                continue
            add(op+'_'+name[:-4], steps=[dict(op=op, file=name)])
    add('zero_weight_native_ray_omitted', steps=[dict(op='drop_index', file=R+'ray_status.csv', index=1)])
    add('missing_history', steps=[dict(op='empty', file=H)])
    add('missing_matrix', steps=[dict(op='empty', file='loc1d_matrix_preflight.csv')])
    add('matrix_iteration_mismatch', steps=[cell('loc1d_matrix_preflight.csv', 0, 'iteration', '1')])
    add('accepted_not_last', steps=[dict(op='duplicate_last', file=L)])
    add('incomplete_unsuccessful_search', steps=[dict(op='drop_last', file=L)])
    add('objective_rejected_equal', 'worse', steps=[cell(L, 1, 'objective_after', '0.025446381722154902')])
    add('objective_rejected_better', 'worse', steps=[cell(L, 1, 'objective_after', '0')])
    add('too_many_trials', 'worse', steps=[dict(op='duplicate_last', file=L)])
    add('premature_history_end', 'valid_dd', config=dict(iterations=3))
    add('history_past_configured_end', 'valid_dd', config=dict(iterations=1))
    add('wrong_stage_skip', 'valid_dd', steps=[dict(op='stages', iterations=[0, 1, 4])],
        config=dict(iterations=9, stage_length=2))
    add('stage2_must_not_continue', 'valid_dd', steps=[dict(op='stages', iterations=[0, 2, 4, 6])],
        config=dict(iterations=9, stage_length=2))
    add('coordinated_initial_state_shift', steps=[dict(op='shift_initial_snapshot')])
    for name, file, row, key, value in [
        ('joint_model_delta', 'delta', 8, 'increment', '.5'),
        ('joint_model_reference', 'delta', 8, 'reference_v', '5.1'),
        ('joint_model_invents_event', 'delta', 8, 'source_event_resource_id', 'wrong'),
        ('joint_model_index', 'delta', 9, 'node', '0'),
        ('joint_model_type', 'delta', 8, 'component', 'velocity'),
    ]:
        add(name, 'state', steps=[dict(op='joint_schema'), cell('dd_iteration_0_solve_'+file+'.csv', row, key, value)])
    add('joint_clamp_mismatch', 'state', steps=[dict(op='joint_schema'),
        cell('dd_rejected_trial_it_0_ls_0_events.csv', 0, 'x', '3.9')])
    for variant, good in [('good',True), ('nonzero',False), ('missing',False), ('duplicate',False),
                          ('other_stage',False), ('wrong_source',False), ('missing_source',False)]:
        add('child_source_prefix_'+variant, 'none', good, [dict(op='child_prefix', variant=variant)], kind='prefix')
    assert len({t['name'] for t in tests}) == len(tests)
    return tests


def config_read(path):
    return {line.split()[0]: float(line.split()[1]) for line in path.read_text().splitlines() if line.strip()}


def stage_fixture(data, op):
    """Declared saved-schema fixture, never an assertion of C++ execution."""
    hfields, hs = table(data/'dd_history.csv')
    mfields, ms = table(data/'dd_matrix_preflight.csv')
    lfields, ls = table(data/'dd_iteration_0_trials.csv')
    for p in data.glob('dd_iteration_*'):
        p.unlink()
    new_h, new_m = [], []
    for it in op['iterations']:
        stage = min(2, it//2)
        h = dict(hs[0], iteration=str(it), stage=str(stage), step_fraction='0', objective_before='1', objective_after='1')
        new_h.append(h); new_m.append(dict(ms[0], iteration=str(it)))
        status = op.get('status', 'objective_rejected')
        records = [dict(ls[0], iteration=str(it), stage=str(stage), trial=str(q),
                        step_fraction=format(math.ldexp(1., -q), '.17g'), status=status,
                        objective_evaluated='1' if status == 'objective_rejected' else '0',
                        objective_before='1', objective_after='2' if status == 'objective_rejected' else '', failure_prefix='')
                   for q in range(12)]
        write_table(data/('dd_iteration_'+str(it)+'_trials.csv'), lfields, records)
    write_table(data/'dd_history.csv', hfields, new_h)
    write_table(data/'dd_matrix_preflight.csv', mfields, new_m)


def joint_schema(data):
    """Keep actual DD ls0/state/solve tables; invent only a hypothetical ending."""
    fields, records = table(data/'dd_iteration_0_trials.csv')
    trial = dict(records[1], status='accepted', objective_evaluated='1', objective_after='0', failure_prefix='')
    write_table(data/'dd_iteration_0_trials.csv', fields, [records[0], trial])
    for p in data.glob('dd_rejected_trial_it_0_ls_*'):
        if not p.name.startswith('dd_rejected_trial_it_0_ls_0_'):
            p.unlink()
    fields, hs = table(HERE/'fixtures/half/loc1d_history.csv')
    _, context = table(data/'dd_iteration_0_solve_context.csv')
    h = dict(hs[0], objective_after='0')
    for key in ('lsqr_iterations', 'lsqr_converged'):
        h[key] = context[0][key]
    h['lsqr_relative_normal_residual'] = format(float(context[0]['lsqr_relative_normal_residual']), '.12g')
    write_table(data/'dd_history.csv', fields, [h])


def mutate(data, op):
    action = op['op']
    if action == 'cell':
        cells(data/op['file'], [(op['row'], op['key'], op['value'])]); return
    if action == 'joint_schema':
        joint_schema(data); return
    if action == 'stages':
        stage_fixture(data, op); return
    if action == 'shift_initial_snapshot':
        # Coordinated t shift leaves all geometry/rays untouched but breaks the
        # known iteration-zero origin-time state. No initial input is changed.
        for name in (S+'accepted_events.csv', R+'accepted_events.csv', 'loc1d_last_accepted_events.csv', R+'events.csv'):
            fields, records = table(data/name)
            for row in records: row['t'] = format(float(row['t'])+1, '.17g')
            write_table(data/name, fields, records)
        for name, key in ((S+'delta.csv', 'reference_t'), (R+'ray_status.csv', 'source_t')):
            fields, records = table(data/name)
            for row in records: row[key] = format(float(row[key])+1, '.17g')
            write_table(data/name, fields, records)
        return
    if action == 'initializer_success':
        fields, records = table(data/(R+'ray_status.csv'))
        for row in records:
            row['ray_initialization_attempted'] = row['ray_initialization_succeeded'] = '1'
        write_table(data/(R+'ray_status.csv'), fields, records)
        cells(data/(R+'context.csv'), [(0,'initialization_required','1')]); return
    if action == 'absent_station_j':
        # Legacy absence means use station itself. This fixture's differential
        # uses station0/epoch1, so adapt i-side epoch to1 in both original and
        # frozen weight rows; absolute rows still provide all three ray keys.
        fields, records = table(data/'observations.csv')
        for row in records:
            if int(row['j']) >= 0:
                row['station'] = row['station_j']
                row['metadata_epoch_start'], row['metadata_epoch_end'] = '1990-01-01T00:00:00Z', ''
            del row['station_j']
        write_table(data/'observations.csv', [x for x in fields if x != 'station_j'], records)
        fields, weights = table(data/(S+'weights.csv'))
        for row in weights:
            if int(row['j']) >= 0:
                row['station'] = row['station_j']
                row['original_metadata_epoch_start'], row['original_metadata_epoch_end'] = '1990-01-01T00:00:00Z', ''
            del row['original_station_j']
        write_table(data/(S+'weights.csv'), [x for x in fields if x != 'original_station_j'], weights)
        return
    if action == 'child_prefix':
        variant = op['variant']
        completed = [dict(stage='dd_invert', return_code=0)]
        source = {'src/main.cpp': MAIN}
        if variant == 'nonzero': completed[0]['return_code'] = 1
        if variant == 'missing': completed = []
        if variant == 'duplicate': completed += [dict(completed[0])]
        if variant == 'other_stage': completed[0]['stage'] = 'other'
        if variant == 'wrong_source': source['src/main.cpp'] = '0'*64
        if variant == 'missing_source': source = {}
        save(data/'dd_inversion_run_manifest.json', dict(source_sha256=source))
        save(data/'dd_inversion_execution.json', dict(completed_commands=completed))
        return
    path = data/op['file']
    if action == 'remove': path.unlink(); return
    if action == 'orphan': path.write_text('preserved invented orphan\n'); return
    if action == 'symlink':
        target = data/('link_target_'+path.name)
        if not op.get('dangling'): shutil.copyfile(str(path), str(target))
        path.unlink(); path.symlink_to(target.name); return
    if action in ('duplicate_header', 'extra_cell'):
        with path.open(newline='') as stream: raw = list(csv.reader(stream))
        if action == 'duplicate_header':
            for row in raw: row.append(row[0])
        else: raw[1].append('extra')
        with path.open('w', newline='') as stream: csv.writer(stream).writerows(raw)
        return
    fields, records = table(path)
    if action == 'drop_last': records.pop()
    elif action == 'drop_index': records.pop(op['index'])
    elif action == 'duplicate_last': records.append(dict(records[-1]))
    elif action == 'reverse': records.reverse()
    elif action == 'empty': records = []
    else: raise ValueError('Unknown fixture operation '+action)
    write_table(path, fields, records)


def prepare():
    assert not (HERE/'prepared.json').exists() and not (HERE/'source').exists()
    inputs = {}
    candidate = json.loads((CANDIDATE/'prepared.json').read_text())
    for name, digest in candidate['input_sha256'].items(): assert sha(ROOT/name) == digest, name
    for name, digest in candidate['output_sha256'].items(): assert sha(CANDIDATE/name) == digest, name

    def copy(src, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        assert src.is_file() and not src.is_symlink()
        inputs[str(src.relative_to(ROOT))] = sha(src)
        shutil.copyfile(str(src), str(dest))

    for name in ('run_hayward_guarded_inversion.py', 'diagnostics/review_trial_completion.py'):
        copy(CANDIDATE/'after'/name, HERE/'source'/name)
    for name in ('run_loma_analytic_simulation.py', 'run_loma_initial_preflight.py',
                 'diagnostics/review_loma_analytic_simulation.py'):
        copy(ROOT/name, HERE/'source'/name)
    for root, names, prefix in ((CANDIDATE, ('prepared.json','README.md','candidate.patch'), 'candidate'),
                               (CONTROLS, ('prepared.json','summary.json','execution.json','review.json',
                                           'nonzero_objective_review.json'), 'controls')):
        for name in names: copy(root/name, HERE/'evidence'/prefix/name)
    summary = json.loads((CONTROLS/'summary.json').read_text())
    for fixture in FIXTURES:
        for src in sorted((CONTROLS/'results/after'/fixture).iterdir()):
            assert summary['artifact_sha256'][str(src.relative_to(CONTROLS))] == sha(src)
            copy(src, HERE/'fixtures'/fixture/src.name)
    save(HERE/'roster.json', roster())
    # Syntax only: no reviewer imports or fixture mutation during preparation.
    for path in [HERE/'check.py'] + list((HERE/'source').rglob('*.py')):
        ast.parse(path.read_text(), filename=str(path))
    inventory = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    save(HERE/'prepared.json', dict(status='prepared_not_executed', input_sha256=inputs,
         prepared_sha256=inventory, python_executable=str(Path(sys.executable).resolve()),
         python_executable_sha256=sha(Path(sys.executable).resolve()), python_version=sys.version,
         control_count=len(roster()), command=[sys.executable, str((HERE/'check.py').relative_to(ROOT)), '--run'],
         scope='Saved-table and explicit schema-only controls; no compiler, rays, inverse or eligibility change'))
    print(json.dumps(dict(status='prepared_not_executed', controls=len(roster()), prepared_sha256=sha(HERE/'prepared.json'))))


def run():
    prepared = json.loads((HERE/'prepared.json').read_text())
    assert prepared['status'] == 'prepared_not_executed'
    for name, digest in prepared['input_sha256'].items(): assert sha(ROOT/name) == digest, name
    for name, digest in prepared['prepared_sha256'].items(): assert sha(HERE/name) == digest, name
    assert sha(Path(sys.executable).resolve()) == prepared['python_executable_sha256']
    results = HERE/'results'; results.mkdir()  # fresh-only, failed attempts retained
    sys.path.insert(0, str(HERE/'source'))
    review = importlib.import_module('diagnostics.review_trial_completion')
    launcher = importlib.import_module('run_hayward_guarded_inversion')
    records = []
    for test in json.loads((HERE/'roster.json').read_text()):
        target = results/test['name']
        if test['base'] == 'none': target.mkdir()
        else: shutil.copytree(str(HERE/'fixtures'/test['base']), str(target))
        try:
            for op in test['steps']: mutate(target, op)
            if test['kind'] == 'trial':
                cfg = config_read(target/'run.cfg'); cfg.update(test['config'])
                (target/'run.cfg').write_text(''.join(k+' '+format(v,'.17g')+'\n' for k,v in sorted(cfg.items())))
        except Exception:
            save(target/'control_error.json', dict(stage='fixture_preparation', traceback=traceback.format_exc()))
            raise
        outcome = None; error = None; reached = False
        try:
            if test['kind'] == 'trial':
                mode = MODE[test['base']]
                hs = list(review.rows(target/(mode+'_history.csv')))
                ms = list(review.rows(target/(mode+'_matrix_preflight.csv')))
                outcome = review.review_trials(target, mode, cfg, hs, ms)
            else:
                class ReachedRows(Exception): pass
                def stop_at_rows(path):
                    assert path.name == 'initial_events.csv'
                    raise ReachedRows('Verified child/main prefix; no final-table eligibility claim')
                original_rows = launcher.rows
                launcher.rows = stop_at_rows
                try:
                    launcher.check_inverse(target, {})
                except ReachedRows:
                    reached = True
                finally:
                    launcher.rows = original_rows
                assert reached
                outcome = dict(scope='Actual check_inverse child/source prefix only', independent_final_ray_table=False)
        except Exception as exc:
            error = dict(type=type(exc).__name__, message=str(exc))
        accepted = error is None
        passed = accepted == test['expected_accept']
        if not accepted and test['required_error_fragment']:
            passed = passed and test['required_error_fragment'] in error['message']
        result = dict(name=test['name'], expected_accept=test['expected_accept'], observed_accept=accepted,
                      passed=passed, error=error, readback=outcome, base=test['base'],
                      mutated=bool(test['steps'] or test['config']), kind=test['kind'])
        save(target/'result.json', result); records.append(result)
    for name, digest in prepared['input_sha256'].items(): assert sha(ROOT/name) == digest, name
    for name, digest in prepared['prepared_sha256'].items(): assert sha(HERE/name) == digest, name
    files, links = {}, {}
    for p in sorted(results.rglob('*')):
        if p.is_symlink(): links[str(p.relative_to(HERE))] = os.readlink(str(p))
        elif p.is_file(): files[str(p.relative_to(HERE))] = sha(p)
    summary = dict(status='passed' if all(r['passed'] for r in records) else 'failed_controls_preserved',
        prepared_sha256=sha(HERE/'prepared.json'), controls=records, controls_passed=sum(r['passed'] for r in records),
        controls_total=len(records), artifact_sha256=files, intentional_symlinks=links,
        scope='Saved-table readback only; prefix seam stops before final tables; no native/forward/inverse execution',
        limitations=['Schema-only completions are invented table contracts, not successful C++ executions.',
                     'Saved residuals and multipliers are not recomputed from forward rays.',
                     'No independently tabulated all-success final full-ray gate exists.',
                     'Current eligibility is unchanged and prospective candidate remains unadopted.'])
    save(HERE/'summary.json', summary)
    print(json.dumps(dict(status=summary['status'], passed=summary['controls_passed'], total=len(records),
                          summary_sha256=sha(HERE/'summary.json'))))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    if not __debug__: raise RuntimeError('Do not disable integrity assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true'); group.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.prepare: prepare()
    else: sys.exit(run())
