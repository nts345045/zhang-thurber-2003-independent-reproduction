#!/usr/bin/env python3
"""Independent saved-result readback. Does not import or execute the reviewer."""
import ast
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHECKS = ROOT/'data/development/hayward_trial_completion_checks_002'
PRIOR = ROOT/'data/development/hayward_trial_completion_checks_001'
CANDIDATE = ROOT/'data/development/hayward_trial_completion_candidate_002'
JOINT = ROOT/'data/development/hayward_old_kernel_trial_backtracking_integration_checks_002'
NUMERIC = {'id','x','y','z','t'}
FAILED = 'independent failed forward evaluation at recorded coordinates; see companion context for evaluation phase'
INPUTS = {}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def pin(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    name = str(path.relative_to(ROOT)); digest = sha(path)
    assert name not in INPUTS or INPUTS[name] == digest
    INPUTS[name] = digest
    return digest


def load(path):
    pin(path)
    return json.loads(path.read_text())


def table(path):
    pin(path)
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
        records = list(reader)
    assert all(None not in r and None not in r.values() for r in records)
    return records


def verify(parent, entries):
    for name, digest in entries.items(): assert pin(parent/name) == digest, name


def number(value):
    x = float(value); assert math.isfinite(x)
    return x


def identity(row, original, prefix='', basis=None):
    count = 0
    for key, value in original.items():
        if key not in NUMERIC:
            expected = basis if key == 'coordinate_basis' and basis is not None else value
            assert row[prefix+key] == expected, prefix+key
            count += 1
    return count


def equal_state(actual_e, actual_g, expected_e, expected_g, digits=17):
    assert len(actual_e) == len(expected_e) and len(actual_g) == len(expected_g)
    for actual, expected in zip(actual_e, expected_e):
        assert actual['id'] == expected['id']
        for axis in 'xyzt': assert number(actual[axis]) == float(format(float(expected[axis]), '.'+str(digits)+'g'))
    for actual, expected in zip(actual_g, expected_g):
        for axis in 'xyzv': assert number(actual[axis]) == float(format(float(expected[axis]), '.'+str(digits)+'g'))


def increment(events, grid, delta, step, bounds):
    out_e = [dict(e) for e in events]; out_g = [dict(g) for g in grid]
    for i, e in enumerate(out_e):
        for k, axis in enumerate('xyz'):
            e[axis] = min(bounds[axis][1], max(bounds[axis][0], number(events[i][axis])+step*delta[4*i+k]))
        e['t'] = number(events[i]['t'])+step*delta[4*i+3]
    for j, g in enumerate(out_g): g['v'] = number(grid[j]['v'])*math.exp(-step*delta[4*len(events)+j])
    return out_e, out_g


def joint_readback():
    source = JOINT/'results/inversion_gate/trial_backtracking'
    frozen = CHECKS/'fixtures/real_joint_dd'
    data = CHECKS/'results/intact_real_joint_dd'
    files = {p.name for p in source.iterdir() if p.is_file()}
    assert files == {p.name for p in frozen.iterdir()}
    for name in files:
        assert pin(source/name) == pin(frozen/name)
        if name != 'run.cfg': assert pin(source/name) == pin(data/name)
    initial = table(data/'initial_events.csv'); stations = table(data/'stations.csv')
    initial_g = table(data/'initial_grid.csv'); obs = table(data/'observations.csv')
    assert [r['id'] for r in initial] == ['0','1'] and [r['id'] for r in stations] == ['0','1']
    assert stations[0]['channel_seed_id'] == stations[1]['channel_seed_id']
    assert stations[0]['metadata_epoch_start'] != stations[1]['metadata_epoch_start']
    support = {(int(r['i']),int(r['station'])) for r in obs}
    support |= {(int(r['j']),int(r.get('station_j',r['station']))) for r in obs if int(r['j']) >= 0}
    assert support == {(0,0),(0,1),(1,0),(1,1)}
    bounds = {axis:(min(number(g[axis]) for g in initial_g), max(number(g[axis]) for g in initial_g)) for axis in 'xyz'}
    history = table(data/'dd_history.csv'); assert [r['iteration'] for r in history] == ['0','1']
    previous_e, previous_g = initial, initial_g
    totals = dict(iterations=2, original_observations=len(obs), native_ray_pairs=len(support),
                  model_columns=len(initial_g), source_columns=4*len(initial), rejected_trials=0,
                  failed_ray_instances=0, failed_path_nodes=0, joined_native_cells=0, accepted_fractions=[])
    for it, expected_rejections in enumerate((9,11)):
        pre = 'dd_iteration_'+str(it)+'_solve_'
        accepted = table(data/(pre+'accepted_events.csv')); model = table(data/(pre+'accepted_grid.csv'))
        equal_state(accepted, model, previous_e, previous_g)
        basis = 'independent accepted inversion state at iteration '+str(it)+'; original unscaled solve recorded separately'
        for e, native in zip(accepted, initial): totals['joined_native_cells'] += identity(e,native,basis=basis)
        drows = table(data/(pre+'delta.csv')); assert len(drows) == 16
        delta = [number(r['increment']) for r in drows]
        for q, d in enumerate(drows):
            assert int(d['parameter_index']) == q
            if q < 8:
                i,k = divmod(q,4)
                assert (d['parameter_type'], d['event'], d['node'], d['component']) == ('source',str(i),'','xyzt'[k])
                for axis in 'xyzt': assert number(d['reference_'+axis]) == number(accepted[i][axis])
                totals['joined_native_cells'] += identity(d,initial[i],'source_',basis)
            else:
                j = q-8
                assert (d['parameter_type'],d['event'],d['node'],d['component']) == ('model','',str(j),'log_slowness')
                for axis in 'xyzv': assert number(d['reference_'+axis]) == number(model[j][axis])
                assert all(not value for key,value in d.items() if key.startswith('source_'))
        weights = table(data/(pre+'weights.csv')); assert len(weights) == len(obs)
        for q,(w,o) in enumerate(zip(weights,obs)):
            assert int(w['observation_index']) == q
            for key in ('i','j','station','type'): assert w[key] == o[key]
            assert number(w['value']) == number(o['value'])
            k2 = o.get('station_j',o['station']) if int(o['j']) >= 0 else '-1'
            assert w['station_j'] == k2
            original = {key:value for key,value in o.items() if key not in ('i','j','station','type','value')}
            assert {key[9:]:value for key,value in w.items() if key.startswith('original_')} == original
            assert number(w['fixed_row_multiplier']) >= 0; number(w['current_residual'])
            totals['joined_native_cells'] += len(original)
        ledger = table(data/('dd_iteration_'+str(it)+'_trials.csv'))
        assert len(ledger) == expected_rejections+1
        assert [r['status'] for r in ledger] == ['local_stopping_rejected']*expected_rejections+['accepted']
        objective = number(ledger[0]['objective_before'])
        for ls, row in enumerate(ledger):
            assert (int(row['iteration']),int(row['stage']),int(row['trial'])) == (it,it,ls)
            step = 2.**-ls; assert number(row['step_fraction']) == step
            assert number(row['objective_before']) == objective
            if ls == expected_rejections:
                assert row['objective_evaluated'] == '1' and not row['failure_prefix']
                assert number(row['objective_after']) <= objective
                previous_e, previous_g = increment(accepted,model,delta,step,bounds)
                totals['accepted_fractions'].append(step)
                for field in ('step_fraction','objective_before','objective_after'):
                    assert number(history[it][field]) == float(format(number(row[field]),'.12g'))
                continue
            assert row['objective_evaluated'] == '0' and row['objective_after'] == ''
            stem = 'dd_rejected_trial_it_'+str(it)+'_ls_'+str(ls)+'_'
            e = table(data/(stem+'events.csv')); g = table(data/(stem+'grid.csv'))
            expected_e, expected_g = increment(accepted,model,delta,step,bounds)
            equal_state(e,g,expected_e,expected_g)
            ae = table(data/(stem+'accepted_events.csv')); ag = table(data/(stem+'accepted_grid.csv'))
            equal_state(ae,ag,accepted,model)
            status = table(data/(stem+'ray_status.csv'))
            assert [(int(r['event']),int(r['station'])) for r in status] == sorted(support)
            failed = {}
            for r in status:
                i,k = int(r['event']),int(r['station'])
                totals['joined_native_cells'] += identity(r,initial[i],'source_',FAILED)+identity(r,stations[k],'receiver_')
                for axis in 'xyz':
                    assert number(r['source_'+axis]) == number(e[i][axis])
                    assert number(r['receiver_'+axis]) == number(stations[k][axis])
                assert number(r['source_t']) == number(e[i]['t'])
                for flag in ('ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint'):
                    assert r[flag] == '1'
                assert r['ray_derivatives_evaluated'] == '0'
                assert not any(r[key] for key in ('source_dx','source_dy','source_dz'))
                assert r['ray_initialization_attempted'] == r['ray_initialization_succeeded'] == '0'
                assert r['ray_converged'] in ('0','1')
                if r['ray_converged'] == '0': failed[i,k] = int(r['ray_path_points'])
            roster = table(data/(stem+'ray_failures.csv'))
            assert [(int(r['event']),int(r['station'])) for r in roster] == sorted(failed)
            for r in roster:
                i,k = int(r['event']),int(r['station'])
                assert r['reasons'] == 'local_stopping_failed'
                totals['joined_native_cells'] += identity(r,initial[i],'source_',FAILED)+identity(r,stations[k],'receiver_')
            paths = table(data/(stem+'ray_paths.csv'))
            expected_indices = [(i,k,j) for (i,k),count in sorted(failed.items()) for j in range(count)]
            assert [(int(r['event']),int(r['station']),int(r['node'])) for r in paths] == expected_indices
            for r in paths:
                i,k,j = int(r['event']),int(r['station']),int(r['node'])
                totals['joined_native_cells'] += identity(r,initial[i],'source_',FAILED)+identity(r,stations[k],'receiver_')
                for axis in 'xyz':
                    value = number(r[axis]); assert bounds[axis][0] <= value <= bounds[axis][1]
                    if j == 0: assert value == number(e[i][axis])
                    if j == failed[i,k]-1: assert value == number(stations[k][axis])
            totals['rejected_trials'] += 1
            totals['failed_ray_instances'] += len(failed); totals['failed_path_nodes'] += len(paths)
    assert totals['accepted_fractions'] == [1/512.,1/2048.]
    equal_state(table(data/'dd_events.csv'),table(data/'dd_grid.csv'),previous_e,previous_g,digits=12)
    return totals


def main():
    summary = load(CHECKS/'summary.json'); execution = load(CHECKS/'execution.json')
    prepared = load(CHECKS/'prepared.json'); prelaunch = load(CHECKS/'prelaunch_review.json')
    assert summary['status'] == 'passed' and summary['controls_passed'] == summary['controls_total'] == 190
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    assert execution['summary_sha256'] == pin(CHECKS/'summary.json')
    verify(ROOT, prepared['input_sha256']); verify(CHECKS, prepared['prepared_sha256'])
    verify(CHECKS, summary['artifact_sha256'])
    for name,target in summary['intentional_symlinks'].items():
        assert (CHECKS/name).is_symlink() and os.readlink(str(CHECKS/name)) == target
    assert summary['prepared_sha256'] == pin(CHECKS/'prepared.json')
    prior = load(PRIOR/'summary.json'); old_roster = load(PRIOR/'roster.json'); new_roster = load(CHECKS/'roster.json')
    assert new_roster[:-1] == old_roster
    assert prior['controls_passed'] == 186 and prior['controls_total'] == 189
    current = {r['name']:r for r in summary['controls']}; old = {r['name']:r for r in prior['controls']}
    gaps = {'history_past_configured_end':'History exceeds configured iteration bound',
            'stage2_must_not_continue':'History continues after stage-2 no-update termination',
            'coordinated_initial_state_shift':'Accepted source states differ'}
    assert {r['name'] for r in prior['controls'] if not r['passed']} == set(gaps)
    for name,message in gaps.items():
        assert old[name]['observed_accept'] and not old[name]['expected_accept']
        assert current[name]['passed'] and not current[name]['observed_accept']
        assert current[name]['error']['message'] == message
    for recipe in new_roster:
        result = current[recipe['name']]
        assert result == load(CHECKS/'results'/recipe['name']/'result.json')
        assert result['expected_accept'] == recipe['expected_accept'] and result['passed']
    for name in ('valid_dd','valid_loc1d','half','quarter','worse'):
        assert current['intact_'+name]['observed_accept']
    joint = joint_readback()
    saved = current['intact_real_joint_dd']['readback']
    assert saved['retriable_trials'] == joint['rejected_trials'] == 20
    assert saved['solve_snapshots'] == 2
    assert saved['failed_path_nodes'] == joint['failed_path_nodes']
    assert saved['rejected_native_ray_instances'] == joint['failed_ray_instances']
    before = CANDIDATE/'before/run_hayward_guarded_inversion.py'
    after = CANDIDATE/'after/run_hayward_guarded_inversion.py'
    pin(before); pin(after)
    trees = [ast.parse(p.read_text()) for p in (before,after)]
    functions = [{n.name:n for n in t.body if isinstance(n,ast.FunctionDef)} for t in trees]
    for name in ('reviewed_inputs','configuration'):
        assert ast.dump(functions[0][name]) == ast.dump(functions[1][name])
    values = [{target.id:ast.dump(n.value) for n in t.body if isinstance(n,ast.Assign)
               for target in n.targets if isinstance(target,ast.Name)} for t in trees]
    for name in ('REVIEWED_GUARD_MAIN','LIMITS','SAMPLE_FILES'): assert values[0][name] == values[1][name]
    inverse = functions[1]['check_inverse']
    calls = [n for n in ast.walk(inverse) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id == 'review_trials']
    assert len(calls) == 1
    expected = ast.parse("review_trials(data, 'dd', configuration(data/'run.cfg'), history, matrix)",mode='eval').body
    assert ast.dump(calls[0]) == ast.dump(expected)
    gates = [n for n in ast.walk(inverse) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict'
             and any(k.arg=='independent_final_ray_table' for k in n.keywords)]
    assert len(gates)==1
    assert ast.literal_eval(next(k.value for k in gates[0].keywords if k.arg=='independent_final_ray_table')) is False
    prefix = [r for r in summary['controls'] if r['kind']=='prefix']
    assert len(prefix)==7 and sum(r['observed_accept'] for r in prefix)==1
    assert current['child_source_prefix_good']['readback']['scope']=='Actual check_inverse child/source prefix only'
    for name,digest in INPUTS.items(): assert sha(ROOT/name)==digest, name
    report = dict(status='passed', reviewer='earthscope_discovery',
        controls_summary_sha256=pin(CHECKS/'summary.json'), execution_sha256=pin(CHECKS/'execution.json'),
        source_sha256=sha(Path(__file__).resolve()), source=str(Path(__file__).resolve().relative_to(ROOT)),
        verified_input_files=len(INPUTS), input_sha256=INPUTS, unchanged_original_recipes=189,
        recorded_controls_passed=190, previously_unsafe_acceptances_now_rejected=sorted(gaps),
        actual_joint_dd_saved_readback=joint, actual_launcher_prefix_cases=7,
        eligibility_AST_unchanged=True, actual_review_trials_call_wiring_verified=True,
        scope='Independent saved table/hash/AST readback only; no import of reviewer, ray call, C++ or inversion.',
        limitations=['Prefix seam stops before final tables; this is not a full positive check_inverse execution.',
                    'Exact child/main contract enforces final full gate, but no all-success final ray table is emitted.',
                    'Current weights/residuals are preserved, not independently recomputed from rays.',
                    'Initial scientific/source eligibility remains unchanged; no bridge or real attempt authorized by this review.',
                    'Actual joint fixture is invented and retains its original zero ray-iteration cap.'])
    output = CHECKS/'review.json'
    with output.open('x') as stream: json.dump(report,stream,indent=2,sort_keys=True); stream.write('\n')
    print(json.dumps(dict(status='passed',review_sha256=sha(output),verified_files=len(INPUTS),joint=joint)))


if __name__ == '__main__':
    if not __debug__: raise RuntimeError('Integrity assertions must remain enabled')
    main()
