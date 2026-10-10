#!/usr/bin/env python3
"""Independent saved integration-test readback; no compiler, ray or inverse."""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        assert len(reader.fieldnames) == len(set(reader.fieldnames)), str(path)
        return list(reader)

def numeric_equal(a, b, keys):
    assert len(a) == len(b)
    assert all(float(x[k]) == float(y[k]) for x, y in zip(a, b) for k in keys)

def moved(events, grid, delta, step):
    e, g = [dict(r) for r in events], [dict(r) for r in grid]
    bounds = {k: (min(float(r[k]) for r in grid), max(float(r[k]) for r in grid)) for k in 'xyz'}
    for i, row in enumerate(e):
        for ax, k in enumerate('xyz'):
            row[k] = min(bounds[k][1], max(bounds[k][0], float(row[k]) + step * delta[4*i+ax]))
        row['t'] = float(row['t']) + step * delta[4*i+3]
    for n, row in enumerate(g):
        row['v'] = float(row['v']) * math.exp(-step * delta[4*len(e)+n])
    return e, g

def smoothing(grid, weight):
    axes = {k: sorted(set(float(r[k]) for r in grid)) for k in 'xyz'}
    velocities = {tuple(float(r[k]) for k in 'xyz'): float(r['v']) for r in grid}
    terms = []
    for position, value in velocities.items():
        for ax, k in enumerate('xyz'):
            index = axes[k].index(position[ax])
            if index + 1 == len(axes[k]):
                continue
            other = list(position); other[ax] = axes[k][index+1]
            h = other[ax] - position[ax]
            terms.append((weight * math.log(value / velocities[tuple(other)]) / h) ** 2)
    return math.fsum(terms)

def main():
    prepared = json.loads((HERE / 'prepared.json').read_text())
    summary = json.loads((HERE / 'summary.json').read_text())
    execution = json.loads((HERE / 'execution.json').read_text())
    assert summary['status'] == 'passed' and execution['status'] == 'completed' and execution['return_code'] == 0
    assert execution['summary_sha256'] == sha(HERE / 'summary.json')
    assert summary['prepared_sha256'] == execution['prepared_sha256'] == sha(HERE / 'prepared.json')
    assert len(execution['commands']) == 9 and all(r['return_code'] == 0 for r in execution['commands'])
    pins = {}
    for group, base in [(prepared['original_sha256'], ROOT), (prepared['runtime_sha256'], Path('/')),
                        (prepared['output_sha256'], HERE), (summary['output_sha256'], HERE)]:
        for name, value in group.items():
            path = base / name
            assert sha(path) == value, str(path)
            pins[str(path)] = value
    assert summary['flags'] == prepared['flags'] and summary['compiler_sha256'] == prepared['runtime_sha256'][prepared['compiler']]
    core = rows(HERE / 'results/core/validation.csv')
    assert len(core) == summary['core_checks'] == 48 and all(r['passed'] == '1' for r in core)
    external = summary['components']['external_input']
    assert external['status'] == 'passed' and len(external['checks']) == 11 and not external['inversions_run']
    component = summary['components']['inversion_gate']
    assert component['status'] == 'passed' and component['trial_fixture_outcome'] == 'completed'
    case = HERE / 'results/inversion_gate/trial_backtracking'
    initial = rows(case / 'initial_events.csv'); grid0 = rows(case / 'initial_grid.csv')
    stations = rows(case / 'stations.csv'); observations = rows(case / 'observations.csv')
    history = rows(case / 'dd_history.csv')
    assert len(history) == 2
    expected_e, expected_g = initial, grid0
    total_rejections = path_nodes = native_cells = 0
    snapshots, ledgers = [], []
    for it, expected_count in [(0, 9), (1, 11)]:
        prefix = case / ('dd_iteration_' + str(it) + '_solve')
        ae, ag = rows(Path(str(prefix)+'_accepted_events.csv')), rows(Path(str(prefix)+'_accepted_grid.csv'))
        numeric_equal(ae, expected_e, 'xyzt'); numeric_equal(ag, expected_g, 'xyzv')
        delta_rows = rows(Path(str(prefix)+'_delta.csv')); weights = rows(Path(str(prefix)+'_weights.csv'))
        context = rows(Path(str(prefix)+'_context.csv'))[0]
        delta = [float(r['increment']) for r in delta_rows]
        assert len(delta) == 4*len(initial)+len(grid0) == 16
        assert [int(r['parameter_index']) for r in delta_rows] == list(range(16))
        assert len(weights) == len(observations)
        for q, (row, obs) in enumerate(zip(weights, observations)):
            assert int(row['observation_index']) == q
            for k, v in obs.items():
                if k not in ('i', 'j', 'station', 'type', 'value'):
                    assert row['original_'+k] == v; native_cells += 1
        penalty = smoothing(ag, float(context['smoothing_weight']))
        before = math.fsum(float(r['fixed_row_multiplier'])**2 * float(r['current_residual'])**2 for r in weights) + penalty
        assert abs(before-float(context['objective_before'])) <= 64*sys.float_info.epsilon*max(1., before)
        ledger = rows(case / ('dd_iteration_' + str(it) + '_trials.csv'))
        assert len(ledger) == expected_count + 1
        assert ledger[-1]['status'] == 'accepted' and float(ledger[-1]['step_fraction']) == 2.**(-expected_count)
        for ls, record in enumerate(ledger):
            assert int(record['trial']) == ls and float(record['step_fraction']) == 2.**(-ls)
            if ls == expected_count:
                assert record['objective_evaluated'] == '1' and float(record['objective_after']) <= float(record['objective_before'])
                continue
            assert record['status'] == 'local_stopping_rejected' and record['objective_evaluated'] == '0' and record['objective_after'] == ''
            total_rejections += 1
            stem = case / ('dd_rejected_trial_it_' + str(it) + '_ls_' + str(ls))
            te, tg = rows(Path(str(stem)+'_events.csv')), rows(Path(str(stem)+'_grid.csv'))
            wanted_e, wanted_g = moved(ae, ag, delta, 2.**(-ls))
            numeric_equal(te, wanted_e, 'xyzt'); numeric_equal(tg, wanted_g, 'xyzv')
            numeric_equal(rows(Path(str(stem)+'_accepted_events.csv')), ae, 'xyzt')
            numeric_equal(rows(Path(str(stem)+'_accepted_grid.csv')), ag, 'xyzv')
            status = rows(Path(str(stem)+'_ray_status.csv'))
            assert [(int(r['event']), int(r['station'])) for r in status] == [(0,0),(0,1),(1,0),(1,1)]
            failed = {(int(r['event']), int(r['station'])): int(r['ray_path_points']) for r in status if r['ray_converged']=='0'}
            roster = rows(Path(str(stem)+'_ray_failures.csv'))
            assert failed and [(int(r['event']), int(r['station'])) for r in roster] == sorted(failed)
            assert all(r['reasons'] == 'local_stopping_failed' for r in roster)
            for r in status:
                i, k = int(r['event']), int(r['station'])
                assert all(r[n]=='1' for n in ('ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint'))
                assert r['ray_derivatives_evaluated']=='0' and all(r['source_d'+ax]=='' for ax in 'xyz')
                for field in ('event_resource_id','origin_resource_id'):
                    assert r['source_'+field]==initial[i][field]; native_cells += 1
                for field, value in stations[k].items():
                    if field not in ('id','x','y','z','t'):
                        assert r['receiver_'+field]==value; native_cells += 1
                for ax in 'xyz':
                    assert float(r['source_'+ax])==float(te[i][ax]) and float(r['receiver_'+ax])==float(stations[k][ax])
                assert float(r['source_t'])==float(te[i]['t'])
            paths = rows(Path(str(stem)+'_ray_paths.csv'))
            expected_nodes = [(i,k,n) for (i,k), count in sorted(failed.items()) for n in range(count)]
            assert [(int(r['event']),int(r['station']),int(r['node'])) for r in paths] == expected_nodes
            for r in paths:
                i,k,n=int(r['event']),int(r['station']),int(r['node'])
                assert r['source_event_resource_id']==initial[i]['event_resource_id'] and r['receiver_channel_seed_id']==stations[k]['channel_seed_id']
                for ax in 'xyz':
                    value=float(r[ax]); assert math.isfinite(value)
                    assert min(float(a[ax]) for a in grid0)<=value<=max(float(a[ax]) for a in grid0)
                    if n==0:assert value==float(te[i][ax])
                    if n==failed[(i,k)]-1:assert value==float(stations[k][ax])
            path_nodes += len(paths)
        expected_e, expected_g = moved(ae, ag, delta, float(ledger[-1]['step_fraction']))
        snapshots.append((ae,ag,weights,context)); ledgers.append(ledger)
    final_e, final_g = rows(case / 'dd_events.csv'), rows(case / 'dd_grid.csv')
    for saved, wanted, keys in [(final_e,expected_e,'xyzt'),(final_g,expected_g,'xyzv')]:
        assert all(float(a[k])==float(format(float(b[k]),'.12g')) for a,b in zip(saved,wanted) for k in keys)
    # Iteration1's 17-digit current residuals independently expose the accepted
    # iteration0 action. Reuse iteration0 fixed weights, not the new stage's.
    weights0, weights1 = snapshots[0][2], snapshots[1][2]
    after0 = math.fsum(float(a['fixed_row_multiplier'])**2 * float(b['current_residual'])**2 for a,b in zip(weights0,weights1))
    after0 += smoothing(snapshots[1][1], float(snapshots[0][3]['smoothing_weight']))
    saved_after0 = float(ledgers[0][-1]['objective_after'])
    assert abs(after0-saved_after0) <= 64*sys.float_info.epsilon*max(1.,after0)
    assert total_rejections == component['rejected_trial_count'] == 20
    assert not list(case.glob('dd_failed_forward*'))
    for name, value in pins.items():assert sha(Path(name))==value,name
    result = {'status':'passed','reviewer':'scientific_audit','summary_sha256':sha(HERE/'summary.json'),
              'execution_sha256':sha(HERE/'execution.json'),'source_sha256':sha(Path(__file__)),
              'verified_pins':len(pins),'executed_artifact_pins':len(summary['output_sha256']),
              'core_checks':48,'external_input_categories':11,'actual_trial_fixture':component,
              'accepted_step_fractions':[float(r[-1]['step_fraction']) for r in ledgers],
              'failed_path_nodes_checked':path_nodes,'native_metadata_cells':native_cells,
              'first_accepted_objective_independent':{'saved':saved_after0,'reconstructed':after0,'absolute_difference':abs(after0-saved_after0)},
              'scope':'Saved-only source/hash/state/native readback; no compiler, ray or inversion rerun.',
              'limitations':['Invented fixtures only; no real-data recovery or later3Daccuracy claim.','Guard fixture retains ray_iterations=0; passing small trial fractions is its actual observed outcome, not a new tolerance.','Controller completion validation and any real launch require separate review.']}
    with (HERE/'review.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(sha(HERE/'review.json'))

if __name__=='__main__':main()
